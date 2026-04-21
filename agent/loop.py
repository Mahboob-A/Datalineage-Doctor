import asyncio
import json
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

import structlog
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agent.parser import RCAParseError, parse_rca_report
from agent.prompts import SYSTEM_PROMPT, build_user_message
from agent.schemas.report import RCAReport
from agent.tools.registry import RCA_TOOLS, dispatch_tool
from app.config import settings
from app.models import ConfidenceLabel, ToolCallLog

logger = structlog.get_logger(__name__)

CORRECTION_PROMPT = (
    "Your previous output failed schema validation. "
    "Return ONLY valid JSON (no markdown, no prose) with all required fields: "
    "root_cause_summary, confidence_score, confidence_label, evidence_chain, "
    "remediation_steps, timeline_events, blast_radius_consumers, "
    "upstream_nodes_checked, tool_calls_made, agent_iterations. "
    "Use ISO-8601 for timeline_events[].occurred_at."
)

TOOL_COLLECTION_PROMPT = (
    "Before returning the final JSON report, you must gather evidence via tool calls. "
    "Call tools first for lineage, blast radius, DQ results, pipeline status, and "
    "ownership/history where relevant. "
    "After tool results are available, return strict JSON only."
)

TRUNCATION_PROMPT = (
    "Your previous answer was truncated. "
    "Do not repeat prior prose. Return ONLY compact valid JSON, or call the next tool "
    "if more evidence is required."
)


def _parse_triggered_at(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(tz=UTC)


def _result_summary(result: dict[str, object]) -> str:
    raw = json.dumps(result, default=str)
    return raw[:1000]


def _parse_tool_arguments(raw_arguments: object) -> tuple[dict[str, object], str]:
    if isinstance(raw_arguments, dict):
        return raw_arguments, json.dumps(raw_arguments)
    if isinstance(raw_arguments, str):
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {}, raw_arguments
        return parsed if isinstance(parsed, dict) else {}, raw_arguments
    return {}, "{}"


def _tool_cache_key(tool_name: str, args: dict[str, object]) -> str:
    return f"{tool_name}:{json.dumps(args, sort_keys=True, default=str)}"


def _extract_tool_calls(message: object) -> list[dict[str, object]]:
    raw_calls = getattr(message, "tool_calls", None) or []
    parsed_calls: list[dict[str, object]] = []
    for call in raw_calls:
        call_id = getattr(call, "id", "")
        function = getattr(call, "function", None)
        tool_name = getattr(function, "name", "") if function is not None else ""
        raw_arguments = (
            getattr(function, "arguments", "{}") if function is not None else "{}"
        )
        parsed_args, raw_args_as_text = _parse_tool_arguments(raw_arguments)
        parsed_calls.append(
            {
                "id": call_id,
                "name": tool_name,
                "args": parsed_args,
                "raw_arguments": raw_args_as_text,
            }
        )
    return parsed_calls


def _assistant_message_payload(message: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "role": "assistant",
        "content": getattr(message, "content", "") or "",
    }
    tool_calls = _extract_tool_calls(message)
    if tool_calls:
        payload["tool_calls"] = [
            {
                "id": call["id"],
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": call["raw_arguments"],
                },
            }
            for call in tool_calls
        ]
    return payload


def _compact_retry_messages(
    messages: list[dict[str, object]],
    *,
    retry_prompt: str,
) -> None:
    """Append a compact retry instruction without preserving oversized drafts."""
    messages.append({"role": "user", "content": retry_prompt})


def _build_fallback_report(
    table_fqn: str,
    triggered_at: str,
    *,
    reason: str,
    tool_calls_made: int,
    iteration: int,
) -> RCAReport:
    """Build a deterministic LOW-confidence report when the loop cannot complete."""
    event_time = _parse_triggered_at(triggered_at)
    return RCAReport(
        root_cause_summary=(
            "Unable to produce a complete RCA report automatically. "
            f"Reason: {reason}."
        ),
        confidence_score=0.2,
        confidence_label=ConfidenceLabel.LOW,
        evidence_chain=[
            "Agent loop exited through fallback path.",
            "Insufficient validated evidence was available in this run.",
        ],
        remediation_steps=[
            "Re-run the RCA workflow after verifying tool responses.",
            "Inspect tool_call_logs for failed or malformed tool outputs.",
        ],
        timeline_events=[
            {
                "occurred_at": event_time,
                "event_type": "dq_test_failure",
                "entity_fqn": table_fqn,
                "entity_type": "table",
                "description": "Fallback report generated due to loop termination.",
                "sequence": 1,
            }
        ],
        blast_radius_consumers=[],
        upstream_nodes_checked=0,
        tool_calls_made=tool_calls_made,
        agent_iterations=iteration,
    )


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError, APIError)),
)
async def call_llm(client: AsyncOpenAI, messages: list[dict[str, object]]) -> object:
    """Call the OpenAI-compatible chat completion endpoint with retry behavior."""
    return await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=RCA_TOOLS,
        tool_choice="auto",
    )


async def log_tool_call(
    *,
    incident_id: UUID | None,
    tool_name: str,
    input_args: dict[str, object],
    result: dict[str, object],
    duration_ms: int,
    success: bool,
    error_message: str | None,
    iteration: int,
    db_session: AsyncSession | None,
) -> None:
    """Persist a single tool invocation entry for traceability."""
    if db_session is None:
        return
    db_session.add(
        ToolCallLog(
            incident_id=incident_id,
            tool_name=tool_name,
            duration_ms=duration_ms,
            input_args=input_args,
            result_summary=_result_summary(result),
            success=success,
            error_message=error_message,
            iteration=iteration,
        )
    )
    await db_session.flush()


async def run_rca_agent(
    table_fqn: str,
    test_case_fqn: str,
    triggered_at: str,
    db_session: AsyncSession | None,
    incident_id: UUID | None = None,
) -> RCAReport:
    """Run the iterative tool-calling RCA loop and return a validated RCAReport."""
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_client_max_retries,
    )
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_user_message(
                table_fqn=table_fqn,
                test_case_fqn=test_case_fqn,
                triggered_at=triggered_at,
            ),
        },
    ]
    iteration = 0
    tool_calls_made = 0
    correction_sent = False
    tool_collection_prompt_sent = False
    rate_limit_retries = 0
    tool_result_cache: dict[str, dict[str, object]] = {}

    while iteration < settings.llm_max_iterations:
        logger.info(
            "rca_agent_iteration_started",
            table_fqn=table_fqn,
            iteration=iteration,
        )
        try:
            response = await call_llm(client=client, messages=messages)
        except RateLimitError as exc:
            rate_limit_retries += 1
            logger.warning(
                "rca_agent_rate_limited",
                table_fqn=table_fqn,
                iteration=iteration,
                retry=rate_limit_retries,
                max_retries=settings.llm_rate_limit_retries,
                error=str(exc),
            )
            if rate_limit_retries <= settings.llm_rate_limit_retries:
                await asyncio.sleep(settings.llm_rate_limit_backoff_seconds)
                continue
            return _build_fallback_report(
                table_fqn=table_fqn,
                triggered_at=triggered_at,
                reason="LLM rate limit exceeded",
                tool_calls_made=tool_calls_made,
                iteration=iteration + 1,
            )
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            logger.warning(
                "rca_agent_llm_call_failed",
                table_fqn=table_fqn,
                iteration=iteration,
                error=str(exc),
            )
            return _build_fallback_report(
                table_fqn=table_fqn,
                triggered_at=triggered_at,
                reason="LLM API call failed after retries",
                tool_calls_made=tool_calls_made,
                iteration=iteration + 1,
            )

        choices = getattr(response, "choices", [])
        if not choices:
            logger.warning(
                "rca_agent_empty_choices",
                table_fqn=table_fqn,
                iteration=iteration,
            )
            return _build_fallback_report(
                table_fqn=table_fqn,
                triggered_at=triggered_at,
                reason="LLM response contained no choices",
                tool_calls_made=tool_calls_made,
                iteration=iteration + 1,
            )

        choice = choices[0]
        message = getattr(choice, "message", None)
        if message is None:
            logger.warning(
                "rca_agent_missing_message",
                table_fqn=table_fqn,
                iteration=iteration,
            )
            return _build_fallback_report(
                table_fqn=table_fqn,
                triggered_at=triggered_at,
                reason="LLM choice did not include a message",
                tool_calls_made=tool_calls_made,
                iteration=iteration + 1,
            )

        finish_reason = getattr(choice, "finish_reason", "stop")

        if finish_reason == "stop":
            content = getattr(message, "content", "") or ""
            try:
                report = parse_rca_report(content)
            except RCAParseError as exc:
                logger.warning(
                    "rca_agent_parse_failed",
                    table_fqn=table_fqn,
                    iteration=iteration,
                    error=str(exc),
                )
                if tool_calls_made == 0 and not tool_collection_prompt_sent:
                    tool_collection_prompt_sent = True
                    _compact_retry_messages(
                        messages,
                        retry_prompt=TOOL_COLLECTION_PROMPT,
                    )
                    iteration += 1
                    continue
                if correction_sent:
                    return _build_fallback_report(
                        table_fqn=table_fqn,
                        triggered_at=triggered_at,
                        reason="LLM output could not be parsed after correction",
                        tool_calls_made=tool_calls_made,
                        iteration=iteration + 1,
                    )
                correction_sent = True
                _compact_retry_messages(
                    messages,
                    retry_prompt=CORRECTION_PROMPT,
                )
                iteration += 1
                continue

            report.tool_calls_made = max(report.tool_calls_made, tool_calls_made)
            report.agent_iterations = max(report.agent_iterations, iteration + 1)
            return report

        if finish_reason == "tool_calls":
            messages.append(_assistant_message_payload(message))
            for tool_call in _extract_tool_calls(message):
                tool_name = str(tool_call.get("name", ""))
                tool_args = tool_call.get("args", {})
                if not isinstance(tool_args, dict):
                    tool_args = {}
                cache_key = _tool_cache_key(tool_name, tool_args)

                if cache_key in tool_result_cache:
                    cached_result = tool_result_cache[cache_key]
                    result = {
                        "cached": True,
                        "tool": tool_name,
                        "message": (
                            "Identical tool call already ran in this RCA run. "
                            "Reuse the prior result."
                        ),
                    }
                    duration_ms = 0
                    success = "error" not in cached_result
                    error_message = (
                        str(cached_result.get("error")) if not success else None
                    )
                else:
                    started = perf_counter()
                    result = await dispatch_tool(
                        tool_name=tool_name, args=tool_args, db_session=db_session
                    )
                    duration_ms = int((perf_counter() - started) * 1000)
                    success = "error" not in result
                    error_message = str(result.get("error")) if not success else None
                    tool_result_cache[cache_key] = result

                await log_tool_call(
                    incident_id=incident_id,
                    tool_name=tool_name,
                    input_args=tool_args,
                    result=result,
                    duration_ms=duration_ms,
                    success=success,
                    error_message=error_message,
                    iteration=iteration,
                    db_session=db_session,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": json.dumps(result, default=str),
                    }
                )
                tool_calls_made += 1
            iteration += 1
            continue

        logger.warning(
            "rca_agent_unknown_finish_reason",
            table_fqn=table_fqn,
            iteration=iteration,
            finish_reason=finish_reason,
        )
        if finish_reason == "length":
            _compact_retry_messages(messages, retry_prompt=TRUNCATION_PROMPT)
        iteration += 1

    logger.warning(
        "rca_agent_max_iterations_reached",
        table_fqn=table_fqn,
        max_iterations=settings.llm_max_iterations,
    )
    return _build_fallback_report(
        table_fqn=table_fqn,
        triggered_at=triggered_at,
        reason="Maximum iteration limit reached",
        tool_calls_made=tool_calls_made,
        iteration=iteration,
    )

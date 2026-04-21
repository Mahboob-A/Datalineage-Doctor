# Agent Module Implementation Guide

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## What This Module Owns

The `agent/` directory owns all reasoning logic. This includes the OpenAI-compatible tool-calling loop, the tool registry, tool function implementations, the system prompt, the `RCAReport` output schema, and the notification dispatch (Slack + OM incident creation). It does not own Celery task management (that is `worker/`) or direct HTTP calls to OpenMetadata (that is `om_client/`).

**Read `knowledge/services/worker.md` when:** you need to understand how an RCA run is triggered, how concurrency is managed, how retries are configured, or how the agent's return value is persisted. The worker is the caller; this module is the reasoner.

---

## Directory Structure

```
agent/
├── __init__.py
├── loop.py               # The tool-calling loop — run_rca_agent() lives here
├── prompts.py            # System prompt constant and user message builder
├── parser.py             # Parses the LLM final message into RCAReport
├── notifications.py      # Slack notification and OM incident creation
│
├── tools/
│   ├── __init__.py
│   ├── registry.py       # RCA_TOOLS list (OpenAI tool schema dicts) + dispatch()
│   ├── lineage.py        # get_upstream_lineage, calculate_blast_radius
│   ├── quality.py        # get_dq_test_results
│   ├── pipeline.py       # get_pipeline_entity_status
│   ├── ownership.py      # get_entity_owners
│   └── history.py        # find_past_incidents (queries local PostgreSQL)
│
└── schemas/
    ├── __init__.py
    ├── report.py         # RCAReport, TimelineEventInput, BlastRadiusConsumerInput
    └── tool_outputs.py   # Typed return shapes for each tool
```

---

## Key Patterns

### Entry Point — `loop.py`

`run_rca_agent()` is the single public function this module exposes to `worker/`.

```python
async def run_rca_agent(
    table_fqn: str,
    test_case_fqn: str,
    triggered_at: str,
    db_session: AsyncSession,
) -> RCAReport:
    messages = build_initial_messages(table_fqn, test_case_fqn, triggered_at)
    iteration = 0

    while True:
        response = await llm_client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=RCA_TOOLS,
            tool_choice="auto",
        )
        choice = response.choices[0]
        messages.append(choice.message)

        if choice.finish_reason == "stop":
            return parse_rca_report(choice.message.content)

        if choice.finish_reason == "tool_calls":
            for tool_call in choice.message.tool_calls:
                result = await dispatch_tool(tool_call, db_session)
                await log_tool_call(tool_call, result, iteration, db_session)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        iteration += 1
        if iteration >= settings.llm_max_iterations:
            return build_fallback_report(table_fqn, iteration)
```

The loop is intentionally explicit. Every step is visible and testable without inspecting framework internals.

### Tool Registration — `tools/registry.py`

Tools are registered in two structures:

1. `RCA_TOOLS` — the list of OpenAI tool schema dicts passed to the LLM
2. `TOOL_HANDLERS` — a dict mapping tool name strings to their Python handler functions

```python
TOOL_HANDLERS: dict[str, Callable] = {
    "get_upstream_lineage":      get_upstream_lineage,
    "get_dq_test_results":       get_dq_test_results,
    "get_pipeline_entity_status": get_pipeline_entity_status,
    "get_entity_owners":         get_entity_owners,
    "calculate_blast_radius":    calculate_blast_radius,
    "find_past_incidents":       find_past_incidents,
}

async def dispatch_tool(
    tool_call: ChatCompletionMessageToolCall,
    db_session: AsyncSession,
) -> dict:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await handler(**args, db_session=db_session)
    except Exception as exc:
        logger.warning("tool_dispatch_failed", tool=name, error=str(exc))
        return {"error": str(exc), "tool": name}
```

Tools never raise to the loop. All errors are returned as dicts.

### Adding a New Tool

1. Write the handler function in the appropriate file under `agent/tools/`
2. Add the OpenAI schema dict to `RCA_TOOLS` in `registry.py`
3. Add the handler to `TOOL_HANDLERS` in `registry.py`
4. Add a typed output schema to `agent/schemas/tool_outputs.py`
5. Update `knowledge/architecture/rca-agent-architecture.md` with the new tool entry
6. Add tests in `tests/test_tools.py`

### Prompt Management — `prompts.py`

The system prompt is a module-level string constant. It is not fetched from a database or external file.

```python
SYSTEM_PROMPT = """
You are a data reliability engineer performing root cause analysis on a data quality incident...
[full prompt — see knowledge/architecture/rca-agent-architecture.md for the strategy]
"""

def build_user_message(table_fqn: str, test_case_fqn: str, triggered_at: str) -> str:
    return (
        f"A data quality test has failed.\n"
        f"Failing table: {table_fqn}\n"
        f"Failing test: {test_case_fqn}\n"
        f"Failure detected at: {triggered_at}\n"
        f"Investigate the root cause using the available tools."
    )
```

To change the prompt: edit `prompts.py` and note the change in a commit message. Do not move prompts to a database or external config — that is `[FUTURE]` scope.

### Output Parsing — `parser.py`

The parser extracts a JSON block from the model's final message and validates it against `RCAReport`.

```python
def parse_rca_report(content: str) -> RCAReport:
    try:
        data = extract_json_from_content(content)
        report = RCAReport.model_validate(data)
        # Always recalculate the label from the score — never trust the model's label field
        report.confidence_label = derive_confidence_label(report.confidence_score)
        return report
    except (ValidationError, ValueError):
        # Send a correction prompt on first failure — handled in loop.py
        raise RCAParseError(content)
```

### Notifications — `notifications.py`

Both notification calls are fire-and-forget. Failures are caught and logged.

```python
async def notify_slack(report: RCAReport, table_fqn: str) -> bool:
    if not settings.slack_enabled or not settings.slack_webhook_url:
        return False
    try:
        payload = build_slack_payload(report, table_fqn)
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.slack_webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("slack_notification_failed", error=str(exc))
        return False
```

---

## Error Handling and Retries

LLM API calls use `tenacity` for retry:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
async def call_llm(messages, tools):
    return await llm_client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
```

Tool failures return error dicts and never abort the loop (see dispatch pattern above).

---

## Logging

Every tool call produces a structured log entry via `structlog`:

```python
logger.info(
    "tool_call_complete",
    tool=tool_name,
    duration_ms=duration,
    success=True,
    result_summary=summarise(result),
    iteration=iteration,
)
```

The `run_rca_agent` function logs loop start, each iteration, and loop termination reason.

---

## Environment Variables

This module reads from `app.config.settings`:
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_ITERATIONS`
- `SLACK_WEBHOOK_URL`
- `SLACK_ENABLED`
- `OM_BASE_URL` (passed through to `om_client`)
- `OM_JWT_TOKEN` (passed through to `om_client`)

---

## When to Read `knowledge/services/worker.md`

Read `worker.md` when:
- Tracing how an RCA run is **triggered** (the Celery task entry point lives in `worker/`)
- Understanding **retry configuration** (Celery task `max_retries`, `default_retry_delay`)
- Understanding how the agent's `RCAReport` return value is **persisted** to PostgreSQL (the worker writes the DB rows after `run_rca_agent()` returns)
- Diagnosing **concurrency or queue** issues (worker pool size, task routing)

Stay in this doc when:
- Modifying tools, the tool registry, or adding new tools
- Changing the system prompt or user message format
- Modifying the output schema or confidence scoring logic
- Debugging agent reasoning or tool call sequences

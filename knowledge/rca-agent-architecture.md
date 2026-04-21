# RCA Agent Architecture

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## Agent Purpose and Boundaries

The RCA agent is the reasoning core of DataLineage Doctor. Its job is to receive a `(table_fqn, test_case_fqn)` pair, use a set of metadata tools to investigate the OpenMetadata knowledge graph, and produce a structured `RCAReport` — a confidence-scored root cause analysis with a timeline, blast radius, and remediation steps.

The agent module (`agent/`) owns:
- The tool-calling loop
- The tool registry
- The system prompt
- The `RCAReport` output schema and parser
- The notification dispatch calls (Slack, OM incident)

The agent module does **not** own:
- HTTP calls to OpenMetadata (delegated to `om_client/`)
- Celery task management (owned by `worker/`)
- Database writes (owned by `worker/` after the agent returns its report)

---

## Why No Framework

LangChain, LangGraph, and similar frameworks are not used. The decision is locked.

The reasons:

1. **One agent, six tools, finite loop** — a framework solves problems this project does not have
2. **Testability** — the agent loop is a plain `while` loop with a list of messages; every step is inspectable without callback hooks
3. **The full reasoning trace is the return value** — the `messages` list after the loop is the audit trail; it is stored, logged, and shown in the dashboard
4. **Provider-agnostic without abstraction** — the OpenAI-compatible standard already provides portability; a framework layer on top adds no benefit

---

## OpenAI-Compatible LLM Integration

The agent uses the `openai` Python SDK with a configurable `base_url`. This makes the system work with any OpenAI-compatible provider without code changes.

**Default provider:** Gemini via its OpenAI-compatible endpoint.

```python
from openai import OpenAI
from app.config import settings

llm_client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    timeout=settings.LLM_TIMEOUT_SECONDS,
)
```

**Provider configuration examples (env vars only — no code changes):**

| Provider | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|
| Gemini (default) | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.0-flash` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| GLM (Zhipu) | `https://open.bigmodel.cn/api/paas/v4` | `glm-4` |
| MiniMax | `https://api.minimax.chat/v1` | `MiniMax-Text-01` |

All five providers support OpenAI-compatible tool calling. The tool schema format is identical across all of them.

---

## Tool-Calling Loop Design

The loop is implemented as an explicit `while` loop in `agent/loop.py`. No recursion, no framework state machine.

```
┌────────────────────────────────────────────────────────┐
│                   run_rca_agent()                       │
│                                                         │
│  messages = [system_prompt, user_incident_context]     │
│  iteration = 0                                          │
│                                                         │
│  while True:                                            │
│    response = llm_client.chat.completions.create(...)  │
│    choice = response.choices[0]                        │
│                                                         │
│    if choice.finish_reason == "stop":                  │
│      ─── parse final message → RCAReport ──────────▶  │
│      break                                              │
│                                                         │
│    if choice.finish_reason == "tool_calls":            │
│      for tool_call in choice.message.tool_calls:       │
│        result = dispatch_tool(tool_call)               │
│        append tool result to messages                  │
│      iteration += 1                                     │
│                                                         │
│    if iteration >= MAX_ITERATIONS:                     │
│      ─── generate fallback LOW-confidence report ───▶  │
│      break                                              │
└────────────────────────────────────────────────────────┘
```

### Messages format

Each pass appends to the `messages` list:

```python
# Assistant turn (with tool calls)
messages.append(choice.message)  # the full assistant message object

# Tool result turns (one per tool call)
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps(tool_result),
})
```

The final `messages` list is the complete reasoning trace. It is stored in `raw_report` on the incident record for debugging and in structured logs.

---

## Tool Registry and Contracts

Tools are registered as a list of OpenAI tool schema dicts in `agent/tools/registry.py`.

### Tool schema pattern

```python
{
    "type": "function",
    "function": {
        "name": "get_upstream_lineage",
        "description": "Traverse the upstream lineage graph from a given table FQN.",
        "parameters": {
            "type": "object",
            "properties": {
                "table_fqn": {
                    "type": "string",
                    "description": "Fully qualified name of the table to start from."
                },
                "depth": {
                    "type": "integer",
                    "description": "How many levels upstream to traverse. Default 3.",
                    "default": 3
                }
            },
            "required": ["table_fqn"]
        }
    }
}
```

### Registered tools

| Tool name | Module | What it calls |
|---|---|---|
| `get_upstream_lineage` | `agent/tools/lineage.py` | `om_client.get_upstream_lineage()` |
| `get_dq_test_results` | `agent/tools/quality.py` | `om_client.get_dq_test_results()` |
| `get_pipeline_entity_status` | `agent/tools/pipeline.py` | `om_client.get_pipeline_status()` |
| `get_entity_owners` | `agent/tools/ownership.py` | `om_client.get_entity_owners()` |
| `calculate_blast_radius` | `agent/tools/lineage.py` | `om_client.get_downstream_lineage()` |
| `find_past_incidents` | `agent/tools/history.py` | SQLAlchemy query on `incidents` table |

### Tool dispatch

```python
def dispatch_tool(tool_call: ChatCompletionMessageToolCall, db_session) -> dict:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    handler = TOOL_REGISTRY.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}

    try:
        return handler(**args, db_session=db_session)
    except Exception as e:
        logger.warning("tool_call_failed", tool=name, error=str(e))
        return {"error": str(e), "tool": name}
```

Tools never raise exceptions to the loop. They return a dict with an `"error"` key on failure. The agent reasons with partial data rather than crashing.

---

## RCA Output Schema

The agent produces a JSON object in its final message. The loop parser deserialises it into a typed `RCAReport` Pydantic model.

```python
class RCAReport(BaseModel):
    root_cause_summary: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_label: ConfidenceLabel
    evidence_chain: list[str] = Field(min_length=1)
    remediation_steps: list[str] = Field(min_length=1)
    timeline_events: list[TimelineEventInput]
    blast_radius_consumers: list[BlastRadiusConsumerInput]
    upstream_nodes_checked: int
    tool_calls_made: int
    agent_iterations: int
```

If the final message cannot be parsed into `RCAReport`, the loop retries the parse with an explicit correction prompt. If the second parse fails, a fallback report is generated.

---

## Confidence Scoring

The confidence score is determined by the agent itself based on its findings. The system prompt instructs the model to set `confidence_score` based on:

- How much corroborating evidence was found (multiple upstream failures = higher)
- Whether a clear causal chain exists (timeline gaps = lower)
- Whether the blast radius could be fully determined (OM 404s = lower)

The `confidence_label` is derived deterministically from the score in the parser:

```python
def derive_confidence_label(score: float) -> ConfidenceLabel:
    if score >= 0.85:
        return ConfidenceLabel.HIGH
    elif score >= 0.60:
        return ConfidenceLabel.MEDIUM
    return ConfidenceLabel.LOW
```

The model's stated score is accepted as-is. The label is always recalculated from the score — the model's label field is ignored.

---

## System Prompt Strategy

The system prompt lives in `agent/prompts.py` as a string constant. Key design principles:

1. **Role framing** — "You are a data reliability engineer performing root cause analysis."
2. **Tool-first instruction** — "Always use the available tools to gather evidence before concluding."
3. **Output contract** — The prompt specifies the exact JSON schema the final message must contain.
4. **Confidence calibration** — The prompt explains the scoring rubric (see above).
5. **Conciseness rule** — The prompt instructs the model to keep `root_cause_summary` under 150 words and each remediation step under 50 words.

The user message contains the incident context: `table_fqn`, `test_case_fqn`, `test_type`, `failure_timestamp`, and `sample_failed_rows` (if available in the webhook payload).

---

## Failure and Retry Behaviour

| Scenario | Handling |
|---|---|
| LLM API timeout | `tenacity` retries the API call up to 3 times with 2s, 4s, 8s backoff |
| LLM returns malformed JSON in final message | Loop sends a correction prompt and retries parse once |
| Loop reaches `MAX_ITERATIONS` (15) | Fallback `RCAReport` produced with `confidence_score=0.1`, `confidence_label=LOW`, summary explains the limit was reached |
| Tool dispatch returns `{"error": ...}` | The error dict is passed back to the LLM as the tool result; agent reasons onward |
| All tools return errors | Agent produces a LOW-confidence report noting data unavailability |

---

## Cost-Control Strategy

- `MAX_ITERATIONS` is capped at 15 to prevent runaway loops
- Tool results are truncated to the most recent N items (configurable per tool) to keep context windows small
- `LLM_TIMEOUT_SECONDS` defaults to 90; providers with higher latency should increase this
- For demo, Gemini 2.0 Flash is used by default — it has a generous free tier and fast responses
- Upstream lineage depth defaults to 3 levels; deeper traversal can be enabled via env var `OM_MAX_LINEAGE_DEPTH`

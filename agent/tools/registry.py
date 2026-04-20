import structlog

from agent.tools.history import find_past_incidents
from agent.tools.lineage import calculate_blast_radius, get_upstream_lineage
from agent.tools.ownership import get_entity_owners
from agent.tools.pipeline import get_pipeline_entity_status
from agent.tools.quality import get_dq_test_results

logger = structlog.get_logger(__name__)

RCA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_upstream_lineage",
            "description": "Get upstream lineage nodes for a table FQN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_fqn": {
                        "type": "string",
                        "description": "Fully qualified table name.",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Requested traversal depth.",
                        "default": 3,
                    },
                },
                "required": ["table_fqn"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dq_test_results",
            "description": "Get recent DQ test execution results for a table FQN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_fqn": {
                        "type": "string",
                        "description": "Fully qualified table name.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 5,
                    },
                },
                "required": ["table_fqn"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_entity_status",
            "description": "Get latest execution status for a pipeline FQN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pipeline_fqn": {
                        "type": "string",
                        "description": "Fully qualified pipeline name.",
                    }
                },
                "required": ["pipeline_fqn"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_owners",
            "description": "Get owner users or teams for an entity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_fqn": {
                        "type": "string",
                        "description": "Fully qualified entity name.",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type: table, pipeline, or dashboard.",
                    },
                },
                "required": ["entity_fqn", "entity_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_blast_radius",
            "description": "Calculate downstream impacted entities for a failing table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_fqn": {
                        "type": "string",
                        "description": "Fully qualified table name.",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Requested downstream traversal depth.",
                        "default": 3,
                    },
                },
                "required": ["table_fqn"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_past_incidents",
            "description": "Find recent complete incidents for a table FQN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_fqn": {
                        "type": "string",
                        "description": "Fully qualified table name.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum incidents to return.",
                        "default": 5,
                    },
                },
                "required": ["table_fqn"],
                "additionalProperties": False,
            },
        },
    },
]

TOOL_HANDLERS = {
    "get_upstream_lineage": get_upstream_lineage,
    "get_dq_test_results": get_dq_test_results,
    "get_pipeline_entity_status": get_pipeline_entity_status,
    "get_entity_owners": get_entity_owners,
    "calculate_blast_radius": calculate_blast_radius,
    "find_past_incidents": find_past_incidents,
}


async def dispatch_tool(tool_name: str, args: dict, db_session) -> dict:
    """Dispatch a named tool and return a structured result or error payload."""
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return await handler(db_session=db_session, **args)
    except Exception as exc:
        logger.warning("tool_dispatch_failed", tool_name=tool_name, error=str(exc))
        return {"error": str(exc), "tool": tool_name}

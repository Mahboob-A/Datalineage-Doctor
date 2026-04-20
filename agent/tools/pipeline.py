import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from om_client.pipeline import get_pipeline_status

logger = structlog.get_logger(__name__)


async def get_pipeline_entity_status(
    pipeline_fqn: str,
    db_session: AsyncSession | None = None,
) -> dict:
    """Return a pipeline status payload for the provided pipeline FQN."""
    _ = db_session
    try:
        status = await get_pipeline_status(pipeline_fqn=pipeline_fqn)
        if isinstance(status, dict):
            return status
        return {"pipeline_status": status.model_dump(mode="json")}
    except Exception as exc:
        logger.warning(
            "get_pipeline_entity_status_failed",
            pipeline_fqn=pipeline_fqn,
            error=str(exc),
        )
        return {"error": str(exc), "tool": "get_pipeline_entity_status"}

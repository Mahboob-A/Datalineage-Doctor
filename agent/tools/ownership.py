import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from om_client.ownership import get_entity_owners as om_get_entity_owners

logger = structlog.get_logger(__name__)


async def get_entity_owners(
    entity_fqn: str,
    entity_type: str,
    db_session: AsyncSession | None = None,
) -> dict:
    """Return owners for a supported entity type and FQN."""
    _ = db_session
    try:
        owners = await om_get_entity_owners(
            entity_fqn=entity_fqn, entity_type=entity_type
        )
        return {"owners": [owner.model_dump(mode="json") for owner in owners]}
    except Exception as exc:
        logger.warning(
            "get_entity_owners_failed",
            entity_fqn=entity_fqn,
            entity_type=entity_type,
            error=str(exc),
        )
        return {"error": str(exc), "tool": "get_entity_owners"}

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from om_client.lineage import get_downstream_lineage as om_get_downstream_lineage
from om_client.lineage import get_upstream_lineage as om_get_upstream_lineage

logger = structlog.get_logger(__name__)


async def get_upstream_lineage(
    table_fqn: str,
    depth: int = 3,
    db_session: AsyncSession | None = None,
) -> dict:
    """Return normalized upstream lineage nodes for a table FQN."""
    _ = db_session
    try:
        normalized_depth = int(depth)
    except (TypeError, ValueError):
        normalized_depth = 3
    try:
        nodes = await om_get_upstream_lineage(
            table_fqn=table_fqn, depth=normalized_depth
        )
        return {
            "upstream_nodes": [
                {
                    "fqn": node.fqn,
                    "entity_type": node.entity_type,
                    "service": node.service,
                    "level": node.level,
                }
                for node in nodes
            ]
        }
    except Exception as exc:
        logger.warning(
            "get_upstream_lineage_failed", table_fqn=table_fqn, error=str(exc)
        )
        return {"error": str(exc), "tool": "get_upstream_lineage"}


async def calculate_blast_radius(
    table_fqn: str,
    depth: int = 3,
    db_session: AsyncSession | None = None,
) -> dict:
    """Return downstream impacted consumers and total affected count."""
    _ = db_session
    try:
        normalized_depth = int(depth)
    except (TypeError, ValueError):
        normalized_depth = 3
    try:
        nodes = await om_get_downstream_lineage(
            table_fqn=table_fqn, depth=normalized_depth
        )
        blast_radius = sorted(
            [
                {
                    "entity_fqn": node.fqn,
                    "entity_type": node.entity_type,
                    "level": node.level,
                    "service": node.service,
                }
                for node in nodes
            ],
            key=lambda item: (item["level"], item["entity_fqn"]),
        )
        return {
            "blast_radius": blast_radius,
            "total_affected": len(blast_radius),
        }
    except Exception as exc:
        logger.warning(
            "calculate_blast_radius_failed", table_fqn=table_fqn, error=str(exc)
        )
        return {"error": str(exc), "tool": "calculate_blast_radius"}

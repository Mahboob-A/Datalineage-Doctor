import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from om_client.quality import get_dq_test_results as om_get_dq_test_results

logger = structlog.get_logger(__name__)


async def get_dq_test_results(
    table_fqn: str,
    limit: int = 5,
    db_session: AsyncSession | None = None,
) -> dict:
    """Return recent data quality test results for the provided table FQN."""
    _ = db_session
    try:
        results = await om_get_dq_test_results(table_fqn=table_fqn, limit=limit)
        return {
            "test_results": [result.model_dump(mode="json") for result in results],
        }
    except Exception as exc:
        logger.warning(
            "get_dq_test_results_failed", table_fqn=table_fqn, error=str(exc)
        )
        return {"error": str(exc), "tool": "get_dq_test_results"}

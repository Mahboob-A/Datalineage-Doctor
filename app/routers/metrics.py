from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from app.services.metrics import get_metrics_payload

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics() -> Response:
    """Expose app-level Prometheus metrics.

    Worker metrics (rca_requests_total, rca_duration_seconds, etc.) are scraped
    directly by Prometheus from worker:9101 as a separate job. No aggregation
    bridge is needed here.
    """
    payload, _ = get_metrics_payload()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

from fastapi import APIRouter, Response

from app.services.metrics import get_metrics_payload

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics() -> Response:
    payload, content_type = get_metrics_payload()
    return Response(content=payload, media_type=content_type)

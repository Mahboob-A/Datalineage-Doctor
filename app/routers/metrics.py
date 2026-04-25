import httpx
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from app.services.metrics import get_metrics_payload

router = APIRouter(tags=["metrics"])

RCA_METRIC_NAMES = (
    "rca_requests_total",
    "rca_duration_seconds",
    "rca_tool_calls_total",
    "rca_confidence_score",
    "blast_radius_size",
    "rca_errors_total",
)


def _strip_rca_metrics(payload: str) -> str:
    filtered: list[str] = []
    for line in payload.splitlines():
        if any(
            line.startswith(f"# HELP {name}")
            or line.startswith(f"# TYPE {name}")
            or line.startswith(f"{name}")
            for name in RCA_METRIC_NAMES
        ):
            continue
        filtered.append(line)
    return "\n".join(filtered)


@router.get("/metrics")
async def metrics() -> Response:
    payload, _ = get_metrics_payload()
    app_metrics = payload.decode("utf-8")

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            worker_response = await client.get("http://worker:9101/metrics")
        if worker_response.status_code == 200:
            merged = f"{_strip_rca_metrics(app_metrics)}\n{worker_response.text}\n"
            return Response(content=merged.encode("utf-8"), media_type=CONTENT_TYPE_LATEST)
    except Exception:
        pass

    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.schemas.webhook import WebhookPayload, WebhookResponse
from app.services.metrics import rca_requests_total
from worker.tasks import rca_task

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/openmetadata", response_model=WebhookResponse, status_code=202)
async def openmetadata_webhook(payload: WebhookPayload) -> WebhookResponse:
    if payload.eventType != "testCaseFailed":
        rca_requests_total.labels(status="ignored").inc()
        return WebhookResponse(status="ignored")

    try:
        task = rca_task.delay(
            table_fqn=payload.entity.fullyQualifiedName,
            test_case_fqn=payload.entity.name,
            triggered_at=datetime.fromtimestamp(payload.timestamp / 1000, tz=UTC).isoformat(),
        )
    except Exception as exc:
        rca_requests_total.labels(status="error").inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    rca_requests_total.labels(status="success").inc()
    return WebhookResponse(status="queued", task_id=task.id)

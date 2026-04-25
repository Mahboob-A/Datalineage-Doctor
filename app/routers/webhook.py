from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.schemas.webhook import WebhookPayload, WebhookResponse
from worker.tasks import rca_task

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/openmetadata", response_model=WebhookResponse, status_code=202)
async def openmetadata_webhook(payload: WebhookPayload) -> WebhookResponse:
    if payload.eventType != "testCaseFailed":
        return WebhookResponse(status="ignored")

    try:
        task = rca_task.delay(
            table_fqn=payload.entity.fullyQualifiedName,
            test_case_fqn=payload.entity.name,
            triggered_at=datetime.fromtimestamp(payload.timestamp / 1000, tz=UTC).isoformat(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return WebhookResponse(status="queued", task_id=task.id)

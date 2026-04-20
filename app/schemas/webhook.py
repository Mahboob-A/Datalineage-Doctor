from pydantic import BaseModel


class WebhookEntity(BaseModel):
    id: str
    name: str
    fullyQualifiedName: str
    entityType: str


class WebhookPayload(BaseModel):
    eventType: str
    entityType: str
    timestamp: int
    entity: WebhookEntity
    changeDescription: dict | None = None


class WebhookResponse(BaseModel):
    status: str
    task_id: str | None = None

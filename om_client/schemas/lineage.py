from pydantic import BaseModel, Field


class LineageNode(BaseModel):
    """Normalized lineage node used by agent tool handlers."""

    fqn: str
    entity_type: str
    service: str
    level: int = Field(ge=1)

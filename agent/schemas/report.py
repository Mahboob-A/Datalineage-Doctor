from datetime import datetime

from pydantic import BaseModel, Field

from app.models import ConfidenceLabel


class TimelineEventInput(BaseModel):
    occurred_at: datetime
    event_type: str
    entity_fqn: str
    entity_type: str
    description: str
    sequence: int


class BlastRadiusConsumerInput(BaseModel):
    entity_fqn: str
    entity_type: str
    level: int
    service: str


class RCAReport(BaseModel):
    root_cause_summary: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_label: ConfidenceLabel
    evidence_chain: list[str]
    remediation_steps: list[str]
    timeline_events: list[TimelineEventInput]
    blast_radius_consumers: list[BlastRadiusConsumerInput]
    upstream_nodes_checked: int
    tool_calls_made: int
    agent_iterations: int

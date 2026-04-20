from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UpstreamLineageOutput(BaseModel):
    """Serialized upstream lineage node returned to the agent."""

    fqn: str
    entity_type: str
    service: str
    level: int


class DQTestResultOutput(BaseModel):
    """Serialized DQ test result returned to the agent."""

    test_case_fqn: str
    result: Literal["Passed", "Failed", "Aborted"]
    timestamp: datetime
    test_type: str


class PipelineTaskStatusOutput(BaseModel):
    """Serialized pipeline task status returned to the agent."""

    name: str
    status: str


class PipelineStatusOutput(BaseModel):
    """Serialized pipeline status returned to the agent."""

    fqn: str
    last_run_status: Literal["Successful", "Failed", "Pending"]
    last_run_at: datetime | None = None
    task_statuses: list[PipelineTaskStatusOutput]


class EntityOwnerOutput(BaseModel):
    """Serialized owner entry returned to the agent."""

    name: str
    email: str
    type: Literal["user", "team"]


class BlastRadiusConsumerOutput(BaseModel):
    """Serialized blast radius consumer returned to the agent."""

    entity_fqn: str
    entity_type: str
    level: int
    service: str


class PastIncidentOutput(BaseModel):
    """Serialized past incident returned to the agent."""

    incident_id: str
    triggered_at: str
    root_cause_summary: str
    confidence_label: Literal["HIGH", "MEDIUM", "LOW"]

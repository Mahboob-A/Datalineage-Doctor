from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TaskStatus(BaseModel):
    """Task-level status for a pipeline execution."""

    name: str
    status: str


class PipelineStatus(BaseModel):
    """Normalized pipeline execution summary."""

    fqn: str
    last_run_status: Literal["Successful", "Failed", "Pending"]
    last_run_at: datetime | None = None
    task_statuses: list[TaskStatus]

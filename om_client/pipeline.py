from datetime import UTC, datetime
from urllib.parse import quote

from om_client.client import OMClient
from om_client.schemas.pipeline import PipelineStatus, TaskStatus


def _parse_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC)
    return None


def _normalize_run_status(value: object) -> str:
    status = str(value or "").lower()
    if "fail" in status:
        return "Failed"
    if "success" in status or "pass" in status:
        return "Successful"
    return "Pending"


def _extract_latest_status(raw_status: object) -> dict[str, object]:
    if isinstance(raw_status, dict):
        return raw_status
    if isinstance(raw_status, list):
        entries = [item for item in raw_status if isinstance(item, dict)]
        if not entries:
            return {}
        return max(
            entries,
            key=lambda item: _parse_timestamp(
                item.get("timestamp")
                or item.get("executionDate")
                or item.get("lastUpdated")
            )
            or datetime.min.replace(tzinfo=UTC),
        )
    return {}


async def get_pipeline_status(pipeline_fqn: str) -> PipelineStatus | dict[str, bool]:
    """Return normalized pipeline execution status for a pipeline FQN."""
    async with OMClient() as om:
        response = await om._get(
            f"/pipelines/name/{quote(pipeline_fqn, safe='')}",
            params={"fields": "pipelineStatus"},
        )

    if not response.get("found", True):
        return {"found": False}

    latest = _extract_latest_status(response.get("pipelineStatus"))
    task_entries = latest.get("taskStatus") or latest.get("taskStatuses") or []
    if not isinstance(task_entries, list):
        task_entries = []

    task_statuses = [
        TaskStatus(
            name=str(task.get("name") or task.get("taskName") or "unknown"),
            status=str(task.get("status") or task.get("executionStatus") or "unknown"),
        )
        for task in task_entries
        if isinstance(task, dict)
    ]

    return PipelineStatus(
        fqn=pipeline_fqn,
        last_run_status=_normalize_run_status(
            latest.get("runStatus")
            or latest.get("status")
            or latest.get("executionStatus")
            or latest.get("pipelineState")
        ),
        last_run_at=_parse_timestamp(
            latest.get("timestamp")
            or latest.get("executionDate")
            or latest.get("lastUpdated")
        ),
        task_statuses=task_statuses,
    )

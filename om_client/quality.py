from datetime import UTC, datetime
from urllib.parse import quote

from om_client.client import OMClient, get_table_fqn_candidates
from om_client.schemas.quality import DQTestResult


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(tz=UTC)
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC)
    return datetime.now(tz=UTC)


def _normalize_result(raw_status: object) -> str:
    status = str(raw_status or "").lower()
    if "fail" in status:
        return "Failed"
    if "pass" in status or "success" in status:
        return "Passed"
    return "Aborted"


async def get_dq_test_results(table_fqn: str, limit: int = 5) -> list[DQTestResult]:
    """Return recent data quality test results for a given table FQN."""
    bounded_limit = max(1, min(limit, 50))
    async with OMClient() as om:
        table = {"found": False}
        resolved_fqn = table_fqn
        for candidate in get_table_fqn_candidates(table_fqn):
            table = await om._get(f"/tables/name/{quote(candidate, safe='')}")
            if table.get("found", True):
                resolved_fqn = candidate
                break
        if not table.get("found", True):
            return []

        response = await om._get(
            "/dataQuality/testCases",
            params={
                "entityFQN": resolved_fqn,
                "limit": bounded_limit,
                "fields": "testCaseResult,testDefinition",
            },
        )

    items = response.get("data", [])
    if not isinstance(items, list):
        return []

    parsed: list[DQTestResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result_obj = item.get("testCaseResult")
        if isinstance(result_obj, list):
            result_data = result_obj[0] if result_obj else {}
        elif isinstance(result_obj, dict):
            result_data = result_obj
        else:
            result_data = {}

        timestamp = _parse_timestamp(
            result_data.get("timestamp")
            or result_data.get("resultTimestamp")
            or result_data.get("testCaseResultTimestamp")
        )
        parsed.append(
            DQTestResult(
                test_case_fqn=str(
                    item.get("fullyQualifiedName")
                    or item.get("testCaseFQN")
                    or item.get("name")
                    or ""
                ),
                result=_normalize_result(
                    result_data.get("testCaseStatus")
                    or result_data.get("status")
                    or result_data.get("result")
                ),
                timestamp=timestamp,
                test_type=str(
                    item.get("testType")
                    or (item.get("testDefinition") or {}).get("name")
                    or "unknown"
                ),
            )
        )

    return sorted(parsed, key=lambda row: row.timestamp, reverse=True)

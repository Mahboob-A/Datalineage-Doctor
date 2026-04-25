import asyncio
import time

import httpx
import structlog

logger = structlog.get_logger(__name__)

LATEST_INCIDENT_URL = "http://app:8000/api/incidents/latest"
MAX_WAIT_SECONDS = 180
POLL_SECONDS = 15


async def main() -> int:
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    baseline_incident_id: str | None = None
    seen_non_complete = False

    async with httpx.AsyncClient(timeout=10) as client:
        while time.monotonic() < deadline:
            try:
                response = await client.get(LATEST_INCIDENT_URL)
                if response.status_code == 200:
                    payload = response.json()
                    incident_id = str(payload.get("incident_id") or "")
                    status = str(payload.get("status", "")).upper()
                    if baseline_incident_id is None:
                        baseline_incident_id = incident_id

                    if status != "COMPLETE":
                        seen_non_complete = True

                    if status == "COMPLETE":
                        if (
                            not seen_non_complete
                            and baseline_incident_id is not None
                            and incident_id == baseline_incident_id
                        ):
                            logger.info(
                                "incident_waiting",
                                incident_id=incident_id,
                                status=status,
                                retry_in_seconds=POLL_SECONDS,
                            )
                            await asyncio.sleep(POLL_SECONDS)
                            continue
                        logger.info(
                            "incident_complete",
                            incident_id=incident_id,
                            status=status,
                        )
                        return 0
                    logger.info(
                        "incident_waiting",
                        incident_id=incident_id,
                        status=status,
                        retry_in_seconds=POLL_SECONDS,
                    )
                else:
                    logger.info(
                        "incident_waiting",
                        status_code=response.status_code,
                        retry_in_seconds=POLL_SECONDS,
                    )
            except Exception as exc:
                logger.info(
                    "incident_waiting",
                    error=str(exc),
                    retry_in_seconds=POLL_SECONDS,
                )
            await asyncio.sleep(POLL_SECONDS)

    logger.error("incident_wait_timeout", timeout_seconds=MAX_WAIT_SECONDS)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

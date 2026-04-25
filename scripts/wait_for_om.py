import asyncio
import os
import time

import httpx
import structlog

logger = structlog.get_logger(__name__)

OM_STATUS_URL = "http://openmetadata_server:8585/api/v1/system/status"
MAX_WAIT_SECONDS = 300
POLL_SECONDS = 15


async def main() -> int:
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    headers = {}
    token = os.getenv("OM_JWT_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=10) as client:
        while time.monotonic() < deadline:
            try:
                response = await client.get(OM_STATUS_URL, headers=headers)
                if response.status_code == 200:
                    logger.info("openmetadata_ready", status_code=response.status_code)
                    return 0
                logger.info(
                    "openmetadata_waiting",
                    status_code=response.status_code,
                    retry_in_seconds=POLL_SECONDS,
                )
            except Exception as exc:
                logger.info(
                    "openmetadata_waiting",
                    error=str(exc),
                    retry_in_seconds=POLL_SECONDS,
                )
            await asyncio.sleep(POLL_SECONDS)

    logger.error("openmetadata_wait_timeout", timeout_seconds=MAX_WAIT_SECONDS)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Poll OpenMetadata until the server is healthy.

Authentication strategy (same priority as OMClient):
  1. OM_JWT_TOKEN env var — used as-is (set for non-expiring bot tokens).
  2. OM_ADMIN_EMAIL + OM_ADMIN_PASSWORD — used to login and obtain a fresh
     token at runtime. No container restart needed when a user token expires.
"""

import asyncio
import os
import time

import httpx
import structlog

logger = structlog.get_logger(__name__)

OM_SERVER_ROOT = os.getenv(
    "OM_SERVER_ROOT",
    # Strip /api/v1 suffix from OM_BASE_URL if set, else use default
    os.getenv("OM_BASE_URL", "http://openmetadata_server:8585/api/v1")
    .rstrip("/")
    .removesuffix("/api/v1"),
)
OM_STATUS_URL = f"{OM_SERVER_ROOT}/api/v1/system/status"
OM_LOGIN_URL = f"{OM_SERVER_ROOT}/api/v1/users/login"

MAX_WAIT_SECONDS = 300
POLL_SECONDS = 15


async def _get_token(http: httpx.AsyncClient) -> str:
    """Return a valid OM bearer token.

    Prefers a static OM_JWT_TOKEN. Falls back to logging in with
    OM_ADMIN_EMAIL + OM_ADMIN_PASSWORD (defaults to the OM demo admin).
    """
    static_token = os.getenv("OM_JWT_TOKEN", "").strip()
    if static_token:
        return static_token

    email = os.getenv("OM_ADMIN_EMAIL", "admin@open-metadata.org")
    password = os.getenv("OM_ADMIN_PASSWORD", "YWRtaW4=")  # base64("admin")

    logger.info("om_wait: no static token set — logging in with admin credentials")
    try:
        resp = await http.post(
            OM_LOGIN_URL,
            json={"email": email, "password": password},
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json()["accessToken"]
        logger.info("om_wait: obtained fresh JWT via login")
        return token
    except Exception as exc:
        logger.warning("om_wait: login attempt failed", error=str(exc))
        return ""


async def main() -> int:
    deadline = time.monotonic() + MAX_WAIT_SECONDS

    async with httpx.AsyncClient(timeout=10) as http:
        # Acquire token once before the polling loop; it will be refreshed
        # on 401 inside the loop if it expires mid-wait (edge case).
        token = await _get_token(http)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        while time.monotonic() < deadline:
            try:
                response = await http.get(OM_STATUS_URL, headers=headers)

                if response.status_code == 401:
                    # Token expired mid-wait — re-acquire and retry immediately
                    logger.info("om_wait: 401 received — refreshing token")
                    token = await _get_token(http)
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    response = await http.get(OM_STATUS_URL, headers=headers)

                if response.status_code == 200:
                    logger.info("openmetadata_ready", status_code=200)
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

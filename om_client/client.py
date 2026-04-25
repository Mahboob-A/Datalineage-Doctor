import asyncio
import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


def get_table_fqn_candidates(table_fqn: str) -> list[str]:
    """Return likely OpenMetadata table FQN variants for compatibility."""
    candidates = [table_fqn]
    parts = table_fqn.split(".")

    if len(parts) == 3:
        service, database, table = parts
        candidates.append(f"{service}.{database}.default.{table}")
    elif len(parts) == 4 and parts[2] == "default":
        service, database, _, table = parts
        candidates.append(f"{service}.{database}.{table}")

    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique.append(candidate)
    return unique


# ---------------------------------------------------------------------------
# Module-level token cache — shared across all OMClient instances in the same
# process so we only call /login once even if multiple tasks start concurrently.
# ---------------------------------------------------------------------------
_cached_token: str = ""
_token_lock = asyncio.Lock()


async def _acquire_token() -> str:
    """Login to OpenMetadata and return a fresh access token.

    Uses the admin credentials from settings. Called once at startup and
    whenever any request gets a 401 response.
    """
    global _cached_token

    base = settings.om_base_url.rstrip("/")
    # Strip the /api/v1 suffix to reach the top-level login endpoint
    server_root = base.removesuffix("/api/v1")
    login_url = f"{server_root}/api/v1/users/login"

    payload = {
        "email": settings.om_admin_email,
        "password": settings.om_admin_password,
    }

    async with httpx.AsyncClient(timeout=30) as http:
        response = await http.post(login_url, json=payload)
        response.raise_for_status()
        data = response.json()

    token = data["accessToken"]
    _cached_token = token
    logger.info("om_client: acquired fresh JWT from OM login endpoint")
    return token


async def _get_token() -> str:
    """Return a valid token, acquiring one if none is cached."""
    global _cached_token

    # 1. Static bot token from .env — never expires, always preferred
    if settings.om_jwt_token:
        return settings.om_jwt_token

    # 2. Already have a cached runtime token
    if _cached_token:
        return _cached_token

    # 3. Need to login — use a lock to prevent thundering herd
    async with _token_lock:
        if _cached_token:          # re-check inside lock
            return _cached_token
        return await _acquire_token()


class OMClient:
    """OpenMetadata HTTP client with shared auth and retry behavior.

    Authentication strategy (in priority order):
      1. Static bot token in settings.om_jwt_token (preferred — never expires).
      2. Runtime login via settings.om_admin_email / om_admin_password.
         The token is cached in-process and refreshed automatically on 401.
    """

    def __init__(self) -> None:
        self.base_url = settings.om_base_url.rstrip("/")
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Open the async HTTP client, acquiring an auth token if needed."""
        token = await _get_token()
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close the async HTTP client on context exit."""
        if self.client is not None:
            await self.client.aclose()

    async def _refresh_auth(self) -> None:
        """Force a fresh token and update the live client's Authorization header.

        Called automatically when any request returns HTTP 401.
        Not used when a static bot token is configured (those never expire).
        """
        global _cached_token
        if settings.om_jwt_token:
            # Static token — nothing we can do here at runtime; surface the error
            logger.error(
                "om_client: 401 received but a static OM_JWT_TOKEN is set. "
                "The token may have expired — replace it with a non-expiring bot token."
            )
            return

        async with _token_lock:
            _cached_token = ""  # invalidate so _acquire_token runs unconditionally
            new_token = await _acquire_token()

        if self.client is not None:
            self.client.headers["Authorization"] = f"Bearer {new_token}"
            logger.info("om_client: Authorization header refreshed with new token")

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def _get(self, path: str, params: dict[str, object] | None = None) -> dict:
        """Issue a GET request; refresh token and retry once on 401."""
        assert self.client is not None
        response = await self.client.get(path, params=params)

        if response.status_code == 401:
            await self._refresh_auth()
            response = await self.client.get(path, params=params)

        if response.status_code == 404:
            return {"found": False}
        if response.status_code in RETRYABLE_STATUS_CODES:
            response.raise_for_status()
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, payload: dict[str, object]) -> dict:
        """Issue a POST request; refresh token and retry once on 401."""
        assert self.client is not None
        response = await self.client.post(path, json=payload)

        if response.status_code == 401:
            await self._refresh_auth()
            response = await self.client.post(path, json=payload)

        if response.status_code == 404:
            return {"found": False}
        response.raise_for_status()
        return response.json()

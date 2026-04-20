import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

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


class OMClient:
    """OpenMetadata HTTP client with shared auth and retry behavior."""

    def __init__(self) -> None:
        self.base_url = settings.om_base_url.rstrip("/")
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Open the async HTTP client for this context."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {settings.om_jwt_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close the async HTTP client on context exit."""
        if self.client is not None:
            await self.client.aclose()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def _get(self, path: str, params: dict[str, object] | None = None) -> dict:
        """Issue a GET request and normalize 404 responses to found=false."""
        assert self.client is not None
        response = await self.client.get(path, params=params)
        if response.status_code == 404:
            return {"found": False}
        if response.status_code in RETRYABLE_STATUS_CODES:
            response.raise_for_status()
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, payload: dict[str, object]) -> dict:
        """Issue a POST request to OpenMetadata and return parsed JSON."""
        assert self.client is not None
        response = await self.client.post(path, json=payload)
        if response.status_code == 404:
            return {"found": False}
        response.raise_for_status()
        return response.json()

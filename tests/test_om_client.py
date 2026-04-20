import httpx
import pytest

from om_client.client import OMClient


class DummyAsyncClient:
    def __init__(self, responses):
        self._responses = responses

    async def get(self, _, params=None):
        _ = params
        return self._responses.pop(0)

    async def post(self, _, json=None):
        _ = json
        return self._responses.pop(0)

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_om_client_404(monkeypatch):
    req = httpx.Request("GET", "http://x/test")
    responses = [httpx.Response(404, request=req)]
    monkeypatch.setattr(
        "om_client.client.httpx.AsyncClient", lambda **_: DummyAsyncClient(responses)
    )

    async with OMClient() as om:
        result = await om._get("/test")
    assert result == {"found": False}


@pytest.mark.asyncio
async def test_om_client_success(monkeypatch):
    req = httpx.Request("GET", "http://x/test")
    responses = [httpx.Response(200, request=req, json={"ok": True})]
    monkeypatch.setattr(
        "om_client.client.httpx.AsyncClient", lambda **_: DummyAsyncClient(responses)
    )

    async with OMClient() as om:
        result = await om._get("/test")
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_om_client_retry_then_success(monkeypatch):
    req = httpx.Request("GET", "http://x/test")
    responses = [
        httpx.Response(503, request=req),
        httpx.Response(200, request=req, json={"ok": True}),
    ]
    monkeypatch.setattr(
        "om_client.client.httpx.AsyncClient", lambda **_: DummyAsyncClient(responses)
    )

    async with OMClient() as om:
        result = await om._get("/test")
    assert result["ok"] is True

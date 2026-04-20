from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import settings
from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> tuple[dict, int] | dict:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "version": "1.0.0", "env": settings.app_env}
    except Exception:
        return Response(
            status_code=503,
            content='{"status":"degraded","checks":{"database":"unreachable"}}',
            media_type="application/json",
        )

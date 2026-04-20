from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.metrics import router as metrics_router
from app.routers.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="DataLineage Doctor", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

app.include_router(dashboard_router)
app.include_router(webhook_router)
app.include_router(health_router)
app.include_router(metrics_router)

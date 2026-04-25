from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
templates = Jinja2Templates(directory="dashboard/templates")

app.include_router(dashboard_router)
app.include_router(webhook_router)
app.include_router(health_router)
app.include_router(metrics_router)


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404 and _wants_html(request):
        return templates.TemplateResponse(
            request=request,
            name="error_404.html",
            context={"request": request, "detail": exc.detail},
            status_code=404,
        )
    error_code = "not_found" if exc.status_code == 404 else "internal_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_code, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if _wants_html(request):
        return templates.TemplateResponse(
            request=request,
            name="error_500.html",
            context={"request": request, "detail": str(exc)},
            status_code=500,
        )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "Unexpected server error"},
    )

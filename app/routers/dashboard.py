from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.incident_store import list_incidents

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="dashboard/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, page: int = 1, db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    try:
        incidents = await list_incidents(db, page=page)
    except Exception:
        incidents = []
    return templates.TemplateResponse(
        request,
        "incidents_list.html",
        {
            "request": request,
            "incidents": incidents,
            "page": page,
        },
    )

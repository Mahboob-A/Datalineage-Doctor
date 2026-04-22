from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.graph_builder import build_graph_data
from app.services.incident_store import (
    get_incident_detail,
    group_blast_radius,
    list_incidents,
)

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="dashboard/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    incidents = await list_incidents(db, page=page, page_size=page_size)
    return templates.TemplateResponse(
        "incidents_list.html",
        {
            "request": request,
            "incidents": incidents,
            "page": page,
        },
    )


@router.get("/incidents/{incident_id}", response_class=HTMLResponse)
async def incident_detail(
    request: Request,
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    detail = await get_incident_detail(db, str(incident_id))
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    incident, timeline_events, blast_radius = detail
    graph_data = build_graph_data(incident, timeline_events, blast_radius)
    return templates.TemplateResponse(
        "incident_detail.html",
        {
            "request": request,
            "incident": incident,
            "timeline_events": timeline_events,
            "blast_radius": blast_radius,
            "blast_radius_grouped": group_blast_radius(blast_radius),
            "graph_data": graph_data,
        },
    )

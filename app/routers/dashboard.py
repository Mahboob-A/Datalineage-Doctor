import asyncio
import sys
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.graph_builder import build_graph_data
from app.services.incident_store import (
    get_incident_detail,
    group_blast_radius,
    latest_incident,
    list_incidents,
)

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="dashboard/templates")

def format_datetime_ist(dt: datetime | str | None) -> str:
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    dt_ist = dt.astimezone(ZoneInfo("Asia/Kolkata"))
    return dt_ist.strftime("%d-%m-%Y %H:%M")

templates.env.filters["format_datetime_ist"] = format_datetime_ist


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    incidents = await list_incidents(db, page=page, page_size=page_size)
    return templates.TemplateResponse(
        request=request,
        name="incidents_list.html",
        context={
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
        request=request,
        name="incident_detail.html",
        context={
            "request": request,
            "incident": incident,
            "timeline_events": timeline_events,
            "blast_radius": blast_radius,
            "blast_radius_grouped": group_blast_radius(blast_radius),
            "graph_data": graph_data,
        },
    )


@router.get("/api/incidents/latest")
async def latest_incident_api(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    incident = await latest_incident(db)
    if incident is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "detail": "No incidents available"},
        )

    return JSONResponse(
        content={
            "incident_id": str(incident.id),
            "status": incident.status.value,
            "table_fqn": incident.table_fqn,
            "test_case_fqn": incident.test_case_fqn,
        }
    )


logger = structlog.get_logger(__name__)


@router.post("/api/demo/trigger")
async def trigger_demo_incident() -> JSONResponse:
    scripts = [
        "scripts/wait_for_om.py",
        "scripts/seed_demo.py",
        "scripts/trigger_demo.py",
    ]

    for script in scripts:
        logger.info("trigger_demo_script_start", script=script)
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(
                "trigger_demo_script_failed",
                script=script,
                returncode=process.returncode,
                stderr=stderr.decode(),
            )
            raise HTTPException(status_code=500, detail=f"Failed to execute {script}")
        logger.info("trigger_demo_script_success", script=script)

    return JSONResponse(
        content={"status": "success", "message": "Demo incident triggered successfully"}
    )

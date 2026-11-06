"""
Reports API Router

Delivers Step 4: Diagnostic Report:
- JSON deliverable for the Vue frontend
- HTML rendered consulting report
- Downloadable PDF deliverable
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse

from ..report.generator import generate_html_report, save_report_files
from ..storage import get_storage
from .advisor import ensure_report_versions, version_summaries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Reports"])


@router.get("/{session_id}/report")
async def get_report_json(session_id: str):
    """
    Step 4: Get Diagnostic Report.
    Returns complete structured JSON for frontend rendering.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.report:
        raise HTTPException(
            status_code=400,
            detail=f"Report has not been generated yet. Current status: {session.status.value}",
        )

    return session.report


@router.get("/{session_id}/report/versions")
async def list_report_versions(session_id: str):
    """Every version of the report (the original plus each approved Synth
    change) and which one is selected."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"session_id": session.id, **version_summaries(session)}


@router.post("/{session_id}/report/versions/{version}/select")
async def select_report_version(session_id: str, version: int):
    """Make `version` the report the page and the PDF export show."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not found")
    ensure_report_versions(session)
    match = next((v for v in session.report_versions if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Report version {version} not found")
    session.report = match["report"]
    session.selected_report_version = version
    await store.update_session(session)
    return {"session_id": session.id, "report": session.report, **version_summaries(session)}


@router.get("/{session_id}/report/html", response_class=HTMLResponse)
async def get_report_html(session_id: str):
    """View styled HTML report in browser."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not found")

    html = generate_html_report(session.report)
    return HTMLResponse(content=html)


@router.get("/{session_id}/report/pdf")
async def download_report_pdf(session_id: str):
    """Download PDF (or HTML deliverable if PDF renderer not installed)."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not found")

    report_path = save_report_files(session_id, session.report)
    if not report_path.exists():
        raise HTTPException(status_code=500, detail="Failed to locate generated report file")

    media_type = "application/pdf" if report_path.suffix == ".pdf" else "text/html"
    return FileResponse(
        path=report_path,
        filename=report_path.name,
        media_type=media_type,
    )

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

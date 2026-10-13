"""
Sessions API Router

Handles repository connection (Git URL + optional token / ZIP upload),
session creation, status polling, and draft saving.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from ..config import settings
from ..ingestion.zip_ingestion import extract_zip_archive
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import (
    CreateSessionRequest,
    CreateSessionResponse,
    DiagnosticSession,
    SessionStatus,
    SessionStatusResponse,
    SourceType,
)
from ..storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: CreateSessionRequest):
    """
    Step 1: Connect Repository.
    Creates a new diagnostic session. Requires privacy & consent acknowledgment.
    """
    if not request.consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Privacy and consent must be accepted to initiate code analysis.",
        )

    if request.source_type == SourceType.GIT and not request.git_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="git_url is required when source_type is 'git'.",
        )

    store = await get_storage()
    session = DiagnosticSession(
        source_type=request.source_type,
        git_url=request.git_url,
        access_token=request.access_token,
        consent_given=request.consent_given,
        status=SessionStatus.CREATED,
    )

    await store.save_session(session)

    # Initialize empty contextual profile
    profile = ContextualProfile(session_id=session.id)
    await store.save_profile(profile)

    return CreateSessionResponse(
        session_id=session.id,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("", response_model=list[SessionStatusResponse])
async def list_sessions():
    """List recent diagnostic sessions."""
    store = await get_storage()
    sessions = await store.list_sessions(limit=20)
    return [
        SessionStatusResponse(
            session_id=s.id,
            status=s.status,
            source_type=s.source_type,
            git_url=s.git_url,
            created_at=s.created_at,
            updated_at=s.updated_at,
            signals_confirmed=s.signals_confirmed,
            report_ready=bool(s.report),
            error_message=s.error_message,
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session(session_id: str):
    """Get status and metadata for a specific session."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        source_type=session.source_type,
        git_url=session.git_url,
        created_at=session.created_at,
        updated_at=session.updated_at,
        signals_confirmed=session.signals_confirmed,
        report_ready=bool(session.report),
        error_message=session.error_message,
    )


@router.post("/{session_id}/upload")
async def upload_zip_archive(session_id: str, archive: UploadFile = File(...)):
    """Upload a ZIP archive for repository analysis."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not archive.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    # Save temp zip
    target_workspace = settings.workspaces_dir / session_id
    temp_zip = settings.data_dir / f"upload_{session_id}.zip"

    try:
        with open(temp_zip, "wb") as f:
            shutil.copyfileobj(archive.file, f)

        workspace_root, repo_info = extract_zip_archive(
            zip_path=temp_zip,
            target_dir=target_workspace,
            original_filename=archive.filename,
        )

        session.workspace_path = str(workspace_root)
        session.source_type = SourceType.ZIP
        await store.update_session(session)

        return {
            "session_id": session.id,
            "filename": archive.filename,
            "status": "uploaded",
            "workspace_path": str(workspace_root),
        }
    finally:
        if temp_zip.exists():
            temp_zip.unlink(missing_ok=True)


class SaveDraftRequest(BaseModel):
    conversation: list[dict] | None = None
    agent_statuses: dict | None = None


@router.put("/{session_id}/draft")
async def save_draft(session_id: str, draft: SaveDraftRequest | None = None):
    """Save mid-diagnostic progress (Figma Feature #7)."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if draft:
        if draft.conversation is not None:
            session.conversation = draft.conversation
        if draft.agent_statuses is not None:
            session.agent_statuses = draft.agent_statuses

    session.status = SessionStatus.DRAFT_SAVED
    await store.update_session(session)

    return {
        "session_id": session.id,
        "status": session.status,
        "saved_at": datetime.utcnow().isoformat(),
    }

"""
Scan & Signals API Router

Handles repository cloning, Light Scanner execution, signal review cards,
signal overriding (PATCH), and signal confirmation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from ..config import settings
from ..ingestion.github_ingestion import clone_github_repo
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import DiagnosticSession, SessionStatus, SourceType
from ..models.scanner_output import ScannerOutput
from ..scanner.scanner import run_light_scanner
from ..storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Scan & Signals"])


async def execute_scan_task(session_id: str):
    """Background task to clone/extract repo and run Light Scanner."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        return

    try:
        workspace_dir = settings.workspaces_dir / session_id

        # Clone if git
        if session.source_type == SourceType.GIT:
            if not session.git_url:
                raise ValueError("git_url is missing for git source")
            session.status = SessionStatus.INGESTING
            await store.update_session(session)

            ws_path, repo_info = clone_github_repo(
                git_url=session.git_url,
                target_dir=workspace_dir,
                access_token=session.access_token,
            )
            session.workspace_path = str(ws_path)
        else:
            ws_path = Path(session.workspace_path)
            repo_info = None

        session.status = SessionStatus.SCANNING
        await store.update_session(session)

        # Run Light Scanner
        scan_result = run_light_scanner(
            workspace_path=ws_path,
            repo_info=repo_info,
        )

        session.scanner_output = scan_result.model_dump(mode="json")
        session.status = SessionStatus.AWAITING_SIGNAL_REVIEW
        session.error_message = None
        await store.update_session(session)

        # Initialize profile scanner signals
        profile = await store.get_profile(session_id)
        if not profile:
            profile = ContextualProfile(session_id=session_id)
        profile.scanner_signals = session.scanner_output
        profile.last_updated = datetime.utcnow()
        await store.save_profile(profile)

        logger.info(f"Scan completed successfully for session {session_id}")

    except Exception as ex:
        logger.exception(f"Scan failed for session {session_id}: {ex}")
        session.status = SessionStatus.ERROR
        session.error_message = str(ex)
        await store.update_session(session)


@router.post("/{session_id}/scan")
async def trigger_scan(session_id: str, background_tasks: BackgroundTasks):
    """
    Step 1 -> 2: Trigger deterministic Light Scanner.
    Clones/ingests repo and extracts all 6 signal groups.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.consent_given:
        raise HTTPException(status_code=400, detail="Consent must be given before scanning")

    session.status = SessionStatus.SCANNING
    await store.update_session(session)

    # For fast PoC execution, can run directly or async
    background_tasks.add_task(execute_scan_task, session_id)

    return {
        "session_id": session.id,
        "status": "scanning",
        "scan_started_at": datetime.utcnow().isoformat(),
        "estimated_duration_ms": 2000,
    }


@router.get("/{session_id}/signals")
async def get_signals(session_id: str):
    """
    Step 2: Review Signals.
    Returns the 6 signal cards formatted directly for the UI.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.scanner_output:
        raise HTTPException(
            status_code=400,
            detail=f"Scanner has not completed yet. Current status: {session.status.value}",
        )

    out = session.scanner_output
    return {
        "session_id": session.id,
        "repository": out.get("repository", {}),
        "scope": out.get("scope", {}),
        "signal_groups": {
            "languages": out.get("languages", {}),
            "size_and_structure": out.get("size_and_structure", {}),
            "stack_and_tooling": out.get("stack_and_tooling", {}),
            "cicd_and_operations": out.get("cicd_and_operations", {}),
            "quality_indicators": out.get("quality_indicators", {}),
            "warnings_and_gaps": out.get("warnings_and_gaps", {}),
        },
    }


class PatchSignalsRequest(BaseModel):
    signal_groups: dict[str, dict]


@router.patch("/{session_id}/signals")
async def patch_signals(session_id: str, patch_data: PatchSignalsRequest):
    """
    Step 2: Edit Signals.
    Allows user to correct or override scanner assumptions before agents run.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session or not session.scanner_output:
        raise HTTPException(status_code=404, detail="Session or signals not found")

    profile = await store.get_profile(session_id)
    if not profile:
        profile = ContextualProfile(session_id=session_id)

    for group_name, update_dict in patch_data.signal_groups.items():
        if group_name in session.scanner_output:
            group = session.scanner_output[group_name]
            if "data" in update_dict:
                group["data"].update(update_dict["data"])
            group["user_edited"] = True
            profile.user_signal_overrides[group_name] = group["data"]

    await store.update_session(session)
    profile.scanner_signals = session.scanner_output
    profile.last_updated = datetime.utcnow()
    await store.save_profile(profile)

    return {
        "session_id": session.id,
        "status": "signals_updated",
        "signal_groups": {
            k: session.scanner_output[k]
            for k in [
                "languages", "size_and_structure", "stack_and_tooling",
                "cicd_and_operations", "quality_indicators", "warnings_and_gaps"
            ]
            if k in session.scanner_output
        },
    }


@router.post("/{session_id}/confirm-signals")
async def confirm_signals(session_id: str):
    """
    Step 2 -> 3: Confirm Signals.
    Locks reviewed signals and transitions to Team Context diagnostic.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.signals_confirmed = True
    session.signals_confirmed_at = datetime.utcnow()
    session.status = SessionStatus.AWAITING_TEAM_CONTEXT
    await store.update_session(session)

    return {
        "session_id": session.id,
        "status": session.status,
        "contextual_profile_initialized": True,
    }

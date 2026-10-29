"""
Scan & Signals API Router

Handles repository cloning, Light Scanner execution, signal review cards,
signal overriding (PATCH), and signal confirmation.
"""

from __future__ import annotations

import logging
import requests
import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from ..config import settings
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import (
    DiagnosticSession,
    SessionStatus,
    SourceType,
    add_notification,
    NotificationType,
    NotificationLevel,
)
from ..storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Scan & Signals"])

async def execute_scan_task(session_id: str):
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        return

    try:
        if not session.scan_id:
            # Nothing has created a scanner job for this session yet — the
            # real (non-mocked) frontend flow goes straight from
            # create-session to POST /scan without ever hitting
            # /sessions/{id}/url, so scan_id is never set upstream. Create
            # the job here instead of assuming it already exists.
            if session.source_type != SourceType.GIT or not session.git_url:
                raise RuntimeError("No scan_id and no git_url to create a scan job from.")

            job_url = f"{settings.scanner_url_base}/job/url"
            job_params = {"url": session.git_url}
            if session.access_token:
                job_params["token"] = session.access_token
            job_response = requests.post(job_url, params=job_params)
            job_response.raise_for_status()
            session.scan_id = job_response.json()["scan_id"]
            await store.update_session(session)

        api_endpoint: str = f"job/?scan_id={session.scan_id}"
        url: str = f"{settings.scanner_url_base}/{api_endpoint}"

        _safety_limit = 100

        for _ in range(0, _safety_limit):
            response: requests.Response = requests.get(url)

            if response.status_code == status.HTTP_204_NO_CONTENT:
                # if not finished yet, wait for a bit and then try again
                # honestly, this is a bit ugly, i just don't know any
                # other way to make it work
                _wait_for_sec = 0.5
                await asyncio.sleep(_wait_for_sec)
                continue

            body: dict = response.json()

            if response.status_code == status.HTTP_400_BAD_REQUEST:
                # failed
                reason: str | None = body.get("reason")
                err_msg = "Unknown (not specified by scanner)" if reason is None else reason

                session.status = SessionStatus.ERROR
                session.error_message = err_msg
                add_notification(
                    session,
                    type=NotificationType.SCAN_FAILED.value,
                    level=NotificationLevel.ERROR.value,
                    title="Scan failed",
                    message=f"Repository scan failed: {err_msg}",
                    route_hint="/",
                )
                await store.update_session(session)
                break

            # The scanner service already runs its own copy of
            # build_scanner_output before returning this response (see
            # scanner/src/core/job_orchestrator.py) — "signalgroup" here is
            # the fully-mapped ScannerOutput, not raw metrics. Re-mapping it
            # through build_scanner_output a second time (as this used to
            # do) fed an already-mapped dict in as if it were raw metrics,
            # so every signal group silently came back empty.
            session.scanner_output = body.get("signalgroup")
            session.status = SessionStatus.AWAITING_SIGNAL_REVIEW
            session.error_message = None
            add_notification(
                session,
                type=NotificationType.SCAN_COMPLETE.value,
                level=NotificationLevel.SUCCESS.value,
                title="Scan complete",
                message="Your repository scan is done — review the signals.",
                route_hint="/signals",
            )
            await store.update_session(session)
    
            # Initialize profile scanner signals
            profile = await store.get_profile(session_id)
            if not profile:
                profile = ContextualProfile(session_id=session_id)
            profile.scanner_signals = session.scanner_output
            profile.last_updated = datetime.utcnow()
            await store.save_profile(profile)
    
            logger.info(f"Scan completed successfully for session {session_id}")

            break

    except Exception as e:
        logger.exception(f"Scan failed for session {session_id}: {e}")
        session.status = SessionStatus.ERROR
        session.error_message = str(e)
        add_notification(
            session,
            type=NotificationType.SCAN_FAILED.value,
            level=NotificationLevel.ERROR.value,
            title="Scan failed",
            message=f"Repository scan failed: {e}",
            route_hint="/",
        )
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

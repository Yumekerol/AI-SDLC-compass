"""
Synth Chat API Router (Step 4)

The chat beside the report talks to Synth — the Synthesizer that wrote the
report. Synth sees the current report and the specialists' findings, answers
questions about them, and when the team asks for a change it drafts one:

1. POST /advisor/messages — one /synthesis/chat round trip to the Agent
   Service. If the message asked for a change, the reply carries a proposal
   with status "drafting" and the revised report is generated in the
   background (/synthesis/revise regenerates the whole report JSON, which
   takes minutes on a local model, so the chat reply is not held up by it).
2. The frontend polls GET /advisor/messages until the proposal is "pending"
   (ready to approve) or "failed".
3. POST /advisor/proposals/{id}/approve adds the revised report as a new
   version and selects it, so the page and the PDF export show it.
   POST /advisor/proposals/{id}/discard drops it.

Versions are listed and selected through reports.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..models.diagnostic_session import ConversationMessage, DiagnosticSession
from ..storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Synth Chat"])

SYNTH_LABEL = "Synthesizer"
_REVISE_TIMEOUT_SECS = 900.0
"""Regenerating the whole report on a local model can take several minutes."""
_STALE_DRAFT_AFTER = timedelta(minutes=20)
"""A draft still "drafting" after this long lost its background task (e.g.
the backend restarted); mark it failed so it stops blocking the chat."""


# ─── Report versions ──────────────────────────────────────────────────

def ensure_report_versions(session: DiagnosticSession) -> None:
    """Sessions whose report predates versioning get it as version 1."""
    if session.report and not session.report_versions:
        session.report_versions = [
            {
                "version": 1,
                "created_at": session.report.get("generated_at")
                or (session.report_generated_at or datetime.utcnow()).isoformat(),
                "label": "Original report",
                "report": session.report,
            }
        ]
        session.selected_report_version = 1
    elif session.report_versions and session.selected_report_version is None:
        session.selected_report_version = session.report_versions[-1]["version"]


def version_summaries(session: DiagnosticSession) -> dict:
    ensure_report_versions(session)
    return {
        "selected_version": session.selected_report_version,
        "versions": [
            {"version": v["version"], "created_at": v.get("created_at"), "label": v.get("label", "")}
            for v in session.report_versions
        ],
    }


# ─── Helpers ──────────────────────────────────────────────────────────

def _public(message: dict) -> dict:
    """A message as the UI sees it: the drafted report stays server-side."""
    proposal = message.get("proposal")
    if not proposal:
        return message
    return {**message, "proposal": {k: v for k, v in proposal.items() if k != "revised_report"}}


def _find_proposal(session: DiagnosticSession, proposal_id: str) -> tuple[dict, dict]:
    for msg in session.advisor_messages:
        proposal = msg.get("proposal")
        if proposal and proposal.get("id") == proposal_id:
            return msg, proposal
    raise HTTPException(status_code=404, detail="Proposal not found")


def _expire_stale_drafts(session: DiagnosticSession) -> bool:
    changed = False
    now = datetime.utcnow()
    for msg in session.advisor_messages:
        proposal = msg.get("proposal")
        if not proposal or proposal.get("status") != "drafting":
            continue
        try:
            started = datetime.fromisoformat(proposal.get("started_at", ""))
        except ValueError:
            started = now - _STALE_DRAFT_AFTER
        if now - started >= _STALE_DRAFT_AFTER:
            proposal["status"] = "failed"
            proposal["error"] = "Drafting the change did not finish. Ask again to retry."
            changed = True
    return changed


def _has_draft_in_progress(session: DiagnosticSession) -> bool:
    return any((m.get("proposal") or {}).get("status") == "drafting" for m in session.advisor_messages)


def _synth_note(content: str) -> dict:
    return ConversationMessage(
        id=f"msg-{uuid4().hex[:8]}", role="agent", agent_label=SYNTH_LABEL, content=content
    ).model_dump(mode="json")


async def _get_session(session_id: str):
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return store, session


# ─── Chat ─────────────────────────────────────────────────────────────

@router.get("/{session_id}/advisor/messages")
async def get_advisor_messages(session_id: str):
    """Full Synth chat history for this session, including the state of any
    drafted report changes (poll this while one is "drafting")."""
    store, session = await _get_session(session_id)
    if _expire_stale_drafts(session):
        await store.update_session(session)
    return {
        "session_id": session.id,
        "messages": [_public(m) for m in session.advisor_messages],
        **version_summaries(session),
    }


class AdvisorMessageRequest(BaseModel):
    content: str


@router.post("/{session_id}/advisor/messages")
async def send_advisor_message(
    session_id: str, request: AdvisorMessageRequest, background_tasks: BackgroundTasks
):
    """Send a message to Synth and get its reply. If it asked for a report
    change, the reply carries a proposal that is drafted in the background."""
    store, session = await _get_session(session_id)
    if not session.report:
        raise HTTPException(status_code=400, detail="The report isn't ready yet, so there's nothing to discuss with Synth.")
    _expire_stale_drafts(session)
    if _has_draft_in_progress(session):
        raise HTTPException(
            status_code=409,
            detail="Synth is still drafting the previous change. Wait for it to finish, then send your message.",
        )
    ensure_report_versions(session)

    history = [
        {"role": m.get("role"), "content": m.get("content", "")}
        for m in session.advisor_messages
        if m.get("content")
    ]
    user_msg = ConversationMessage(id=f"msg-{uuid4().hex[:8]}", role="user", content=request.content)
    session.advisor_messages.append(user_msg.model_dump(mode="json"))

    try:
        async with httpx.AsyncClient(timeout=settings.agents_request_timeout) as client:
            resp = await client.post(
                f"{settings.agents_url}/synthesis/chat",
                json={
                    "report": session.report,
                    "message": request.content,
                    "history": history,
                    "specialist_reports": session.specialist_reports,
                },
            )
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        logger.exception(f"Synth chat failed for session {session_id}: {e}")
        await store.update_session(session)  # keep the user's message even if the reply failed
        raise HTTPException(status_code=502, detail=f"Synth is unavailable: {type(e).__name__}: {e}")

    reply = ConversationMessage(
        id=f"msg-{uuid4().hex[:8]}",
        role="agent",
        agent_label=SYNTH_LABEL,
        content=result.get("answer", ""),
    ).model_dump(mode="json")

    if result.get("change_requested"):
        title = result.get("change_title") or request.content
        reply["proposal"] = {
            "id": f"prop-{uuid4().hex[:8]}",
            "title": title,
            "reason": result.get("change_reason", ""),
            "status": "drafting",
            "base_version": session.selected_report_version,
            "started_at": datetime.utcnow().isoformat(),
        }
        instruction = f"{request.content}\n\nChange to make: {title}"
        background_tasks.add_task(
            _draft_revision, session_id, reply["id"], instruction, session.report, session.specialist_reports
        )

    session.advisor_messages.append(reply)
    await store.update_session(session)
    return {
        "session_id": session.id,
        "messages": [_public(user_msg.model_dump(mode="json")), _public(reply)],
    }


async def _draft_revision(
    session_id: str,
    message_id: str,
    instruction: str,
    base_report: dict,
    specialist_reports: list[dict],
) -> None:
    """Background task: generate the revised report and attach it to the
    proposal. Re-reads the session before writing so chat messages sent
    meanwhile aren't lost."""
    revised: dict[str, Any] | None = None
    error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=_REVISE_TIMEOUT_SECS) as client:
            resp = await client.post(
                f"{settings.agents_url}/synthesis/revise",
                json={"report": base_report, "instruction": instruction, "specialist_reports": specialist_reports},
            )
            resp.raise_for_status()
            revised = resp.json()["report"]
    except Exception as e:
        logger.exception(f"Synth revise failed for session {session_id}: {e}")
        error = f"Synth couldn't draft this change ({type(e).__name__}). Ask again to retry."

    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        return
    msg = next((m for m in session.advisor_messages if m.get("id") == message_id), None)
    proposal = (msg or {}).get("proposal")
    if not proposal or proposal.get("status") != "drafting":
        return
    if revised is None:
        proposal["status"] = "failed"
        proposal["error"] = error
    else:
        # Keep what only the backend adds (repository, knowledge gaps, ids).
        proposal["revised_report"] = {**base_report, **revised, "revised_at": datetime.utcnow().isoformat()}
        proposal["status"] = "pending"
    await store.update_session(session)


# ─── Approve / discard ────────────────────────────────────────────────

@router.post("/{session_id}/advisor/proposals/{proposal_id}/approve")
async def approve_proposal(session_id: str, proposal_id: str):
    """Apply a drafted change: it becomes a new report version and is
    selected, so the page and the PDF export show it."""
    store, session = await _get_session(session_id)
    _, proposal = _find_proposal(session, proposal_id)
    if proposal.get("status") != "pending" or not proposal.get("revised_report"):
        raise HTTPException(status_code=409, detail=f"This change can't be approved (it is {proposal.get('status')}).")

    ensure_report_versions(session)
    version = max((v["version"] for v in session.report_versions), default=0) + 1
    session.report_versions.append(
        {
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
            "label": proposal.get("title", f"Version {version}"),
            "report": proposal["revised_report"],
        }
    )
    session.report = proposal["revised_report"]
    session.selected_report_version = version
    proposal["status"] = "approved"
    proposal["version"] = version
    proposal.pop("revised_report", None)  # now lives in report_versions

    note = _synth_note(
        f"Applied as version {version}. The report and the PDF export now show this version; "
        "you can switch back to an earlier one at any time."
    )
    session.advisor_messages.append(note)
    await store.update_session(session)
    return {"session_id": session.id, "messages": [note], **version_summaries(session)}


@router.post("/{session_id}/advisor/proposals/{proposal_id}/discard")
async def discard_proposal(session_id: str, proposal_id: str):
    store, session = await _get_session(session_id)
    _, proposal = _find_proposal(session, proposal_id)
    if proposal.get("status") not in ("pending", "failed", "drafting"):
        raise HTTPException(status_code=409, detail=f"This change can't be discarded (it is {proposal.get('status')}).")
    proposal["status"] = "discarded"
    proposal.pop("revised_report", None)
    await store.update_session(session)
    return {"session_id": session.id, "proposal": {k: v for k, v in proposal.items()}}

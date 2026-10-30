"""
Diagnostic Conversation & Multi-Agent API Router

Supports Step 3: Team Context diagnostic conversation via both REST and WebSocket:
- Left chat panel: supervisor introduction + agent targeted questions
- Right sidebar: unresolved knowledge gaps and specialist activity statuses
- Progression trigger: continue-diagnostic to execute synthesis
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from ..models.diagnostic_session import ConversationMessage, DiagnosticSession, SessionStatus
from ..orchestrator.supervisor import ROLE_LABELS, Supervisor
from ..storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Diagnostic Conversation"])


@router.post("/{session_id}/diagnose")
async def start_diagnostic(session_id: str, background_tasks: BackgroundTasks):
    """
    Step 3: Start Diagnostic.
    Returns immediately with a welcome message; the actual specialist
    pipeline runs via the Agent Service in the background, since it can take
    as long as a full specialist run (or several, back to back) — far longer
    than a request should block for. Poll GET /conversation (watch
    `processing`) for what happens next.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    supervisor = Supervisor(store)
    # Only one diagnostic can use the local model at a time.
    await supervisor.cancel_other_running(session.id)
    session.status = SessionStatus.DIAGNOSING
    session.processing = True
    session.agent_statuses = {role: {"status": "analyzing", "progress": 0.1} for role in ROLE_LABELS}
    welcome = supervisor.build_welcome_message(session)
    session.conversation = [welcome]
    await store.update_session(session)

    background_tasks.add_task(supervisor.start_diagnostic, session)

    return {
        "session_id": session.id,
        "status": session.status,
        "processing": True,
        "initial_messages": [welcome],
    }


@router.post("/{session_id}/cancel-diagnostic")
async def cancel_diagnostic(session_id: str):
    """Stop the running diagnostic: the specialist working right now is
    interrupted and the session is marked cancelled. POST /diagnose starts
    it again from the beginning."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.DIAGNOSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No diagnostic to cancel (status: {session.status.value}).",
        )

    await Supervisor(store).cancel_diagnostic(session)
    return {"session_id": session.id, "status": session.status, "processing": False}


@router.get("/{session_id}/conversation")
async def get_conversation(session_id: str):
    """Get full diagnostic conversation history and agent statuses. Poll this
    while `processing` is true to find out when a background turn finishes.

    `pipeline_progress` (null outside the diagnosing step, or if the Agent
    Service can't be reached) says which specialist is working right now —
    see Supervisor.get_pipeline_progress for its shape."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    progress = None
    if session.status == SessionStatus.DIAGNOSING:
        progress = await Supervisor(store).get_pipeline_progress(session_id)

    return {
        "session_id": session.id,
        "messages": session.conversation,
        "agent_statuses": session.agent_statuses,
        "processing": session.processing,
        "status": session.status,
        "error_message": session.error_message,
        "pipeline_progress": progress,
    }


class SendMessageRequest(BaseModel):
    content: str
    responding_to_questions: list[str] | None = None


@router.post("/{session_id}/conversation")
async def send_user_message(session_id: str, request: SendMessageRequest, background_tasks: BackgroundTasks):
    """Send user response in the diagnostic conversation (REST). Appends the
    message and returns immediately; forwarding it to the Agent Service and
    continuing the pipeline happens in the background — see /diagnose for why."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = ConversationMessage(id=f"msg-{uuid.uuid4().hex[:8]}", role="user", content=request.content)
    session.conversation.append(user_msg.model_dump(mode="json"))
    session.processing = True
    await store.update_session(session)

    supervisor = Supervisor(store)
    background_tasks.add_task(supervisor.continue_user_turn, session_id, request.content)

    return {
        "session_id": session.id,
        "processing": True,
        "agent_statuses": session.agent_statuses,
    }


@router.get("/{session_id}/knowledge-gaps")
async def get_knowledge_gaps(session_id: str):
    """
    Right sidebar: unresolved gaps and follow-up questions per agent domain.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.id,
        "gaps": session.knowledge_gaps or {},
    }


@router.post("/{session_id}/continue-diagnostic")
async def continue_diagnostic(session_id: str):
    """
    Step 3 -> 4: Trigger final agent analysis and report synthesis.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    supervisor = Supervisor(store)
    try:
        await supervisor.run_synthesis(session)
    except RuntimeError as e:
        # The pipeline hasn't reached a final report yet (a specialist is
        # still working or waiting on an answer) — a clear 409, not a crash.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return {
        "session_id": session.id,
        "status": session.status,
        "report_ready": True,
    }


# WebSocket endpoint for real-time interactive multi-turn chat
@router.websocket("/ws/{session_id}/conversation")
async def websocket_conversation(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time diagnostic conversation.
    Supports streaming agent status updates and immediate message turns.
    """
    await websocket.accept()
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    supervisor = Supervisor(store)

    try:
        # Initial greeting if empty — the WS connection stays open for as
        # long as this takes, so unlike the REST endpoints there's no need
        # to push this to a background task.
        if not session.conversation:
            session.status = SessionStatus.DIAGNOSING
            session.processing = True
            session.agent_statuses = {role: {"status": "analyzing", "progress": 0.1} for role in ROLE_LABELS}
            session.conversation = [supervisor.build_welcome_message(session)]
            await store.update_session(session)
            await supervisor.start_diagnostic(session)  # mutates + persists session itself

        await websocket.send_json({
            "type": "initial_state",
            "messages": session.conversation,
            "agent_statuses": session.agent_statuses,
        })

        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            msg_type = data.get("type", "user_message")

            if msg_type == "user_message":
                content = data.get("content", "")

                user_msg = ConversationMessage(id=f"msg-{uuid.uuid4().hex[:8]}", role="user", content=content)
                session.conversation.append(user_msg.model_dump(mode="json"))
                await store.update_session(session)

                # Notify thinking status
                await websocket.send_json({
                    "type": "agent_status",
                    "status": "agents_processing",
                })

                # Process turn (refetches the session internally)
                await supervisor.continue_user_turn(session_id, content)
                session = await store.get_session(session_id)
                if not session:
                    break
                # _handle_pipeline_result always appends exactly one message per turn
                new_responses = session.conversation[-1:]

                # Send responses back
                for r in new_responses:
                    await websocket.send_json({
                        "type": "agent_message",
                        "message": r,
                    })

                # Send updated agent statuses
                await websocket.send_json({
                    "type": "agent_status",
                    "agents": session.agent_statuses,
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as ex:
        logger.exception(f"WebSocket error for session {session_id}: {ex}")

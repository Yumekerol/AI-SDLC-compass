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
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from ..models.diagnostic_session import DiagnosticSession, SessionStatus
from ..orchestrator.supervisor import Supervisor
from ..storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Diagnostic Conversation"])


@router.post("/{session_id}/diagnose")
async def start_diagnostic(session_id: str):
    """
    Step 3: Start Diagnostic.
    Supervisor introduces scan findings and agents initiate the conversation.
    """
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    supervisor = Supervisor(store)
    initial_messages = await supervisor.start_diagnostic(session)

    return {
        "session_id": session.id,
        "status": session.status,
        "initial_messages": initial_messages,
    }


@router.get("/{session_id}/conversation")
async def get_conversation(session_id: str):
    """Get full diagnostic conversation history and agent statuses."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.id,
        "messages": session.conversation,
        "agent_statuses": session.agent_statuses,
    }


class SendMessageRequest(BaseModel):
    content: str
    responding_to_questions: list[str] | None = None


@router.post("/{session_id}/conversation")
async def send_user_message(session_id: str, request: SendMessageRequest):
    """Send user response in the diagnostic conversation (REST)."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    supervisor = Supervisor(store)
    new_responses = await supervisor.process_user_turn(
        session=session,
        content=request.content,
        responding_to_questions=request.responding_to_questions,
    )

    return {
        "session_id": session.id,
        "agent_statuses": session.agent_statuses,
        "new_messages": new_responses,
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
    report = await supervisor.run_synthesis(session)

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
        # Initial greeting if empty
        if not session.conversation:
            initial_msgs = await supervisor.start_diagnostic(session)
            await websocket.send_json({
                "type": "initial_state",
                "messages": initial_msgs,
                "agent_statuses": session.agent_statuses,
            })
        else:
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
                responding_to = data.get("responding_to_questions", [])

                # Notify thinking status
                await websocket.send_json({
                    "type": "agent_status",
                    "status": "agents_processing",
                })

                # Process turn
                new_responses = await supervisor.process_user_turn(
                    session=session,
                    content=content,
                    responding_to_questions=responding_to,
                )

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

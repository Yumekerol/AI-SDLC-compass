"""
Advisor/Support Chat API Router

Step 5: open-ended Q&A about the repository, available even after the report
is ready. Unlike the Step-3 diagnostic conversation (pipeline-turn structured,
can pause on a specialist's clarifying question), this is a single bounded
call per message to the Agent Service's generic /chat endpoint — no
background-task/poll treatment needed, since there's no multi-specialist
sequence behind it.
"""

from __future__ import annotations

import logging
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..models.diagnostic_session import ConversationMessage, SourceType
from ..storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Advisor Chat"])


@router.get("/{session_id}/advisor/messages")
async def get_advisor_messages(session_id: str):
    """Full advisor chat history for this session (persists across reloads —
    the Agent Service's own memory of the conversation is just scratch space
    for drafting the next reply, not the source of truth)."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session.id, "messages": session.advisor_messages}


class AdvisorMessageRequest(BaseModel):
    content: str


@router.post("/{session_id}/advisor/messages")
async def send_advisor_message(session_id: str, request: AdvisorMessageRequest):
    """Send a message to the advisor and get its reply. A single call, not a
    background task — one /chat round trip, not a multi-specialist pipeline."""
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.source_type != SourceType.GIT or not session.git_url:
        raise HTTPException(
            status_code=400,
            detail="The advisor currently only supports repositories connected by Git URL, not ZIP uploads.",
        )

    user_msg = ConversationMessage(id=f"msg-{uuid4().hex[:8]}", role="user", content=request.content)
    session.advisor_messages.append(user_msg.model_dump(mode="json"))

    try:
        async with httpx.AsyncClient(timeout=settings.agents_request_timeout) as client:
            resp = await client.post(
                f"{settings.agents_url}/chat",
                json={
                    "message": request.content,
                    "session_id": session_id,
                    "git_url": session.git_url,
                    "access_token": session.access_token,
                },
            )
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        logger.exception(f"Advisor chat failed for session {session_id}: {e}")
        await store.update_session(session)  # keep the user's message even if the reply failed
        raise HTTPException(status_code=502, detail=f"Advisor is unavailable: {type(e).__name__}: {e}")

    reply_msg = ConversationMessage(
        id=f"msg-{uuid4().hex[:8]}",
        role="agent",
        agent_label="Advisor",
        content=result.get("answer", ""),
    )
    session.advisor_messages.append(reply_msg.model_dump(mode="json"))
    await store.update_session(session)

    return {"session_id": session.id, "messages": [user_msg.model_dump(mode="json"), reply_msg.model_dump(mode="json")]}

"""
Session Notifications API Router

A durable, pollable record of user-facing events (scan done, a specialist
needs input, the report is ready) — separate from `conversation` so the
frontend can check "did anything happen?" cheaply, without pulling the full
chat history. Notifications are created at the exact points in scan.py and
orchestrator/supervisor.py where these events already occur; this router
only reads/acknowledges them.
"""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, HTTPException

from ..models.diagnostic_session import NotificationLevel, _DEFAULT_LEVELS
from ..storage import get_storage

router = APIRouter(prefix="/sessions", tags=["Notifications"])


@router.get("/{session_id}/notifications")
async def get_notifications(session_id: str, unread_only: bool = False):
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    notifications = session.notifications
    if unread_only:
        notifications = [n for n in notifications if not n.get("read")]

    # Guarantee all notifications have level and created_at fields for the frontend
    for n in notifications:
        if "level" not in n:
            n_type = n.get("type", "")
            n["level"] = _DEFAULT_LEVELS.get(n_type, NotificationLevel.INFO.value)
        if "created_at" not in n:
            n["created_at"] = datetime.utcnow().isoformat()

    return {"session_id": session.id, "notifications": notifications}


@router.post("/{session_id}/notifications/{notification_id}/read")
async def mark_notification_read(session_id: str, notification_id: str):
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    for n in session.notifications:
        if n.get("id") == notification_id:
            n["read"] = True
            await store.update_session(session)
            return {"session_id": session.id, "notification": n}

    raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/{session_id}/notifications/read-all")
async def mark_all_notifications_read(session_id: str):
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    for n in session.notifications:
        n["read"] = True
    await store.update_session(session)

    return {"session_id": session.id, "notifications": session.notifications}

@router.delete("/{session_id}/notifications")
async def clear_all_notifications(session_id: str):
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.notifications = []
    await store.update_session(session)

    return {"session_id": session.id, "notifications": []}


@router.delete("/{session_id}/notifications/{notification_id}")
async def delete_notification(session_id: str, notification_id: str):
    store = await get_storage()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    initial_count = len(session.notifications)
    session.notifications = [n for n in session.notifications if n.get("id") != notification_id]

    if len(session.notifications) == initial_count:
        raise HTTPException(status_code=404, detail="Notification not found")

    await store.update_session(session)

    return {"session_id": session.id, "notification_id": notification_id, "deleted": True}


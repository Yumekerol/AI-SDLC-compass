"""
SQLite Storage Implementation

SQLite storage backend for local development and zero-cost PoC execution.
Uses Python standard library `sqlite3` wrapped with `asyncio.to_thread` for non-blocking I/O.
Stores full session and profile data as typed JSON blobs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import DiagnosticSession, SessionStatus, SourceType
from .base_store import BaseStore

logger = logging.getLogger(__name__)


class SQLiteStore(BaseStore):
    """SQLite implementation using standard library sqlite3 + asyncio.to_thread."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            self.db_path = settings.data_dir / "sdlc_compass.db"
        else:
            self.db_path = Path(db_path)
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _sync_initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    git_url TEXT,
                    access_token TEXT,
                    consent_given INTEGER NOT NULL DEFAULT 0,
                    workspace_path TEXT,
                    scan_id TEXT,
                    scanner_output TEXT,
                    signals_confirmed INTEGER NOT NULL DEFAULT 0,
                    signals_confirmed_at TEXT,
                    conversation TEXT,
                    agent_statuses TEXT,
                    knowledge_gaps TEXT,
                    report TEXT,
                    report_generated_at TEXT,
                    pdf_path TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    session_id TEXT PRIMARY KEY,
                    scanner_signals TEXT,
                    user_signal_overrides TEXT,
                    team_context TEXT,
                    qa_pairs TEXT,
                    created_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        self._initialized = True
        logger.info(f"SQLite database initialized at {self.db_path}")

    async def initialize(self) -> None:
        if not self._initialized:
            await asyncio.to_thread(self._sync_initialize)

    def _sync_save_session(self, session: DiagnosticSession) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (
                    id, status, source_type, git_url, access_token, consent_given,
                    workspace_path, scanner_output, signals_confirmed, signals_confirmed_at,
                    conversation, agent_statuses, knowledge_gaps, report,
                    report_generated_at, pdf_path, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.id,
                session.status.value if hasattr(session.status, "value") else str(session.status),
                session.source_type.value if hasattr(session.source_type, "value") else str(session.source_type),
                session.git_url,
                session.access_token,
                1 if session.consent_given else 0,
                session.workspace_path,
                json.dumps(session.scanner_output, default=str) if session.scanner_output else None,
                1 if session.signals_confirmed else 0,
                session.signals_confirmed_at.isoformat() if session.signals_confirmed_at else None,
                json.dumps(session.conversation, default=str),
                json.dumps(session.agent_statuses, default=str),
                json.dumps(session.knowledge_gaps, default=str) if session.knowledge_gaps else None,
                json.dumps(session.report, default=str) if session.report else None,
                session.report_generated_at.isoformat() if session.report_generated_at else None,
                session.pdf_path,
                session.error_message,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
            ))
            conn.commit()

    async def save_session(self, session: DiagnosticSession) -> None:
        await self.initialize()
        await asyncio.to_thread(self._sync_save_session, session)

    def _sync_get_session(self, session_id: str) -> DiagnosticSession | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None

            return DiagnosticSession(
                id=row["id"],
                status=SessionStatus(row["status"]),
                source_type=SourceType(row["source_type"]),
                git_url=row["git_url"],
                access_token=row["access_token"],
                consent_given=bool(row["consent_given"]),
                workspace_path=row["workspace_path"],
                scan_id=row["scan_id"],
                scanner_output=json.loads(row["scanner_output"]) if row["scanner_output"] else None,
                signals_confirmed=bool(row["signals_confirmed"]),
                signals_confirmed_at=datetime.fromisoformat(row["signals_confirmed_at"]) if row["signals_confirmed_at"] else None,
                conversation=json.loads(row["conversation"]) if row["conversation"] else [],
                agent_statuses=json.loads(row["agent_statuses"]) if row["agent_statuses"] else {},
                knowledge_gaps=json.loads(row["knowledge_gaps"]) if row["knowledge_gaps"] else None,
                report=json.loads(row["report"]) if row["report"] else None,
                report_generated_at=datetime.fromisoformat(row["report_generated_at"]) if row["report_generated_at"] else None,
                pdf_path=row["pdf_path"],
                error_message=row["error_message"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    async def get_session(self, session_id: str) -> DiagnosticSession | None:
        await self.initialize()
        return await asyncio.to_thread(self._sync_get_session, session_id)

    async def update_session(self, session: DiagnosticSession) -> None:
        session.updated_at = datetime.utcnow()
        await self.save_session(session)

    def _sync_list_sessions(self, limit: int) -> list[DiagnosticSession]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            sessions = []
            for row in rows:
                s = self._sync_get_session(row["id"])
                if s:
                    sessions.append(s)
            return sessions

    async def list_sessions(self, limit: int = 50) -> list[DiagnosticSession]:
        await self.initialize()
        return await asyncio.to_thread(self._sync_list_sessions, limit)

    def _sync_delete_session(self, session_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            cursor.execute("DELETE FROM profiles WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def delete_session(self, session_id: str) -> bool:
        await self.initialize()
        return await asyncio.to_thread(self._sync_delete_session, session_id)

    def _sync_save_profile(self, profile: ContextualProfile) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO profiles (
                    session_id, scanner_signals, user_signal_overrides,
                    team_context, qa_pairs, created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.session_id,
                json.dumps(profile.scanner_signals, default=str),
                json.dumps(profile.user_signal_overrides, default=str),
                json.dumps(profile.team_context.model_dump(mode="json"), default=str),
                json.dumps(profile.qa_pairs, default=str),
                profile.created_at.isoformat(),
                profile.last_updated.isoformat(),
            ))
            conn.commit()

    async def save_profile(self, profile: ContextualProfile) -> None:
        await self.initialize()
        await asyncio.to_thread(self._sync_save_profile, profile)

    def _sync_get_profile(self, session_id: str) -> ContextualProfile | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None

            return ContextualProfile(
                session_id=row["session_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_updated=datetime.fromisoformat(row["last_updated"]),
                scanner_signals=json.loads(row["scanner_signals"]) if row["scanner_signals"] else {},
                user_signal_overrides=json.loads(row["user_signal_overrides"]) if row["user_signal_overrides"] else {},
                team_context=json.loads(row["team_context"]) if row["team_context"] else {},
                qa_pairs=json.loads(row["qa_pairs"]) if row["qa_pairs"] else [],
            )

    async def get_profile(self, session_id: str) -> ContextualProfile | None:
        await self.initialize()
        return await asyncio.to_thread(self._sync_get_profile, session_id)

    async def close(self) -> None:
        pass

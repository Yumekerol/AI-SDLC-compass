"""
Pipeline position store.

The LangGraph checkpointer (persistence.py) tracks each *specialist's* paused
state, keyed by its own thread_id. It knows nothing about "which specialist
are we on" across the whole 4-specialist sequence — that's a separate,
smaller piece of state this module owns: one row per session, holding which
specialist index we're on, the Reports already collected, and (if paused)
which specialist and thread_id is waiting on a reply. Backend calls
`/pipeline/start` and `/pipeline/reply` as separate HTTP requests, so this
has to survive between them the same way the checkpointer does.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .config import settings

_DB_PATH = None


def _db_path():
    global _DB_PATH
    if _DB_PATH is None:
        settings.base_dir.joinpath("data").mkdir(parents=True, exist_ok=True)
        _DB_PATH = settings.base_dir / "data" / "pipeline_state.db"
    return _DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pipeline_state (
            session_id TEXT PRIMARY KEY,
            state TEXT NOT NULL
        )
        """
    )
    return conn


def get_state(session_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT state FROM pipeline_state WHERE session_id = ?", (session_id,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def save_state(session_id: str, state: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pipeline_state (session_id, state) VALUES (?, ?)",
            (session_id, json.dumps(state)),
        )
        conn.commit()


def delete_state(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM pipeline_state WHERE session_id = ?", (session_id,))
        conn.commit()

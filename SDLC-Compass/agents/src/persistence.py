"""
LangGraph checkpointer for specialist runs.

`InMemorySaver` (what the generic /chat agent still uses) loses every paused
thread the moment the process restarts. That was an acceptable shortcut when
nothing actually paused mid-run; now that `ask_user` is a real, used feature
(a specialist can sit waiting on a person for minutes), losing that state on
any restart is a real regression, not just a theoretical one. A SQLite-backed
checkpointer survives the common case — the process stays up while the user
types their answer — without taking on a separate database service.

This is not bulletproof: a paused specialist's thread is still tied to this
one process (a different replica couldn't resume it), and a hard crash mid
-checkpoint-write is unhandled. That's an acceptable gap for now; revisit if
the service is ever run with more than one worker/replica.
"""

from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from .config import settings

_checkpointer: SqliteSaver | None = None


def get_checkpointer() -> SqliteSaver:
    """Return the process-wide specialist checkpointer, creating it on first use."""
    global _checkpointer
    if _checkpointer is None:
        settings.base_dir.joinpath("data").mkdir(parents=True, exist_ok=True)
        db_path = settings.base_dir / "data" / "checkpoints.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        _checkpointer.setup()
    return _checkpointer

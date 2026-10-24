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

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .config import settings

_checkpointer: AsyncSqliteSaver | None = None
_conn: aiosqlite.Connection | None = None


async def init_checkpointer() -> None:
    """Open the async SQLite connection and create the checkpointer.
    Call once during application startup (e.g. from the FastAPI lifespan)."""
    global _checkpointer, _conn
    if _checkpointer is not None:
        return
    settings.base_dir.joinpath("data").mkdir(parents=True, exist_ok=True)
    db_path = settings.base_dir / "data" / "checkpoints.db"
    _conn = await aiosqlite.connect(str(db_path))
    _checkpointer = AsyncSqliteSaver(_conn)
    await _checkpointer.setup()


async def close_checkpointer() -> None:
    """Close the connection. Call during application shutdown."""
    global _checkpointer, _conn
    if _conn is not None:
        await _conn.close()
    _checkpointer = None
    _conn = None


def get_checkpointer() -> AsyncSqliteSaver:
    """Return the process-wide specialist checkpointer (must be initialized first)."""
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized — call init_checkpointer() during startup")
    return _checkpointer



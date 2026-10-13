"""Storage package initialization."""

from .base_store import BaseStore
from .sqlite_store import SQLiteStore

# Global store singleton
_store: BaseStore | None = None


async def get_storage() -> BaseStore:
    """Get initialized storage instance."""
    global _store
    if _store is None:
        _store = SQLiteStore()
        await _store.initialize()
    return _store


__all__ = ["BaseStore", "SQLiteStore", "get_storage"]

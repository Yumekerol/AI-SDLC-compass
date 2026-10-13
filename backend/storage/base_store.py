"""
Storage Backend Abstraction

Defines the abstract interface for session and profile persistence.
Allows zero-downtime swapping from SQLite to Cloud Firestore or PostgreSQL later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import DiagnosticSession


class BaseStore(ABC):
    """Abstract storage interface for diagnostic data."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database connection, schemas, and tables."""
        pass

    @abstractmethod
    async def save_session(self, session: DiagnosticSession) -> None:
        """Create or replace a diagnostic session."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> DiagnosticSession | None:
        """Retrieve a diagnostic session by ID."""
        pass

    @abstractmethod
    async def update_session(self, session: DiagnosticSession) -> None:
        """Update an existing session."""
        pass

    @abstractmethod
    async def list_sessions(self, limit: int = 50) -> list[DiagnosticSession]:
        """List recent sessions."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        pass

    @abstractmethod
    async def save_profile(self, profile: ContextualProfile) -> None:
        """Save or update a contextual profile."""
        pass

    @abstractmethod
    async def get_profile(self, session_id: str) -> ContextualProfile | None:
        """Retrieve the contextual profile for a session."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connections."""
        pass

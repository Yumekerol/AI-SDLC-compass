"""
Diagnostic Session Model

Tracks the full lifecycle of a diagnostic session, from repository
connection through scanning, team context conversation, and report generation.

Maps to the 4-step progress bar in the Figma UI:
  1. Connect repository
  2. Review signals
  3. Team context
  4. Diagnostic report
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Diagnostic session lifecycle states."""
    CREATED = "created"
    INGESTING = "ingesting"
    SCANNING = "scanning"
    SCAN_COMPLETE = "scan_complete"
    AWAITING_SIGNAL_REVIEW = "awaiting_signal_review"
    SIGNALS_CONFIRMED = "signals_confirmed"
    DIAGNOSING = "diagnosing"
    AWAITING_TEAM_CONTEXT = "awaiting_team_context"
    SYNTHESIZING = "synthesizing"
    REPORT_READY = "report_ready"
    DRAFT_SAVED = "draft_saved"
    ERROR = "error"


class SourceType(str, Enum):
    """How the repository was provided."""
    GIT = "git"
    ZIP = "zip"


class ConversationMessage(BaseModel):
    """A single message in the diagnostic conversation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str  # "supervisor", "agent", "user"
    agent_domain: str | None = None  # e.g., "requirements_design"
    agent_label: str | None = None  # e.g., "Requirements & Design"
    content: str = ""
    questions: list[ConversationQuestion] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationQuestion(BaseModel):
    """A targeted question from an agent to the user."""
    question_id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    priority: str = "medium"  # "high", "medium", "low"
    tdm_field: str | None = None  # Which TDM field this question aims to fill
    answered: bool = False
    answer: str | None = None


class AgentStatus(BaseModel):
    """Current status of a specialist agent."""
    status: str = "idle"  # "idle", "gathering", "analyzing", "waiting_for_input", "complete"
    progress: float = 0.0  # 0.0 to 1.0


class SessionNotification(BaseModel):
    """A durable, user-facing event the frontend can show as a toast/modal."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str  # "scan_complete" | "needs_input" | "report_ready"
    title: str
    message: str
    domain: str | None = None  # which specialist, for "needs_input"
    route_hint: str | None = None  # e.g. "/signals", "/questions", "/report"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read: bool = False


class DiagnosticSession(BaseModel):
    """
    The top-level session model tracking the entire diagnostic lifecycle.

    This is the central state object persisted in the database and
    referenced by all API endpoints.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Step 1: Repository connection
    source_type: SourceType = SourceType.GIT
    git_url: str | None = None
    access_token: str | None = None  # Optional, for private repos
    consent_given: bool = False
    workspace_path: str | None = None  # Local path to the cloned/extracted repo
    scan_id: str | None = None

    # Step 2: Scanner signals (stored as JSON)
    scanner_output: dict | None = None  # Serialized ScannerOutput
    signals_confirmed: bool = False
    signals_confirmed_at: datetime | None = None

    # Step 3: Diagnostic conversation
    processing: bool = False
    """True while a background task is mid-turn with the Agent Service (a
    specialist run, a resume, or the synthesizer). The frontend polls
    GET /conversation and waits for this to go false before reading new
    messages — /diagnose and /conversation POSTs return immediately rather
    than blocking for however long the pipeline takes."""
    conversation: list[dict] = Field(default_factory=list)  # Serialized ConversationMessages
    agent_statuses: dict[str, dict] = Field(default_factory=lambda: {
        "requirements_design": {"status": "idle", "progress": 0.0},
        "code_refactoring": {"status": "idle", "progress": 0.0},
        "qa_testing": {"status": "idle", "progress": 0.0},
        "devops_monitoring": {"status": "idle", "progress": 0.0},
    })
    knowledge_gaps: dict | None = None  # Per-agent unresolved gaps

    # Step 4: Report
    report: dict | None = None  # Serialized report JSON
    report_generated_at: datetime | None = None
    pdf_path: str | None = None

    # Step 5: Advisor/support chat — stays available after the report is
    # ready. Separate from `conversation` (the Step-3 diagnostic interview,
    # pipeline-turn structured); this is open-ended Q&A, same shape as a
    # ConversationMessage so the frontend can reuse the same rendering.
    advisor_messages: list[dict] = Field(default_factory=list)

    # User-facing events (scan done, specialist needs input, report ready) —
    # a durable, pollable record separate from `conversation` so the
    # frontend can check "anything new happen?" without pulling the whole
    # chat history.
    notifications: list[dict] = Field(default_factory=list)

    # Error tracking
    error_message: str | None = None


_MAX_NOTIFICATIONS = 100


def add_notification(
    session: DiagnosticSession,
    *,
    type: str,
    title: str,
    message: str,
    domain: str | None = None,
    route_hint: str | None = None,
) -> None:
    """Append a notification to `session` and persist-ready it (caller still
    owns calling store.update_session). Caps the list so a long-running
    session's notification history can't grow unbounded."""
    n = SessionNotification(
        type=type, title=title, message=message, domain=domain, route_hint=route_hint
    )
    session.notifications.append(n.model_dump(mode="json"))
    session.notifications = session.notifications[-_MAX_NOTIFICATIONS:]


# ─── API Request / Response Models ────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Request body for POST /api/v1/sessions."""
    source_type: SourceType = SourceType.GIT
    git_url: str | None = None
    access_token: str | None = None
    consent_given: bool = False


class CreateSessionResponse(BaseModel):
    """Response body for POST /api/v1/sessions."""
    session_id: str
    status: SessionStatus
    created_at: datetime


class SessionStatusResponse(BaseModel):
    """Response body for GET /api/v1/sessions/{id}."""
    session_id: str
    status: SessionStatus
    source_type: SourceType
    git_url: str | None = None
    created_at: datetime
    updated_at: datetime
    signals_confirmed: bool = False
    report_ready: bool = False
    error_message: str | None = None

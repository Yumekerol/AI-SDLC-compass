"""
Contextual Profile — The Living Document

The Contextual Profile is the central data structure that evolves throughout
the diagnostic. It is:
  - Initialized with scanner signals (Step 2)
  - Enriched with user corrections to signals (Step 2 edits)
  - Enriched with team context from Q&A conversation (Step 3)
  - Consumed by all specialist agents as their primary input
  - Persisted as the final diagnostic source of truth

This is NOT a raw data dump — it is structured context that agents
use to fill their Target Diagnostic Models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TeamContext(BaseModel):
    """
    Team and process context gathered from the Q&A conversation.
    These are things the scanner cannot extract from code alone.
    """
    # Team structure
    team_size: int | None = None
    team_roles: list[str] = Field(default_factory=list)
    has_dedicated_qa: bool | None = None
    has_dedicated_devops: bool | None = None

    # Pain points declared by the team
    declared_pain_points: list[str] = Field(default_factory=list)
    ai_maturity_level: str | None = None  # "none", "exploring", "using_basic", "advanced"
    current_ai_tools: list[str] = Field(default_factory=list)

    # Requirements & Design context
    requirements_format: str | None = None
    acceptance_criteria_exist: str | None = None  # "yes", "partial", "no"
    design_review_process: str | None = None
    stakeholder_communication: str | None = None

    # Code & Refactoring context
    code_review_process: str | None = None
    avg_pr_review_time: str | None = None
    boilerplate_pain: str | None = None
    refactoring_backlog: str | None = None

    # QA & Testing context
    test_types_present: list[str] = Field(default_factory=list)
    external_testing_tools: list[str] = Field(default_factory=list)
    test_data_strategy: str | None = None
    critical_untested_modules: str | None = None
    regression_frequency: str | None = None
    qa_role_workflow: str | None = None

    # DevOps & Monitoring context
    deployment_method: str | None = None
    deployment_frequency: str | None = None
    environment_count: str | None = None
    rollback_strategy: str | None = None
    logging_strategy: str | None = None
    incident_response: str | None = None
    downtime_history: str | None = None


class ContextualProfile(BaseModel):
    """
    The living document that agents consume.

    Combines deterministic scanner signals with human-provided
    team context into a unified view of the project state.
    """
    session_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # From scanner (Step 2) — stored as the confirmed signal groups
    scanner_signals: dict = Field(default_factory=dict)

    # From user edits to signals (Step 2 edits)
    user_signal_overrides: dict = Field(default_factory=dict)

    # From team Q&A conversation (Step 3)
    team_context: TeamContext = Field(default_factory=TeamContext)

    # Raw Q&A pairs for agent reference
    qa_pairs: list[dict] = Field(default_factory=list)

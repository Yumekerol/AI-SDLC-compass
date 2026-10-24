"""
Specialist declaration and result shapes.

A specialist is data, not a subclass: `SpecialistSpec` + the one generic
`run_specialist()` in `runner.py` is a Strategy, not Template Method — adding
a fifth specialist means a new prompt file and a four-line SPEC, no new class
and no change to the runner. Reserve subclassing for a specialist that
genuinely needs different control flow, not just a different prompt/tools/cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


@dataclass
class SpecialistSpec:
    role: str
    """One of: requirements_design | code_refactoring | qa_testing | devops_monitoring.
    Matches the keys already used in `session.agent_statuses` and
    `ContextualProfile.team_context` groupings on the backend, so no
    translation layer is needed when the backend relay calls this service."""

    label: str
    """Human-readable label, e.g. "Requirements & Design" — used in the
    readiness scorecard the synthesizer produces."""

    prompt_path: Path
    """.md file holding the system prompt for this role."""

    tool_names: list[str] = field(default_factory=list)
    """Names of tools (from tools.build_tools()) this specialist may use.
    `note` and `ask_user` are always available regardless of this list —
    the runner adds them unconditionally."""

    max_tool_calls: int | None = None
    """Cap on non-ask_user tool calls before the specialist is forced to wrap
    up. None = uncapped. Deliberately a plain per-spec value, not a global
    setting: we don't yet know whether capping helps or hurts, so it should
    be trivial to try both per specialist."""

    num_ctx: int = 16384

    @property
    def prompt(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8")


class Finding(BaseModel):
    claim: str
    evidence_paths: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"


class Report(BaseModel):
    """What a specialist produces. Built from the accumulated `note()` calls,
    not from the model's final chat message — so how a specialist chooses to
    end its turn never affects what actually gets reported."""

    role: str
    label: str
    findings: list[Finding] = Field(default_factory=list)
    questions_asked: list[str] = Field(default_factory=list)
    """Every ask_user question this specialist raised during its run, whether
    or not it got a satisfying answer. Feeds the backend's knowledge-gaps
    sidebar: a question the repository itself couldn't answer is exactly
    what that sidebar is for."""
    summary: str = ""
    status: Literal["complete", "capped"] = "complete"


class NeedsInput(BaseModel):
    """Returned instead of a Report when the specialist calls ask_user and
    the run is paused awaiting a reply. `thread_id` is what resume_specialist
    needs to continue the exact same paused run."""

    role: str
    thread_id: str
    question: str

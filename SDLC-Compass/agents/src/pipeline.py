"""
The pipeline: a plain orchestration loop over the 4 independent specialist
agents, not a second LangGraph graph layered on top of them. Each specialist
is already its own graph (see runner.py); a meta-graph here would add
complexity without buying anything, since there's no branching to express —
just a fixed sequence (single local Ollama daemon serializes inference
regardless of what the orchestration code does, so "sequential" is the real
execution model, not a UI framing choice).

Backend calls this turn-by-turn over separate HTTP requests (see main.py's
/pipeline/start and /pipeline/reply), so position in the sequence is
persisted via pipeline_store rather than held in memory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from . import pipeline_store
from .context import RunContext
from .runner import resume_specialist, run_specialist
from .specialists import PIPELINE_ORDER, SPECS_BY_ROLE
from .specialists.base import NeedsInput, Report
from .synthesizer import synthesize


class PipelineResult(BaseModel):
    status: Literal["needs_input", "complete"]
    role: str | None = None
    question: str | None = None
    reports: list[Report] | None = None
    synthesis: dict[str, Any] | None = None


def _task_for(spec, team_context: dict[str, Any]) -> str:
    return (
        f"Assess the {spec.label} domain of this repository for AI-SDLC "
        "readiness. Known team context so far (may be partial or empty): "
        f"{json.dumps(team_context, default=str)}"
    )


async def _advance(session_id: str, ctx: RunContext, state: dict[str, Any]) -> PipelineResult:
    """Run specialists starting at state['current_index'] until one pauses or all finish."""
    team_context = state.get("team_context", {})
    completed: list[Report] = [Report.model_validate(r) for r in state.get("completed_reports", [])]

    for index in range(state["current_index"], len(PIPELINE_ORDER)):
        spec = PIPELINE_ORDER[index]
        outcome = await run_specialist(spec, _task_for(spec, team_context), ctx)

        if isinstance(outcome, NeedsInput):
            state["current_index"] = index
            state["completed_reports"] = [r.model_dump(mode="json") for r in completed]
            state["paused"] = outcome.model_dump(mode="json")
            pipeline_store.save_state(session_id, state)
            return PipelineResult(status="needs_input", role=outcome.role, question=outcome.question)

        completed.append(outcome)

    synthesis = await synthesize(completed)
    pipeline_store.delete_state(session_id)
    return PipelineResult(status="complete", reports=completed, synthesis=synthesis)


async def run_pipeline(
    session_id: str,
    repo_path: str,
    team_context: dict[str, Any],
    scan_output: dict[str, Any] | None = None,
) -> PipelineResult:
    ctx = RunContext(root=Path(repo_path), scan_output=scan_output or {})
    state = {
        "current_index": 0,
        "completed_reports": [],
        "paused": None,
        "repo_path": str(ctx.root),
        "team_context": team_context,
        "scan_output": scan_output or {},
    }
    pipeline_store.save_state(session_id, state)
    return await _advance(session_id, ctx, state)


async def resume_pipeline(session_id: str, answer: str) -> PipelineResult:
    state = pipeline_store.get_state(session_id)
    if not state or not state.get("paused"):
        raise ValueError(f"No paused pipeline found for session {session_id}")

    paused = NeedsInput.model_validate(state["paused"])
    spec = SPECS_BY_ROLE[paused.role]
    ctx = RunContext(root=Path(state["repo_path"]), scan_output=state.get("scan_output", {}))

    outcome = await resume_specialist(spec, paused.thread_id, answer, ctx)

    if isinstance(outcome, NeedsInput):
        state["paused"] = outcome.model_dump(mode="json")
        pipeline_store.save_state(session_id, state)
        return PipelineResult(status="needs_input", role=outcome.role, question=outcome.question)

    completed = [Report.model_validate(r) for r in state.get("completed_reports", [])]
    completed.append(outcome)
    state["current_index"] += 1
    state["completed_reports"] = [r.model_dump(mode="json") for r in completed]
    state["paused"] = None
    pipeline_store.save_state(session_id, state)

    return await _advance(session_id, ctx, state)


def get_status(session_id: str) -> dict[str, Any] | None:
    return pipeline_store.get_state(session_id)

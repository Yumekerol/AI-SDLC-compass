"""
Supervisor — thin relay between backend session state and the Agent Service.

No agent logic lives here anymore. The real supervisor + 4 specialists +
synthesizer pipeline runs in SDLC-Compass/agents/ (LangGraph + Ollama); this
class's only job is to own `DiagnosticSession`/conversation state, call that
service, and translate its turn-based responses into the conversation-message
shape the frontend already renders (QuestionsView.vue).

Every call into the Agent Service can take as long as a full specialist run —
possibly several specialists plus the synthesizer in one turn, if none of
them need to pause on a question. So `start_diagnostic` and `continue_user_turn`
are meant to run as FastAPI background tasks, not be awaited inline by a
request handler: see `api/diagnostic.py`, which does the fast synchronous
bookkeeping (append the message, flip `session.processing`) itself and hands
the actual Agent Service call off to a background task. The frontend polls
`GET /conversation` and waits for `processing` to go false.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

import httpx

from ..config import settings
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import (
    ConversationMessage,
    ConversationQuestion,
    DiagnosticSession,
    SessionStatus,
    SourceType,
)
from ..storage import BaseStore

logger = logging.getLogger(__name__)

ROLE_LABELS = {
    "requirements_design": "Requirements & Design",
    "code_refactoring": "Code & Refactoring",
    "qa_testing": "QA & Testing",
    "devops_monitoring": "DevOps & Monitoring",
}


class Supervisor:
    """Relay between one diagnostic session and the Agent Service."""

    def __init__(self, store: BaseStore):
        self.store = store

    async def _call_agents(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=settings.agents_request_timeout) as client:
            resp = await client.post(f"{settings.agents_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()

    def _build_knowledge_gaps(self, reports: list[dict]) -> dict[str, list[str]]:
        """Turn the specialists' own output into the Step-3 sidebar's gap
        list: a low-confidence finding is something the repo only partly
        answered, and a question the specialist had to ask is, by
        definition, something the repo didn't answer at all."""
        gaps: dict[str, list[str]] = {}
        for report in reports:
            role = report.get("role", "")
            descriptions: list[str] = []
            for finding in report.get("findings", []):
                if finding.get("confidence") == "low":
                    descriptions.append(f"Low confidence: {finding.get('claim', '')}")
            for question in report.get("questions_asked", []):
                descriptions.append(f"Asked: {question}")
            gaps[role] = descriptions
        return gaps

    async def _handle_pipeline_result(self, session: DiagnosticSession, result: dict) -> list[dict]:
        """Turn one /pipeline/start or /pipeline/reply response into the new
        conversation message(s) for this turn, updating session state.
        Does NOT persist or touch `processing` — the caller (a background
        task) owns that, so it can clear the flag in a `finally` regardless
        of whether this raises."""
        responses: list[dict] = []

        if result["status"] == "needs_input":
            role = result["role"]
            session.agent_statuses[role] = {"status": "waiting_for_input", "progress": 0.5}
            msg = ConversationMessage(
                id=f"msg-{uuid4().hex[:8]}",
                role="agent",
                agent_domain=role,
                agent_label=ROLE_LABELS.get(role, role),
                content=result["question"],
                questions=[ConversationQuestion(question_id=f"q-{uuid4().hex[:6]}", text=result["question"])],
            )
            responses.append(msg.model_dump(mode="json"))
        else:  # "complete"
            for role in ROLE_LABELS:
                session.agent_statuses[role] = {"status": "complete", "progress": 1.0}

            session.knowledge_gaps = self._build_knowledge_gaps(result.get("reports") or [])

            report = dict(result.get("synthesis") or {})
            repo_info = (session.scanner_output or {}).get("repository", {})
            report.setdefault(
                "repository",
                {
                    "name": repo_info.get("name"),
                    "branch": repo_info.get("branch"),
                    "commit_hash": repo_info.get("commit_hash"),
                },
            )
            report["session_id"] = session.id
            report["generated_at"] = datetime.utcnow().isoformat()

            session.report = report
            session.report_generated_at = datetime.utcnow()
            session.status = SessionStatus.REPORT_READY

            sup_msg = ConversationMessage(
                id=f"msg-{uuid4().hex[:8]}",
                role="supervisor",
                content=(
                    "All four specialists have finished and your AI-SDLC Compass report "
                    "is ready. Open the Report tab to see it."
                ),
            )
            responses.append(sup_msg.model_dump(mode="json"))

        for r in responses:
            session.conversation.append(r)
        return responses

    def build_welcome_message(self, session: DiagnosticSession) -> dict:
        """The fast, synchronous part of kicking off a diagnostic: just the
        greeting. Called directly by the API handler, before scheduling
        `start_diagnostic` as a background task, so the UI has something to
        show immediately instead of a blank screen until the first
        specialist responds."""
        welcome = ConversationMessage(
            id=f"msg-{uuid4().hex[:8]}",
            role="supervisor",
            content=(
                "Welcome! I've completed the deterministic code scan. Our four domain "
                "specialists will now review the repository and may ask you a few "
                "clarifying questions as they go."
            ),
        )
        return welcome.model_dump(mode="json")

    async def start_diagnostic(self, session: DiagnosticSession) -> None:
        """Background task: run the pipeline (supervisor -> 4 specialists ->
        synthesizer) via the Agent Service. Expects the caller to have
        already set session.status/processing and persisted the welcome
        message synchronously (see build_welcome_message)."""
        profile = await self.store.get_profile(session.id)
        if not profile:
            profile = ContextualProfile(session_id=session.id, scanner_signals=session.scanner_output or {})
            await self.store.save_profile(profile)

        try:
            if session.source_type != SourceType.GIT or not session.git_url:
                # The Agent Service clones its own copy from a git URL (see
                # agents/src/acquisition.py) — a ZIP-uploaded session has
                # nothing for it to clone. Out of scope for this beta rather
                # than silently sending it a URL that doesn't exist.
                raise RuntimeError(
                    "The specialist pipeline currently only supports repositories "
                    "connected by Git URL, not ZIP uploads."
                )
            result = await self._call_agents(
                "/pipeline/start",
                {
                    "session_id": session.id,
                    "git_url": session.git_url,
                    "access_token": session.access_token,
                    "team_context": profile.team_context.model_dump(mode="json"),
                    "scan_output": session.scanner_output or {},
                },
            )
            await self._handle_pipeline_result(session, result)
        except Exception as e:
            logger.exception(f"Pipeline start failed for session {session.id}: {e}")
            session.status = SessionStatus.ERROR
            session.error_message = str(e)
        finally:
            session.processing = False
            await self.store.update_session(session)

    async def continue_user_turn(self, session_id: str, content: str) -> None:
        """Background task: forward the user's answer to whichever
        specialist is paused waiting for it, and continue the pipeline from
        there. Re-fetches the session fresh since this runs after the HTTP
        response for the triggering request has already gone out."""
        session = await self.store.get_session(session_id)
        if not session:
            logger.warning(f"continue_user_turn: session {session_id} vanished before the background task ran")
            return

        try:
            result = await self._call_agents("/pipeline/reply", {"session_id": session_id, "answer": content})
            await self._handle_pipeline_result(session, result)
        except Exception as e:
            logger.exception(f"Pipeline resume failed for session {session_id}: {e}")
            session.status = SessionStatus.ERROR
            session.error_message = str(e)
        finally:
            session.processing = False
            await self.store.update_session(session)

    async def run_synthesis(self, session: DiagnosticSession) -> dict:
        """There's no separate synthesis step to trigger anymore — the Agent
        Service already ran it as soon as the pipeline completed, inside
        whichever turn finished the last specialist. If the diagnostic
        conversation hasn't reached that point yet, there's nothing to
        return."""
        if session.report:
            return session.report
        raise RuntimeError(
            "The diagnostic isn't finished yet — one or more specialists are still "
            "working or waiting on an answer. Finish the conversation before continuing."
        )

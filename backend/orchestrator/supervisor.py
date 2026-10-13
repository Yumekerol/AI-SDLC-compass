"""
Supervisor Agent & Diagnostic Orchestrator

Coordinates the state machine, agent lifecycle, multi-agent conversation,
and report generation across the diagnostic session.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from ..agents.code_agent import CodeAgent
from ..agents.devops_agent import DevOpsAgent
from ..agents.qa_agent import QAAgent
from ..agents.requirements_agent import RequirementsAgent
from ..agents.synthesizer_agent import SynthesizerAgent
from ..llm import get_llm_provider
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import (
    ConversationMessage,
    ConversationQuestion,
    DiagnosticSession,
    SessionStatus,
)
from ..storage import BaseStore
from .question_manager import QuestionManager

logger = logging.getLogger(__name__)


class Supervisor:
    """Orchestrator coordinating specialist agents and session progression."""

    def __init__(self, store: BaseStore):
        self.store = store
        self.llm = get_llm_provider()
        self.requirements_agent = RequirementsAgent(self.llm)
        self.code_agent = CodeAgent(self.llm)
        self.qa_agent = QAAgent(self.llm)
        self.devops_agent = DevOpsAgent(self.llm)
        self.synthesizer = SynthesizerAgent(self.llm)

    async def start_diagnostic(self, session: DiagnosticSession) -> list[dict]:
        """
        Transition session to DIAGNOSING, run initial Gather phase across all 4 agents,
        and generate the introductory conversation messages.
        """
        session.status = SessionStatus.DIAGNOSING

        # Ensure contextual profile exists
        profile = await self.store.get_profile(session.id)
        if not profile:
            profile = ContextualProfile(
                session_id=session.id,
                scanner_signals=session.scanner_output or {},
                user_signal_overrides={},
            )
            await self.store.save_profile(profile)

        # Run Gather in parallel across all 4 specialists
        req_res, code_res, qa_res, ops_res = await asyncio.gather(
            self.requirements_agent.gather(profile),
            self.code_agent.gather(profile),
            self.qa_agent.gather(profile),
            self.devops_agent.gather(profile),
        )

        req_gather, req_q, req_gaps = req_res
        code_gather, code_q, code_gaps = code_res
        qa_gather, qa_q, qa_gaps = qa_res
        ops_gather, ops_q, ops_gaps = ops_res

        # Store knowledge gaps for sidebar
        session.knowledge_gaps = {
            "requirements_design": {
                "resolved": max(0, 6 - len(req_gaps)),
                "total": 6,
                "unresolved": req_gaps,
                "follow_up_questions": [q.model_dump(mode="json") for q in req_q],
            },
            "code_refactoring": {
                "resolved": max(0, 8 - len(code_gaps)),
                "total": 8,
                "unresolved": code_gaps,
                "follow_up_questions": [q.model_dump(mode="json") for q in code_q],
            },
            "qa_testing": {
                "resolved": max(0, 9 - len(qa_gaps)),
                "total": 9,
                "unresolved": qa_gaps,
                "follow_up_questions": [q.model_dump(mode="json") for q in qa_q],
            },
            "devops_monitoring": {
                "resolved": max(0, 10 - len(ops_gaps)),
                "total": 10,
                "unresolved": ops_gaps,
                "follow_up_questions": [q.model_dump(mode="json") for q in ops_q],
            },
        }

        # Update specialist status
        session.agent_statuses = {
            "requirements_design": {"status": "waiting_for_input", "progress": 0.25},
            "code_refactoring": {"status": "waiting_for_input", "progress": 0.20},
            "qa_testing": {"status": "waiting_for_input", "progress": 0.15},
            "devops_monitoring": {"status": "waiting_for_input", "progress": 0.10},
        }

        # Build initial messages
        repo_name = (session.scanner_output or {}).get("repository", {}).get("name", "Repository")
        code_files = (session.scanner_output or {}).get("size_and_structure", {}).get("data", {}).get("code_files", 0)
        primary_lang = (session.scanner_output or {}).get("languages", {}).get("data", {}).get("primary_language", "Software")

        supervisor_msg = ConversationMessage(
            id=f"msg-{uuid4().hex[:8]}",
            role="supervisor",
            content=(
                f"Welcome! I have completed the deterministic code scan for **{repo_name}** "
                f"({code_files} code files, primarily {primary_lang}). "
                f"Our four domain specialist agents will now ask targeted clarification questions "
                f"to assess your team's processes and AI adoption readiness."
            ),
        )

        initial_messages = [supervisor_msg.model_dump(mode="json")]

        # Attach first round of questions from Requirements & Code specialists
        if req_q:
            req_msg = ConversationMessage(
                id=f"msg-{uuid4().hex[:8]}",
                role="agent",
                agent_domain="requirements_design",
                agent_label="Requirements & Design",
                content="To assess your Spec Hygiene, I need clarity on how requirements flow to your team:",
                questions=req_q[:2],
            )
            initial_messages.append(req_msg.model_dump(mode="json"))

        if qa_q:
            qa_msg = ConversationMessage(
                id=f"msg-{uuid4().hex[:8]}",
                role="agent",
                agent_domain="qa_testing",
                agent_label="QA & Testing",
                content="Regarding your Harness Hygiene, I noticed your test coverage proxy signals:",
                questions=qa_q[:2],
            )
            initial_messages.append(qa_msg.model_dump(mode="json"))

        session.conversation = initial_messages
        await self.store.update_session(session)

        return initial_messages

    async def process_user_turn(
        self,
        session: DiagnosticSession,
        content: str,
        responding_to_questions: list[str] | None = None,
    ) -> list[dict]:
        """
        Handle incoming user message, map answers to living document profile,
        advance agent states, and return new conversation responses.
        """
        profile = await self.store.get_profile(session.id)
        if not profile:
            profile = ContextualProfile(session_id=session.id)

        # 1. Record user message
        user_msg = ConversationMessage(
            id=f"msg-{uuid4().hex[:8]}",
            role="user",
            content=content,
        )
        session.conversation.append(user_msg.model_dump(mode="json"))

        # 2. Map answer into profile
        profile.qa_pairs.append({
            "question_ids": responding_to_questions or [],
            "answer": content,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Heuristic mapping into team_context based on content
        content_lower = content.lower()
        if "jira" in content_lower or "prds" in content_lower or "ticket" in content_lower:
            profile.team_context.requirements_format = content
        if "acceptance criteria" in content_lower or "given" in content_lower or "when" in content_lower:
            profile.team_context.acceptance_criteria_exist = content
        if "test" in content_lower or "unit" in content_lower or "integration" in content_lower:
            profile.team_context.test_types_present.append(content)
        if "deploy" in content_lower or "ci" in content_lower or "pipeline" in content_lower or "docker" in content_lower:
            profile.team_context.deployment_method = content
        if "pr" in content_lower or "review" in content_lower:
            profile.team_context.code_review_process = content

        await self.store.save_profile(profile)

        # 3. Generate response from specialists or supervisor
        responses: list[dict] = []

        # If user has submitted 2 or more responses, supervisor suggests proceeding to report
        user_message_count = sum(1 for m in session.conversation if m.get("role") == "user")

        if user_message_count >= 2:
            session.agent_statuses = {
                "requirements_design": {"status": "complete", "progress": 1.0},
                "code_refactoring": {"status": "complete", "progress": 1.0},
                "qa_testing": {"status": "complete", "progress": 1.0},
                "devops_monitoring": {"status": "complete", "progress": 1.0},
            }
            sup_msg = ConversationMessage(
                id=f"msg-{uuid4().hex[:8]}",
                role="supervisor",
                content=(
                    "Thank you for sharing those insights. We now have sufficient context across all four domains "
                    "(Spec, Code, Harness, and Ops). You can continue chatting or click **Continue diagnostic** "
                    "to generate your comprehensive AI-SDLC Compass Report."
                ),
            )
            responses.append(sup_msg.model_dump(mode="json"))
        else:
            # Code or DevOps specialist follow-up question
            code_msg = ConversationMessage(
                id=f"msg-{uuid4().hex[:8]}",
                role="agent",
                agent_domain="code_refactoring",
                agent_label="Code & Refactoring",
                content="Got it. For code hygiene: What is your team's typical pull request review turnaround time and are reviews blocking?",
                questions=[
                    ConversationQuestion(
                        question_id=f"q-{uuid4().hex[:6]}",
                        text="What is your average PR review turnaround time (hours or days), and are approvals required before merge?",
                        priority="medium",
                        tdm_field="code_review_process",
                    )
                ],
            )
            session.agent_statuses["code_refactoring"] = {"status": "analyzing", "progress": 0.6}
            session.agent_statuses["qa_testing"] = {"status": "analyzing", "progress": 0.5}
            responses.append(code_msg.model_dump(mode="json"))

        for r in responses:
            session.conversation.append(r)

        await self.store.update_session(session)
        return responses

    async def run_synthesis(self, session: DiagnosticSession) -> dict:
        """
        Transition session to SYNTHESIZING, execute full specialist agent cycles,
        and run the SynthesizerAgent to create the diagnostic report.
        """
        session.status = SessionStatus.SYNTHESIZING
        await self.store.update_session(session)

        profile = await self.store.get_profile(session.id)
        if not profile:
            profile = ContextualProfile(
                session_id=session.id,
                scanner_signals=session.scanner_output or {},
            )

        # Run full 3-phase cycles for all 4 agents
        req_full, code_full, qa_full, ops_full = await asyncio.gather(
            self.requirements_agent.run_full_cycle(profile),
            self.code_agent.run_full_cycle(profile),
            self.qa_agent.run_full_cycle(profile),
            self.devops_agent.run_full_cycle(profile),
        )

        agent_results = {
            "requirements_design": req_full,
            "code_refactoring": code_full,
            "qa_testing": qa_full,
            "devops_monitoring": ops_full,
        }

        # Synthesize into final deliverable
        synthesis_report = await self.synthesizer.synthesize(
            session_id=session.id,
            profile=profile,
            agent_results=agent_results,
        )

        session.report = synthesis_report.model_dump(mode="json")
        session.report_generated_at = datetime.utcnow()
        session.status = SessionStatus.REPORT_READY
        await self.store.update_session(session)

        return session.report

"""
Requirements & Design Specialist Agent

Assesses SPEC HYGIENE:
- Evaluates clarity, formality, and traceability of specifications.
- Identifies whether requirements can reliably feed AI code generators.
- Generates targeted questions and recommendations.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ..llm.base_provider import BaseLLMProvider
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import ConversationQuestion
from ..models.tdm_requirements import (
    RequirementsGatherFields,
    RequirementsInsight,
    RequirementsRecommendation,
    TDMFieldStatus,
    TDMRequirements,
)
from .base_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class RequirementsAgent(BaseSpecialistAgent):
    """Specialist agent for Requirements & Design (Spec Hygiene)."""

    def __init__(self, llm_provider: BaseLLMProvider):
        super().__init__(
            llm_provider=llm_provider,
            domain_name="requirements_design",
            domain_label="Requirements & Design",
        )

    async def gather(
        self, profile: ContextualProfile
    ) -> tuple[dict, list[ConversationQuestion], list[dict]]:
        tc = profile.team_context
        scanner_signals = profile.scanner_signals or {}
        cicd_data = scanner_signals.get("cicd_and_operations", {}).get("data", {})

        gather = RequirementsGatherFields()
        questions: list[ConversationQuestion] = []
        gaps: list[dict] = []

        # 1. API Specification (from scanner or team context)
        has_docs = cicd_data.get("has_documentation", False)
        doc_notes = cicd_data.get("documentation_notes", "")
        if "API specification" in doc_notes or "OpenAPI" in doc_notes:
            gather.api_specification = TDMFieldStatus(
                value="Documented in repository",
                source="scanner",
                confidence="high",
                filled=True,
            )
        elif tc.requirements_format:
            gather.api_specification = TDMFieldStatus(
                value="Declared in conversation",
                source="user_qa",
                confidence="medium",
                filled=True,
            )
        else:
            gather.api_specification = TDMFieldStatus(
                value=None, source="scanner", confidence="low", filled=False
            )
            gaps.append({
                "field": "api_specification",
                "description": "No formal OpenAPI or Swagger schemas detected in repository.",
                "priority": "medium",
            })

        # 2. Architecture documentation
        if "ADRs" in doc_notes or "docs/" in doc_notes:
            gather.architecture_documentation = TDMFieldStatus(
                value="Architecture docs / ADRs found",
                source="scanner",
                confidence="high",
                filled=True,
            )
        else:
            gather.architecture_documentation = TDMFieldStatus(
                value=None, source="scanner", confidence="low", filled=False
            )
            gaps.append({
                "field": "architecture_documentation",
                "description": "Missing Architecture Decision Records (ADRs) or design specifications.",
                "priority": "medium",
            })

        # 3. Requirements format (from team context)
        if tc.requirements_format:
            gather.requirements_format = TDMFieldStatus(
                value=tc.requirements_format,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            gather.requirements_format = TDMFieldStatus(
                value=None, source="user_qa", confidence="low", filled=False
            )
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="How does your team document requirements before implementation (e.g. Jira tickets with detailed user stories, PRDs, or informal verbal chats)?",
                priority="high",
                tdm_field="requirements_format",
            )
            questions.append(q)
            gaps.append({
                "field": "requirements_format",
                "description": "Formality of user stories and ticket specs is unknown.",
                "priority": "high",
            })

        # 4. Acceptance criteria
        if tc.acceptance_criteria_exist:
            gather.acceptance_criteria_exist = TDMFieldStatus(
                value=tc.acceptance_criteria_exist,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            gather.acceptance_criteria_exist = TDMFieldStatus(
                value=None, source="user_qa", confidence="low", filled=False
            )
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="Do user stories typically have explicit Given/When/Then acceptance criteria or testable definitions of done?",
                priority="high",
                tdm_field="acceptance_criteria_exist",
            )
            questions.append(q)
            gaps.append({
                "field": "acceptance_criteria_exist",
                "description": "Presence of testable acceptance criteria is unconfirmed.",
                "priority": "high",
            })

        # 5. Design review process
        if tc.design_review_process:
            gather.design_review_process = TDMFieldStatus(
                value=tc.design_review_process,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            gaps.append({
                "field": "design_review_process",
                "description": "Process for technical design reviews and RFCs is undocumented.",
                "priority": "medium",
            })

        # 6. Stakeholder communication
        if tc.stakeholder_communication:
            gather.stakeholder_communication = TDMFieldStatus(
                value=tc.stakeholder_communication,
                source="user_qa",
                confidence="high",
                filled=True,
            )

        return gather.model_dump(), questions, gaps

    async def analyze(
        self, profile: ContextualProfile, gathered_data: dict
    ) -> list[dict]:
        tc = profile.team_context
        analysis = [
            {
                "dimension": "spec_to_code_drift",
                "description": "How far has implementation diverged from specs?",
                "finding": "Specifications exist mostly in issues/tickets; minimal in-repo schemas to validate drift against implementation.",
                "severity": "high" if not tc.acceptance_criteria_exist else "medium",
            },
            {
                "dimension": "knowledge_bus_factor",
                "description": "Is critical design knowledge documented or tribal?",
                "finding": "Core architectural assumptions rely heavily on team memory rather than committed RFCs/ADRs.",
                "severity": "high" if not profile.scanner_signals.get("cicd_and_operations", {}).get("data", {}).get("has_documentation") else "low",
            },
            {
                "dimension": "requirements_traceability",
                "description": "Can you trace a feature from requirement → code → test?",
                "finding": "Traceability is partial; stories are not deterministically mapped to automated test verification suites.",
                "severity": "medium",
            },
            {
                "dimension": "communication_gaps",
                "description": "Where does information get lost between roles?",
                "finding": "Handoff from requirements to development frequently requires verbal clarification cycles.",
                "severity": "medium",
            },
        ]
        return analysis

    async def insight(
        self,
        profile: ContextualProfile,
        gathered_data: dict,
        analysis_data: list[dict],
    ) -> dict:
        tc = profile.team_context
        # Calculate readiness & opportunity
        ac_filled = gathered_data.get("acceptance_criteria_exist", {}).get("filled", False)
        api_spec_filled = gathered_data.get("api_specification", {}).get("filled", False)

        readiness = 4
        if ac_filled:
            readiness += 2
        if api_spec_filled:
            readiness += 2

        opportunity = 8  # High AI opportunity in automating spec creation and acceptance test generation

        label = "High" if readiness >= 8 else "Medium" if readiness >= 5 else "Low"

        insights = [
            RequirementsInsight(
                title="Specification ambiguity limits autonomous code generation",
                description="Without formal OpenAPI schemas and structured Given/When/Then acceptance criteria, AI code tools risk hallucinating business edge cases.",
                evidence="Absence of in-repo API contract specifications and informal user story structures.",
                risk_level="high",
                ai_opportunity="very_high",
            ),
            RequirementsInsight(
                title="High opportunity for AI-assisted requirements drafting",
                description="LLM tools can convert informal product briefs into testable BDD scenarios and Gherkin syntax before engineering begins.",
                evidence="Frequent clarification handoffs between product and developers.",
                risk_level="low",
                ai_opportunity="high",
            ),
        ]

        recommendations = [
            RequirementsRecommendation(
                title="Adopt formal OpenAPI/Swagger specifications for API endpoints",
                description="Store versioned OpenAPI specs in the repository as the single source of truth for backend endpoints and client SDK generation.",
                is_foundation=True,
                effort="Small (1-2 days)",
                impact="high",
                ai_relevance="Provides deterministic context for AI coding assistants to generate accurate endpoints and client calls.",
            ),
            RequirementsRecommendation(
                title="Deploy AI Spec Drafter for automated Acceptance Criteria",
                description="Use an AI workflow to ingest draft Jira tickets and automatically output Given/When/Then acceptance criteria and edge case checklists.",
                is_foundation=False,
                effort="Medium (1 sprint)",
                impact="very_high",
                ai_relevance="Directly eliminates requirements ambiguity and provides ready-to-test specs.",
            ),
        ]

        return {
            "readiness_score": readiness,
            "opportunity_score": opportunity,
            "readiness_label": label,
            "verdict": "API contracts partially documented; acceptance criteria need structured formatting before scaling AI code generation.",
            "insights": [i.model_dump() for i in insights],
            "recommendations": [r.model_dump() for r in recommendations],
            "gather_complete": True,
            "analysis_complete": True,
            "insight_complete": True,
        }

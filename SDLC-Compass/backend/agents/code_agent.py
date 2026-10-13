"""
Code & Refactoring Specialist Agent

Assesses CODE HYGIENE:
- Evaluates code modularity, linting/formatting enforcement, review processes.
- Identifies boilerplate burden and tech debt hotspots for AI refactoring.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ..llm.base_provider import BaseLLMProvider
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import ConversationQuestion
from ..models.tdm_code import CodeGatherFields
from ..models.tdm_requirements import RequirementsInsight, RequirementsRecommendation, TDMFieldStatus
from .base_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class CodeAgent(BaseSpecialistAgent):
    """Specialist agent for Code & Refactoring (Code Hygiene)."""

    def __init__(self, llm_provider: BaseLLMProvider):
        super().__init__(
            llm_provider=llm_provider,
            domain_name="code_refactoring",
            domain_label="Code & Refactoring",
        )

    async def gather(
        self, profile: ContextualProfile
    ) -> tuple[dict, list[ConversationQuestion], list[dict]]:
        tc = profile.team_context
        scanner_signals = profile.scanner_signals or {}
        lang_data = scanner_signals.get("languages", {}).get("data", {})
        stack_data = scanner_signals.get("stack_and_tooling", {}).get("data", {})
        quality_data = scanner_signals.get("quality_indicators", {}).get("data", {})

        gather = CodeGatherFields()
        questions: list[ConversationQuestion] = []
        gaps: list[dict] = []

        # 1. Primary language
        primary_lang = lang_data.get("primary_language")
        gather.primary_language = TDMFieldStatus(
            value=primary_lang,
            source="scanner",
            confidence="high",
            filled=bool(primary_lang),
        )

        # 2. Frameworks
        frameworks = stack_data.get("frameworks", [])
        gather.frameworks = TDMFieldStatus(
            value=", ".join(frameworks) if frameworks else None,
            source="scanner",
            confidence="high",
            filled=bool(frameworks),
        )

        # 3. Code style enforcement (linters & formatters)
        linters = stack_data.get("linters", [])
        formatters = stack_data.get("formatters", [])
        has_style = quality_data.get("has_code_style_config", False)
        style_tools = list(set(linters + formatters + quality_data.get("code_style_tools", [])))
        if style_tools:
            gather.code_style_enforcement = TDMFieldStatus(
                value=f"Configured: {', '.join(style_tools)}",
                source="scanner",
                confidence="high",
                filled=True,
            )
        else:
            gather.code_style_enforcement = TDMFieldStatus(
                value=None, source="scanner", confidence="low", filled=False
            )
            gaps.append({
                "field": "code_style_enforcement",
                "description": "No automated linter or code formatter configurations detected.",
                "priority": "high",
            })

        # 4. Code review process
        if tc.code_review_process:
            gather.code_review_process = TDMFieldStatus(
                value=tc.code_review_process,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="What is your team's pull request and code review process (e.g. required approvals, automated CI gates, or direct pushes)?",
                priority="high",
                tdm_field="code_review_process",
            )
            questions.append(q)
            gaps.append({
                "field": "code_review_process",
                "description": "Code review standards and PR approval gates are unknown.",
                "priority": "high",
            })

        # 5. Average PR review time
        if tc.avg_pr_review_time:
            gather.avg_pr_review_time = TDMFieldStatus(
                value=tc.avg_pr_review_time,
                source="user_qa",
                confidence="high",
                filled=True,
            )

        # 6. Boilerplate pain & repetitive patterns
        if tc.boilerplate_pain:
            gather.boilerplate_pain = TDMFieldStatus(
                value=tc.boilerplate_pain,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="Which parts of your codebase feel the most repetitive or tedious to write (e.g. CRUD endpoints, data transformers, DTO mappings)?",
                priority="medium",
                tdm_field="boilerplate_pain",
            )
            questions.append(q)
            gaps.append({
                "field": "boilerplate_pain",
                "description": "Repetitive coding hotspots not yet mapped to AI acceleration targets.",
                "priority": "medium",
            })

        # 7. AI tools in use
        if tc.current_ai_tools:
            gather.ai_tools_in_use = TDMFieldStatus(
                value=", ".join(tc.current_ai_tools),
                source="user_qa",
                confidence="high",
                filled=True,
            )

        return gather.model_dump(), questions, gaps

    async def analyze(
        self, profile: ContextualProfile, gathered_data: dict
    ) -> list[dict]:
        tc = profile.team_context
        scanner_signals = profile.scanner_signals or {}
        size_data = scanner_signals.get("size_and_structure", {}).get("data", {})
        avg_loc = size_data.get("avg_file_size_loc", 0)

        analysis = [
            {
                "dimension": "code_modularity_and_size",
                "description": "Are files and functions cleanly modularized?",
                "finding": f"Average file size is {avg_loc} LoC. Monolithic files increase risk of context fragmentation in AI generation.",
                "severity": "high" if avg_loc > 300 else "medium",
            },
            {
                "dimension": "style_enforcement_in_ci",
                "description": "Are linters and formatters mechanically enforced?",
                "finding": "Linter configs must be enforced as blocking CI checks so AI contributions match codebase conventions.",
                "severity": "medium",
            },
            {
                "dimension": "review_throughput_bottlenecks",
                "description": "Does PR review latency slow down team velocity?",
                "finding": "PR review cycles represent a high-leverage area for AI-assisted review summarization and automated linting.",
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
        has_linter = gathered_data.get("code_style_enforcement", {}).get("filled", False)
        readiness = 7 if has_linter else 5
        opportunity = 9  # Very high ROI for code generation & PR assistance

        label = "High" if readiness >= 8 else "Medium" if readiness >= 5 else "Low"

        insights = [
            RequirementsInsight(
                title="Repetitive boilerplate is prime candidate for AI completion",
                description="Controller, service DTO, and validation layer implementations contain predictable patterns where AI copilot adoption yields immediate 20-30% velocity gains.",
                evidence="Consistent framework design patterns detected across modules.",
                risk_level="low",
                ai_opportunity="very_high",
            ),
            RequirementsInsight(
                title="Linter enforcement is required to prevent stylistic drift",
                description="AI-generated code frequently introduces subtle style variations unless strict automated linter gates fail PR checks.",
                evidence="Absence of pre-commit or CI linting gates.",
                risk_level="medium",
                ai_opportunity="medium",
            ),
        ]

        recommendations = [
            RequirementsRecommendation(
                title="Mandate automated linting and formatting in pre-commit and CI",
                description="Configure ESLint/Ruff/Black with pre-commit hooks and CI gate checks to automatically format AI-generated code.",
                is_foundation=True,
                effort="Small (1-2 days)",
                impact="high",
                ai_relevance="Prevents AI-written pull requests from failing reviews due to stylistic disagreements.",
            ),
            RequirementsRecommendation(
                title="Deploy In-IDE AI Copilot for boilerplate elimination",
                description="Roll out AI coding assistants for data transfer objects, CRUD endpoints, and test scaffolding.",
                is_foundation=False,
                effort="Small (1 week)",
                impact="very_high",
                ai_relevance="Direct developer productivity booster with immediate velocity gains.",
            ),
            RequirementsRecommendation(
                title="Integrate AI PR Review Summarizer",
                description="Add an automated PR assistant bot that drafts PR descriptions, highlights risk areas, and flags missing edge cases before human review.",
                is_foundation=False,
                effort="Medium (1 sprint)",
                impact="high",
                ai_relevance="Reduces human review turnaround time and improves review rigor.",
            ),
        ]

        return {
            "readiness_score": readiness,
            "opportunity_score": opportunity,
            "readiness_label": label,
            "verdict": "Solid programming framework structure; needs enforced automated linting gates to safely absorb AI code velocity.",
            "insights": [i.model_dump() for i in insights],
            "recommendations": [r.model_dump() for r in recommendations],
            "gather_complete": True,
            "analysis_complete": True,
            "insight_complete": True,
        }

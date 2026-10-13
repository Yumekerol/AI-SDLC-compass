"""
QA & Testing Specialist Agent

Assesses HARNESS HYGIENE:
- Evaluates test safety net depth, test-to-code ratios, and regression risks.
- Assesses whether test harnesses can automatically verify AI-written code.
- Identifies prime targets for automated AI test generation.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ..llm.base_provider import BaseLLMProvider
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import ConversationQuestion
from ..models.tdm_qa import QAGatherFields
from ..models.tdm_requirements import RequirementsInsight, RequirementsRecommendation, TDMFieldStatus
from .base_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class QAAgent(BaseSpecialistAgent):
    """Specialist agent for QA & Testing (Harness Hygiene)."""

    def __init__(self, llm_provider: BaseLLMProvider):
        super().__init__(
            llm_provider=llm_provider,
            domain_name="qa_testing",
            domain_label="QA & Testing",
        )

    async def gather(
        self, profile: ContextualProfile
    ) -> tuple[dict, list[ConversationQuestion], list[dict]]:
        tc = profile.team_context
        scanner_signals = profile.scanner_signals or {}
        stack_data = scanner_signals.get("stack_and_tooling", {}).get("data", {})
        quality_data = scanner_signals.get("quality_indicators", {}).get("data", {})

        gather = QAGatherFields()
        questions: list[ConversationQuestion] = []
        gaps: list[dict] = []

        # 1. Test framework
        test_libs = stack_data.get("testing_libraries", [])
        if test_libs:
            gather.test_framework = TDMFieldStatus(
                value=", ".join(test_libs),
                source="scanner",
                confidence="high",
                filled=True,
            )
        else:
            gather.test_framework = TDMFieldStatus(
                value=None, source="scanner", confidence="low", filled=False
            )
            gaps.append({
                "field": "test_framework",
                "description": "No recognized test frameworks (pytest, jest, JUnit) detected.",
                "priority": "critical",
            })

        # 2. Test file count
        test_count = quality_data.get("test_file_count", 0)
        gather.test_file_count = TDMFieldStatus(
            value=str(test_count),
            source="scanner",
            confidence="high",
            filled=True,
        )

        # 3. Ratio
        ratio = quality_data.get("test_to_code_file_ratio", 0.0)
        gather.code_to_test_ratio = TDMFieldStatus(
            value=f"{ratio:.2f}",
            source="scanner",
            confidence="high",
            filled=True,
        )

        # 4. Critical untested modules (Q&A)
        if tc.critical_untested_modules:
            gather.critical_untested_modules = TDMFieldStatus(
                value=tc.critical_untested_modules,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="Which modules or business paths currently lack automated tests and cause the most anxiety during releases?",
                priority="high",
                tdm_field="critical_untested_modules",
            )
            questions.append(q)
            gaps.append({
                "field": "critical_untested_modules",
                "description": "High-risk untested modules not yet identified.",
                "priority": "high",
            })

        # 5. Test types present
        if tc.test_types_present:
            gather.test_types_present = TDMFieldStatus(
                value=", ".join(tc.test_types_present),
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="What types of automated tests does your team run regularly (unit, API integration, end-to-end browser, or predominantly manual verification)?",
                priority="high",
                tdm_field="test_types_present",
            )
            questions.append(q)
            gaps.append({
                "field": "test_types_present",
                "description": "Distribution of unit vs integration vs e2e tests is unconfirmed.",
                "priority": "high",
            })

        # 6. Test data strategy
        if tc.test_data_strategy:
            gather.test_data_strategy = TDMFieldStatus(
                value=tc.test_data_strategy,
                source="user_qa",
                confidence="high",
                filled=True,
            )

        # 7. Regression frequency
        if tc.regression_frequency:
            gather.regression_frequency = TDMFieldStatus(
                value=tc.regression_frequency,
                source="user_qa",
                confidence="high",
                filled=True,
            )

        return gather.model_dump(), questions, gaps

    async def analyze(
        self, profile: ContextualProfile, gathered_data: dict
    ) -> list[dict]:
        scanner_signals = profile.scanner_signals or {}
        quality_data = scanner_signals.get("quality_indicators", {}).get("data", {})
        test_count = quality_data.get("test_file_count", 0)
        source_count = quality_data.get("source_file_count", 0)

        analysis = [
            {
                "dimension": "test_harness_adequacy_for_ai",
                "description": "Can tests catch hallucinated edge cases in AI code?",
                "finding": f"Repository has {test_count} test files against {source_count} source files. "
                           + ("Insufficient safety net to prevent AI regression risks." if test_count < 5 else "Basic test suite present, but integration coverage is limited."),
                "severity": "critical" if test_count < 3 else "high",
            },
            {
                "dimension": "test_data_and_mocking_maturity",
                "description": "Are test fixtures clean enough for automated test synthesis?",
                "finding": "Test fixtures require standardized mocking utilities to enable AI agents to autonomously generate new regression tests.",
                "severity": "medium",
            },
            {
                "dimension": "flaky_tests_and_execution_speed",
                "description": "Are test suites fast and reliable enough for rapid feedback?",
                "finding": "Feedback loop from test execution must run within seconds to enable interactive AI code-generation iteration.",
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
        scanner_signals = profile.scanner_signals or {}
        quality_data = scanner_signals.get("quality_indicators", {}).get("data", {})
        test_count = quality_data.get("test_file_count", 0)

        # If tests are minimal, readiness is low, but opportunity for automated test generation is maximum
        readiness = 3 if test_count == 0 else 4 if test_count < 5 else 6
        opportunity = 10  # Prime target for AI test generation

        label = "Critical" if readiness <= 3 else "Low" if readiness <= 5 else "Medium"

        insights = [
            RequirementsInsight(
                title="Fragile safety harness blocks autonomous AI code commits",
                description="Without comprehensive regression tests, adopting AI code generation will amplify debugging time and bug escape rates into production.",
                evidence=f"Low test file count ({test_count}) relative to codebase volume.",
                risk_level="critical",
                ai_opportunity="very_high",
            ),
            RequirementsInsight(
                title="Immediate high-value opportunity in AI-generated Unit Tests",
                description="AI tools excel at analyzing existing pure functions and generating high-coverage pytest/jest unit tests with parameterized edge cases.",
                evidence="Existing source files have clean inputs and outputs ready for test synthesis.",
                risk_level="low",
                ai_opportunity="very_high",
            ),
        ]

        recommendations = [
            RequirementsRecommendation(
                title="Establish foundational test suites for critical core logic",
                description="Create automated test files covering primary business logic modules before expanding generative coding tools.",
                is_foundation=True,
                effort="Medium (1 sprint)",
                impact="critical",
                ai_relevance="The prerequisite safety net required before allowing AI assistants to touch core domain logic.",
            ),
            RequirementsRecommendation(
                title="Deploy AI Test Generation Agent for untested modules",
                description="Use AI to automatically draft unit and integration tests for uncovered functions, including boundary value and error condition assertions.",
                is_foundation=False,
                effort="Small (1 week)",
                impact="very_high",
                ai_relevance="Accelerates test coverage creation by 4x without burdening senior developers.",
            ),
        ]

        return {
            "readiness_score": readiness,
            "opportunity_score": opportunity,
            "readiness_label": label,
            "verdict": "Test harness is currently insufficient to safely validate AI-written code; bootstrap automated tests first.",
            "insights": [i.model_dump() for i in insights],
            "recommendations": [r.model_dump() for r in recommendations],
            "gather_complete": True,
            "analysis_complete": True,
            "insight_complete": True,
        }

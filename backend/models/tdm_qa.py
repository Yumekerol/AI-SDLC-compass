"""
Target Diagnostic Model — QA & Testing Agent

Defines the HARNESS HYGIENE assessment schema.

Assesses whether testing infrastructure can automatically verify AI-written code,
and identifies high-risk untested areas for automated test generation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from .tdm_requirements import TDMFieldStatus


class QAGatherFields(BaseModel):
    """GATHER phase: fields the agent must fill."""
    test_framework: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="pytest / jest / JUnit / none"
    )
    test_file_count: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Number of test files detected"
    )
    code_to_test_ratio: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Ratio of source files to test files"
    )
    test_types_present: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="unit / integration / e2e / none"
    )
    external_testing_tools: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Postman / Selenium / manual QA"
    )
    test_data_strategy: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="fixtures / factories / production copies"
    )
    critical_untested_modules: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Which areas worry the team most?"
    )
    regression_frequency: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="How often do bugs resurface?"
    )
    qa_role_workflow: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Dedicated QA person's actual process"
    )


class QAAnalysisDimension(BaseModel):
    """A single analysis dimension with its finding."""
    dimension: str
    description: str
    finding: str | None = None
    severity: str | None = None


class QAInsight(BaseModel):
    """A contextual insight produced by the QA agent."""
    title: str
    description: str
    evidence: str | None = None
    risk_level: str = "medium"
    ai_opportunity: str = "medium"


class QARecommendation(BaseModel):
    """A specific recommendation for testing hygiene or AI adoption."""
    title: str
    description: str
    is_foundation: bool = False
    effort: str = ""
    impact: str = ""
    ai_relevance: str = ""


class TDMQA(BaseModel):
    """
    Complete Target Diagnostic Model for the QA & Testing Agent.

    Assesses HARNESS HYGIENE: Can the testing infrastructure automatically
    verify AI-written code, and where should AI test generation be deployed?
    """
    domain: str = "qa_testing"
    domain_label: str = "QA & Testing"

    # Phase 1: GATHER
    gather: QAGatherFields = Field(default_factory=QAGatherFields)

    # Phase 2: ANALYZE
    analysis: list[QAAnalysisDimension] = Field(default_factory=lambda: [
        QAAnalysisDimension(
            dimension="coverage_distribution",
            description="Are tests covering critical paths or just utilities?"
        ),
        QAAnalysisDimension(
            dimension="test_quality",
            description="Are existing tests meaningful or superficial assertions?"
        ),
        QAAnalysisDimension(
            dimension="risk_exposure",
            description="Which untested areas carry highest business risk?"
        ),
        QAAnalysisDimension(
            dimension="testing_roi_map",
            description="Where would adding tests yield the most value?"
        ),
        QAAnalysisDimension(
            dimension="automation_gap",
            description="What's manual today that could be automated?"
        ),
    ])

    # Phase 3: INSIGHT
    readiness_score: int | None = None
    opportunity_score: int | None = None
    readiness_label: str | None = None
    insights: list[QAInsight] = Field(default_factory=list)
    recommendations: list[QARecommendation] = Field(default_factory=list)

    # Completion tracking
    gather_complete: bool = False
    analysis_complete: bool = False
    insight_complete: bool = False

    def get_unfilled_fields(self) -> list[str]:
        """Return names of TDM gather fields that are not yet filled."""
        unfilled = []
        for field_name, field_status in self.gather:
            if not field_status.filled:
                unfilled.append(field_name)
        return unfilled

    def completion_ratio(self) -> float:
        """Return the percentage of gather fields that are filled."""
        total = 0
        filled = 0
        for _, field_status in self.gather:
            total += 1
            if field_status.filled:
                filled += 1
        return filled / total if total > 0 else 0.0

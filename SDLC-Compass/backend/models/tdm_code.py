"""
Target Diagnostic Model — Code & Refactoring Agent

Defines the CODE HYGIENE assessment schema.

Assesses whether code quality practices (linting, modularity, review processes)
are mature enough to safely adopt AI code generation tools, and identifies
complexity hotspots where AI refactoring delivers maximum velocity gains.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from .tdm_requirements import TDMFieldStatus


class CodeGatherFields(BaseModel):
    """GATHER phase: fields the agent must fill."""
    primary_language: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Main language detected from scanner"
    )
    frameworks: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Frameworks detected from scanner"
    )
    code_style_enforcement: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="ESLint / Prettier / Black / none"
    )
    code_review_process: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="PR reviews / pair programming / none"
    )
    avg_pr_review_time: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="hours / days"
    )
    boilerplate_pain: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Which patterns feel repetitive?"
    )
    refactoring_backlog: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Known tech debt areas"
    )
    ai_tools_in_use: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Copilot / Cursor / ChatGPT / none"
    )


class CodeAnalysisDimension(BaseModel):
    """A single analysis dimension with its finding."""
    dimension: str
    description: str
    finding: str | None = None
    severity: str | None = None


class CodeInsight(BaseModel):
    """A contextual insight produced by the Code agent."""
    title: str
    description: str
    evidence: str | None = None
    risk_level: str = "medium"
    ai_opportunity: str = "medium"


class CodeRecommendation(BaseModel):
    """A specific recommendation for code hygiene or AI adoption."""
    title: str
    description: str
    is_foundation: bool = False
    effort: str = ""
    impact: str = ""
    ai_relevance: str = ""


class TDMCode(BaseModel):
    """
    Complete Target Diagnostic Model for the Code & Refactoring Agent.

    Assesses CODE HYGIENE: Are code quality practices mature enough to
    safely adopt AI code generation, and where are complexity bottlenecks?
    """
    domain: str = "code_refactoring"
    domain_label: str = "Code & Refactoring"

    # Phase 1: GATHER
    gather: CodeGatherFields = Field(default_factory=CodeGatherFields)

    # Phase 2: ANALYZE
    analysis: list[CodeAnalysisDimension] = Field(default_factory=lambda: [
        CodeAnalysisDimension(
            dimension="boilerplate_density",
            description="What % of code is repetitive scaffolding vs. business logic?"
        ),
        CodeAnalysisDimension(
            dimension="complexity_hotspots",
            description="Which files/modules carry disproportionate complexity?"
        ),
        CodeAnalysisDimension(
            dimension="framework_utilization",
            description="Is the team using framework features or reinventing wheels?"
        ),
        CodeAnalysisDimension(
            dimension="review_bottleneck",
            description="Is PR review time a delivery constraint?"
        ),
        CodeAnalysisDimension(
            dimension="ai_tool_effectiveness",
            description="If AI tools are in use, are they used effectively?"
        ),
    ])

    # Phase 3: INSIGHT
    readiness_score: int | None = None
    opportunity_score: int | None = None
    readiness_label: str | None = None
    insights: list[CodeInsight] = Field(default_factory=list)
    recommendations: list[CodeRecommendation] = Field(default_factory=list)

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

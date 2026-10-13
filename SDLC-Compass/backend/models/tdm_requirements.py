"""
Target Diagnostic Model — Requirements & Design Agent

Defines the SPEC HYGIENE assessment schema.

The TDM specifies:
  - GATHER fields: What the agent needs to know (some from scanner, some from Q&A)
  - ANALYZE dimensions: What reasoning the agent performs
  - INSIGHT outputs: The structured findings and recommendations
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TDMFieldStatus(BaseModel):
    """Tracks the fill state of a single TDM field."""
    value: str | None = None
    source: str = "unknown"  # "scanner", "user_qa", "agent_inference"
    confidence: str = "unknown"  # "high", "medium", "low"
    filled: bool = False


class RequirementsGatherFields(BaseModel):
    """GATHER phase: fields the agent must fill to complete its model."""
    requirements_format: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Jira stories / Notion docs / verbal / none"
    )
    acceptance_criteria_exist: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="yes / partial / no"
    )
    api_specification: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="OpenAPI / Swagger / GraphQL schema / none"
    )
    architecture_documentation: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="diagrams / ADRs / wiki / none"
    )
    design_review_process: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="formal / informal / none"
    )
    stakeholder_communication: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="structured / ad-hoc"
    )


class RequirementsAnalysisDimension(BaseModel):
    """A single analysis dimension with its finding."""
    dimension: str
    description: str
    finding: str | None = None
    severity: str | None = None  # "critical", "high", "medium", "low", "none"


class RequirementsInsight(BaseModel):
    """A single contextual insight produced by the agent."""
    title: str
    description: str
    evidence: str | None = None
    risk_level: str = "medium"  # "critical", "high", "medium", "low"
    ai_opportunity: str = "medium"  # "very_high", "high", "medium", "low"


class RequirementsRecommendation(BaseModel):
    """A specific, actionable recommendation."""
    title: str
    description: str
    is_foundation: bool = False  # True = prerequisite fix; False = AI tool adoption
    effort: str = ""  # "Small (1-2 days)", "Medium (1 sprint)", etc.
    impact: str = ""
    ai_relevance: str = ""  # Why this matters for AI adoption


class TDMRequirements(BaseModel):
    """
    Complete Target Diagnostic Model for the Requirements & Design Agent.

    Assesses SPEC HYGIENE: Are the team's specifications mature enough
    to feed AI code generators, and where can AI eliminate requirements ambiguity?
    """
    domain: str = "requirements_design"
    domain_label: str = "Requirements & Design"

    # Phase 1: GATHER
    gather: RequirementsGatherFields = Field(default_factory=RequirementsGatherFields)

    # Phase 2: ANALYZE
    analysis: list[RequirementsAnalysisDimension] = Field(default_factory=lambda: [
        RequirementsAnalysisDimension(
            dimension="spec_to_code_drift",
            description="How far has implementation diverged from specs?"
        ),
        RequirementsAnalysisDimension(
            dimension="knowledge_bus_factor",
            description="Is critical design knowledge documented or tribal?"
        ),
        RequirementsAnalysisDimension(
            dimension="requirements_traceability",
            description="Can you trace a feature from requirement → code → test?"
        ),
        RequirementsAnalysisDimension(
            dimension="communication_gaps",
            description="Where does information get lost between roles?"
        ),
    ])

    # Phase 3: INSIGHT
    readiness_score: int | None = None  # 1-10
    opportunity_score: int | None = None  # 1-10
    readiness_label: str | None = None  # "High", "Medium", "Low", "Critical"
    insights: list[RequirementsInsight] = Field(default_factory=list)
    recommendations: list[RequirementsRecommendation] = Field(default_factory=list)

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

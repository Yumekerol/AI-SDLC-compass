"""
Target Diagnostic Model — DevOps & Monitoring Agent

Defines the OPS HYGIENE assessment schema.

Assesses whether the deployment environment is automated enough to support
autonomous AI agents, and identifies ops tasks where AI reduces incident
recovery time.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from .tdm_requirements import TDMFieldStatus


class DevOpsGatherFields(BaseModel):
    """GATHER phase: fields the agent must fill."""
    has_pipeline: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="CI/CD pipeline detected by scanner"
    )
    has_dockerfile: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Dockerfile or containerization present"
    )
    deployment_method: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="manual SSH / CI/CD / PaaS / k8s"
    )
    deployment_frequency: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="daily / weekly / monthly / ad-hoc"
    )
    environment_count: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="dev / staging / prod"
    )
    rollback_strategy: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="manual / automated / none"
    )
    monitoring_tools: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Datadog / Grafana / CloudWatch / none"
    )
    logging_strategy: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="structured / unstructured / none"
    )
    incident_response: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="runbook / ad-hoc debugging"
    )
    downtime_history: TDMFieldStatus = Field(
        default_factory=TDMFieldStatus,
        description="Recent outages and root causes"
    )


class DevOpsAnalysisDimension(BaseModel):
    """A single analysis dimension with its finding."""
    dimension: str
    description: str
    finding: str | None = None
    severity: str | None = None


class DevOpsInsight(BaseModel):
    """A contextual insight produced by the DevOps agent."""
    title: str
    description: str
    evidence: str | None = None
    risk_level: str = "medium"
    ai_opportunity: str = "medium"


class DevOpsRecommendation(BaseModel):
    """A specific recommendation for ops hygiene or AI adoption."""
    title: str
    description: str
    is_foundation: bool = False
    effort: str = ""
    impact: str = ""
    ai_relevance: str = ""


class TDMDevOps(BaseModel):
    """
    Complete Target Diagnostic Model for the DevOps & Monitoring Agent.

    Assesses OPS HYGIENE: Is the deployment environment automated enough
    to support AI-driven operations, and where can AI reduce incident MTTR?
    """
    domain: str = "devops_monitoring"
    domain_label: str = "DevOps & Monitoring"

    # Phase 1: GATHER
    gather: DevOpsGatherFields = Field(default_factory=DevOpsGatherFields)

    # Phase 2: ANALYZE
    analysis: list[DevOpsAnalysisDimension] = Field(default_factory=lambda: [
        DevOpsAnalysisDimension(
            dimension="deployment_risk",
            description="How risky is each deployment? What can go wrong?"
        ),
        DevOpsAnalysisDimension(
            dimension="recovery_capability",
            description="If something breaks, how fast can you recover?"
        ),
        DevOpsAnalysisDimension(
            dimension="observability_gap",
            description="Can you tell when something is wrong before users do?"
        ),
        DevOpsAnalysisDimension(
            dimension="automation_maturity",
            description="What's the distance from current state to full CI/CD?"
        ),
        DevOpsAnalysisDimension(
            dimension="operational_overhead",
            description="How much time does the team spend on ops vs. features?"
        ),
    ])

    # Phase 3: INSIGHT
    readiness_score: int | None = None
    opportunity_score: int | None = None
    readiness_label: str | None = None
    insights: list[DevOpsInsight] = Field(default_factory=list)
    recommendations: list[DevOpsRecommendation] = Field(default_factory=list)

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

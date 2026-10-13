"""
Synthesis Output Model

The Synthesizer Agent's output schema — the final consulting deliverable
that cross-references all 4 specialist agent findings and produces a
prioritized, phased implementation roadmap.

Maps directly to the Step 4 (Diagnostic Report) UI in the Figma.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReadinessScore(BaseModel):
    """Readiness and opportunity score for a single SDLC domain."""
    domain: str  # "requirements_design", "code_refactoring", etc.
    domain_label: str  # "Requirements & Design"
    readiness_score: int  # 1-10
    opportunity_score: int  # 1-10
    readiness_label: str  # "High", "Medium", "Low", "Critical"
    verdict: str  # One-line summary of the hygiene state


class Recommendation(BaseModel):
    """A single prioritized recommendation in the phased roadmap."""
    id: str
    title: str
    domain: str
    description: str
    effort: str  # "Small (1-2 days)", "Medium (1 sprint)", etc.
    impact: str  # "critical", "very_high", "high", "medium", "low"
    risk_level: str  # "critical", "high", "medium", "low"
    prerequisites: list[str] = Field(default_factory=list)  # IDs of prerequisite recs
    ai_relevance: str = ""  # Why this matters for AI adoption
    is_foundation: bool = False  # True = prerequisite fix; False = AI tool adoption


class RecommendationPhase(BaseModel):
    """A phase in the implementation roadmap."""
    phase_label: str
    phase_description: str
    estimated_effort: str
    recommendations: list[Recommendation] = Field(default_factory=list)


class ConversationHighlight(BaseModel):
    """A key exchange from the diagnostic conversation worth highlighting."""
    agent_domain: str
    key_exchange: str
    insight_derived: str


class KnowledgeGapSummary(BaseModel):
    """Summary of resolved vs unresolved knowledge gaps."""
    total_resolved: int = 0
    total_asked: int = 0
    unresolved_gaps: list[dict] = Field(default_factory=list)


class ReportDisclaimers(BaseModel):
    """Legal and accuracy disclaimers for the report."""
    scope: str = "This diagnostic covers the reviewed repository scope only."
    accuracy: str = "Signals are estimates based on static analysis; executed metrics were not measured."
    affiliation: str = "Independent concept. Not affiliated with or endorsed by Accenture."


class SynthesisOutput(BaseModel):
    """
    The complete diagnostic report produced by the Synthesizer Agent.

    This is the final deliverable — a structured, prioritized assessment
    of AI readiness and adoption opportunities across the SDLC.
    """
    session_id: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Repository metadata (carried forward)
    repository: dict = Field(default_factory=dict)

    # Executive summary
    executive_summary: dict = Field(default_factory=lambda: {
        "headline": "",
        "overall_readiness": "medium",
        "overall_readiness_score": 0.0,
        "summary_text": "",
    })

    # Readiness scorecard (the 4 hygiene dimensions)
    readiness_scorecard: dict[str, ReadinessScore] = Field(default_factory=dict)

    # Knowledge gaps
    knowledge_gaps_summary: KnowledgeGapSummary = Field(
        default_factory=KnowledgeGapSummary
    )

    # Phased recommendations (the 3 implementation horizons)
    phased_recommendations: dict[str, RecommendationPhase] = Field(
        default_factory=lambda: {
            "phase_1_foundation": RecommendationPhase(
                phase_label="Phase 1: Stabilise before scaling",
                phase_description="Fix structural hygiene gaps that would make AI adoption risky",
                estimated_effort="1-2 sprints",
            ),
            "phase_2_quick_wins": RecommendationPhase(
                phase_label="Phase 2: High-ROI AI adoption",
                phase_description="Deploy AI tools where readiness is proven and ROI is immediate",
                estimated_effort="2-3 sprints",
            ),
            "phase_3_advanced": RecommendationPhase(
                phase_label="Phase 3: Advanced AI workflows",
                phase_description="Unlock gated opportunities once foundations are stable",
                estimated_effort="Ongoing",
            ),
        }
    )

    # Conversation highlights for the report
    conversation_highlights: list[ConversationHighlight] = Field(default_factory=list)

    # Disclaimers
    disclaimers: ReportDisclaimers = Field(default_factory=ReportDisclaimers)

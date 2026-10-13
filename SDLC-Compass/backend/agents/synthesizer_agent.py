"""
Synthesizer Agent

Cross-references findings from all 4 specialist agents (Spec, Code, Harness, Ops)
to produce the consulting deliverable:
- Overall AI readiness score and executive summary headline
- Multi-dimensional readiness scorecard
- Phased 3-horizon implementation roadmap (Foundation → Quick Wins → Advanced)
- Prerequisite sequencing and ROI ranking
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from ..llm.base_provider import BaseLLMProvider
from ..models.contextual_profile import ContextualProfile
from ..models.synthesis import (
    ConversationHighlight,
    KnowledgeGapSummary,
    ReadinessScore,
    Recommendation,
    RecommendationPhase,
    ReportDisclaimers,
    SynthesisOutput,
)

logger = logging.getLogger(__name__)


class SynthesizerAgent:
    """Agent that aggregates specialist insights into a prioritized deliverable."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def synthesize(
        self,
        session_id: str,
        profile: ContextualProfile,
        agent_results: dict[str, dict],
    ) -> SynthesisOutput:
        """
        Aggregate all specialist agent outputs into the final SynthesisOutput report.
        """
        scanner_signals = profile.scanner_signals or {}
        lang_data = scanner_signals.get("languages", {}).get("data", {})
        stack_data = scanner_signals.get("stack_and_tooling", {}).get("data", {})
        repo_info = scanner_signals.get("repository", {})

        # 1. Build Scorecard
        scorecard: dict[str, ReadinessScore] = {}
        total_readiness = 0.0
        domain_weights = {
            "requirements_design": ("spec_hygiene", "Requirements & Design", 0.20),
            "code_refactoring": ("code_hygiene", "Code & Refactoring", 0.25),
            "qa_testing": ("harness_hygiene", "QA & Testing", 0.35),
            "devops_monitoring": ("ops_hygiene", "DevOps & Monitoring", 0.20),
        }

        for agent_key, (card_key, label, weight) in domain_weights.items():
            res = agent_results.get(agent_key, {})
            r_score = res.get("readiness_score", 5)
            o_score = res.get("opportunity_score", 7)
            r_label = res.get("readiness_label", "Medium")
            verdict = res.get("verdict", f"{label} assessment complete.")

            scorecard[card_key] = ReadinessScore(
                domain=agent_key,
                domain_label=label,
                readiness_score=r_score,
                opportunity_score=o_score,
                readiness_label=r_label,
                verdict=verdict,
            )
            total_readiness += r_score * weight

        overall_score = round(total_readiness, 1)
        overall_label = "high" if overall_score >= 7.5 else "medium" if overall_score >= 4.5 else "low"

        # 2. Executive Summary
        if overall_score >= 7.0:
            headline = "Mature engineering foundations ready for accelerated AI adoption"
            summary_text = (
                f"The repository demonstrates strong hygiene across specifications and code structure. "
                f"The team is well-positioned to deploy generative AI copilots and automated PR review assistants."
            )
        elif overall_score >= 4.5:
            headline = "Stabilise testing and release practices before scaling AI adoption"
            summary_text = (
                f"The repository possesses a functional framework foundation, but critical gaps in test safety harnesses "
                f"and deployment automation create operational risk. Establish test gates before adopting high-velocity AI code generation."
            )
        else:
            headline = "Address critical hygiene prerequisites prior to AI implementation"
            summary_text = (
                f"The codebase lacks essential automated testing and continuous integration safeguards. "
                f"Introducing AI code generation without these guardrails will compound regression defects."
            )

        # 3. Compile Phased Recommendations
        phase_1_recs: list[Recommendation] = []
        phase_2_recs: list[Recommendation] = []
        phase_3_recs: list[Recommendation] = []

        rec_counter = 1
        for agent_key, res in agent_results.items():
            domain_recs = res.get("recommendations", [])
            for r in domain_recs:
                rec_id = f"rec-{rec_counter}"
                rec_counter += 1
                rec_model = Recommendation(
                    id=rec_id,
                    title=r.get("title", ""),
                    domain=agent_key,
                    description=r.get("description", ""),
                    effort=r.get("effort", "Medium (1 sprint)"),
                    impact=r.get("impact", "high"),
                    risk_level="low" if r.get("is_foundation") else "medium",
                    prerequisites=[],
                    ai_relevance=r.get("ai_relevance", ""),
                    is_foundation=r.get("is_foundation", False),
                )
                if r.get("is_foundation", False):
                    phase_1_recs.append(rec_model)
                elif r.get("impact") in ("very_high", "critical"):
                    phase_2_recs.append(rec_model)
                else:
                    phase_3_recs.append(rec_model)

        # Connect prerequisites: phase 2 recs depend on phase 1 foundation recs
        foundation_ids = [r.id for r in phase_1_recs]
        for r in phase_2_recs:
            r.prerequisites = foundation_ids[:2]
        for r in phase_3_recs:
            r.prerequisites = foundation_ids[:1]

        phased_recommendations = {
            "phase_1_foundation": RecommendationPhase(
                phase_label="Phase 1: Stabilise before scaling",
                phase_description="Fix structural hygiene gaps that would make AI adoption risky",
                estimated_effort="1-2 sprints",
                recommendations=phase_1_recs,
            ),
            "phase_2_quick_wins": RecommendationPhase(
                phase_label="Phase 2: High-ROI AI adoption",
                phase_description="Deploy AI tools where readiness is proven and ROI is immediate",
                estimated_effort="2-3 sprints",
                recommendations=phase_2_recs,
            ),
            "phase_3_advanced": RecommendationPhase(
                phase_label="Phase 3: Advanced AI workflows",
                phase_description="Unlock gated opportunities once foundations are stable",
                estimated_effort="Ongoing",
                recommendations=phase_3_recs,
            ),
        }

        # 4. Compile Knowledge Gaps Summary
        all_unresolved = []
        total_gaps_count = 0
        for agent_key, res in agent_results.items():
            gaps = res.get("gaps", [])
            total_gaps_count += len(gaps)
            for g in gaps:
                all_unresolved.append({
                    "domain": agent_key,
                    "field": g.get("field", ""),
                    "description": g.get("description", ""),
                })

        gaps_summary = KnowledgeGapSummary(
            total_resolved=max(0, 16 - len(all_unresolved)),
            total_asked=16,
            unresolved_gaps=all_unresolved,
        )

        # 5. Conversation Highlights
        highlights = [
            ConversationHighlight(
                agent_domain="requirements_design",
                key_exchange="Assessed requirement format and API contract formality.",
                insight_derived="In-repo OpenAPI specifications needed before deploying autonomous code generators.",
            ),
            ConversationHighlight(
                agent_domain="qa_testing",
                key_exchange="Identified lack of automated regression harnesses for core business paths.",
                insight_derived="Prioritize AI test generation over generative code writing.",
            ),
            ConversationHighlight(
                agent_domain="devops_monitoring",
                key_exchange="Evaluated deployment automation and pipeline gates.",
                insight_derived="Staging preview environment required to validate AI contributions.",
            ),
        ]

        return SynthesisOutput(
            session_id=session_id,
            generated_at=datetime.utcnow(),
            repository={
                "name": repo_info.get("name", "Repository"),
                "branch": repo_info.get("branch", "main"),
                "commit_hash": repo_info.get("commit_hash", "HEAD"),
                "languages": [b.get("language") for b in lang_data.get("breakdown", [])][:3],
                "frameworks": stack_data.get("frameworks", []),
            },
            executive_summary={
                "headline": headline,
                "overall_readiness": overall_label,
                "overall_readiness_score": overall_score,
                "summary_text": summary_text,
            },
            readiness_scorecard=scorecard,
            knowledge_gaps_summary=gaps_summary,
            phased_recommendations=phased_recommendations,
            conversation_highlights=highlights,
            disclaimers=ReportDisclaimers(),
        )

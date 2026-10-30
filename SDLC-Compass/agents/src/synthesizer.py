"""
Final synthesis: takes the 4 specialists' compact Reports (not their raw
tool-calling transcripts — that's the point of the note()/scratchpad design)
and produces one report dict.

The output schema below is not invented — it matches `BackendSynthesisOutput`
in `frontend/src/api/types.ts` field-for-field, which is what `ReportView.vue`
renders and what `backend/report/generator.py`'s PDF template reads. Matching
it exactly means neither of those needs to change for this pipeline to work.
"""

from __future__ import annotations

from typing import Literal

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from .config import settings
from .specialists.base import Report

PHASE_KEYS = ("phase_1_foundation", "phase_2_quick_wins", "phase_3_advanced")


class ReadinessScore(BaseModel):
    domain: str
    domain_label: str
    readiness_score: int = Field(ge=0, le=10)
    opportunity_score: int = Field(ge=0, le=10)
    readiness_label: Literal["Critical", "Weak", "Developing", "Solid", "Strong"]
    """A short badge label, not a sentence — report/generator.py renders this
    directly inside a pill. Constrained to a fixed set rather than left as a
    free string, since a local model will otherwise happily return a full
    sentence here (seen in real testing)."""
    verdict: str


class Recommendation(BaseModel):
    id: str
    title: str
    domain: str
    description: str
    effort: str
    impact: str
    risk_level: str
    prerequisites: list[str] = Field(default_factory=list)
    ai_relevance: str = ""
    is_foundation: bool = False


class RecommendationPhase(BaseModel):
    phase_label: str
    phase_description: str
    estimated_effort: str
    recommendations: list[Recommendation] = Field(default_factory=list)


class ExecutiveSummary(BaseModel):
    headline: str
    overall_readiness: Literal["Critical", "Weak", "Developing", "Solid", "Strong"]
    """Same fixed set as ReadinessScore.readiness_label, for the same reason:
    left as a free string, a local model returned "And" here in real testing."""
    overall_readiness_score: float
    summary_text: str


class SynthesisOutput(BaseModel):
    executive_summary: ExecutiveSummary
    readiness_scorecard: dict[str, ReadinessScore]
    phased_recommendations: dict[Literal["phase_1_foundation", "phase_2_quick_wins", "phase_3_advanced"], RecommendationPhase]
    disclaimers: dict[str, str] = Field(
        default_factory=lambda: {
            "scope": "This diagnostic reflects what the repository and the answers provided reveal; it is not a complete audit.",
            "accuracy": "Findings are produced by an AI reviewer and may contain errors — verify before acting.",
            "affiliation": "AI-SDLC Compass is not affiliated with any tool or vendor it mentions.",
        }
    )


SYNTHESIS_SYSTEM_PROMPT = """You are the Synthesizer for an AI-SDLC Compass diagnostic. You receive \
structured findings from 4 specialists (Requirements & Design, Code & Refactoring, QA & Testing, \
DevOps & Monitoring), each a list of discrete findings with evidence. Your job:

1. Write a short, honest executive summary grounded in what the specialists actually found \
   (overall_readiness_score is 0-10, aggregating the 4 domain scores; be conservative — a repo with \
   little evidence should not score high). overall_readiness is ONE of exactly: "Critical", "Weak", \
   "Developing", "Solid", "Strong".
2. Produce one readiness_scorecard entry per domain (readiness_score and opportunity_score 0-10, \
   both grounded in the findings, not guessed). readiness_label is ONE of exactly: "Critical", \
   "Weak", "Developing", "Solid", "Strong" — never a sentence or anything else. verdict is where the \
   explanation goes, one or two sentences.
3. Produce phased_recommendations across exactly three phases — phase_1_foundation (prerequisites that \
   block everything else), phase_2_quick_wins (low-effort, high-impact), phase_3_advanced (deeper AI \
   integration work) — each with concrete recommendations tied back to specific findings.

Do not invent findings the specialists didn't report. If a domain has little evidence, say so plainly \
in its verdict rather than scoring it as if it were well understood."""


def _format_reports(reports: list[Report]) -> str:
    sections = []
    for report in reports:
        findings_text = "\n".join(
            f"  - [{f.confidence}] {f.claim} (evidence: {', '.join(f.evidence_paths) or 'none'})"
            for f in report.findings
        ) or "  (no findings recorded)"
        sections.append(
            f"## {report.label} ({report.role})\nStatus: {report.status}\n"
            f"Summary: {report.summary or '(none)'}\nFindings:\n{findings_text}"
        )
    return "\n\n".join(sections)


async def synthesize(reports: list[Report]) -> dict:
    model = ChatOllama(
        model=settings.chat_model,
        base_url=settings.ollama_host,
        temperature=settings.temperature,
        num_ctx=settings.num_ctx,
        num_predict=settings.synthesis_num_predict,
        reasoning=settings.think,
        keep_alive=settings.keep_alive,
    )
    structured_model = model.with_structured_output(SynthesisOutput)

    findings_text = _format_reports(reports)
    result: SynthesisOutput = await structured_model.ainvoke(
        [
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": f"Specialist findings:\n\n{findings_text}"},
        ]
    )

    # Guarantee all three phase keys exist even if the model only filled some.
    phases = {key: result.phased_recommendations.get(key) for key in PHASE_KEYS}
    for key, default_label in zip(
        PHASE_KEYS, ("Foundation", "Quick wins", "Advanced AI integration")
    ):
        if phases[key] is None:
            phases[key] = RecommendationPhase(
                phase_label=default_label, phase_description="", estimated_effort="unknown"
            )

    output = result.model_copy(update={"phased_recommendations": phases})
    return output.model_dump(mode="json")

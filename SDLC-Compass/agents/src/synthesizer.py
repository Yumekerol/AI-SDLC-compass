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

import json
from typing import Any, Literal

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
    repository_evidence: str = ""
    """What in the repository backs this recommendation: file paths and the
    specialist finding they support. Empty only if no finding supports it."""
    team_input: str = ""
    """What the team said that bears on this recommendation. Empty when the
    team said nothing relevant; never invented."""


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
4. For every recommendation fill two fields that show why it is there:
   - repository_evidence: one sentence naming the repository evidence behind it — the file paths \
     and the specialist finding they support (e.g. "6 test files for 42 source files; \
     .github/workflows/build.yml has no test step").
   - team_input: one sentence on what the team said that bears on it, drawn only from the team's \
     answers and team context below. If the team said nothing relevant, leave it as an empty string.

Do not invent findings the specialists didn't report. If a domain has little evidence, say so plainly \
in its verdict rather than scoring it as if it were well understood."""


def _format_reports(reports: list[Report]) -> str:
    sections = []
    for report in reports:
        findings_text = "\n".join(
            f"  - [{f.confidence}] {f.claim} (evidence: {', '.join(f.evidence_paths) or 'none'})"
            for f in report.findings
        ) or "  (no findings recorded)"
        answers_text = "\n".join(
            f"  - Q: {a.question}\n    A: {a.answer}" for a in report.team_answers
        ) or "  (the team was not asked or did not answer)"
        sections.append(
            f"## {report.label} ({report.role})\nStatus: {report.status}\n"
            f"Summary: {report.summary or '(none)'}\nFindings:\n{findings_text}\n"
            f"Team answers:\n{answers_text}"
        )
    return "\n\n".join(sections)


def _model(num_predict: int) -> ChatOllama:
    return ChatOllama(
        model=settings.chat_model,
        base_url=settings.ollama_host,
        temperature=settings.temperature,
        num_ctx=settings.num_ctx,
        num_predict=num_predict,
        reasoning=settings.think,
        keep_alive=settings.keep_alive,
    )


def _fill_missing_phases(result: SynthesisOutput) -> dict:
    """Guarantee all three phase keys exist even if the model only filled some."""
    phases = {key: result.phased_recommendations.get(key) for key in PHASE_KEYS}
    for key, default_label in zip(
        PHASE_KEYS, ("Foundation", "Quick wins", "Advanced AI integration")
    ):
        if phases[key] is None:
            phases[key] = RecommendationPhase(
                phase_label=default_label, phase_description="", estimated_effort="unknown"
            )
    return result.model_copy(update={"phased_recommendations": phases}).model_dump(mode="json")


async def synthesize(reports: list[Report], team_context: dict[str, Any] | None = None) -> dict:
    structured_model = _model(settings.synthesis_num_predict).with_structured_output(SynthesisOutput)

    findings_text = _format_reports(reports)
    context_text = json.dumps(team_context, default=str) if team_context else "(none provided)"
    result: SynthesisOutput = await structured_model.ainvoke(
        [
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Team context: {context_text}\n\nSpecialist findings:\n\n{findings_text}",
            },
        ]
    )

    return _fill_missing_phases(result)


# ─── Talking to Synth after the report exists ─────────────────────────
#
# Two calls, not one: answering a question is a short reply, while changing
# the report means regenerating the whole report JSON (thousands of tokens on
# a local model). `chat` decides whether a change was asked for; `revise`
# produces the changed report only when it was, and the backend runs it in
# the background so the chat reply is not held up by it.

_SYNTHESIS_KEYS = ("executive_summary", "readiness_scorecard", "phased_recommendations", "disclaimers")


class SynthChatReply(BaseModel):
    answer: str
    """The reply shown in the chat."""
    change_requested: bool = False
    """True only when the user asked to change the report itself (reword,
    reprioritise, add, remove, move or rescore something). A question or a
    challenge that needs no change to the report is False."""
    change_title: str = ""
    """When change_requested: one sentence saying what will change."""
    change_reason: str = ""
    """When change_requested: one sentence on why, in the team's terms."""


SYNTH_CHAT_SYSTEM_PROMPT = """You are the Synthesizer for an AI-SDLC Compass diagnostic. You wrote the \
report below from the specialists' findings, and the team is now asking you about it.

- Answer questions about the report, its scores and its recommendations, grounded in the report and \
  the specialist findings. If the findings do not support something, say so plainly; never invent \
  evidence.
- If the team asks you to change the report (reword, reprioritise, reorder, add, remove or rescore \
  something), set change_requested to true, put one sentence on what will change in change_title \
  and one sentence on why in change_reason, and say in answer that you have drafted the change for \
  their approval. Do not claim the report has already changed.
- If a requested change contradicts the specialist findings, still draft it if asked, but say in \
  answer what the findings show.
- Keep answer short: a few sentences."""


SYNTH_REVISE_SYSTEM_PROMPT = SYNTHESIS_SYSTEM_PROMPT + """

You are now revising a report you already wrote. Apply ONLY the requested change. Everything the \
change does not touch must come back exactly as it was: same ids, titles, wording, scores and order. \
Update the executive summary only if the change affects what it says."""


def _report_for_model(report: dict) -> str:
    return json.dumps({k: report[k] for k in _SYNTHESIS_KEYS if k in report}, indent=1, default=str)


def _parse_reports(raw: list[dict] | None) -> list[Report]:
    parsed = []
    for r in raw or []:
        try:
            parsed.append(Report.model_validate(r))
        except Exception:
            continue  # a malformed stored report shouldn't block the chat
    return parsed


def _findings_text(raw_reports: list[dict] | None) -> str:
    reports = _parse_reports(raw_reports)
    return _format_reports(reports) if reports else "(specialist findings were not kept for this report)"


async def chat(
    report: dict,
    message: str,
    history: list[dict] | None = None,
    specialist_reports: list[dict] | None = None,
) -> dict:
    structured_model = _model(settings.synthesis_chat_num_predict).with_structured_output(SynthChatReply)
    messages: list[dict] = [
        {"role": "system", "content": SYNTH_CHAT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Current report:\n{_report_for_model(report)}\n\n"
                f"Specialist findings:\n\n{_findings_text(specialist_reports)}"
            ),
        },
        {"role": "assistant", "content": "Understood. What would you like to know or change?"},
    ]
    for h in (history or [])[-10:]:
        role = "user" if h.get("role") == "user" else "assistant"
        if h.get("content"):
            messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": message})

    result: SynthChatReply = await structured_model.ainvoke(messages)
    if not result.change_requested:
        result = result.model_copy(update={"change_title": "", "change_reason": ""})
    return result.model_dump(mode="json")


async def revise(
    report: dict,
    instruction: str,
    specialist_reports: list[dict] | None = None,
) -> dict:
    """Return the report with `instruction` applied, in the same schema
    `synthesize` produces. The caller keeps any keys outside that schema."""
    structured_model = _model(settings.synthesis_num_predict).with_structured_output(SynthesisOutput)
    result: SynthesisOutput = await structured_model.ainvoke(
        [
            {"role": "system", "content": SYNTH_REVISE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current report:\n{_report_for_model(report)}\n\n"
                    f"Specialist findings:\n\n{_findings_text(specialist_reports)}\n\n"
                    f"Requested change: {instruction}"
                ),
            },
        ]
    )
    return _fill_missing_phases(result)

"""
The specialist runner — the only place a specialist agent is created.

Each call to `run_specialist`/`resume_specialist` builds a fresh `create_agent`
graph from a `SpecialistSpec` + a `RunContext`. Behavior varies entirely by
data (the spec) and injected context, not by subclassing: adding a fifth
specialist means a new prompt file and a four-line spec, not a new runner.

Findings and the tool-call cap are both derived from the LangGraph-persisted
message history rather than kept in a plain Python list/counter, specifically
so they survive the pause/resume boundary correctly: `note()` and the capped
tools run inside one HTTP request, `resume_specialist()` runs in a later,
separate one, and only the checkpointer's state actually bridges the two.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool, tool
from langchain_ollama import ChatOllama
from langgraph.types import Command, interrupt

try:
    from langchain.agents import create_agent
except ImportError:
    from langgraph.prebuilt import create_react_agent as create_agent

from .config import settings
from .context import RunContext
from .persistence import get_checkpointer
from .specialists.base import Finding, NeedsInput, Report, SpecialistSpec
from .tools import build_tools

logger = logging.getLogger(__name__)


@tool
def ask_user(question: str) -> str:
    """Ask the person running this diagnostic a clarifying question about how
    their team actually works, and wait for their answer. Only use this when
    the repository itself doesn't tell you, not for things your other tools
    could find. Ask one specific question at a time.
    """
    return interrupt({"question": question})


def _make_note_tool(ctx: RunContext):
    @tool
    def note(claim: str, evidence_paths: list[str] | None = None, confidence: str = "medium") -> str:
        """Record one finding as soon as you learn it. `claim` is the finding
        itself; `evidence_paths` are repository-relative file paths that
        support it. confidence is "low", "medium", or "high". This is
        bookkeeping, not exploration — it never counts against your tool-call
        budget.
        """
        if not claim.strip():
            return "Error: claim must not be empty."
        paths = evidence_paths or []
        missing = [p for p in paths if not (ctx.root / p).exists()]
        if missing:
            return f"Error: these evidence paths do not exist: {missing}"
        return "Noted."

    return note


def _with_cap(base_tool, counter: list[int], cap: int | None):
    """Wrap a repo tool so that once `cap` calls have been made in this run
    (seeded from prior history on resume), further calls stop doing real work
    and instead tell the model to wrap up. No-op when cap is None — the
    with/without-cap experiment is just this one argument."""
    if cap is None:
        return base_tool

    def _wrapped(**kwargs: Any) -> str:
        if counter[0] >= cap:
            return (
                f"[tool budget reached: {cap} calls] Stop exploring. Call "
                "note() for anything you haven't recorded yet, then give a "
                "brief final summary without calling any more tools."
            )
        counter[0] += 1
        return base_tool.invoke(kwargs)

    return StructuredTool.from_function(
        func=_wrapped,
        name=base_tool.name,
        description=base_tool.description,
        args_schema=base_tool.args_schema,
    )


def _build_agent(spec: SpecialistSpec, ctx: RunContext, counter: list[int]):
    available = build_tools(ctx)
    repo_tools = [_with_cap(available[name], counter, spec.max_tool_calls) for name in spec.tool_names]
    tools = repo_tools + [_make_note_tool(ctx), ask_user]

    model = ChatOllama(
        model=settings.chat_model,
        base_url=settings.ollama_host,
        temperature=settings.temperature,
        num_ctx=spec.num_ctx,
    )
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=spec.prompt,
        checkpointer=get_checkpointer(),
    )


def _tool_call_results(messages: list[Any]) -> dict[str, str]:
    results = {}
    for msg in messages:
        if getattr(msg, "type", None) == "tool":
            results[msg.tool_call_id] = str(msg.content)
    return results


def _extract_findings(messages: list[Any]) -> list[Finding]:
    results = _tool_call_results(messages)
    findings: list[Finding] = []
    for msg in messages:
        for call in getattr(msg, "tool_calls", None) or []:
            if call.get("name") != "note":
                continue
            if results.get(call.get("id"), "").startswith("Error:"):
                continue
            args = call.get("args") or {}
            findings.append(
                Finding(
                    claim=args.get("claim", ""),
                    evidence_paths=args.get("evidence_paths") or [],
                    confidence=args.get("confidence", "medium"),
                )
            )
    return findings


def _count_tool_calls(messages: list[Any], tool_names: list[str]) -> int:
    names = set(tool_names)
    count = 0
    for msg in messages:
        count += sum(1 for c in getattr(msg, "tool_calls", None) or [] if c.get("name") in names)
    return count


def _extract_questions_asked(messages: list[Any]) -> list[str]:
    questions: list[str] = []
    for msg in messages:
        for call in getattr(msg, "tool_calls", None) or []:
            if call.get("name") == "ask_user":
                question = (call.get("args") or {}).get("question")
                if question:
                    questions.append(question)
    return questions


def _final_summary(messages: list[Any]) -> str:
    for msg in reversed(messages):
        if getattr(msg, "type", None) == "ai" and msg.content and not (getattr(msg, "tool_calls", None)):
            return str(msg.content)
    return ""


def _extract_interrupt_question(result: dict[str, Any]) -> str | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    payload = getattr(interrupts[0], "value", interrupts[0])
    if isinstance(payload, dict):
        return payload.get("question", str(payload))
    return str(payload)


def _finish(spec: SpecialistSpec, thread_id: str, result: dict[str, Any]) -> Report | NeedsInput:
    question = _extract_interrupt_question(result)
    if question:
        return NeedsInput(role=spec.role, thread_id=thread_id, question=question)

    messages = result.get("messages", [])
    tool_calls_made = _count_tool_calls(messages, spec.tool_names)
    status = "capped" if spec.max_tool_calls is not None and tool_calls_made >= spec.max_tool_calls else "complete"
    return Report(
        role=spec.role,
        label=spec.label,
        findings=_extract_findings(messages),
        questions_asked=_extract_questions_asked(messages),
        summary=_final_summary(messages),
        status=status,
    )


async def run_specialist(spec: SpecialistSpec, task: str, ctx: RunContext) -> Report | NeedsInput:
    """Run one specialist from a fresh thread until it finishes or pauses on ask_user."""
    thread_id = f"{spec.role}:{id(ctx)}:{ctx.root.name}"
    counter = [0]
    agent = _build_agent(spec, ctx, counter)
    config = {"configurable": {"thread_id": thread_id}}

    result = await agent.ainvoke({"messages": [{"role": "user", "content": task}]}, config=config)
    return _finish(spec, thread_id, result)


async def resume_specialist(spec: SpecialistSpec, thread_id: str, answer: str, ctx: RunContext) -> Report | NeedsInput:
    """Resume a specialist paused on ask_user with the person's answer.

    This typically runs in a separate HTTP request from the one that paused
    it, so the tool-call counter is re-seeded from the checkpointed history
    rather than assumed to be zero.
    """
    counter = [0]
    agent = _build_agent(spec, ctx, counter)
    config = {"configurable": {"thread_id": thread_id}}

    prior_state = await agent.aget_state(config)
    prior_messages = prior_state.values.get("messages", []) if prior_state and prior_state.values else []
    counter[0] = _count_tool_calls(prior_messages, spec.tool_names)

    result = await agent.ainvoke(Command(resume=answer), config=config)
    return _finish(spec, thread_id, result)

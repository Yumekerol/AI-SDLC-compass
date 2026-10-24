"""
Agent Builder & Orchestrator using LangChain / LangGraph and ChatOllama
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

try:
    from langchain.agents import create_agent
except ImportError:
    from langgraph.prebuilt import create_react_agent as create_agent

from .config import settings
from .tools import TOOLS, set_current_repo_root

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI-SDLC Compass Advisor. You help software engineering teams assess their repository "
    "architecture, code hygiene, testing coverage, and DevOps readiness for AI adoption. "
    "You have access to tools to inspect the repository structure, read files, and analyze text. "
    "Use tools when the user's request needs codebase inspection. "
    "If the question doesn't need a tool, answer directly. "
    "If a tool returns an error, explain the error plainly."
)


class AgentService:
    """Manages LangGraph agent instances and in-memory session threads."""

    def __init__(self):
        self.checkpointer = InMemorySaver()
        self._agent = None

    def get_agent(self):
        """Build or return cached agent graph."""
        if self._agent is None:
            model = ChatOllama(
                model=settings.chat_model,
                base_url=settings.ollama_host,
                temperature=settings.temperature,
            )
            self._agent = create_agent(
                model=model,
                tools=TOOLS,
                system_prompt=SYSTEM_PROMPT,
                checkpointer=self.checkpointer,
            )
        return self._agent

    async def run(
        self,
        message: str,
        session_id: str = "default",
        repo_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a turn with the agent for a given session/thread.
        Maintains conversation history via InMemorySaver keyed by session_id.
        """
        if repo_path:
            target_path = Path(repo_path).resolve()
            if target_path.exists():
                set_current_repo_root(target_path)
            else:
                logger.warning(f"Specified repo_path {target_path} does not exist. Using default.")

        agent = self.get_agent()
        config = {"configurable": {"thread_id": session_id}}

        tool_calls: list[dict[str, Any]] = []
        answer = ""

        try:
            # Stream execution events to track tool calls and extract the final response
            for chunk in agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                stream_mode="updates",
            ):
                for node, update in chunk.items():
                    for msg in update.get("messages", []):
                        if node == "model":
                            calls = getattr(msg, "tool_calls", None) or []
                            for call in calls:
                                tool_calls.append({
                                    "name": call.get("name"),
                                    "args": call.get("args"),
                                })
                            if msg.content and not calls:
                                answer = msg.content
                        elif node == "tools":
                            # Attach tool output snippet to last tool call
                            if tool_calls:
                                tool_calls[-1]["result"] = str(msg.content)[:300]

            # Fallback if streaming ended without direct content on the last turn
            if not answer and hasattr(agent, "get_state"):
                state = agent.get_state(config)
                if state and state.values.get("messages"):
                    last_msg = state.values["messages"][-1]
                    if last_msg.content:
                        answer = last_msg.content

            return {
                "session_id": session_id,
                "answer": answer or "(No answer generated)",
                "tool_calls": tool_calls,
                "status": "success",
            }
        except Exception as e:
            logger.exception(f"Error during agent execution: {e}")
            return {
                "session_id": session_id,
                "answer": f"Error running agent: {type(e).__name__}: {str(e)}",
                "tool_calls": tool_calls,
                "status": "error",
            }


agent_service = AgentService()

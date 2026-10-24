"""
SDLC-Compass Agent Service Entry Point

Provides a FastAPI HTTP server for frontend/backend integration
and retains an interactive CLI fallback for terminal testing.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import agent_service
from .config import settings

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sdlc_compass.agents")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SDLC-Compass Agent Service...")
    logger.info(f"Target Ollama model: {settings.chat_model} at {settings.ollama_host}")
    yield
    logger.info("Agent Service shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Tool-calling Ollama Agent Service for repository exploration and SDLC advisory.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or prompt for the agent")
    session_id: str = Field(default="default", description="Session/thread identifier for memory persistence")
    repo_path: str | None = Field(default=None, description="Optional absolute path to target repository")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "success"


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "model": settings.chat_model,
        "ollama_host": settings.ollama_host,
    }


@app.post("/chat", response_model=ChatResponse, tags=["Advisor"])
async def chat_with_agent(req: ChatRequest):
    """
    Send a message to the agent.
    The agent uses its tools (read_file, directory_tree, list_files)
    to inspect the repository as needed and returns the response.
    """
    result = await agent_service.run(
        message=req.message,
        session_id=req.session_id,
        repo_path=req.repo_path,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("answer"))
    return ChatResponse(**result)


def run_cli():
    """Terminal CLI mode for local development and direct testing."""
    import asyncio

    print(f"--- SDLC-Compass Agent Terminal (Model: {settings.chat_model}) ---")
    print("Type your question. Type 'exit' to quit.\n")

    async def _loop():
        session_id = "cli-session"
        while True:
            try:
                question = input("You: ").strip()
                if not question or question.lower() == "exit":
                    break

                res = await agent_service.run(message=question, session_id=session_id)
                for tc in res.get("tool_calls", []):
                    print(f"  [tool call] {tc.get('name')}({tc.get('args')})")
                    if "result" in tc:
                        print(f"  [tool result] {tc['result'][:150]}...")
                print(f"\nAdvisor: {res.get('answer')}\n")
            except (KeyboardInterrupt, EOFError):
                break

    asyncio.run(_loop())


if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        import uvicorn
        uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)

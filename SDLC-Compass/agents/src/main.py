"""
SDLC-Compass Agent Service Entry Point

Provides a FastAPI HTTP server for frontend/backend integration
and retains an interactive CLI fallback for terminal testing.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .acquisition import ensure_repo
from .agent import agent_service
from .config import settings
from . import pipeline
from .persistence import init_checkpointer, close_checkpointer

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sdlc_compass.agents")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SDLC-Compass Agent Service...")
    logger.info(f"Target Ollama model: {settings.chat_model} at {settings.ollama_host}")
    await init_checkpointer()
    logger.info("Async checkpointer ready.")
    yield
    await close_checkpointer()
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


class PipelineStartRequest(BaseModel):
    session_id: str
    git_url: str
    access_token: str | None = None
    team_context: dict[str, Any] = Field(default_factory=dict)
    scan_output: dict[str, Any] | None = None
    background: bool = Field(default=False, description="If true, returns immediately with accepted status")


class PipelineReplyRequest(BaseModel):
    session_id: str
    answer: str
    background: bool = Field(default=False, description="If true, returns immediately with accepted status")


# Background tasks keyed by session_id so we can detect double-starts.
_running_tasks: dict[str, asyncio.Task] = {}


@app.post("/pipeline/start", tags=["Pipeline"])
async def pipeline_start(req: PipelineStartRequest):
    """
    Run the supervisor -> 4 specialists -> synthesizer pipeline for one
    diagnostic session.

    If `background=False` (default), blocks until the turn finishes (either
    pausing on ask_user with status="needs_input" or completing with
    status="complete"). This is the direct relay mode used by the backend.

    If `background=True`, fires a background task and returns {"status": "accepted"}
    immediately. Poll GET /pipeline/status?session_id=... to monitor progress.
    """
    if req.session_id in _running_tasks and not _running_tasks[req.session_id].done():
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running for session {req.session_id}",
        )

    if req.background:
        async def _run():
            try:
                repo_path = await ensure_repo(req.session_id, req.git_url, req.access_token)
                await pipeline.run_pipeline(
                    session_id=req.session_id,
                    repo_path=str(repo_path),
                    team_context=req.team_context,
                    scan_output=req.scan_output,
                )
            except Exception:
                logger.exception("Background pipeline task failed for session %s", req.session_id)
            finally:
                _running_tasks.pop(req.session_id, None)

        _running_tasks[req.session_id] = asyncio.create_task(_run())
        return {"session_id": req.session_id, "status": "accepted"}

    try:
        repo_path = await ensure_repo(req.session_id, req.git_url, req.access_token)
        result = await pipeline.run_pipeline(
            session_id=req.session_id,
            repo_path=str(repo_path),
            team_context=req.team_context,
            scan_output=req.scan_output,
        )
        return result.model_dump(mode="json")
    except Exception as e:
        logger.exception("Pipeline start failed for session %s: %s", req.session_id, e)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/pipeline/reply", tags=["Pipeline"])
async def pipeline_reply(req: PipelineReplyRequest):
    """
    Answer the clarifying question a specialist is currently paused on, and
    continue the pipeline from there.

    Supports synchronous return (default) or background execution (background=True).
    """
    if req.session_id in _running_tasks and not _running_tasks[req.session_id].done():
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline already running for session {req.session_id}",
        )

    if req.background:
        async def _resume():
            try:
                await pipeline.resume_pipeline(session_id=req.session_id, answer=req.answer)
            except Exception:
                logger.exception("Background pipeline resume failed for session %s", req.session_id)
            finally:
                _running_tasks.pop(req.session_id, None)

        _running_tasks[req.session_id] = asyncio.create_task(_resume())
        return {"session_id": req.session_id, "status": "accepted"}

    try:
        result = await pipeline.resume_pipeline(session_id=req.session_id, answer=req.answer)
        return result.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline resume failed for session %s: %s", req.session_id, e)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")



@app.get("/pipeline/status", tags=["Pipeline"])
async def pipeline_status(session_id: str):
    """
    Poll this endpoint to watch pipeline progress.
    Returns status (running | needs_input | complete | error) and the result
    payload once the pipeline finishes or pauses for a question.
    """
    state = pipeline.get_status(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No pipeline state for session {session_id}")
    return state


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

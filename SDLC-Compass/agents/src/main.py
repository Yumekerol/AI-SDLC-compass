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
from . import pipeline, pipeline_store
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
    git_url: str | None = Field(
        default=None,
        description="If given, resolved via the same clone-or-reuse logic as /pipeline/start (reuses that session's existing clone if present). Takes precedence over repo_path.",
    )
    access_token: str | None = None


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
        git_url=req.git_url,
        access_token=req.access_token,
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


# Running pipeline work keyed by session_id: background tasks, and the
# request handler itself in the default blocking mode, so a run can be both
# detected (no double-starts) and cancelled (/pipeline/cancel).
_running_tasks: dict[str, asyncio.Task] = {}


def _register_current(session_id: str) -> None:
    task = asyncio.current_task()
    if task is not None:
        _running_tasks[session_id] = task


def _unregister_current(session_id: str) -> None:
    if _running_tasks.get(session_id) is asyncio.current_task():
        _running_tasks.pop(session_id, None)


def _cancelled(session_id: str) -> HTTPException:
    """Turn a /pipeline/cancel of this request into a clean 409 reply."""
    task = asyncio.current_task()
    if task is not None:
        task.uncancel()
    logger.info("Pipeline request for session %s stopped by cancel", session_id)
    return HTTPException(status_code=409, detail="Pipeline cancelled")


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

    _register_current(req.session_id)
    try:
        repo_path = await ensure_repo(req.session_id, req.git_url, req.access_token)
        result = await pipeline.run_pipeline(
            session_id=req.session_id,
            repo_path=str(repo_path),
            team_context=req.team_context,
            scan_output=req.scan_output,
        )
        return result.model_dump(mode="json")
    except asyncio.CancelledError:
        raise _cancelled(req.session_id)
    except Exception as e:
        logger.exception("Pipeline start failed for session %s: %s", req.session_id, e)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    finally:
        _unregister_current(req.session_id)


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

    _register_current(req.session_id)
    try:
        result = await pipeline.resume_pipeline(session_id=req.session_id, answer=req.answer)
        return result.model_dump(mode="json")
    except asyncio.CancelledError:
        raise _cancelled(req.session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline resume failed for session %s: %s", req.session_id, e)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    finally:
        _unregister_current(req.session_id)


class PipelineCancelRequest(BaseModel):
    session_id: str


@app.post("/pipeline/cancel", tags=["Pipeline"])
async def pipeline_cancel(req: PipelineCancelRequest):
    """
    Stop a session's pipeline: interrupts the specialist that is running
    (which also aborts its in-flight Ollama request) and drops any paused
    state, so an abandoned diagnostic stops taking model time from others.
    Safe to call for a session that isn't running.
    """
    task = _running_tasks.get(req.session_id)
    was_running = bool(task and not task.done())
    if was_running:
        task.cancel()
    pipeline_store.delete_state(req.session_id)
    pipeline_store.set_job_status(req.session_id, "cancelled")
    logger.info("Pipeline for session %s cancelled (was running: %s)", req.session_id, was_running)
    return {"session_id": req.session_id, "cancelled": True, "was_running": was_running}



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

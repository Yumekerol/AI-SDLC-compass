"""
AI-SDLC Compass — Backend Application Entry Point

FastAPI application serving the complete AI-SDLC Compass diagnostic pipeline.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import api_v1_router
from .config import settings
from .storage import get_storage

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sdlc_compass")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize storage and ensure paths exist."""
    logger.info("Initializing AI-SDLC Compass backend...")
    store = await get_storage()
    logger.info("Storage backend initialized successfully.")
    yield
    logger.info("Shutting down AI-SDLC Compass backend...")
    await store.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Proof-of-concept AI diagnostic tool assessing team readiness and AI adoption opportunities across the SDLC.",
    lifespan=lifespan,
)

# Enable CORS for frontend applications (Vue / React / Vanilla)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 endpoints
app.include_router(api_v1_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
    }


# Mount frontend static directory if present
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)

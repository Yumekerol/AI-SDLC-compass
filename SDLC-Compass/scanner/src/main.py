""" 
SDLC-Compass Scanner Entry Point.

Uses FastAPI.

That's all folks!
"""

from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .api import api
from .core.job_orchestrator import job_handler

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sdlc_compass")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing scanner service...")
    settings.init()
    job_handler.init()
    logger.info("Scanner service has been started.")
    yield
    logger.info("Cleaning temporary files and closing...")
    settings.close()
    job_handler.close()
    

app = FastAPI(
    title= settings.app_name,
    version= settings.app_version,
    description="Scanner prototype for the AI-SDLC-Compass application.",
    lifespan=lifespan
)

app.include_router(api)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scanner.src.main:app", host=settings.host, port=settings.port, reload=True)
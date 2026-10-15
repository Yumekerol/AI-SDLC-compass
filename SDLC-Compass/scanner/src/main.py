""" 
SDLC-Compass Scanner Entry Point.

Uses FastAPI.

That's all folks!
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from .config import settings

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sdlc_compass")

app = FastAPI(
    title= settings.app_name,
    version= settings.app_version,
    description="Scanner prototype for the AI-SDLC-Compass application."
)

#app.include_router(api)

async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scanner.main:app", host=settings.host, port=settings.port, reload=True)
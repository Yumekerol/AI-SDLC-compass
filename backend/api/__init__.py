"""API package initialization and router registration."""

from fastapi import APIRouter

from .diagnostic import router as diagnostic_router
from .reports import router as reports_router
from .scan import router as scan_router
from .sessions import router as sessions_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(sessions_router)
api_v1_router.include_router(scan_router)
api_v1_router.include_router(diagnostic_router)
api_v1_router.include_router(reports_router)

__all__ = ["api_v1_router"]

from fastapi import APIRouter

from .scan import router as scan_router

api = APIRouter(prefix="/api/v1")
api.include_router(scan_router)

__all__ = ["api"]
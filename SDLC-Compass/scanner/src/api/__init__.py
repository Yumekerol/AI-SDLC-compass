from fastapi import APIRouter

from .scans import router as scans_router

api = APIRouter(prefix="/api/v1")
api.include_router(scans_router)

__all__ = ["api"]
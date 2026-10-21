from fastapi import APIRouter

from .scan import router as scan_router
from .async_job import router as job_router

api = APIRouter(prefix="/api/v1")
api.include_router(scan_router)
api.include_router(job_router)

__all__ = ["api"]
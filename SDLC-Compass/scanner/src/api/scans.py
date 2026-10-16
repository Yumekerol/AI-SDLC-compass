from __future__ import annotations

import json
import logging

from fastapi import APIRouter, File, UploadFile, Response, status
from pydantic import BaseModel
from typing import Annotated
from fastapi import HTTPException
from ..core.git_extract import GitExtractError, clone_repository

from ..models.scanner_output import ScannerOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan")

@router.get("/")
async def report():
    return {"message": "not implemented"}

@router.post("/zip", status_code=status.HTTP_200_OK)
async def start_scan(file: UploadFile, response: Response):
    if file.content_type != "application/zip":
        response.status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        return {"err": "NOT A ZIP!"}
    return {"content_type": file.content_type}

@router.post("/url")
async def start_scan(url: str, token: str | None = None):
    try:
        clone = await clone_repository(url, token)
    except GitExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha}


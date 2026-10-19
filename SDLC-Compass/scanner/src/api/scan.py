from __future__ import annotations

import logging

from fastapi import APIRouter, UploadFile, Response, status, HTTPException

from pathlib import Path

from ..aquisition.git_aquisition import aquire_and_validate_repository, GitExtractError
from ..aquisition.zip_aquisition import aquire_and_validate_zip

from ..models.constraint_output import Result
from ..models.zip_result import ZipResult
from ..models.clone_result import CloneResult

from ..core.metrics import collect_all_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan")



@router.get("/")
async def report():
    return {"message": "not implemented"}

@router.post("/zip", status_code=status.HTTP_200_OK)
async def start_scan(file: UploadFile, response: Response):
    if file.content_type != "application/zip":
        response.status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        return {
            "reason": f"Uploaded file was expected to be of type 'application/zip', but was instead '{file.content_type}'."
        }

    try:
        result: ZipResult = await aquire_and_validate_zip(file)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "err": f"Raised exception was not handled: {e}" #debug, remove later
        }

    if result.constraint_output.result != Result.OK:
        response.status_code = status.HTTP_412_PRECONDITION_FAILED
        return {
            "reason": result.constraint_output.message 
        }

    root: Path = result.path
    
    metrics = collect_all_metrics(root)
        
    return {"scan_id": result.scan_id, "metrics": metrics}


@router.post("/url")
async def start_scan(response: Response, url: str, token: str | None = None):
    try:
        clone: CloneResult = await aquire_and_validate_repository(url, token)
    except GitExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if clone.constraint_output.result != Result.OK:
        response.status_code = status.HTTP_412_PRECONDITION_FAILED
        return {
            "reason": clone.constraint_output.message 
        }
    
    root: Path = clone.path

    metrics = collect_all_metrics(root)
        
    return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha, "metrics": metrics}

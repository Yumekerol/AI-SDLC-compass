from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, UploadFile, Response, status, HTTPException

from pathlib import Path

from ..aquisition.git_aquisition import aquire_and_validate_repository, GitExtractError
from ..aquisition.zip_aquisition import aquire_and_validate_zip

from ..models.constraint_output import Result
from ..models.zip_result import ZipResult
from ..models.clone_result import CloneResult

from ..core.metrics import collect_all_metrics

from ..config import settings

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

    tmp_folder: Path = settings.tmp_dir
    tmp_name = uuid.uuid4().hex

    scan_id: str = uuid.uuid4().hex

    filepath: Path = tmp_folder / f'{tmp_name}.zip'

    with open(filepath, "wb") as f:
        content = file.file.read()
        f.write(content)

    try:
        result: ZipResult = aquire_and_validate_zip(scan_id, filepath)
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

    from ..models.scanner_mapping_output import map_languages, map_size_and_structure, map_stack_and_tooling, map_cicd_and_operations, map_quality_indicators, map_warnings_and_gaps, map_repository, map_scope
            
    signalgroup = {
        #"languages": map_languages(metrics),
        #"size_and_structure": map_size_and_structure(metrics),
        #"stack_and_tooling": map_stack_and_tooling(metrics),
        "cicd_and_operations": map_cicd_and_operations(metrics),
        #"quality_indicators": map_quality_indicators(metrics),
        #"warnings_and_gaps": map_warnings_and_gaps(metrics),
    }
    
    #return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha, "metrics": metrics}
    return {"scan_id": result.scan_id, "signalgroup": signalgroup}
        
    return {"scan_id": result.scan_id, "metrics": metrics}


@router.post("/url")
async def start_scan(response: Response, url: str, token: str | None = None):
    scan_id: str = uuid.uuid4().hex

    try:
        clone: CloneResult = aquire_and_validate_repository(scan_id, url, token)
    except GitExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if clone.constraint_output.result != Result.OK:
        response.status_code = status.HTTP_412_PRECONDITION_FAILED
        return {
            "reason": clone.constraint_output.message 
        }
    
    root: Path = clone.path

    metrics = collect_all_metrics(root)

    from ..models.scanner_mapping_output import map_languages, map_size_and_structure, map_stack_and_tooling, map_cicd_and_operations, map_quality_indicators, map_warnings_and_gaps, map_repository, map_scope
        
    signalgroup = {
        #"languages": map_languages(metrics),
        #"size_and_structure": map_size_and_structure(metrics),
        #"stack_and_tooling": map_stack_and_tooling(metrics),
        "cicd_and_operations": map_cicd_and_operations(metrics),
        #"quality_indicators": map_quality_indicators(metrics),
        #"warnings_and_gaps": map_warnings_and_gaps(metrics),
    }
    
    #return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha, "metrics": metrics}
    return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha, "signalgroup": signalgroup}

from __future__ import annotations

import json
import logging
import uuid
import sys
import os
import stat
import shutil

from fastapi import APIRouter, File, UploadFile, Response, status, HTTPException
from pydantic import BaseModel
from typing import Annotated
from pathlib import Path

from ..core.git_extract import GitExtractError, clone_repository

from ..models.scanner_output import ScannerOutput
from ..models.constraint_output import ConstraintOutput, Result

from ..security.constraints import zip_file_count_constraint, zip_file_depth_constraint, zip_file_format_constraint
from ..security.constraints import git_repo_count_constraint, git_repo_depth_constraint

from ..core.git_extract import cleanup_dir

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan")





@router.get("/")
async def report():
    return {"message": "not implemented"}

@router.post("/zip", status_code=status.HTTP_200_OK)
async def start_scan(file: UploadFile, response: Response):
    
    format_constraint: ConstraintOutput = zip_file_format_constraint(file)
    if format_constraint.result != Result.OK:
        
        #if something other than wrong_format was sent by this constraint, something has gone very wrong
        if format_constraint.result != Result.WRONG_FORMAT:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"err": "Impossible result returned by zip_file_format_constraint()"}
        
        response.status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        return {"reason": format_constraint.message}
    
    scan_id = uuid.uuid4().hex
    scan_folder: Path = settings.tmp_dir / scan_id
    
    scan_folder.mkdir(parents=True, exist_ok=True)
    
    filepath: Path = scan_folder / f"{scan_id}.zip"
    
    with open(filepath, "wb") as f:
        content = file.file.read()
        f.write(content)
    
    # at this point, file is confirmed a zip, and is stored in the tmp folder, identified by a scan_id

    count_constraint: ConstraintOutput = zip_file_count_constraint(filepath)
    if count_constraint.result != Result.OK:
        try:
            cleanup_dir(scan_folder)
        except Exception as e:
            logger.error(f"Failed to remove tmp. dir. {scan_folder}. Exception raised: {e}")
        
        #if something other than file_limit was sent by this constraing, something has gone very wrong
        if count_constraint.result != Result.FILE_LIMIT:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"err": "Impossible result returned by zip_file_count_constraint()"}

        response.status_code = status.HTTP_412_PRECONDITION_FAILED
        return {"reason": count_constraint.message}
    
    depth_constraint: ConstraintOutput = zip_file_depth_constraint(filepath)
    if depth_constraint.result != Result.OK:
        try:
            cleanup_dir(scan_folder)
        except Exception as e:
            logger.error(f"Failed to remove tmp. dir. {scan_folder}. Exception raised: {e}")
        
        #if something other than depth_limit was sent by this constraint, somethign has gone very wrong
        if depth_constraint.result != Result.DEPTH_LIMIT:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"err": "Impossible result returned by zip_file_depth_constraint()"}
        
        response.status_code = status.HTTP_412_PRECONDITION_FAILED
        return {"reason": depth_constraint.message}
    
    # by this point, all constraints have been checked and passed.

    return {"filename": file.filename ,"content_type": file.content_type}

@router.post("/url")
async def start_scan(response: Response, url: str, token: str | None = None):
    try:
        clone = await clone_repository(url, token)
    except GitExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    root: Path = settings.tmp_dir / clone.scan_id
    
    count_constraint: ConstraintOutput = git_repo_count_constraint(root)
    if count_constraint.result != Result.OK:
        try:
            cleanup_dir(root)
        except Exception as e:
            logger.error(f"Failed to remove tmp. dir. {root}. Exception raised: {e}")
            
        if count_constraint.result != Result.FILE_LIMIT:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"err": "Impossible result returned by git_repo_count_constraint()"}
            
        response.status_code = status.HTTP_412_PRECONDITION_FAILED
        return {"reason": count_constraint.message}
    
    depth_constraint: ConstraintOutput = git_repo_depth_constraint(root)
    if depth_constraint.result != Result.OK:
        try:
            cleanup_dir(root)
        except Exception as e:
            logger.error(f"Failed to remove tmp. dir. {root}. Exception raised: {e}")
            
        if depth_constraint.result != Result.DEPTH_LIMIT:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"err": "Impossible result returned by git_repo_depth_constraint()"}
        
        response.status_code = status.HTTP_412_PRECONDITION_FAILED
        return {"reason": depth_constraint.message}
    
    
    #by this point, every constraint has been met    
    
    return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha}
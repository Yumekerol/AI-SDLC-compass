from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, UploadFile, Response, status
from pathlib import Path

from ..config import settings
from ..models.job import Job, JobStatus
from ..core.job_orchestrator import job_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/job")

@router.get('/status', status_code = status.HTTP_200_OK)
def get_status(scan_id: str, response: Response):
    st = job_handler.get_job_status(scan_id)

    if not st:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "reason": f"Job with id '{scan_id}' does not exist."
        }
    
    status_message = {
        JobStatus.QUEUED: "scan job is queued.",
        JobStatus.INPROGRESS: "scan job is currently in progress.",
        JobStatus.COMPLETED: "scan job is complete.",
        JobStatus.FAILED: "scan job failed."
    }
    
    return {
        "scan_id": scan_id,
        "status": st,
        "message": status_message[st]
    }
    
@router.get('/', status_code = status.HTTP_200_OK)
def get_job_output(scan_id: str, response: Response):
    job: Job = job_handler.get_job(scan_id)
    if not job:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "reason": f"Job with id '{scan_id}' does not exist."
        }
        
    if job.status != JobStatus.COMPLETED:
        response.status_code = status.HTTP_204_NO_CONTENT
        return {
            "reason": f"Job with id '{scan_id}' has not been completed yet."
        }

    if job.status == JobStatus.FAILED:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "reason": job.constraint_output.message
        }
        
    return {"signalgroup": job.scan_result}

@router.post('/', status_code = status.HTTP_201_CREATED)
def _post_scan_dbg(scan_id: str, response: Response):
    job_handler.add_job(scan_id)
    
    return {
        "message": f"Job '{scan_id}' has been queued."
    }
    
@router.post('/zip', status_code = status.HTTP_201_CREATED)
def queue_zip(file: UploadFile, response: Response):
    if file.content_type != "application/zip":
        response.status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        return {
            "reason": f"Uploaded file was expected to be of type 'application/zip', but was instead '{file.content_type}'."
        }

    tmp_folder: Path = settings.tmp_dir
    tmp_name = uuid.uuid4().hex

    filepath: Path = tmp_folder / f'{tmp_name}.zip'

    with open(filepath, "wb") as f:
        content = file.file.read()
        f.write(content)

    scan_id:str = job_handler.add_job_zip(filepath)
    return {
        "scan_id": scan_id
    }

@router.post('/url', status_code = status.HTTP_201_CREATED)
def queue_url(response: Response, url: str, token: str | None = None):
    scan_id: str = job_handler.add_job_url(url, token)
    return {
        "scan_id": scan_id
    }


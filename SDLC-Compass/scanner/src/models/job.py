from __future__ import annotations

from datetime import datetime

from enum import Enum
from pydantic import BaseModel, Field
from pathlib import Path

from fastapi import UploadFile

from .scanner_output import ScannerOutput
from .constraint_output import ConstraintOutput
from .scanner_output import SignalGroup

class URLInput(BaseModel):
    url: str
    token: str | None

class RepoKind(str, Enum):
    ZIP = "zip"
    URL = "url"

class JobStatus(str, Enum):
    QUEUED = "queued"
    INPROGRESS = "inprogress"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(BaseModel):
    scan_id: str = ""

    repo_kind: RepoKind = RepoKind.ZIP
    status: JobStatus = JobStatus.QUEUED

    input: URLInput | Path | None = None

    constraint_output: ConstraintOutput | None = None
    error: str | None = None

    creation_time: datetime = datetime.now()
    completion_time: datetime | None = None
    
    scan_result: ScannerOutput | dict[str, SignalGroup] | None = None
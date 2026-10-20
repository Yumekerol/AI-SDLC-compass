from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

from pathlib import Path

from .constraint_output import ConstraintOutput

class CloneResult(BaseModel):
    scan_id: str
    constraint_output: ConstraintOutput

    path: Path               # internal only, do not expose to API clients
    repo_url: str            # normalised, never contains credentials
    head_sha: str
    branch: str | None       # None when HEAD is detached
    commits_total: int
    is_shallow: bool
    tracked_files: int       # raw `git ls-files` count, before scanner filters
    exceeds_poc_limit: bool  # tracked_files > settings.poc_max_files
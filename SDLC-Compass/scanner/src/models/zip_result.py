from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

from pathlib import Path

from .constraint_output import ConstraintOutput

class ZipResult(BaseModel):
    scan_id: str
    constraint_output: ConstraintOutput

    path: Path 
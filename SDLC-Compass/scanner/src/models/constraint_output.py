from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

class Result(str, Enum):
    OK = "ok"
    FILE_LIMIT = "file_limit"
    DEPTH_LIMIT = "depth_limit"
    WRONG_FORMAT = "wrong_format"

class ConstraintOutput(BaseModel):
    result: Result = Field(default_factory=Result)
    message: str = "ok"
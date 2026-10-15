from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MIXED = "mixed"
    ESTIMATED = "estimated"

class AnalysisStatus(str, Enum):
    OK = "ok"
    ERR = "err"
    #add more if needed

class SignalStatus(str, Enum):
    MEASURED = "measured"
    PARTIAL = "partial" # some info is not present


class AnalysisOutput(BaseModel):
    confidence_level: ConfidenceLevel = Field(default_factory=ConfidenceLevel)
    analysis_status: AnalysisStatus = Field(default_factory=AnalysisStatus)
    signal_status: SignalStatus = Field(default_factory=SignalStatus)


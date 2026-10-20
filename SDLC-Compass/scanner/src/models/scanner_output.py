"""
Scanner Output Models

Pydantic schemas for the Light Scanner's structured output.
Maps directly to the 6 signal cards in the Figma UI (Step 2: Review Signals).

Each signal group includes:
- confidence: How reliable the detection is
- confidence_source: What method was used to detect
- data: The actual extracted values
- evidence_paths: File paths that were inspected as proof
- user_edited: Whether the user has overridden this group
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


# ─── Confidence & Evidence ────────────────────────────────────────────

class ConfidenceLevel(str, Enum):
    """How reliable a scanner signal is."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MIXED = "mixed"
    ESTIMATED = "estimated"


# ─── Signal Group 1: Languages ────────────────────────────────────────

class LanguageBreakdown(BaseModel):
    """A single language detected in the repository."""
    language: str
    files: int = 0
    percentage: float = 0.0
    loc: int = 0
    loc_share : float = 0.0


class LanguagesData(BaseModel):
    """Detected programming languages and their distribution."""
    primary_language: str | None = None
    breakdown: list[LanguageBreakdown] = Field(default_factory=list)


# ─── Signal Group 2: Size & Structure ─────────────────────────────────

class SizeAndStructureData(BaseModel):
    """Repository size, structure, and complexity estimates."""
    code_files: int = 0
    total_files: int = 0
    loc_estimate: int = 0
    module_estimate: int = 0
    avg_file_size_loc: float = 0.0


# ─── Signal Group 3: Stack & Tooling ──────────────────────────────────

class StackAndToolingData(BaseModel):
    """Detected frameworks, libraries, and development tools."""
    frameworks: list[str] = Field(default_factory=list)
    testing_libraries: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    linters: list[str] = Field(default_factory=list)
    formatters: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)


# ─── Signal Group 4: CI/CD & Operations ───────────────────────────────

class CICDAndOperationsData(BaseModel):
    """CI/CD pipeline and operational infrastructure signals."""
    cicd_tool: str | None = None
    cicd_description: str | None = None
    has_containerization: bool = False
    dockerfile_path: str | None = None
    has_documentation: bool = False
    documentation_notes: str | None = None
    has_test_step_in_ci: bool = False
    has_deploy_step_in_ci: bool = False
    has_monitoring_config: bool = False
    monitoring_tools: list[str] = Field(default_factory=list)
    has_iac: bool = False
    iac_tools: list[str] = Field(default_factory=list)


# ─── Signal Group 5: Quality Indicators ───────────────────────────────

class QualityIndicatorsData(BaseModel):
    """Testing and code quality proxy signals."""
    test_to_code_file_ratio: float | None = None
    test_file_count: int = 0
    source_file_count: int = 0
    executed_coverage: float | None = None  # null = not measured
    has_quality_gate: bool = False
    quality_gate_notes: str | None = None
    has_code_style_config: bool = False
    code_style_tools: list[str] = Field(default_factory=list)


# ─── Signal Group 6: Warnings & Gaps ──────────────────────────────────

class ScannerWarning(BaseModel):
    """A warning or gap flag raised by the scanner."""
    category: str  # e.g., "monitoring", "testing", "documentation"
    title: str
    description: str


class WarningsAndGapsData(BaseModel):
    """Signals expected but absent, or ambiguous signals requiring confirmation."""
    warnings: list[ScannerWarning] = Field(default_factory=list)


# ─── Generic Signal Group Wrapper ─────────────────────────────────────

class SignalGroup(BaseModel):
    """
    A single signal group card as displayed in the UI.
    Wraps data with confidence metadata and evidence.
    """
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_source: str = ""
    data: dict = Field(default_factory=dict)
    evidence_paths: list[str] = Field(default_factory=list)
    user_edited: bool = False


# ─── Complete Scanner Output ──────────────────────────────────────────

class RepositoryInfo(BaseModel):
    """Basic repository metadata."""
    name: str = ""
    branch: str | None = None
    commit_hash: str | None = None
    source_type: str = "git"  # "git" or "zip"
    clone_url: str | None = None


class ScopeAssessment(BaseModel):
    """PoC eligibility and scope information."""
    eligible_for_poc: bool = True
    supported_code_files: int = 0
    excluded_items: int = 0
    exclusion_rules: list[str] = Field(default_factory=list)
    scope_warnings: list[str] = Field(default_factory=list)


class ScannerOutput(BaseModel):
    """
    Complete output of the Light Scanner.

    This is the full structured result containing all 6 signal groups,
    repository metadata, and scope assessment. Maps directly to the
    Step 2 UI in the Figma.
    """
    repository: RepositoryInfo = Field(default_factory=RepositoryInfo)
    scope: ScopeAssessment = Field(default_factory=ScopeAssessment)

    # The 6 signal groups (matching Figma cards)
    languages: SignalGroup = Field(default_factory=SignalGroup)
    size_and_structure: SignalGroup = Field(default_factory=SignalGroup)
    stack_and_tooling: SignalGroup = Field(default_factory=SignalGroup)
    cicd_and_operations: SignalGroup = Field(default_factory=SignalGroup)
    quality_indicators: SignalGroup = Field(default_factory=SignalGroup)
    warnings_and_gaps: SignalGroup = Field(default_factory=SignalGroup)
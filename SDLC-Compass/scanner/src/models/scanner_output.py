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
    #executed_coverage: float | None = None  # null = not measured ISTO È MM FKED DE MEDIR, OU TERIA DE LER O REPO COMPLETO PARA CALCULAR ISTO, O QUE É MUITO PESADO
    has_quality_gate: bool = False          # OU TERIA DE FZR UNS PARSERS TODOS ESTRANHOS COM CERTAS LIBS, 
    quality_gate_notes: str | None = None
    has_code_style_config: bool = False
    code_style_tools: list[str] = Field(default_factory=list)


# ─── Signal Group 6: Technical Debt ──────────────────────────────────

class MarkerCount(BaseModel):
    marker: str                      # TODO, FIXME, HACK, XXX, WORKAROUND
    count: int = 0


class DebtHotspot(BaseModel):
    file: str
    markers: int = 0


class DebtOccurrence(BaseModel):
    marker: str
    file: str
    line: int


class TechnicalDebtData(BaseModel):
    """Technical debt proxy signals (TODO/FIXME/HACK/XXX/WORKAROUND markers)."""
    total_markers: int = 0
    files_with_markers: int = 0
    marker_counts: list[MarkerCount] = Field(default_factory=list)
    top_files: list[DebtHotspot] = Field(default_factory=list)
    occurrences: list[DebtOccurrence] = Field(default_factory=list)
    occurrences_truncated: bool = False


# ─── Signal Group 7: Documentation ──────────────────────────────────

class DocumentationFile(BaseModel):
    file: str
    categories: list[str] = Field(default_factory=list)


class DocumentationChangedFile(BaseModel):
    file: str
    commits: int = 0
    last_change_date: str | None = None     # YYYY-MM-DD


class DocumentationData(BaseModel):
    """Documentation presence and maintenance signals."""
    documentation_files_count: int = 0

    # Presença por tipo
    has_readme: bool = False
    has_changelog: bool = False
    has_adr: bool = False
    has_runbooks: bool = False
    has_onboarding_docs: bool = False
    has_docs_directory: bool = False

    files_by_category: dict[str, int] = Field(default_factory=dict)
    documentation_files: list[DocumentationFile] = Field(default_factory=list)

    # Manutenção (a partir do histórico Git analisado)
    commits_touching_docs: int = 0
    share_of_commits: float | None = None          # 0.0 a 1.0; None se não houver histórico
    most_changed_files: list[DocumentationChangedFile] = Field(default_factory=list)


# ─── Signal Group 8: Fixes and Reverts ──────────────────────────────────

class CommitEvidence(BaseModel):
    """Um commit usado como evidência (sem sha nem autor, por desenho do coletor)."""
    date: str                                   # ISO 8601
    message: str
    matched_term: str | None = None             # só nas correções (fix, bug, hotfix…)


class FixesAndRevertsData(BaseModel):
    """Bug-fix and revert activity inferred from commit messages."""
    commits_analyzed: int = 0

    fix_commits: int = 0
    fix_ratio: float | None = None              # 0.0 a 1.0; None se não houver commits
    fixes_by_month: dict[str, int] = Field(default_factory=dict)      # "YYYY-MM" -> n

    revert_commits: int = 0
    revert_ratio: float | None = None           # 0.0 a 1.0
    reverts_by_month: dict[str, int] = Field(default_factory=dict)

    fix_evidence: list[CommitEvidence] = Field(default_factory=list)
    revert_evidence: list[CommitEvidence] = Field(default_factory=list)
    evidence_truncated: bool = False


# ─── Signal Group 9: File Churn ──────────────────────────────────

class ChurnedFile(BaseModel):
    """Um ficheiro do ranking de churn."""
    file: str
    lines_added: int = 0
    lines_deleted: int = 0
    lines_changed: int = 0          # adicionadas + removidas
    commits: int = 0                # nº de commits que tocaram o ficheiro


class FileChurnData(BaseModel):
    """Files with the most change activity in the analyzed history."""
    files_with_changes: int = 0
    lines_added_total: int = 0
    lines_deleted_total: int = 0
    lines_changed_total: int = 0
    top_files_share_of_churn: float | None = None     # 0.0 a 1.0; None se não houve churn
    top_files: list[ChurnedFile] = Field(default_factory=list)


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
    #user_edited: bool = False


# ─── Complete Scanner Output ──────────────────────────────────────────

class RepositoryInfo(BaseModel):
    """Basic repository metadata."""
    name: str = ""
    branch: str | None = None
    commit_hash: str | None = None
    source_type: str = "git"  # "git" or "zip"
    clone_url: str | None = None
    scan_id: str | None = None


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

    # The signal groups (matching Figma cards) + extras
    languages: SignalGroup = Field(default_factory=SignalGroup)
    size_and_structure: SignalGroup = Field(default_factory=SignalGroup)
    stack_and_tooling: SignalGroup = Field(default_factory=SignalGroup)
    cicd_and_operations: SignalGroup = Field(default_factory=SignalGroup)
    quality_indicators: SignalGroup = Field(default_factory=SignalGroup)
    technical_debt: SignalGroup = Field(default_factory=SignalGroup)
    documentation: SignalGroup = Field(default_factory=SignalGroup)
    fixes_and_reverts: SignalGroup = Field(default_factory=SignalGroup)
    file_churn: SignalGroup = Field(default_factory=SignalGroup)
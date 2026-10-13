"""
Light Scanner Orchestrator

Coordinates all deterministic scanner submodules and produces
the complete ScannerOutput model matching the 6 signal cards in the Figma UI.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..models.scanner_output import (
    ConfidenceLevel,
    RepositoryInfo,
    ScannerOutput,
    ScannerWarning,
    SignalGroup,
    WarningsAndGapsData,
)
from .cicd import detect_cicd_and_operations
from .code_metrics import (
    assess_poc_scope,
    collect_repo_files,
    detect_size_and_structure,
)
from .documentation import detect_documentation_signals
from .tech_stack import detect_languages, detect_stack_and_tooling
from .testing import detect_quality_indicators

logger = logging.getLogger(__name__)


def generate_warnings_and_gaps(
    quality_group: SignalGroup,
    cicd_group: SignalGroup,
    has_documentation: bool,
    stack_group: SignalGroup,
) -> SignalGroup:
    """
    Evaluate detected signals and compile explicit warnings and knowledge gaps.
    Maps to Figma Signal Card 6: Warnings & Missing Signals.
    """
    warnings: list[ScannerWarning] = []
    evidence_paths: list[str] = []

    q_data = quality_group.data or {}
    c_data = cicd_group.data or {}
    s_data = stack_group.data or {}

    # 1. Testing gap
    test_files = q_data.get("test_file_count", 0)
    if test_files == 0:
        warnings.append(ScannerWarning(
            category="testing",
            title="No automated test suite detected",
            description="No unit or integration tests were found in standard test folders. Autonomous AI code generation requires regression safety harnesses.",
        ))

    # 2. CI/CD gap
    if not c_data.get("cicd_tool"):
        warnings.append(ScannerWarning(
            category="cicd",
            title="No CI/CD pipeline definition",
            description="No workflow files (GitHub Actions, GitLab CI, etc.) detected. Automated AI evaluation gates require a functioning pipeline.",
        ))
    elif not c_data.get("has_test_step_in_ci") and test_files > 0:
        warnings.append(ScannerWarning(
            category="cicd",
            title="CI pipeline does not run automated tests",
            description="A CI pipeline was detected, but test execution steps were not recognized in workflow files.",
        ))

    # 3. Monitoring & Observability gap
    if not c_data.get("has_monitoring_config"):
        warnings.append(ScannerWarning(
            category="monitoring",
            title="Missing monitoring and observability configs",
            description="No APM, Prometheus, Datadog, or Sentry configs detected. Operational AI incident triage needs structured telemetry.",
        ))

    # 4. Containerization gap
    if not c_data.get("has_containerization"):
        warnings.append(ScannerWarning(
            category="operations",
            title="No containerization (Docker) detected",
            description="Missing Dockerfile or Compose file. Containerized ephemeral environments simplify automated AI testing and staging.",
        ))

    # 5. Documentation gap
    if not has_documentation:
        warnings.append(ScannerWarning(
            category="documentation",
            title="Minimal or missing project documentation",
            description="No comprehensive README, docs folder, or API specifications detected. Context ingestion for Spec AI tools is limited.",
        ))

    # 6. Linter & Style gap
    linters = s_data.get("linters", [])
    formatters = s_data.get("formatters", [])
    if not linters and not formatters and not q_data.get("has_code_style_config"):
        warnings.append(ScannerWarning(
            category="code_hygiene",
            title="No code linting or formatting configuration",
            description="No ESLint, Prettier, Black, or Ruff config found. AI-generated code should adhere to strict automated style checks.",
        ))

    data = WarningsAndGapsData(warnings=warnings)

    return SignalGroup(
        confidence=ConfidenceLevel.HIGH,
        confidence_source="Deterministic gap and missing signal analysis",
        data=data.model_dump(),
        evidence_paths=evidence_paths,
    )


def run_light_scanner(
    workspace_path: str | Path,
    repo_info: RepositoryInfo | None = None,
) -> ScannerOutput:
    """
    Run the deterministic Light Scanner across a cloned or extracted repository.

    Parameters:
    - workspace_path: Local filesystem directory of the repo
    - repo_info: Optional metadata about repo origin, branch, commit

    Returns:
    - Complete ScannerOutput with all 6 signal groups and PoC scope assessment.
    """
    workspace = Path(workspace_path).resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ValueError(f"Workspace path does not exist or is not a directory: {workspace}")

    logger.info(f"Starting Light Scanner on {workspace}")

    # Step 1: Collect files and assess size
    supported_code_files, all_valid_files, excluded_count = collect_repo_files(workspace)
    scope = assess_poc_scope(supported_code_files, excluded_count)

    # Step 2: Signal Group 1 — Languages
    languages_group = detect_languages(supported_code_files)

    # Step 3: Signal Group 2 — Size & Structure
    size_group = detect_size_and_structure(workspace, supported_code_files, all_valid_files)

    # Step 4: Signal Group 3 — Stack & Tooling
    stack_group = detect_stack_and_tooling(workspace, supported_code_files)

    # Step 5: Documentation
    has_doc, doc_notes, doc_evidence = detect_documentation_signals(workspace)

    # Step 6: Signal Group 5 — Quality Indicators
    known_linters = stack_group.data.get("linters", [])
    known_formatters = stack_group.data.get("formatters", [])
    quality_group = detect_quality_indicators(
        workspace,
        supported_code_files,
        known_linters=known_linters,
        known_formatters=known_formatters,
    )

    # Step 7: Signal Group 4 — CI/CD & Operations
    cicd_group = detect_cicd_and_operations(
        workspace,
        has_documentation=has_doc,
        documentation_notes=doc_notes,
    )
    # Merge doc evidence into cicd group evidence
    cicd_group.evidence_paths = list(dict.fromkeys(cicd_group.evidence_paths + doc_evidence))[:10]

    # Step 8: Signal Group 6 — Warnings & Gaps
    warnings_group = generate_warnings_and_gaps(
        quality_group=quality_group,
        cicd_group=cicd_group,
        has_documentation=has_doc,
        stack_group=stack_group,
    )

    repository = repo_info or RepositoryInfo(
        name=workspace.name,
        source_type="git",
    )

    return ScannerOutput(
        repository=repository,
        scope=scope,
        languages=languages_group,
        size_and_structure=size_group,
        stack_and_tooling=stack_group,
        cicd_and_operations=cicd_group,
        quality_indicators=quality_group,
        warnings_and_gaps=warnings_group,
    )

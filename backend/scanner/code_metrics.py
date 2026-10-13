"""
Code Metrics & Structure Scanner Module

Calculates lines of code, code file counts, average file sizes,
directory nesting depth, module estimations, and scope/PoC eligibility.

This module is deterministic — no AI involved.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import settings
from ..models.scanner_output import (
    ConfidenceLevel,
    ScopeAssessment,
    SignalGroup,
    SizeAndStructureData,
)
from .tech_stack import LANGUAGE_EXTENSIONS


def is_excluded_path(path: Path, workspace: Path) -> bool:
    """Check if a path falls within excluded directories or files."""
    try:
        rel_parts = path.relative_to(workspace).parts
    except ValueError:
        rel_parts = path.parts

    for part in rel_parts:
        if part in settings.excluded_dirs or part.startswith(".git"):
            return True

    if path.suffix.lower() in settings.excluded_extensions:
        return True

    return False


def collect_repo_files(workspace: Path) -> tuple[list[Path], list[Path], int]:
    """
    Traverse the workspace and collect:
    - supported_code_files: files matching known programming language extensions
    - all_valid_files: all non-excluded files
    - excluded_count: count of excluded files/directories encountered
    """
    supported_code_files: list[Path] = []
    all_valid_files: list[Path] = []
    excluded_count = 0

    for root, dirs, files in os.walk(workspace):
        # Prune excluded directories in-place for fast traversal
        dirs[:] = [
            d for d in dirs
            if d not in settings.excluded_dirs and not d.startswith(".git")
        ]

        for file in files:
            file_path = Path(root) / file
            if is_excluded_path(file_path, workspace):
                excluded_count += 1
                continue

            try:
                if file_path.stat().st_size > settings.max_file_size_bytes:
                    excluded_count += 1
                    continue
            except OSError:
                excluded_count += 1
                continue

            all_valid_files.append(file_path)
            if file_path.suffix.lower() in LANGUAGE_EXTENSIONS:
                supported_code_files.append(file_path)

    return supported_code_files, all_valid_files, excluded_count


def calculate_loc_for_file(file_path: Path) -> int:
    """Count non-empty lines of code in a file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = 0
            for line in f:
                if line.strip():
                    lines += 1
            return lines
    except Exception:
        return 0


def detect_size_and_structure(
    workspace: Path,
    supported_code_files: list[Path],
    all_valid_files: list[Path],
) -> SignalGroup:
    """
    Calculate size and structure signals:
    - code_files count
    - total_files count
    - loc_estimate
    - module_estimate (distinct directories containing code files)
    - avg_file_size_loc
    """
    total_loc = 0
    modules = set()
    evidence_paths = []

    for file_path in supported_code_files:
        loc = calculate_loc_for_file(file_path)
        total_loc += loc
        try:
            rel_dir = file_path.relative_to(workspace).parent
            modules.add(str(rel_dir))
        except ValueError:
            modules.add(str(file_path.parent))

    code_files_count = len(supported_code_files)
    total_files_count = len(all_valid_files)
    avg_loc = round(total_loc / code_files_count, 1) if code_files_count > 0 else 0.0

    # Collect sample evidence paths
    for f in supported_code_files[:5]:
        try:
            evidence_paths.append(str(f.relative_to(workspace)))
        except ValueError:
            evidence_paths.append(str(f))

    data = SizeAndStructureData(
        code_files=code_files_count,
        total_files=total_files_count,
        loc_estimate=total_loc,
        module_estimate=len(modules),
        avg_file_size_loc=avg_loc,
    )

    confidence = ConfidenceLevel.HIGH if code_files_count > 0 else ConfidenceLevel.LOW

    return SignalGroup(
        confidence=confidence,
        confidence_source="Deterministic line and file analysis",
        data=data.model_dump(),
        evidence_paths=evidence_paths,
    )


def assess_poc_scope(
    supported_code_files: list[Path],
    excluded_count: int,
) -> ScopeAssessment:
    """
    Determine if repository fits within PoC scope limits:
    - Target: <= settings.poc_max_files (typically 50 files)
    - Language support check
    """
    code_count = len(supported_code_files)
    scope_warnings: list[str] = []
    eligible = True

    if code_count == 0:
        eligible = False
        scope_warnings.append("No supported source code files detected in repository.")
    elif code_count > settings.poc_max_files:
        eligible = True  # Can still proceed with warning or sample
        scope_warnings.append(
            f"Repository contains {code_count} code files, which exceeds the recommended PoC target of {settings.poc_max_files}. Analysis will run on all detected code."
        )

    exclusion_rules = [
        "Ignored vendor, virtualenv, and build directories (node_modules, .venv, target, dist, build)",
        "Ignored binary files, images, archives, and compiled assets",
        f"Ignored files larger than {settings.max_file_size_bytes // 1000} KB",
    ]

    return ScopeAssessment(
        eligible_for_poc=eligible,
        supported_code_files=code_count,
        excluded_items=excluded_count,
        exclusion_rules=exclusion_rules,
        scope_warnings=scope_warnings,
    )

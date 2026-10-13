"""
Testing & Quality Indicators Scanner Module

Detects test files, testing structures, test-to-code ratios, and
code style/quality gate configurations.

This module is deterministic — no AI involved.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models.scanner_output import (
    ConfidenceLevel,
    QualityIndicatorsData,
    SignalGroup,
)


TEST_DIR_NAMES = {
    "test", "tests", "__tests__", "spec", "specs", "testing",
    "integration_test", "integration_tests", "e2e", "unit", "units",
}

QUALITY_GATE_CONFIGS = {
    "sonar-project.properties": "SonarQube",
    ".codecov.yml": "Codecov",
    "codecov.yml": "Codecov",
    ".coveragerc": "Coverage.py",
    ".pre-commit-config.yaml": "pre-commit",
    ".pre-commit-config.yml": "pre-commit",
    ".github/workflows/codeql.yml": "CodeQL",
    ".github/workflows/codeql-analysis.yml": "CodeQL",
    ".codeclimate.yml": "Code Climate",
}

STYLE_CONFIGS = {
    ".eslintrc": "ESLint",
    ".eslintrc.js": "ESLint",
    ".eslintrc.json": "ESLint",
    ".eslintrc.yml": "ESLint",
    "eslint.config.js": "ESLint",
    "eslint.config.mjs": "ESLint",
    ".prettierrc": "Prettier",
    ".prettierrc.json": "Prettier",
    ".prettierrc.js": "Prettier",
    "biome.json": "Biome",
    ".flake8": "flake8",
    "ruff.toml": "ruff",
    ".ruff.toml": "ruff",
    ".editorconfig": "EditorConfig",
    "pyproject.toml": None,  # May configure ruff, black, pytest
    "setup.cfg": None,
}


def is_test_file(file_path: Path, workspace: Path) -> bool:
    """
    Check if a file is a test file based on its naming pattern
    or presence within a test directory.
    """
    name = file_path.name.lower()

    # Check directory parts
    try:
        rel_parts = file_path.relative_to(workspace).parts
    except ValueError:
        rel_parts = file_path.parts

    for part in rel_parts[:-1]:
        if part.lower() in TEST_DIR_NAMES:
            return True

    # Python
    if name.startswith("test_") or name.endswith("_test.py"):
        return True

    # JS / TS
    if re.search(r'\.(test|spec)\.(js|jsx|ts|tsx)$', name):
        return True

    # Java / Kotlin
    if re.search(r'(test|tests|testcase)\.(java|kt|scala)$', name):
        return True

    # Go
    if name.endswith("_test.go"):
        return True

    # Ruby / PHP
    if name.endswith("_spec.rb") or name.endswith("test.php"):
        return True

    return False


def detect_quality_indicators(
    workspace: Path,
    supported_code_files: list[Path],
    known_linters: list[str] | None = None,
    known_formatters: list[str] | None = None,
) -> SignalGroup:
    """
    Analyze test coverage proxy signals, quality gates, and code style tools.
    """
    test_files: list[Path] = []
    source_files: list[Path] = []
    evidence_paths: list[str] = []

    for file_path in supported_code_files:
        if is_test_file(file_path, workspace):
            test_files.append(file_path)
        else:
            source_files.append(file_path)

    test_count = len(test_files)
    source_count = len(source_files)
    ratio = round(test_count / source_count, 2) if source_count > 0 else 0.0

    # Collect sample test evidence
    for tf in test_files[:5]:
        try:
            evidence_paths.append(str(tf.relative_to(workspace)))
        except ValueError:
            evidence_paths.append(str(tf))

    # Quality gates detection
    quality_gates_found: list[str] = []
    for rel_path, gate_name in QUALITY_GATE_CONFIGS.items():
        candidate = workspace / rel_path
        if candidate.exists():
            quality_gates_found.append(gate_name)
            evidence_paths.append(rel_path)

    has_quality_gate = len(quality_gates_found) > 0
    quality_gate_notes = (
        f"Detected quality tools: {', '.join(quality_gates_found)}"
        if has_quality_gate else "No external quality gate configurations found."
    )

    # Code style tools
    style_tools: set[str] = set()
    if known_linters:
        style_tools.update(known_linters)
    if known_formatters:
        style_tools.update(known_formatters)

    for rel_path, tool_name in STYLE_CONFIGS.items():
        candidate = workspace / rel_path
        if candidate.exists():
            if tool_name:
                style_tools.add(tool_name)
            evidence_paths.append(rel_path)

    has_style = len(style_tools) > 0

    data = QualityIndicatorsData(
        test_to_code_file_ratio=ratio,
        test_file_count=test_count,
        source_file_count=source_count,
        executed_coverage=None,  # Requires test execution, so marked None (estimated via proxy)
        has_quality_gate=has_quality_gate,
        quality_gate_notes=quality_gate_notes,
        has_code_style_config=has_style,
        code_style_tools=sorted(list(style_tools)),
    )

    # Determine confidence
    if test_count > 0 or has_style:
        confidence = ConfidenceLevel.HIGH
        confidence_source = "Test file discovery and style configuration parsing"
    else:
        confidence = ConfidenceLevel.LOW
        confidence_source = "No test files or style configurations discovered"

    return SignalGroup(
        confidence=confidence,
        confidence_source=confidence_source,
        data=data.model_dump(),
        evidence_paths=list(dict.fromkeys(evidence_paths))[:10],
    )

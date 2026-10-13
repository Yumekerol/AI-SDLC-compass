"""
Documentation Scanner Module

Detects project documentation, README files, API specifications
(OpenAPI/Swagger/GraphQL), Architecture Decision Records (ADRs),
contributing guides, and licenses.

This module is deterministic — no AI involved.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..models.scanner_output import ConfidenceLevel, SignalGroup


README_CANDIDATES = [
    "README.md", "readme.md", "README.rst", "README.txt", "README", "ReadMe.md"
]

API_SPEC_PATTERNS = [
    "openapi.json", "openapi.yaml", "openapi.yml",
    "swagger.json", "swagger.yaml", "swagger.yml",
    "api-spec.yaml", "api-spec.json", "schema.graphql",
]

DOCS_DIRS = ["docs", "doc", "documentation", "wiki"]


def detect_documentation_signals(workspace: Path) -> tuple[bool, str, list[str]]:
    """
    Detect documentation health, returning:
    - has_documentation: bool
    - documentation_notes: str summary
    - evidence_paths: list of found doc files
    """
    evidence_paths: list[str] = []
    notes: list[str] = []

    # 1. README check
    has_readme = False
    readme_path = None
    for cand in README_CANDIDATES:
        p = workspace / cand
        if p.exists():
            has_readme = True
            readme_path = cand
            evidence_paths.append(cand)
            try:
                size_kb = round(p.stat().st_size / 1024, 1)
                notes.append(f"Found {cand} ({size_kb} KB)")
            except Exception:
                notes.append(f"Found {cand}")
            break

    if not has_readme:
        notes.append("No top-level README found")

    # 2. Docs directory / Architecture / ADRs
    has_docs_dir = False
    for dd in DOCS_DIRS:
        p = workspace / dd
        if p.exists() and p.is_dir():
            has_docs_dir = True
            doc_files = [f for f in p.glob("**/*") if f.is_file() and f.suffix in {".md", ".rst", ".adoc"}]
            notes.append(f"Found '{dd}/' directory with {len(doc_files)} doc file(s)")
            for df in doc_files[:3]:
                try:
                    evidence_paths.append(str(df.relative_to(workspace)))
                except ValueError:
                    evidence_paths.append(str(df))
            break

    # ADRs check
    adr_candidates = [
        workspace / "docs" / "adr",
        workspace / "doc" / "adr",
        workspace / "adr",
    ]
    for adr in adr_candidates:
        if adr.exists() and adr.is_dir():
            adrs = list(adr.glob("*.md"))
            if adrs:
                notes.append(f"Found {len(adrs)} Architecture Decision Records (ADRs)")
                evidence_paths.append(str(adr.relative_to(workspace)))

    # 3. API Specs
    api_specs = []
    for spec in API_SPEC_PATTERNS:
        p = workspace / spec
        if p.exists():
            api_specs.append(spec)
            evidence_paths.append(spec)
    for pattern in ["*openapi*.yaml", "*openapi*.json", "*swagger*.yaml", "*swagger*.json"]:
        for match in workspace.glob(pattern):
            if match.is_file():
                try:
                    rel = str(match.relative_to(workspace))
                    if rel not in api_specs:
                        api_specs.append(rel)
                        evidence_paths.append(rel)
                except ValueError:
                    pass

    if api_specs:
        notes.append(f"API specification detected: {', '.join(api_specs[:2])}")

    # 4. Contributing & License
    for cl in ["CONTRIBUTING.md", "LICENSE", "LICENSE.md", "LICENSE.txt"]:
        if (workspace / cl).exists():
            evidence_paths.append(cl)

    has_documentation = has_readme or has_docs_dir or len(api_specs) > 0
    documentation_notes = "; ".join(notes) if notes else "No documentation found"

    return has_documentation, documentation_notes, evidence_paths

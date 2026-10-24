"""Specialist agent specs and the shapes their runs produce."""

from __future__ import annotations

from .base import Finding, NeedsInput, Report, SpecialistSpec
from .code_refactoring import SPEC as CODE_REFACTORING_SPEC
from .devops_monitoring import SPEC as DEVOPS_MONITORING_SPEC
from .qa_testing import SPEC as QA_TESTING_SPEC
from .requirements_design import SPEC as REQUIREMENTS_DESIGN_SPEC

# Fixed pipeline order: single local Ollama daemon serializes inference
# regardless, so "sequential" is the real execution model, not just a UI
# framing choice.
PIPELINE_ORDER: list[SpecialistSpec] = [
    REQUIREMENTS_DESIGN_SPEC,
    CODE_REFACTORING_SPEC,
    QA_TESTING_SPEC,
    DEVOPS_MONITORING_SPEC,
]

SPECS_BY_ROLE: dict[str, SpecialistSpec] = {spec.role: spec for spec in PIPELINE_ORDER}

__all__ = [
    "Finding",
    "NeedsInput",
    "Report",
    "SpecialistSpec",
    "PIPELINE_ORDER",
    "SPECS_BY_ROLE",
]

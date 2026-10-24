"""
Per-run context for a single specialist invocation.

Replaces the old module-level `contextvars.ContextVar` repo-root scoping in
`tools.py`: that pattern is safe for exactly one conversation at a time, but
breaks the moment two specialist runs (different sessions, or two specialists
running back to back on different repos) are live in the same process, since
they'd share one global variable. A `RunContext` is built fresh per call and
passed explicitly instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunContext:
    """Everything a specialist's tools need to inspect one repository."""

    root: Path
    scan_output: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()

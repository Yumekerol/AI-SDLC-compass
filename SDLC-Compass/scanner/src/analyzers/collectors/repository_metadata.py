from __future__ import annotations

import logging

from pathlib import Path
from typing import Any

from .__common__ import _run_git

logger = logging.getLogger(__name__)


def collect_repository_metadata(repo_path: Path) -> dict[str, Any]:
    """Recolhe metadados gerais; parte deles já existe em CloneResult."""
    commits_total = _run_git(repo_path, "rev-list", "--count", "HEAD")
    branch = _run_git(repo_path, "branch", "--show-current")
    head_sha = _run_git(repo_path, "rev-parse", "HEAD")
    shallow = _run_git(repo_path, "rev-parse", "--is-shallow-repository")

    return {
        "commits_total": int(commits_total) if commits_total.isdigit() else None,
        "branch": branch or None,
        "head_sha": head_sha or None,
        # Se for um clone superficial, todas as métricas de histórico são parciais.
        "is_shallow_clone": {"true": True, "false": False}.get(shallow),
    }


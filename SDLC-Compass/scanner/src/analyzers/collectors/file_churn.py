from __future__ import annotations

import logging
import subprocess

from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from .__common__ import CommitRecord, _ensure_history, TOP_N_DEFAULT


def get_current_files(repo_path: Path) -> set[str]:
    """Devolve os paths dos ficheiros existentes no commit atual."""

    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    return set(result.stdout.splitlines())


def collect_file_churn(
    repo_path: Path,
    commits: list[CommitRecord] | None = None,
    top_n: int = TOP_N_DEFAULT,
    *,
    since: str | None = None,
) -> dict[str, Any]:
    commits = _ensure_history(repo_path, commits, since)
    added: Counter[str] = Counter()
    deleted: Counter[str] = Counter()
    commit_count: Counter[str] = Counter()

    for commit in commits:
        for path, a, d in commit.files:
            added[path] += a
            deleted[path] += d
            commit_count[path] += 1

    total_changed = sum(added.values()) + sum(deleted.values())

    # Obter os ficheiros existentes no commit atual.
    current_files = get_current_files(repo_path)

    # Excluir do ranking os ficheiros que já foram apagados.
    ranking_candidates = [
        p for p in commit_count
        if p in current_files
    ]

    ranking = sorted(
        ranking_candidates,
        key=lambda p: added[p] + deleted[p],
        reverse=True,
    )[:top_n]

    top_changed = sum(added[p] + deleted[p] for p in ranking)

    return {
        "files_with_changes": len(commit_count),
        "lines_added_total": sum(added.values()),
        "lines_deleted_total": sum(deleted.values()),
        "top_files": [
            {
                "file": p,
                "lines_added": added[p],
                "lines_deleted": deleted[p],
                "lines_changed": added[p] + deleted[p],
                "commits": commit_count[p],
            }
            for p in ranking
        ],
        "top_files_share_of_churn": (
            round(top_changed / total_changed, 4) if total_changed else None
        ),
        "limitations": (
            "Churn elevado não significa, por si só, dívida técnica. Renomeações são tratadas "
            "como remoção+adição (--no-renames); lockfiles e ficheiros gerados são ignorados."
        ),
    }
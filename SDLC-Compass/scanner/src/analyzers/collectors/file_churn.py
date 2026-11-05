from __future__ import annotations

import logging
import subprocess

from collections import Counter
from pathlib import Path
from typing import Any

from pathlib import Path, PurePosixPath
from typing import Any

from .__common__ import CommitRecord, _ensure_history, _run_git, TOP_N_DEFAULT, get_current_files

logger = logging.getLogger(__name__)

CHURN_NOISE_NAMES = {"history.md", "changelog.md", "changes.md", "package.json"}

def _is_churn_noise(path: str) -> bool:
    return PurePosixPath(path).name.lower() in CHURN_NOISE_NAMES


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
            if _is_churn_noise(path):      # NOVO: ruído fora de TODOS os totais
                continue
            added[path] += a
            deleted[path] += d
            commit_count[path] += 1

    total_changed = sum(added.values()) + sum(deleted.values())

    current_files = get_current_files(repo_path)

    ranking_candidates = [p for p in commit_count if p in current_files]

    # Ordenar TODOS antes de cortar: churn desc, empate por nome (determinístico)
    ranking = sorted(
        ranking_candidates,
        key=lambda p: (-(added[p] + deleted[p]), p),
    )[:top_n]

    top_changed = sum(added[p] + deleted[p] for p in ranking)

    top_files = [
        {
            "file": p,
            "lines_added": added[p],
            "lines_deleted": deleted[p],
            "lines_changed": added[p] + deleted[p],
            "commits": commit_count[p],
        }
        for p in ranking
    ]

    return {
        "files_with_changes": len(commit_count),
        "lines_added_total": sum(added.values()),
        "lines_deleted_total": sum(deleted.values()),
        "top_files": top_files,
        "top_files_share_of_churn": (
            round(top_changed / total_changed, 4) if total_changed else None
        ),
        "limitations": (
            "Churn elevado não significa, por si só, dívida técnica. Renomeações são tratadas "
            "como remoção+adição (--no-renames); lockfiles, ficheiros gerados, changelogs e "
            "package.json são excluídos dos totais. O top inclui só ficheiros presentes no HEAD; "
            "os totais incluem ficheiros entretanto removidos."
        ),
    }
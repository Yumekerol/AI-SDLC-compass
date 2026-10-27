from __future__ import annotations

import logging

from collections import defaultdict
from pathlib import Path
from typing import Any

from .__common__ import CommitRecord, _ensure_history, MAX_COMMITS_LISTED, _distribution, LARGE_COMMIT_LINES, TOP_N_DEFAULT, _truncate

logger = logging.getLogger(__name__)


def _commit_summary(commit: CommitRecord) -> dict[str, Any]:
    return {
        #"sha": commit.sha,
        "date": commit.date,
        "message": _truncate(commit.subject),
        "files_changed": commit.files_changed,
        "lines_added": commit.lines_added,
        "lines_deleted": commit.lines_deleted,
    }



def collect_commit_churn(
    repo_path: Path,
    commits: list[CommitRecord] | None = None,
    *,
    since: str | None = None,
    max_listed: int = MAX_COMMITS_LISTED,
) -> dict[str, Any]:
    commits = _ensure_history(repo_path, commits, since)
    measured = [c for c in commits if c.files]    # commits só com ficheiros excluídos distorcem a mediana

    by_month: dict[str, list[CommitRecord]] = defaultdict(list)
    for commit in measured:
        by_month[commit.month].append(commit)

    periods = {
        month: {
            "commits": len(items),
            "lines_changed": _distribution([c.lines_changed for c in items]),
            "files_changed": _distribution([c.files_changed for c in items]),
        }
        for month, items in sorted(by_month.items())
    }
    large = [c for c in measured if c.lines_changed >= LARGE_COMMIT_LINES]
    largest = sorted(measured, key=lambda c: c.lines_changed, reverse=True)[:TOP_N_DEFAULT]

    return {
        "commits_measured": len(measured),
        "commits_without_measurable_changes": len(commits) - len(measured),
        "lines_changed_per_commit": _distribution([c.lines_changed for c in measured]),
        "files_changed_per_commit": _distribution([c.files_changed for c in measured]),
        "large_commit_threshold_lines": LARGE_COMMIT_LINES,
        "large_commits_count": len(large),
        "large_commits_ratio": round(len(large) / len(measured), 4) if measured else None,
        "by_month": periods,
        "largest_commits": [_commit_summary(c) for c in largest],
        "commits": [_commit_summary(c) for c in commits[:max_listed]],   # mais recentes primeiro
        "commits_list_truncated": len(commits) > max_listed,
        "limitations": (
            "Tamanho = linhas adicionadas+removidas em ficheiros de texto (binários contam "
            "como 0 linhas). Merges, lockfiles e ficheiros gerados excluídos. Sem dados de "
            "autor: não usar para avaliar produtividade individual."
        ),
    }

from __future__ import annotations

import logging
import re

from collections import Counter
from pathlib import Path
from typing import Any

from .__common__ import CommitRecord, _ensure_history, MAX_LISTED_ITEMS, _truncate

logger = logging.getLogger(__name__)




FIX_RE = re.compile(
    r"\b(fix(?:e[sd])?|bugs?|bugfix(?:es)?|hotfix(?:es)?|defects?|corrig\w*|correç\w+)\b",
    re.IGNORECASE,
)
REVERT_SUBJECT_RE = re.compile(r"^\s*revert\b|\breverts?\s+commit\b", re.IGNORECASE)


def collect_fixes_and_reverts(
    repo_path: Path,
    commits: list[CommitRecord] | None = None,
    *,
    since: str | None = None,
) -> dict[str, Any]:
    commits = _ensure_history(repo_path, commits, since)
    fix_evidence: list[dict[str, Any]] = []
    revert_evidence: list[dict[str, Any]] = []
    fixes_by_month: Counter[str] = Counter()
    reverts_by_month: Counter[str] = Counter()
    fix_count = revert_count = 0

    for commit in commits:
        fix_match = FIX_RE.search(commit.subject)
        if fix_match:
            fix_count += 1
            fixes_by_month[commit.month] += 1
            if len(fix_evidence) < MAX_LISTED_ITEMS:
                fix_evidence.append({
                    #"sha": commit.sha, 
                    "date": commit.date,
                    "message": _truncate(commit.subject),
                    "matched_term": fix_match.group(0).lower(),
                })
        if REVERT_SUBJECT_RE.search(commit.subject): #or commit.reverts_sha:
            revert_count += 1
            reverts_by_month[commit.month] += 1
            if len(revert_evidence) < MAX_LISTED_ITEMS:
                revert_evidence.append({
                    #"sha": commit.sha, 
                    "date": commit.date,
                    "message": _truncate(commit.subject),
                    "matched_term": revert_match.group(0).lower() if (revert_match := REVERT_SUBJECT_RE.search(commit.subject)) else None,
                    #"reverted_sha": commit.reverts_sha,
                })

    total = len(commits)
    return {
        "commits_analyzed": total,
        "fix_commits": fix_count,
        "fix_ratio": round(fix_count / total, 4) if total else None,
        "revert_commits": revert_count,
        "revert_ratio": round(revert_count / total, 4) if total else None,
        "fixes_by_month": dict(sorted(fixes_by_month.items())),
        "reverts_by_month": dict(sorted(reverts_by_month.items())),
        "fix_evidence": fix_evidence,
        "revert_evidence": revert_evidence,
        "evidence_truncated": fix_count > MAX_LISTED_ITEMS or revert_count > MAX_LISTED_ITEMS,
        "limitations": (
            "Classificação pelo assunto do commit (palavras como fix, bug, hotfix, defect, "
            "revert, corrige/correção). Não identifica todos os bugs e pode ter falsos positivos. "
            "Um commit pode contar como correção e reversão."
        ),
    }


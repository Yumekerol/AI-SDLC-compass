from __future__ import annotations

import logging

from collections import Counter
from pathlib import Path
from typing import Any

from .__common__ import CommitRecord, _ensure_history

logger = logging.getLogger(__name__)



# Em monorepos, o "componente" é o 2.º nível (ex.: packages/api).
MONOREPO_CONTAINER_DIRS = {"packages", "apps", "services", "libs", "modules", "plugins", "projects", "src"}


def _component_of(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return "(root)"
    if parts[0].lower() in MONOREPO_CONTAINER_DIRS and len(parts) > 2:
        return "/".join(parts[:2])
    return parts[0]


def collect_component_activity(
    repo_path: Path,
    commits: list[CommitRecord] | None = None,
    top_n: int = 30,
    *,
    since: str | None = None,
) -> dict[str, Any]:
    commits = _ensure_history(repo_path, commits, since)
    stats: dict[str, dict[str, Any]] = {}

    for commit in commits:
        touched: set[str] = set()
        for path, added, deleted in commit.files:
            component = _component_of(path)
            entry = stats.setdefault(component, {
                "commits": 0, "files": set(), "lines_added": 0, "lines_deleted": 0,
                "months": Counter(), "first_date": commit.date[:10], "last_date": commit.date[:10],
            })
            entry["files"].add(path)
            entry["lines_added"] += added
            entry["lines_deleted"] += deleted
            touched.add(component)
        for component in touched:
            entry = stats[component]
            entry["commits"] += 1
            entry["months"][commit.month] += 1
            entry["first_date"] = min(entry["first_date"], commit.date[:10])
            entry["last_date"] = max(entry["last_date"], commit.date[:10])

    ranked = sorted(stats.items(),
                    key=lambda kv: kv[1]["lines_added"] + kv[1]["lines_deleted"], reverse=True)
    return {
        "components_total": len(stats),
        "components": [
            {
                "component": name,
                "commits": s["commits"],
                "files_changed": len(s["files"]),
                "lines_added": s["lines_added"],
                "lines_deleted": s["lines_deleted"],
                "lines_changed": s["lines_added"] + s["lines_deleted"],
                "first_change_date": s["first_date"],
                "last_change_date": s["last_date"],
                "commits_by_month": dict(sorted(s["months"].items())),
            }
            for name, s in ranked[:top_n]
        ],
        "limitations": (
            "Contagens observadas; o agrupamento em componentes é heurístico (1.º diretório, ou "
            "2.º nível em monorepos como packages/, apps/, services/, src/). Ficheiros na raiz "
            "ficam em '(root)'."
        ),
    }


from __future__ import annotations

import logging
import re

from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


from .__common__ import CommitRecord, _resolve_files, _relative_path, _ensure_history, MAX_LISTED_ITEMS, TOP_N_DEFAULT, get_current_files

logger = logging.getLogger(__name__)


DOC_MARKUP_EXTENSIONS = {".md", ".mdx", ".rst", ".adoc"}
DOC_EXTENSIONS = DOC_MARKUP_EXTENSIONS | {".txt"}
_DOC_DIR_NAMES = {"docs", "doc", "documentation", "wiki"}
_ADR_DIR_NAMES = {"adr", "adrs", "decisions", "architecture-decisions", "architecture_decisions"}
_CHANGELOG_STEMS = {"changelog", "changes", "history", "release_notes", "release-notes",
                    "releasenotes", "news"}
_RUNBOOK_RE = re.compile(r"runbook|playbook", re.IGNORECASE)
_ONBOARDING_RE = re.compile(r"install|setup|onboarding|getting[-_ ]?started|quick[-_ ]?start|contributing",
                            re.IGNORECASE)
_ADR_NAME_RE = re.compile(r"^adr[-_]?\d+", re.IGNORECASE)



def _classify_doc(relative: str) -> list[str]:
    """Devolve uma única categoria de documentação por ficheiro."""
    path = PurePosixPath(relative)
    suffix = path.suffix.lower()
    stem = path.stem.lower()

    if suffix not in DOC_EXTENSIONS and suffix != "":
        return []

    dirs = [part.lower() for part in path.parts[:-1]]

    # Prioridade 1: README
    if stem == "readme":
        return ["readme"]

    # Prioridade 2: Changelog
    if stem in _CHANGELOG_STEMS:
        return ["changelog"]

    # Prioridade 3: ADR
    if any(d in _ADR_DIR_NAMES for d in dirs) or _ADR_NAME_RE.match(stem):
        return ["adr"]

    # Prioridade 4: Runbook
    if _RUNBOOK_RE.search(relative):
        return ["runbook"]

    # Prioridade 5: Instalação e onboarding
    if _ONBOARDING_RE.search(path.name):
        return ["install_onboarding"]

    # Prioridade 6: Diretórios de documentação
    if any(d in _DOC_DIR_NAMES for d in dirs):
        return ["docs_dir"]

    # Ficheiros sem extensão só contam se forem README ou CHANGELOG
    if suffix == "":
        return []

    # Outros ficheiros Markdown / documentação
    if suffix in DOC_MARKUP_EXTENSIONS:
        return ["other"]

    return []


def collect_documentation_inventory(
    repo_path: Path,
    files: list[Path] | None = None,
    commits: list[CommitRecord] | None = None,
    *,
    since: str | None = None,
) -> dict[str, Any]:
    docs: dict[str, list[str]] = {}
    for path in _resolve_files(repo_path, files):
        relative = _relative_path(repo_path, path)
        categories = _classify_doc(relative)
        if categories:
            docs[relative] = categories

    by_category: Counter[str] = Counter(c for cats in docs.values() for c in cats)

    # Frequência de alterações aos ficheiros de documentação (a partir do histórico).
    commits = _ensure_history(repo_path, commits, since)
    cache: dict[str, bool] = {}
    commits_touching_docs = 0
    changes: Counter[str] = Counter()
    last_change: dict[str, str] = {}
    for commit in commits:                       # mais recentes primeiro
        touched = False
        for path, _a, _d in commit.files:
            if path not in cache:
                cache[path] = bool(_classify_doc(path))
            if cache[path]:
                touched = True
                changes[path] += 1
                last_change.setdefault(path, commit.date[:10])
        commits_touching_docs += touched

    current_files = get_current_files(repo_path)

    ranked = sorted(
        ((f, n) for f, n in changes.items() if f in current_files),
        key=lambda kv: (-kv[1], kv[0]),
    )[:TOP_N_DEFAULT]

    return {
        "documentation_files_count": len(docs),
        "files_by_category": dict(by_category.most_common()),
        "documentation_files": [
            {"file": f, "categories": cats} for f, cats in sorted(docs.items())[:MAX_LISTED_ITEMS]
        ],
        "documentation_files_truncated": len(docs) > MAX_LISTED_ITEMS,
        "change_frequency": {
            "commits_touching_docs": commits_touching_docs,
            "share_of_commits": round(commits_touching_docs / len(commits), 4) if commits else None,
            "most_changed_files": [
                {"file": f, "commits": n, "last_change_date": last_change[f]}
                for f, n in ranked
            ],
        },
        "limitations": (
            "Categorias por nome/diretório (README, docs/, ADRs, runbooks, instalação/onboarding, "
            "changelogs). A ausência de documentação detetada não prova que não exista noutro sistema."
        ),
    }

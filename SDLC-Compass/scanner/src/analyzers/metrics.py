from __future__ import annotations

import logging

from pathlib import Path
from typing import Any

from .collectors.__common__ import (
    _iter_source_files, 
    count_excluded_items,
    _load_commit_history,
    CommitRecord, 
    DEFAULT_MAX_COMMITS, 
)

from .collectors.repository_metadata import collect_repository_metadata
from .collectors.file_churn import collect_file_churn
from .collectors.frameworks_dependencies import collect_frameworks_dependencies
from .collectors.files_by_language import collect_files_by_language
from .collectors.cicd_configuration import collect_cicd_configuration
from .collectors.test_inventory import collect_test_inventory
from .collectors.commit_churn import collect_commit_churn
from .collectors.fixes_and_reverts import collect_fixes_and_reverts
from .collectors.component_activity import collect_component_activity
from .collectors.documentation_inventory import collect_documentation_inventory
from .collectors.technical_debt_markers import collect_technical_debt_markers
from .collectors.size_and_structure import collect_size_and_structure
from .collectors.infrastructure import collect_infrastructure


logger = logging.getLogger(__name__)


def _history_window(
    commits: list[CommitRecord], since: str | None, max_commits: int
) -> dict[str, Any]:
    dates = sorted(c.date[:10] for c in commits)
    return {
        "commits_analyzed": len(commits),
        "truncated_by_max_commits": len(commits) >= max_commits,
        "first_commit_date": dates[0] if dates else None,
        "last_commit_date": dates[-1] if dates else None,
        "note": "Merges excluídos; ficheiros gerados/lockfiles e exclusões das Settings ignorados.",
    }


def _safe_collect(name: str, func, *args, **kwargs) -> dict[str, Any]:
    """Isola falhas: um coletor com erro não impede os restantes."""
    try:
        return func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - queremos isolar qualquer falha de coletor
        logger.exception("Coletor %s falhou", name)
        return {"error": f"Coletor falhou ({type(exc).__name__})."}


def collect_all_metrics(
    repo_path: Path,
    since: str | None = None,
    max_commits: int = DEFAULT_MAX_COMMITS,
) -> dict[str, Any]:
    """Executa os coletores e devolve um resultado JSON-serializável.

    Args:
        repo_path: caminho do clone.
        since: período do histórico (formato de `git log --since`, ex.: "12 months ago").
        max_commits: limite de commits analisados (do mais recente para o mais antigo).
    """
    repo_path = Path(repo_path).resolve()

    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError("repo_path tem de apontar para uma pasta existente.")

    files = list(_iter_source_files(repo_path))          # uma só travessia do sistema de ficheiros
    commits = _load_commit_history(repo_path, since=since, max_commits=max_commits)  # um só `git log`

    return {
        "repository": _safe_collect("repository", collect_repository_metadata, repo_path),
        "excluded_items": _safe_collect("excluded_items", count_excluded_items, repo_path),
        "history_window": _history_window(commits, since, max_commits),
        "file_churn": _safe_collect("file_churn", collect_file_churn, repo_path, commits),
        "frameworks_dependencies": _safe_collect(
            "frameworks_dependencies", collect_frameworks_dependencies, repo_path, files),
        "files_by_language": _safe_collect(
            "files_by_language", collect_files_by_language, repo_path, files),
        "cicd_configuration": _safe_collect(
            "cicd_configuration", collect_cicd_configuration, repo_path, files),
        "test_inventory": _safe_collect("test_inventory", collect_test_inventory, repo_path, files),
        "commit_churn": _safe_collect("commit_churn", collect_commit_churn, repo_path, commits),
        "fixes_and_reverts": _safe_collect(
            "fixes_and_reverts", collect_fixes_and_reverts, repo_path, commits),
        "component_activity": _safe_collect(
            "component_activity", collect_component_activity, repo_path, commits),
        "documentation_inventory": _safe_collect(
            "documentation_inventory", collect_documentation_inventory, repo_path, files, commits),
        "technical_debt_markers": _safe_collect(
            "technical_debt_markers", collect_technical_debt_markers, repo_path, files),
        "size_and_structure": _safe_collect(
            "size_and_structure", collect_size_and_structure, repo_path, files),
        "infrastructure": _safe_collect("infrastructure", collect_infrastructure, repo_path, files),
    }
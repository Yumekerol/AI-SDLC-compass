from __future__ import annotations

import logging
import re
import subprocess

from pathlib import Path, PurePosixPath
from typing import Any

from ...config import settings

logger = logging.getLogger("analyzer_common_utils")



DEFAULT_MAX_COMMITS = 2_000        # limite de commits analisados (evita timeouts)
HISTORY_TIMEOUT_SECONDS = 180       # timeout do `git log` completo
TOP_N_DEFAULT = 10
MAX_LISTED_ITEMS = 200              # limite de itens em listas de evidências
MAX_COMMITS_LISTED = 500            # limite de commits individuais devolvidos
LARGE_COMMIT_LINES = 500            # limiar (linhas adicionadas+removidas) para "commit grande"
MAX_DEPS_PER_MANIFEST = 500


LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript/JSX",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/TSX",
    ".java": "Java",
}

class CommitRecord:
    """Um commit (não-merge) com estatísticas por ficheiro. Sem dados de autor."""

    def __init__(self, sha: str, date: str, subject: str, reverts_sha: str | None, files: tuple[tuple[str, int, int], ...], lines_added: int, lines_deleted: int):
        self.sha = sha
        self.date = date
        self.subject = subject
        self.reverts_sha = reverts_sha
        self.files = files
        self.lines_added = lines_added
        self.lines_deleted = lines_deleted

    """ sha: str
    date: str                                  # ISO 8601 (data do committer)
    subject: str
    reverts_sha: str | None                    # extraído de "This reverts commit <sha>"
    files: tuple[tuple[str, int, int], ...]    # (path, adicionadas, removidas)
    lines_added: int
    lines_deleted: int """

    @property
    def lines_changed(self) -> int:
        return self.lines_added + self.lines_deleted

    @property
    def files_changed(self) -> int:
        return len(self.files)

    @property
    def month(self) -> str:
        return self.date[:7]

_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"
_BODY_END = "\x1d"
_GIT_LOG_FORMAT = f"%x1e%H%x1f%cI%x1f%s%x1f%b%x1d"
_REVERTS_RE = re.compile(r"This reverts commit ([0-9a-f]{7,64})")



def _run_git(
    repo_path: Path,
    *args: str,
    timeout: int = 30,
    strip: bool = True,
) -> str:
    """Executa um comando Git de leitura e devolve stdout.

    O repositório deve ser um clone já validado pelo módulo git_extract.
    Não usar comandos que executem hooks, scripts ou conteúdo do repositório.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "-c", "core.quotepath=false", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Comando Git excedeu o timeout (%s)", args[0])
        return ""

    if result.returncode != 0:
        logger.warning("Comando Git falhou (%s): %s", args[0], result.stderr[:200])
        return ""
    return result.stdout.strip() if strip else result.stdout


def _iter_source_files(repo_path: Path):
    """Percorre ficheiros respeitando os filtros definidos em Settings."""
    excluded_dirs = set(settings.excluded_dirs)
    excluded_extensions = {ext.lower() for ext in settings.excluded_extensions}

    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue

        # Não analisar o conteúdo interno do próprio Git.
        relative_parts = path.relative_to(repo_path).parts
        if ".git" in relative_parts:
            continue

        # Ignorar diretórios excluídos em qualquer nível.
        if any(part in excluded_dirs for part in relative_parts[:-1]):
            continue

        if path.suffix.lower() in excluded_extensions:
            continue

        try:
            if path.stat().st_size > settings.max_file_size_bytes:
                continue
        except OSError:
            continue

        yield path


def count_excluded_items(repo_path: Path) -> int:
    """Conta o número de ficheiros excluídos pelos filtros definidos em Settings."""

    excluded_dirs = set(settings.excluded_dirs)
    excluded_extensions = {
        ext.lower() for ext in settings.excluded_extensions
    }

    excluded_count = 0

    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue

        relative_parts = path.relative_to(repo_path).parts

        # Ignorar ficheiros dentro de diretórios excluídos.
        if any(part in excluded_dirs for part in relative_parts[:-1]):
            excluded_count += 1
            continue

        # Ignorar extensões excluídas.
        if path.suffix.lower() in excluded_extensions:
            excluded_count += 1
            continue

    return excluded_count


def _resolve_files(repo_path: Path, files: list[Path] | None) -> list[Path]:
    """Reutiliza a lista de ficheiros já percorrida (evita várias travessias)."""
    return files if files is not None else list(_iter_source_files(repo_path))


def _read_text(path: Path) -> str | None:
    """Lê ficheiros de texto pequenos; ignora binários e erros de encoding."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _relative_path(repo_path: Path, path: Path) -> str:
    return path.relative_to(repo_path).as_posix()


def _truncate(text: str, limit: int = 200) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _percentile(sorted_values: list[int], pct: float) -> float:
    """Percentil com interpolação linear sobre uma lista já ordenada."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * pct / 100
    lower = int(k)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (k - lower)


def _distribution(values: list[int]) -> dict[str, Any]:
    """Estatísticas descritivas (mediana e percentis) de uma lista de inteiros."""
    if not values:
        return {"count": 0, "mean": None, "median": None,
                "p75": None, "p90": None, "p95": None, "max": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "mean": round(sum(ordered) / len(ordered), 2),
        "median": round(_percentile(ordered, 50), 2),
        "p75": round(_percentile(ordered, 75), 2),
        "p90": round(_percentile(ordered, 90), 2),
        "p95": round(_percentile(ordered, 95), 2),
        "max": ordered[-1],
    }


GENERATED_FILE_NAMES = {
    "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "go.sum",
    "gradle.lockfile", "packages.lock.json",
}
GENERATED_SUFFIXES = (".lock", ".min.js", ".min.css", ".map")


class _PathFilter:
    """Aplica às paths vindas do histórico Git os mesmos filtros do sistema de ficheiros."""

    def __init__(self) -> None:
        self.excluded_dirs = set(settings.excluded_dirs)
        self.excluded_extensions = {ext.lower() for ext in settings.excluded_extensions}

    def excluded(self, rel: str) -> bool:
        path = PurePosixPath(rel)
        if any(part in self.excluded_dirs for part in path.parts[:-1]):
            return True
        return path.suffix.lower() in self.excluded_extensions

    @staticmethod
    def is_generated(rel: str) -> bool:
        name = PurePosixPath(rel).name.lower()
        return name in GENERATED_FILE_NAMES or name.endswith(GENERATED_SUFFIXES)


def _load_commit_history(
    repo_path: Path,
    since: str | None = None,
    max_commits: int = DEFAULT_MAX_COMMITS,
) -> list[CommitRecord]:
    """Lê o histórico (mais recente primeiro) com uma única chamada a `git log`.

    `since` aceita qualquer valor suportado por `git log --since` (ex.: "12 months ago").
    Ficheiros excluídos pelas Settings e ficheiros gerados são ignorados.
    """
    path_filter = _PathFilter()
    args = [
        "log", "--no-merges", "--no-renames", "--numstat",
        f"--format={_GIT_LOG_FORMAT}", f"--max-count={max_commits}",
    ]
    if since:
        args.append(f"--since={since}")

    raw = _run_git(repo_path, *args, timeout=HISTORY_TIMEOUT_SECONDS, strip=False)
    commits: list[CommitRecord] = []

    for chunk in raw.split(_RECORD_SEP):
        if not chunk.strip():
            continue
        head, _, stats = chunk.partition(_BODY_END)
        fields = head.split(_FIELD_SEP, 3)
        if len(fields) < 4:
            continue
        sha, date, subject, body = (field.strip() for field in fields)
        #if not _SHA_RE.match(sha):
        #    continue

        files: list[tuple[str, int, int]] = []
        for line in stats.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            added_raw, deleted_raw, filename = parts
            filename = filename.strip()
            if path_filter.excluded(filename) or path_filter.is_generated(filename):
                continue
            # Git usa '-' para ficheiros binários: contam como ficheiro alterado, 0 linhas.
            files.append((
                filename,
                int(added_raw) if added_raw.isdigit() else 0,
                int(deleted_raw) if deleted_raw.isdigit() else 0,
            ))

        reverts = _REVERTS_RE.search(body)
        commits.append(CommitRecord(
            sha=sha,
            date=date,
            subject=subject,
            reverts_sha=reverts.group(1) if reverts else None,
            files=tuple(files),
            lines_added=sum(f[1] for f in files),
            lines_deleted=sum(f[2] for f in files),
        ))

    return commits


def _ensure_history(
    repo_path: Path,
    commits: list[CommitRecord] | None,
    since: str | None,
    max_commits: int = DEFAULT_MAX_COMMITS,
) -> list[CommitRecord]:
    if commits is not None:
        return commits
    return _load_commit_history(repo_path, since=since, max_commits=max_commits)


def _count_loc(text: str, suffix: str) -> int:
    """Linhas não vazias que não são só comentário (heurística por prefixo)."""
    prefixes = ("#",) if suffix == ".py" else ("//", "/*", "*")
    return sum(
        1
        for line in text.splitlines()
        if (stripped := line.strip()) and not stripped.startswith(prefixes)
    )


TEST_PATH_MARKERS = {
    "tests", "test", "__tests__", "spec", "specs", "testing", "e2e", "cypress", "playwright",
}
TEST_FILENAME_RE = re.compile(
    r"^(test_.*\.py|.*_test\.(py|go|rb|exs|js|ts|c|cc|cpp|dart)|.*_spec\.rb"
    r"|.*\.(test|spec|cy|e2e)\.[^.]+)$",
    re.IGNORECASE,
)
TEST_CLASS_SUFFIX_RE = re.compile(r"^.*(Test|Tests|IT|ITCase|Spec)\.(java|kt|scala|cs|swift|php)$")


def _is_test_file(relative: str) -> bool:
    path = PurePosixPath(relative)
    if any(part.lower() in TEST_PATH_MARKERS for part in path.parts[:-1]):
        return True
    return bool(TEST_FILENAME_RE.match(path.name) or TEST_CLASS_SUFFIX_RE.match(path.name))

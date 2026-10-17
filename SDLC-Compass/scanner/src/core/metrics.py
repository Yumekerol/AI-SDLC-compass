"""
metrics.py
==========
Coletores de métricas do repositório Git para identificar oportunidades de
integração de AI ao longo do SDLC.

Este ficheiro deve receber o caminho do clone (CloneResult.path) e devolver
um dicionário serializável em JSON. Não clona o repositório nem altera ficheiros.

Métricas implementadas (ver "Métricas Git para identificar oportunidades de AI"):
    01 file_churn               04 cicd_configuration       07 fixes_and_reverts       10 technical_debt_markers
    02 frameworks_dependencies  05 test_inventory           08 component_activity
    03 files_by_language        06 commit_churn             09 documentation_inventory
Extras de contexto: repository, history_window, infrastructure.

Princípios:
- Respeitar os filtros de settings.excluded_dirs, settings.excluded_extensions
  e settings.max_file_size_bytes sempre que se percorrem ficheiros.
- Não executar código do repositório analisado (só se lê texto; só comandos Git de leitura).
- Não ler nem devolver valores de segredos, tokens ou variáveis de ambiente
  (URLs/referências diretas em dependências são omitidas; linhas de código nunca são devolvidas).
- Distinguir métricas diretamente observadas de heurísticas aproximadas:
  cada coletor devolve "evidence_type" ("observed", "heuristic" ou "mixed") e "limitations".
- Manter cada coletor pequeno e independente para facilitar testes.
- Não inferir produtividade individual: nenhum autor/committer é recolhido.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from ..config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes de configuração dos coletores
# ---------------------------------------------------------------------------

DEFAULT_MAX_COMMITS = 20_000        # limite de commits analisados (evita timeouts)
HISTORY_TIMEOUT_SECONDS = 180       # timeout do `git log` completo
TOP_N_DEFAULT = 20
MAX_LISTED_ITEMS = 200              # limite de itens em listas de evidências
MAX_COMMITS_LISTED = 500            # limite de commits individuais devolvidos
LARGE_COMMIT_LINES = 500            # limiar (linhas adicionadas+removidas) para "commit grande"
MAX_DEPS_PER_MANIFEST = 500


# ---------------------------------------------------------------------------
# Helpers comuns
# ---------------------------------------------------------------------------

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


# Ficheiros gerados/lockfiles distorcem churn e tamanho de alterações.
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


# ---------------------------------------------------------------------------
# Histórico Git (carregado uma só vez e partilhado por vários coletores)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommitRecord:
    """Um commit (não-merge) com estatísticas por ficheiro. Sem dados de autor."""

    sha: str
    date: str                                  # ISO 8601 (data do committer)
    subject: str
    reverts_sha: str | None                    # extraído de "This reverts commit <sha>"
    files: tuple[tuple[str, int, int], ...]    # (path, adicionadas, removidas)
    lines_added: int
    lines_deleted: int

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
_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")


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
        if not _SHA_RE.match(sha):
            continue

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


def _commit_summary(commit: CommitRecord) -> dict[str, Any]:
    return {
        "sha": commit.sha,
        "date": commit.date,
        "message": _truncate(commit.subject),
        "files_changed": commit.files_changed,
        "lines_added": commit.lines_added,
        "lines_deleted": commit.lines_deleted,
    }


def _history_window(
    commits: list[CommitRecord], since: str | None, max_commits: int
) -> dict[str, Any]:
    dates = sorted(c.date[:10] for c in commits)
    return {
        "since": since,
        "max_commits": max_commits,
        "commits_analyzed": len(commits),
        "truncated_by_max_commits": len(commits) >= max_commits,
        "first_commit_date": dates[0] if dates else None,
        "last_commit_date": dates[-1] if dates else None,
        "note": "Merges excluídos; ficheiros gerados/lockfiles e exclusões das Settings ignorados.",
    }


# ---------------------------------------------------------------------------
# ======= METADADOS GERAIS DO REPOSITÓRIO (contexto) =======
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ======= 01 · FICHEIROS COM MAIOR CHURN (file_churn) =======
# Ranking de ficheiros por linhas adicionadas+removidas e nº de commits.
# ---------------------------------------------------------------------------

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
    ranking = sorted(commit_count, key=lambda p: added[p] + deleted[p], reverse=True)[:top_n]
    top_changed = sum(added[p] + deleted[p] for p in ranking)

    return {
        "evidence_type": "observed",
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


# ---------------------------------------------------------------------------
# ======= 02 · FRAMEWORKS E BIBLIOTECAS (frameworks_dependencies) =======
# Lê manifestos como texto/JSON/TOML (nunca instala nem executa nada).
# ---------------------------------------------------------------------------

DEPENDENCY_MANIFESTS = {
    "package.json": "Node.js / JavaScript / TypeScript",
    "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (pyproject)",
    "Pipfile": "Python (Pipenv)",
    "setup.py": "Python (setuptools)",
    "setup.cfg": "Python (setuptools)",
    "poetry.lock": "Python (Poetry lockfile)",
    "uv.lock": "Python (uv lockfile)",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle Kotlin DSL",
    "Cargo.toml": "Rust (Cargo)",
    "Cargo.lock": "Rust (Cargo lockfile)",
    "go.mod": "Go modules",
    "Gemfile": "Ruby (Bundler)",
    "composer.json": "PHP (Composer)",
    "Package.swift": "Swift Package Manager",
    "mix.exs": "Elixir (Mix)",
    "pubspec.yaml": "Dart / Flutter",
    "package-lock.json": "Node.js (npm lockfile)",
    "yarn.lock": "Node.js (Yarn lockfile)",
    "pnpm-lock.yaml": "Node.js (pnpm lockfile)",
}

_REQUIREMENTS_NAME_RE = re.compile(r"^requirements[-_.\w]*\.txt$", re.IGNORECASE)

KNOWN_FRAMEWORKS = {
    # Python
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI", "sqlalchemy": "SQLAlchemy",
    "celery": "Celery", "pydantic": "Pydantic", "pytest": "pytest", "pandas": "pandas",
    "numpy": "NumPy", "torch": "PyTorch", "tensorflow": "TensorFlow",
    "scikit-learn": "scikit-learn", "langchain": "LangChain", "openai": "OpenAI SDK",
    "anthropic": "Anthropic SDK",
    # JavaScript / TypeScript
    "react": "React", "next": "Next.js", "vue": "Vue", "nuxt": "Nuxt", "svelte": "Svelte",
    "@angular/core": "Angular", "express": "Express", "@nestjs/core": "NestJS",
    "jest": "Jest", "vitest": "Vitest", "cypress": "Cypress", "playwright": "Playwright",
    "@playwright/test": "Playwright", "typescript": "TypeScript", "vite": "Vite",
    "webpack": "webpack", "eslint": "ESLint",
    # JVM
    "spring-boot-starter": "Spring Boot", "spring-boot-starter-web": "Spring Boot",
    "junit": "JUnit", "junit-jupiter": "JUnit 5", "hibernate-core": "Hibernate",
    # Go / Rust / Ruby / PHP
    "github.com/gin-gonic/gin": "Gin", "github.com/labstack/echo": "Echo",
    "tokio": "Tokio", "actix-web": "Actix Web", "axum": "Axum", "serde": "Serde",
    "rails": "Rails", "sinatra": "Sinatra", "laravel/framework": "Laravel",
}


def _clean_version(value: Any) -> str | None:
    """Normaliza especificações de versão; omite URLs/refs diretas (podem conter credenciais)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "://" in text or text.startswith(("git+", "git@")):
        return "(direct reference)"
    return text[:100]


def _dep(name: str, version: Any, scope: str) -> dict[str, Any]:
    return {"name": name, "version_spec": _clean_version(version), "scope": scope}


_PEP508_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*([^;#]*)")


def _parse_requirement(line: str, scope: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line or line.startswith(("#", "-")):   # comentários e opções (-r, -e, --index-url…)
        return None
    match = _PEP508_RE.match(line)
    if not match:
        return None
    rest = match.group(2).strip()
    if rest.startswith("@"):
        rest = "(direct reference)"
    return _dep(match.group(1), rest or None, scope)


def _toml_loads(text: str) -> dict[str, Any] | None:
    if tomllib is None:
        return None
    try:
        return tomllib.loads(text)
    except ValueError:
        return None


def _deps_package_json(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    deps: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return deps
    for section, scope in (
        ("dependencies", "runtime"), ("devDependencies", "dev"),
        ("peerDependencies", "peer"), ("optionalDependencies", "optional"),
    ):
        table = data.get(section)
        if isinstance(table, dict):
            deps += [_dep(n, v if isinstance(v, str) else None, scope) for n, v in table.items()]
    return deps


def _deps_composer_json(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    deps: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for section, scope in (("require", "runtime"), ("require-dev", "dev")):
            table = data.get(section)
            if isinstance(table, dict):
                deps += [_dep(n, v if isinstance(v, str) else None, scope)
                         for n, v in table.items() if n != "php" and not n.startswith("ext-")]
    return deps


def _deps_requirements(text: str) -> list[dict[str, Any]]:
    return [d for d in (_parse_requirement(l, "runtime") for l in text.splitlines()) if d]


def _toml_table_deps(table: Any, scope: str, skip: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Tabelas `nome = "versão"` ou `nome = {version=..., git=...}` (Poetry, Cargo, Pipfile)."""
    deps: list[dict[str, Any]] = []
    if not isinstance(table, dict):
        return deps
    for name, spec in table.items():
        if name in skip:
            continue
        if isinstance(spec, str):
            version: Any = spec
        elif isinstance(spec, dict):
            version = spec.get("version")
            if version is None and any(k in spec for k in ("git", "path", "url")):
                version = "(direct reference)"
        else:
            version = None
        deps.append(_dep(name, version, scope))
    return deps


def _deps_pyproject(text: str) -> list[dict[str, Any]]:
    data = _toml_loads(text)
    if not data:
        return []
    deps: list[dict[str, Any]] = []
    project = data.get("project") or {}
    for spec in project.get("dependencies") or []:
        if isinstance(spec, str) and (d := _parse_requirement(spec, "runtime")):
            deps.append(d)
    for group, specs in (project.get("optional-dependencies") or {}).items():
        deps += [d for s in specs if isinstance(s, str) and (d := _parse_requirement(s, f"optional:{group}"))]
    for group, specs in (data.get("dependency-groups") or {}).items():
        deps += [d for s in specs if isinstance(s, str) and (d := _parse_requirement(s, f"group:{group}"))]

    poetry = (data.get("tool") or {}).get("poetry") or {}
    deps += _toml_table_deps(poetry.get("dependencies"), "runtime", skip=("python",))
    deps += _toml_table_deps(poetry.get("dev-dependencies"), "dev", skip=("python",))
    for group, content in (poetry.get("group") or {}).items():
        if isinstance(content, dict):
            deps += _toml_table_deps(content.get("dependencies"), f"group:{group}", skip=("python",))
    return deps


def _deps_pipfile(text: str) -> list[dict[str, Any]]:
    data = _toml_loads(text) or {}
    return (_toml_table_deps(data.get("packages"), "runtime")
            + _toml_table_deps(data.get("dev-packages"), "dev"))


def _deps_cargo(text: str) -> list[dict[str, Any]]:
    data = _toml_loads(text) or {}
    deps: list[dict[str, Any]] = []
    for section, scope in (("dependencies", "runtime"), ("dev-dependencies", "dev"),
                           ("build-dependencies", "build")):
        deps += _toml_table_deps(data.get(section), scope)
    workspace = data.get("workspace") or {}
    deps += _toml_table_deps(workspace.get("dependencies"), "workspace")
    return deps


def _pom_tag(block: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}>\s*([^<]+?)\s*</{tag}>", block)
    return match.group(1) if match else None


def _deps_pom(text: str) -> list[dict[str, Any]]:
    # Regex em vez de um parser XML: evita expansão de entidades em ficheiros não confiáveis.
    deps: list[dict[str, Any]] = []
    for block in re.findall(r"<dependency>(.*?)</dependency>", text, flags=re.DOTALL):
        group, artifact = _pom_tag(block, "groupId"), _pom_tag(block, "artifactId")
        if artifact:
            deps.append(_dep(f"{group}:{artifact}" if group else artifact,
                             _pom_tag(block, "version"), _pom_tag(block, "scope") or "compile"))
    return deps


_GRADLE_CONFIGS = {
    "implementation", "api", "compileOnly", "runtimeOnly", "testImplementation",
    "testCompileOnly", "testRuntimeOnly", "annotationProcessor", "kapt", "ksp", "classpath",
    "compile", "runtime", "testCompile", "developmentOnly", "androidTestImplementation",
    "debugImplementation", "releaseImplementation",
}
_GRADLE_DEP_RE = re.compile(
    r"""^\s*(?P<conf>[A-Za-z][A-Za-z0-9_]*)\s*\(?\s*["'](?P<group>[^"':\s]+):(?P<name>[^"':\s]+)"""
    r"""(?::(?P<version>[^"'\s]+))?["']""",
    re.MULTILINE,
)


def _deps_gradle(text: str) -> list[dict[str, Any]]:
    return [
        _dep(f"{m.group('group')}:{m.group('name')}", m.group("version"), m.group("conf"))
        for m in _GRADLE_DEP_RE.finditer(text)
        if m.group("conf") in _GRADLE_CONFIGS
    ]


def _deps_go_mod(text: str) -> list[dict[str, Any]]:
    deps: list[dict[str, Any]] = []
    in_block = False
    for raw in text.splitlines():
        indirect = "// indirect" in raw
        line = raw.split("//")[0].strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        if line.startswith("require ") and "(" not in line:
            line = line[len("require "):].strip()
        elif not in_block:
            continue
        parts = line.split()
        if len(parts) >= 2:
            deps.append(_dep(parts[0], parts[1], "indirect" if indirect else "direct"))
    return deps


_GEM_RE = re.compile(r"""^\s*gem\s+["']([^"']+)["'](?:\s*,\s*["']([^"']+)["'])?""", re.MULTILINE)


def _deps_gemfile(text: str) -> list[dict[str, Any]]:
    return [_dep(m.group(1), m.group(2), "runtime") for m in _GEM_RE.finditer(text)]


def _manifest_ecosystem(path: Path) -> str | None:
    if path.name in DEPENDENCY_MANIFESTS:
        return DEPENDENCY_MANIFESTS[path.name]
    if _REQUIREMENTS_NAME_RE.match(path.name):
        return "Python (pip)"
    if path.suffix.lower() == ".txt" and path.parent.name.lower() == "requirements":
        return "Python (pip)"
    return None


def _manifest_parser(path: Path):
    name = path.name
    if name == "package.json":
        return _deps_package_json
    if name == "composer.json":
        return _deps_composer_json
    if name == "pyproject.toml":
        return _deps_pyproject
    if name == "Pipfile":
        return _deps_pipfile
    if name == "Cargo.toml":
        return _deps_cargo
    if name == "pom.xml":
        return _deps_pom
    if name in {"build.gradle", "build.gradle.kts"}:
        return _deps_gradle
    if name == "go.mod":
        return _deps_go_mod
    if name == "Gemfile":
        return _deps_gemfile
    if _manifest_ecosystem(path) == "Python (pip)":
        return _deps_requirements
    return None   # lockfiles e manifestos sem parser: apenas listados


def _detect_frameworks(names: set[str]) -> list[str]:
    found: set[str] = set()
    for name in names:
        key = name.lower()
        for candidate in (key, key.split(":")[-1]):
            if candidate in KNOWN_FRAMEWORKS:
                found.add(KNOWN_FRAMEWORKS[candidate])
        if key.startswith("org.springframework.boot:"):
            found.add("Spring Boot")
    return sorted(found)


def collect_frameworks_dependencies(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    all_names: set[str] = set()
    ecosystems: Counter[str] = Counter()

    for path in _resolve_files(repo_path, files):
        ecosystem = _manifest_ecosystem(path)
        if not ecosystem:
            continue
        ecosystems[ecosystem] += 1
        entry: dict[str, Any] = {
            "file": _relative_path(repo_path, path),
            "ecosystem": ecosystem,
            "parsed": False,
            "dependencies": [],
        }
        parser = _manifest_parser(path)
        text = _read_text(path) if parser else None
        if parser and text is not None:
            deps = parser(text)
            entry["parsed"] = True
            entry["dependencies_count"] = len(deps)
            entry["dependencies"] = deps[:MAX_DEPS_PER_MANIFEST]
            entry["truncated"] = len(deps) > MAX_DEPS_PER_MANIFEST
            all_names.update(d["name"] for d in deps)
        manifests.append(entry)

    return {
        "evidence_type": "observed",
        "manifest_count": len(manifests),
        "ecosystems": dict(ecosystems.most_common()),
        "unique_dependencies_count": len(all_names),
        "detected_frameworks": _detect_frameworks(all_names),
        "manifests": manifests,
        "limitations": (
            "Dependências declaradas, não necessariamente utilizadas. Versões podem ser "
            "intervalos ou variáveis (${...}). pom.xml/Gradle/Gemfile lidos por regex. "
            "'detected_frameworks' é heurístico (nomes conhecidos). pyproject/Cargo/Pipfile "
            "exigem Python 3.11+ (ou o pacote 'tomli')."
        ),
    }


# ---------------------------------------------------------------------------
# ======= 03 · FICHEIROS POR LINGUAGEM (files_by_language) =======
# É uma aproximação por extensão, não uma análise semântica da linguagem.
# ---------------------------------------------------------------------------

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript/JSX",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/TSX",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".pl": "Perl",
    ".r": "R",
    ".jl": "Julia",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".json": "JSON",
    ".md": "Markdown",
}

# Extensões de dados/markup que não contam como "código" em rácios.
NON_CODE_EXTENSIONS = {".md", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css", ".scss"}


def collect_files_by_language(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for path in _resolve_files(repo_path, files):
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            counts[language] += 1

    total = sum(counts.values())
    return {
        "evidence_type": "heuristic",
        "files_by_language": dict(counts.most_common()),
        "share_by_language": {lang: round(n / total, 4) for lang, n in counts.most_common()} if total else {},
        "recognized_source_files": total,
        "limitations": (
            "Classificação por extensão; inclui linguagens de dados/markup (JSON, YAML, "
            "Markdown…) e não identifica extensões desconhecidas."
        ),
    }


# ---------------------------------------------------------------------------
# ======= 04 · CONFIGURAÇÃO DE CI/CD (cicd_configuration) =======
# ---------------------------------------------------------------------------

BUILD_TASK_FILE_NAMES = {
    "Makefile", "makefile", "justfile", "tox.ini", "noxfile.py", "Taskfile.yml", "Taskfile.yaml",
}
QUALITY_CONFIG_NAMES = {
    ".pre-commit-config.yaml", ".flake8", ".pylintrc", "mypy.ini", "ruff.toml", ".ruff.toml",
    "sonar-project.properties", ".rubocop.yml", ".editorconfig", "tslint.json", "biome.json",
    "codecov.yml", ".codecov.yml", ".coveragerc", "renovate.json",
    "dependabot.yml", "dependabot.yaml",
}
QUALITY_CONFIG_PREFIXES = (".eslintrc", "eslint.config.", ".prettierrc", "prettier.config.", ".golangci")


def _classify_ci(relative: str) -> str | None:
    """Devolve o sistema de CI/CD a que o ficheiro pertence (ou None)."""
    path = PurePosixPath(relative)
    name = path.name
    lowered = "/" + relative.lower()
    suffix = path.suffix.lower()

    if "/.github/workflows/" in lowered and suffix in {".yml", ".yaml"}:
        return "GitHub Actions"
    if name == ".gitlab-ci.yml" or "/.gitlab/ci/" in lowered:
        return "GitLab CI"
    if name.startswith("Jenkinsfile"):
        return "Jenkins"
    if name in {"azure-pipelines.yml", "azure-pipelines.yaml"} or "/.azure-pipelines/" in lowered:
        return "Azure Pipelines"
    if name == "bitbucket-pipelines.yml":
        return "Bitbucket Pipelines"
    if "/.circleci/" in lowered and name in {"config.yml", "config.yaml"}:
        return "CircleCI"
    if name == ".travis.yml":
        return "Travis CI"
    if name == ".drone.yml":
        return "Drone CI"
    if name in {"appveyor.yml", ".appveyor.yml"}:
        return "AppVeyor"
    if name in {"cloudbuild.yaml", "cloudbuild.yml"}:
        return "Google Cloud Build"
    if "/.buildkite/" in lowered:
        return "Buildkite"
    if name == "bitrise.yml":
        return "Bitrise"
    if name == ".woodpecker.yml" or "/.woodpecker/" in lowered:
        return "Woodpecker CI"
    return None


def collect_cicd_configuration(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    by_system: dict[str, list[str]] = defaultdict(list)
    quality: list[str] = []
    build_tasks: list[str] = []

    for path in _resolve_files(repo_path, files):
        relative = _relative_path(repo_path, path)
        system = _classify_ci(relative)
        if system:
            by_system[system].append(relative)
        if path.name in BUILD_TASK_FILE_NAMES:
            build_tasks.append(relative)
        if path.name in QUALITY_CONFIG_NAMES or path.name.startswith(QUALITY_CONFIG_PREFIXES):
            quality.append(relative)

    return {
        "evidence_type": "heuristic",
        "ci_systems_detected": sorted(by_system),
        "ci_config_files_count": sum(len(v) for v in by_system.values()),
        "ci_config_files_by_system": {k: sorted(v) for k, v in sorted(by_system.items())},
        "build_task_files": sorted(build_tasks),
        "quality_config_files": sorted(quality),
        "limitations": (
            "Deteção por nome/caminho. A presença de configuração não demonstra que os "
            "pipelines são executados nem que passam. Se settings.excluded_dirs incluir "
            "'.github' ou similares, essas configurações não serão vistas."
        ),
    }


# ---------------------------------------------------------------------------
# ======= 05 · INVENTÁRIO DE TESTES (test_inventory) =======
# ---------------------------------------------------------------------------

TEST_PATH_MARKERS = {
    "tests", "test", "__tests__", "spec", "specs", "testing", "e2e", "cypress", "playwright",
}
TEST_FILENAME_RE = re.compile(
    r"^(test_.*\.py|.*_test\.(py|go|rb|exs|js|ts|c|cc|cpp|dart)|.*_spec\.rb"
    r"|.*\.(test|spec|cy|e2e)\.[^.]+)$",
    re.IGNORECASE,
)
# Sufixos de classe (sensíveis a maiúsculas para evitar falsos positivos tipo "Edit.java").
TEST_CLASS_SUFFIX_RE = re.compile(r"^.*(Test|Tests|IT|ITCase|Spec)\.(java|kt|scala|cs|swift|php)$")

E2E_DIR_MARKERS = {"e2e", "end-to-end", "end_to_end", "cypress", "playwright", "selenium",
                   "puppeteer", "acceptance"}
INTEGRATION_DIR_MARKERS = {"integration", "integrations", "integration_tests", "integration-tests",
                           "itests", "it"}
UNIT_DIR_MARKERS = {"unit", "units", "unit_tests", "unit-tests"}

TEST_CONFIG_PATTERNS = [
    (re.compile(r"^pytest\.ini$"), "pytest"),
    (re.compile(r"^conftest\.py$"), "pytest"),
    (re.compile(r"^tox\.ini$"), "tox"),
    (re.compile(r"^jest\.config\."), "Jest"),
    (re.compile(r"^vitest\.config\."), "Vitest"),
    (re.compile(r"^karma\.conf\."), "Karma"),
    (re.compile(r"^cypress\.config\."), "Cypress"),
    (re.compile(r"^playwright\.config\."), "Playwright"),
    (re.compile(r"^wdio\.conf\."), "WebdriverIO"),
    (re.compile(r"^\.mocharc"), "Mocha"),
    (re.compile(r"^phpunit\.xml(\.dist)?$"), "PHPUnit"),
    (re.compile(r"^\.rspec$"), "RSpec"),
]


def _is_test_file(relative: str) -> bool:
    path = PurePosixPath(relative)
    if any(part.lower() in TEST_PATH_MARKERS for part in path.parts[:-1]):
        return True
    return bool(TEST_FILENAME_RE.match(path.name) or TEST_CLASS_SUFFIX_RE.match(path.name))


def _classify_test_type(relative: str) -> str:
    path = PurePosixPath(relative)
    dirs = {part.lower() for part in path.parts[:-1]}
    name = path.name
    lowered = name.lower()

    if dirs & E2E_DIR_MARKERS or re.search(r"e2e|end[-_]to[-_]end|\.cy\.", lowered):
        return "e2e"
    if (dirs & INTEGRATION_DIR_MARKERS or "integration" in lowered
            or re.search(r"IT(Case)?\.(java|kt|scala)$", name)):
        return "integration"
    if dirs & UNIT_DIR_MARKERS or "unit" in lowered:
        return "unit"
    return "unclassified"   # não se assume "unit" sem evidência


def collect_test_inventory(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    tests: dict[str, str] = {}
    configs: list[dict[str, str]] = []
    code_files_non_test = 0

    for path in _resolve_files(repo_path, files):
        relative = _relative_path(repo_path, path)
        for pattern, framework in TEST_CONFIG_PATTERNS:
            if pattern.match(path.name):
                configs.append({"file": relative, "framework": framework})
                break

        if _is_test_file(relative):
            if path.name != "conftest.py":
                tests[relative] = _classify_test_type(relative)
        else:
            suffix = path.suffix.lower()
            if suffix in LANGUAGE_BY_EXTENSION and suffix not in NON_CODE_EXTENSIONS:
                code_files_non_test += 1

    by_type = Counter(tests.values())
    ordered = sorted(tests.items())
    return {
        "evidence_type": "heuristic",
        "test_files_count": len(tests),
        "test_files_by_type": dict(by_type),
        "test_files": [{"file": f, "type": t} for f, t in ordered[:MAX_LISTED_ITEMS]],
        "test_files_truncated": len(ordered) > MAX_LISTED_ITEMS,
        "test_framework_configs": sorted(configs, key=lambda c: c["file"]),
        "test_to_code_file_ratio": (
            round(len(tests) / code_files_non_test, 4) if code_files_non_test else None
        ),
        "limitations": (
            "Inventário por nomes/diretórios; o tipo (unit/integration/e2e) é aproximado e "
            "'unclassified' não é assumido como unitário. Não mede cobertura nem qualidade, "
            "nem garante que os testes executem."
        ),
    }


# ---------------------------------------------------------------------------
# ======= 06 · TAMANHO DAS ALTERAÇÕES POR COMMIT (commit_churn) =======
# ---------------------------------------------------------------------------

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
        "evidence_type": "observed",
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


# ---------------------------------------------------------------------------
# ======= 07 · CORREÇÕES E REVERSÕES (fixes_and_reverts) =======
# Classificação por mensagem de commit: imperfeita por natureza.
# ---------------------------------------------------------------------------

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
                    "sha": commit.sha, "date": commit.date,
                    "message": _truncate(commit.subject),
                    "matched_term": fix_match.group(0).lower(),
                })
        if REVERT_SUBJECT_RE.search(commit.subject) or commit.reverts_sha:
            revert_count += 1
            reverts_by_month[commit.month] += 1
            if len(revert_evidence) < MAX_LISTED_ITEMS:
                revert_evidence.append({
                    "sha": commit.sha, "date": commit.date,
                    "message": _truncate(commit.subject),
                    "reverted_sha": commit.reverts_sha,
                })

    total = len(commits)
    return {
        "evidence_type": "heuristic",
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


# ---------------------------------------------------------------------------
# ======= 08 · ATIVIDADE POR DIRETÓRIO/COMPONENTE (component_activity) =======
# ---------------------------------------------------------------------------

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
        "evidence_type": "mixed",
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


# ---------------------------------------------------------------------------
# ======= 09 · INVENTÁRIO DE DOCUMENTAÇÃO (documentation_inventory) =======
# ---------------------------------------------------------------------------

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
    """Categorias de documentação de um caminho (lista vazia se não for documentação)."""
    path = PurePosixPath(relative)
    suffix = path.suffix.lower()
    stem = path.stem.lower()
    if suffix not in DOC_EXTENSIONS and suffix != "":
        return []

    dirs = [part.lower() for part in path.parts[:-1]]
    categories: list[str] = []
    if stem == "readme":
        categories.append("readme")
    if stem in _CHANGELOG_STEMS:
        categories.append("changelog")
    if any(d in _ADR_DIR_NAMES for d in dirs) or _ADR_NAME_RE.match(stem):
        categories.append("adr")
    if _RUNBOOK_RE.search(relative):
        categories.append("runbook")
    if _ONBOARDING_RE.search(path.name):
        categories.append("install_onboarding")
    if any(d in _DOC_DIR_NAMES for d in dirs):
        categories.append("docs_dir")

    if suffix == "" and not ({"readme", "changelog"} & set(categories)):
        return []     # ficheiros sem extensão só contam se forem README/CHANGELOG
    if not categories:
        return ["other"] if suffix in DOC_MARKUP_EXTENSIONS else []   # .txt solto ≠ documentação
    return categories


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

    return {
        "evidence_type": "heuristic",
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
                for f, n in changes.most_common(TOP_N_DEFAULT)
            ],
        },
        "limitations": (
            "Categorias por nome/diretório (README, docs/, ADRs, runbooks, instalação/onboarding, "
            "changelogs). A ausência de documentação detetada não prova que não exista noutro sistema."
        ),
    }


# ---------------------------------------------------------------------------
# ======= 10 · DÍVIDA TÉCNICA (technical_debt_markers) =======
# Conta TODO, FIXME, HACK, XXX, WORKAROUND. Nunca devolve o texto das linhas.
# A deteção é sensível a maiúsculas: "todo" é uma palavra comum em português.
# ---------------------------------------------------------------------------

TECH_DEBT_MARKERS = re.compile(r"\b(TODO|FIXME|HACK|XXX|WORKAROUND)\b")
MAX_LINE_LENGTH_SCANNED = 2000    # ignora linhas gigantes (minificados/dados)


def collect_technical_debt_markers(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    per_file: Counter[str] = Counter()
    occurrences: list[dict[str, Any]] = []

    for path in _resolve_files(repo_path, files):
        if _PathFilter.is_generated(path.name):
            continue
        text = _read_text(path)
        if text is None:
            continue

        relative = _relative_path(repo_path, path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if len(line) > MAX_LINE_LENGTH_SCANNED:
                continue
            for match in TECH_DEBT_MARKERS.finditer(line):
                marker = match.group(1)
                counts[marker] += 1
                per_file[relative] += 1
                if len(occurrences) < MAX_LISTED_ITEMS:
                    occurrences.append({"marker": marker, "file": relative, "line": line_number})

    return {
        "evidence_type": "observed",
        "marker_counts": dict(counts),
        "total_markers": sum(counts.values()),
        "files_with_markers": len(per_file),
        "top_files": [{"file": f, "markers": n} for f, n in per_file.most_common(TOP_N_DEFAULT)],
        "occurrences": occurrences,
        "occurrences_truncated": sum(counts.values()) > MAX_LISTED_ITEMS,
        "limitations": (
            "Apenas ficheiro e linha (o conteúdo das linhas não é devolvido). Marcadores em "
            "maiúsculas; não são uma medida completa da dívida técnica."
        ),
    }


# ---------------------------------------------------------------------------
# ======= INFRAESTRUTURA (contexto adicional) =======
# Presença de Docker, Kubernetes e infraestrutura como código.
# ---------------------------------------------------------------------------

INFRA_FILE_NAMES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "Chart.yaml",
    "terraform.tf",
    "main.tf",
    "variables.tf",
    "cloudformation.yaml",
    "cloudformation.yml",
}


def collect_infrastructure(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    found: list[str] = []
    for path in _resolve_files(repo_path, files):
        relative = _relative_path(repo_path, path)
        parts_lower = {part.lower() for part in path.parts}
        if (
            path.name in INFRA_FILE_NAMES
            or path.suffix.lower() == ".tf"
            or "k8s" in parts_lower
            or "kubernetes" in parts_lower
        ):
            found.append(relative)

    return {
        "evidence_type": "heuristic",
        "infrastructure_files_count": len(set(found)),
        "infrastructure_files": sorted(set(found))[:MAX_LISTED_ITEMS],
    }


# ---------------------------------------------------------------------------
# ======= EXECUÇÃO DE TODOS OS COLETORES =======
# Ponto de entrada para a API: chamar collect_all_metrics(clone.path).
# ---------------------------------------------------------------------------

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
        "infrastructure": _safe_collect("infrastructure", collect_infrastructure, repo_path, files),
    }
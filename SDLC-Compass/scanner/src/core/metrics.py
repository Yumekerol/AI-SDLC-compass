"""
metrics.py
==========
Coletores de métricas do repositório Git para identificar oportunidades de
integração de AI ao longo do SDLC.

Este ficheiro deve receber o caminho do clone (CloneResult.path) e devolver
um dicionário serializável em JSON. Não clona o repositório nem altera ficheiros.

Princípios:
- Respeitar os filtros de settings.excluded_dirs, settings.excluded_extensions
  e settings.max_file_size_bytes sempre que se percorrem ficheiros.
- Não executar código do repositório analisado.
- Não ler nem devolver valores de segredos, tokens ou variáveis de ambiente.
- Distinguir métricas diretamente observadas de heurísticas aproximadas.
- Manter cada coletor pequeno e independente para facilitar testes.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers comuns
# ---------------------------------------------------------------------------

def _run_git(repo_path: Path, *args: str) -> str:
    """Executa um comando Git de leitura e devolve stdout.

    O repositório deve ser um clone já validado pelo módulo git_extract.
    Não usar comandos que executem hooks, scripts ou conteúdo do repositório.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        logger.warning("Comando Git falhou (%s): %s", args[0], result.stderr[:200])
        return ""
    return result.stdout.strip()


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


def _read_text(path: Path) -> str | None:
    """Lê ficheiros de texto pequenos; ignora binários e erros de encoding."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _relative_path(repo_path: Path, path: Path) -> str:
    return path.relative_to(repo_path).as_posix()


# ---------------------------------------------------------------------------
# ======= METADADOS GERAIS DO REPOSITÓRIO =======
# Métricas para contextualizar o tamanho e o estado do repositório.
# ---------------------------------------------------------------------------

def collect_repository_metadata(repo_path: Path) -> dict[str, Any]:
    """Recolhe metadados gerais; parte deles já existe em CloneResult."""
    commits_total = _run_git(repo_path, "rev-list", "--count", "HEAD")
    branch = _run_git(repo_path, "branch", "--show-current")
    head_sha = _run_git(repo_path, "rev-parse", "HEAD")

    return {
        "commits_total": int(commits_total) if commits_total.isdigit() else None,
        "branch": branch or None,
        "head_sha": head_sha or None,
    }


# ---------------------------------------------------------------------------
# ======= LINGUAGENS =======
# Métrica: linguagens presentes e número de ficheiros por extensão.
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


def collect_languages(repo_path: Path) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for path in _iter_source_files(repo_path):
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            counts[language] += 1

    total = sum(counts.values())
    return {
        "files_by_language": dict(counts.most_common()),
        "recognized_source_files": total,
    }


# ---------------------------------------------------------------------------
# ======= FRAMEWORKS E DEPENDÊNCIAS =======
# Métrica: ficheiros de manifesto que ajudam a identificar o ecossistema.
# Esta versão identifica ficheiros existentes; extrair dependências/versões
# pode ser implementado num coletor posterior, sem instalar pacotes.
# ---------------------------------------------------------------------------

DEPENDENCY_MANIFESTS = {
    "package.json": "Node.js / JavaScript / TypeScript",
    "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (pyproject)",
    "Pipfile": "Python (Pipenv)",
    "poetry.lock": "Python (Poetry lockfile)",
    "uv.lock": "Python (uv lockfile)",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle Kotlin DSL",
    "Cargo.toml": "Rust (Cargo)",
    "go.mod": "Go modules",
    "Gemfile": "Ruby (Bundler)",
    "composer.json": "PHP (Composer)",
    "Package.swift": "Swift Package Manager",
    "mix.exs": "Elixir (Mix)",
    "pubspec.yaml": "Dart / Flutter",
}


def collect_dependency_manifests(repo_path: Path) -> dict[str, Any]:
    found: list[dict[str, str]] = []
    for path in _iter_source_files(repo_path):
        if path.name in DEPENDENCY_MANIFESTS:
            found.append({
                "file": _relative_path(repo_path, path),
                "ecosystem": DEPENDENCY_MANIFESTS[path.name],
            })

    return {
        "manifest_count": len(found),
        "manifests": found,
        "note": (
            "Identificação por nome de ficheiro; não equivale a uma lista "
            "completa de frameworks ou versões instaladas."
        ),
    }


# ---------------------------------------------------------------------------
# ======= COMMITS =======
# Métricas: total de commits e distribuição temporal simples.
# ---------------------------------------------------------------------------

def collect_commit_metrics(repo_path: Path) -> dict[str, Any]:
    count_raw = _run_git(repo_path, "rev-list", "--count", "HEAD")
    dates_raw = _run_git(repo_path, "log", "--format=%cs", "--all")

    dates = Counter(line for line in dates_raw.splitlines() if line)
    return {
        "commits_total": int(count_raw) if count_raw.isdigit() else None,
        "commits_by_date": dict(sorted(dates.items())),
    }


# ---------------------------------------------------------------------------
# ======= TAMANHO E CHURN DE CÓDIGO =======
# Métricas: linhas adicionadas/removidas e ficheiros mais alterados.
# Nota: --numstat não inclui necessariamente ficheiros binários como texto.
# ---------------------------------------------------------------------------

def collect_code_churn(repo_path: Path, top_n: int = 20) -> dict[str, Any]:
    raw = _run_git(repo_path, "log", "--numstat", "--format=")
    churn: Counter[str] = Counter()
    additions_total = 0
    deletions_total = 0

    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue

        added, deleted, filename = parts
        # Git usa '-' para ficheiros binários; não contar esses valores.
        if added.isdigit():
            additions_total += int(added)
            churn[filename] += int(added)
        if deleted.isdigit():
            deletions_total += int(deleted)
            churn[filename] += int(deleted)

    return {
        "lines_added_total": additions_total,
        "lines_deleted_total": deletions_total,
        "top_churn_files": [
            {"file": name, "lines_changed": value}
            for name, value in churn.most_common(top_n)
        ],
    }


# ---------------------------------------------------------------------------
# ======= TESTES =======
# Métricas: presença de testes e frameworks de teste comuns.
# A presença de ficheiros não representa cobertura percentual nem qualidade.
# ---------------------------------------------------------------------------

TEST_PATH_MARKERS = {
    "tests", "test", "__tests__", "spec", "specs"
}
TEST_FILENAME_RE = re.compile(
    r"(^test_.*\.py$|.*_test\.py$|.*\.test\.[^.]+$|.*\.spec\.[^.]+$)",
    re.IGNORECASE,
)


def collect_test_inventory(repo_path: Path) -> dict[str, Any]:
    test_files: list[str] = []
    for path in _iter_source_files(repo_path):
        relative = path.relative_to(repo_path)
        if any(part.lower() in TEST_PATH_MARKERS for part in relative.parts[:-1]):
            test_files.append(relative.as_posix())
        elif TEST_FILENAME_RE.match(path.name):
            test_files.append(relative.as_posix())

    return {
        "test_files_count": len(set(test_files)),
        "sample_test_files": sorted(set(test_files))[:100],
        "note": "Inventário heurístico; não mede cobertura nem garante que os testes executem.",
    }


# ---------------------------------------------------------------------------
# ======= CI/CD E QUALIDADE =======
# Métricas: presença de configuração de CI, lint, type-check e testes.
# ---------------------------------------------------------------------------

CI_CONFIG_NAMES = {
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "tox.ini",
    "Makefile",
    "justfile",
}
QUALITY_CONFIG_NAMES = {
    ".pre-commit-config.yaml",
    ".eslintrc",
    ".eslintrc.json",
    "eslint.config.js",
    "pyproject.toml",
    "mypy.ini",
    ".flake8",
    ".ruff.toml",
    "sonar-project.properties",
}


def collect_ci_quality_configs(repo_path: Path) -> dict[str, Any]:
    found_ci: list[str] = []
    found_quality: list[str] = []

    for path in _iter_source_files(repo_path):
        relative = _relative_path(repo_path, path)
        if path.name in CI_CONFIG_NAMES or ".github/workflows" in relative:
            found_ci.append(relative)
        if path.name in QUALITY_CONFIG_NAMES:
            found_quality.append(relative)

    return {
        "ci_config_files": sorted(set(found_ci)),
        "quality_config_files": sorted(set(found_quality)),
    }


# ---------------------------------------------------------------------------
# ======= DOCUMENTAÇÃO =======
# Métricas: inventário e distribuição da documentação Markdown.
# ---------------------------------------------------------------------------

def collect_documentation(repo_path: Path) -> dict[str, Any]:
    docs: list[str] = []
    for path in _iter_source_files(repo_path):
        relative = path.relative_to(repo_path)
        if path.suffix.lower() in {".md", ".rst", ".adoc"}:
            docs.append(relative.as_posix())
        elif path.name.lower() in {"readme", "changelog", "changes"}:
            docs.append(relative.as_posix())

    return {
        "documentation_files_count": len(set(docs)),
        "documentation_files": sorted(set(docs))[:200],
    }


# ---------------------------------------------------------------------------
# ======= DÍVIDA TÉCNICA =======
# Métrica: ocorrências de TODO, FIXME, HACK e XXX em ficheiros de texto.
# Não devolve linhas completas para reduzir risco de expor informação sensível.
# ---------------------------------------------------------------------------

TECH_DEBT_MARKERS = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)


def collect_technical_debt(repo_path: Path) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for path in _iter_source_files(repo_path):
        text = _read_text(path)
        if text is None:
            continue

        relative = _relative_path(repo_path, path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in TECH_DEBT_MARKERS.finditer(line):
                marker = match.group(1).upper()
                counts[marker] += 1
                if len(examples) < 100:
                    examples.append({
                        "marker": marker,
                        "file": relative,
                        "line": line_number,
                    })

    return {
        "marker_counts": dict(counts),
        "total_markers": sum(counts.values()),
        "examples": examples,
    }


# ---------------------------------------------------------------------------
# ======= CONFIGURAÇÃO DE INFRAESTRUTURA =======
# Métrica: presença de Docker, Kubernetes e infraestrutura como código.
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


def collect_infrastructure(repo_path: Path) -> dict[str, Any]:
    files: list[str] = []
    for path in _iter_source_files(repo_path):
        relative = _relative_path(repo_path, path)
        if (
            path.name in INFRA_FILE_NAMES
            or path.suffix.lower() in {".tf"}
            or "k8s" in {part.lower() for part in path.parts}
            or "kubernetes" in {part.lower() for part in path.parts}
        ):
            files.append(relative)

    return {
        "infrastructure_files_count": len(set(files)),
        "infrastructure_files": sorted(set(files))[:200],
    }


# ---------------------------------------------------------------------------
# ======= EXECUÇÃO DE TODOS OS COLETORES =======
# Ponto de entrada para a API: chamar collect_all_metrics(clone.path).
# ---------------------------------------------------------------------------

def collect_all_metrics(repo_path: Path) -> dict[str, Any]:
    """Executa os coletores e devolve um resultado JSON-serializável."""
    repo_path = Path(repo_path).resolve()

    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError("repo_path tem de apontar para uma pasta existente.")

    return {
        "repository": collect_repository_metadata(repo_path),
        "languages": collect_languages(repo_path),
        "dependencies": collect_dependency_manifests(repo_path),
        "commits": collect_commit_metrics(repo_path),
        "code_churn": collect_code_churn(repo_path),
        "tests": collect_test_inventory(repo_path),
        "ci_quality": collect_ci_quality_configs(repo_path),
        "documentation": collect_documentation(repo_path),
        "technical_debt": collect_technical_debt(repo_path),
        "infrastructure": collect_infrastructure(repo_path),
    }

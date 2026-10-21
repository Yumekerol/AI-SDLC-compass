"""
mappers.py
==========
Camada de mapeamento: dicionário de métricas (metrics.collect_all_metrics)
-> grupos de sinais Pydantic (models.ScannerOutput).

Regras:
- Uma função `map_<cartão>(metrics) -> SignalGroup` por cartão da UI.
- Cada mapper lê só as chaves de que precisa e nunca chama o metrics.py.
- Se o coletor falhou (`{"error": ...}`) ou a chave não existe, devolve um grupo
  LOW com os valores por omissão do modelo, em vez de rebentar.
- Os dados passam sempre pelo modelo `*Data` (validação) e depois `.model_dump()`.

Para adicionar um cartão: copiar `map_languages`, trocar a chave de metrics e o
modelo `*Data`, e registar a função em MAPPERS / build_scanner_output.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Callable
from ..config import settings
from urllib.parse import urlparse

from ..models.scanner_output import (
    ConfidenceLevel,
    LanguageBreakdown,
    LanguagesData,
    SizeAndStructureData,
    StackAndToolingData,
    CICDAndOperationsData,
    QualityIndicatorsData,
    MarkerCount,
    DebtHotspot,
    DebtOccurrence,
    TechnicalDebtData,
    DocumentationFile,
    DocumentationChangedFile,
    DocumentationData,
    CommitEvidence,
    FixesAndRevertsData,
    ChurnedFile,
    FileChurnData,
    SignalGroup,
    RepositoryInfo,
    ScopeAssessment,
    ScannerOutput,
)

Metrics = dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers comuns
# ---------------------------------------------------------------------------

def _section(metrics: Metrics, key: str) -> dict[str, Any] | None:
    """Devolve a secção de métricas, ou None se faltar ou o coletor tiver falhado."""
    raw = metrics.get(key)
    if not isinstance(raw, dict) or "error" in raw:
        return None
    return raw


def _unavailable(reason: str, empty_data: dict[str, Any] | None = None) -> SignalGroup:
    """Grupo de fallback: dados por omissão e confiança LOW."""
    return SignalGroup(
        confidence=ConfidenceLevel.LOW,
        confidence_source=reason,
        data=empty_data or {},
    )


def _not_implemented(card: str) -> Callable[[Metrics], SignalGroup]:
    """Stub para cartões ainda por mapear (o ScannerOutput continua válido)."""
    def mapper(metrics: Metrics) -> SignalGroup:
        return _unavailable(f"{card}: mapper not implemented yet")
    return mapper


# ---------------------------------------------------------------------------
# 1 · Languages          <- metrics["files_by_language"]
# ---------------------------------------------------------------------------
# Campo Pydantic                  Fonte (metrics)
# primary_language                chave com mais ficheiros em files_by_language
# breakdown[].language / .files   files_by_language.files_by_language
# breakdown[].percentage          files_by_language.share_by_language * 100
# ---------------------------------------------------------------------------

def map_languages(metrics: Metrics) -> SignalGroup:
    raw = _section(metrics, "files_by_language")
    if raw is None:
        return _unavailable("Language collector unavailable", LanguagesData().model_dump())

    counts: dict[str, int] = raw.get("files_by_language", {})
    shares: dict[str, float] = raw.get("share_by_language", {})
    loc_counts: dict[str, int] = raw.get("loc_by_language", {})
    loc_shares: dict[str, float] = raw.get("loc_share_by_language", {})
    paths: list[str] = raw.get("files_of_code", [])

    breakdown = [
        LanguageBreakdown(
            language=lang,
            files=files,
            percentage=round(shares.get(lang, 0.0) * 100, 2),
            loc=loc_counts.get(lang, 0),
            loc_share=round(loc_shares.get(lang, 0.0) * 100, 2),
        )
        for lang, files in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    ]

    data = LanguagesData(
        primary_language=breakdown[0].language if breakdown else None,
        breakdown=breakdown,
    )

    return SignalGroup(
        confidence=ConfidenceLevel.HIGH if breakdown else ConfidenceLevel.LOW,
        confidence_source="File extension mapping (.py, .js, .jsx, .ts, .tsx, .java)",
        data=data.model_dump(),
        evidence_paths=paths,
    )


# ---------------------------------------------------------------------------
# 2 · Size & Structure   <- metrics["size_and_structure"]
# ---------------------------------------------------------------------------
# Campo Pydantic        Fonte (metrics)
# code_files            size_and_structure.code_files
# total_files           size_and_structure.total_files
# loc_estimate          size_and_structure.loc_estimate
# module_estimate       size_and_structure.module_estimate
# avg_file_size_loc     size_and_structure.avg_file_size_loc  (None -> 0.0)
# ---------------------------------------------------------------------------

def map_size_and_structure(metrics: Metrics) -> SignalGroup:
    raw = _section(metrics, "size_and_structure")
    if raw is None:
        return _unavailable("Size collector unavailable", SizeAndStructureData().model_dump())

    data = SizeAndStructureData(
        code_files=raw.get("code_files", 0),
        total_files=raw.get("total_files", 0),
        loc_estimate=raw.get("loc_estimate", 0),
        module_estimate=raw.get("module_estimate", 0),
        avg_file_size_loc=raw.get("avg_file_size_loc") or 0.0,
    )

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED,
        confidence_source="File counts after Settings filters; LOC and modules are heuristics",
        data=data.model_dump(),
    )

 
# ---------------------------------------------------------------------------
# 3 · Stack & Tooling    <- metrics["frameworks_dependencies"]
# ---------------------------------------------------------------------------
# Campo Pydantic        Fonte (metrics)
# frameworks            detected_frameworks (menos o que é teste/build/linter/formatter/DB)
# testing_libraries     dependências declaradas (_TESTING)
# build_tools           dependências (_BUILD) + ficheiros (pom.xml, build.gradle, setup.py…)
# linters / formatters  dependências (_LINTERS / _FORMATTERS)
# databases             drivers/clientes declarados (_DATABASES)
# package_managers      nomes dos manifestos/lockfiles (_PACKAGE_MANAGER_FILES)
# ---------------------------------------------------------------------------

# chave normalizada (minúsculas, "_" -> "-") -> nome a mostrar.
# Para Maven/Gradle compara-se a coordenada completa e o artifactId.

_TESTING = {
    "pytest": "pytest", "pytest-asyncio": "pytest-asyncio", "pytest-cov": "pytest-cov",
    "hypothesis": "Hypothesis", "tox": "tox", "nose2": "nose2",
    "jest": "Jest", "vitest": "Vitest", "mocha": "Mocha", "chai": "Chai",
    "cypress": "Cypress", "playwright": "Playwright", "@playwright/test": "Playwright",
    "@testing-library/react": "Testing Library", "supertest": "Supertest",
    "junit": "JUnit 4", "junit-jupiter": "JUnit 5", "mockito-core": "Mockito",
    "testng": "TestNG", "assertj-core": "AssertJ", "spring-boot-starter-test": "Spring Boot Test",
}
_BUILD = {
    "vite": "Vite", "webpack": "Webpack", "rollup": "Rollup", "esbuild": "esbuild",
    "parcel": "Parcel", "turbo": "Turborepo", "tsup": "tsup",
    "setuptools": "setuptools", "hatchling": "Hatch", "poetry-core": "Poetry",
    "flit-core": "Flit",
}
_LINTERS = {
    "eslint": "ESLint", "stylelint": "Stylelint", "tslint": "TSLint",
    "pylint": "Pylint", "flake8": "Flake8", "ruff": "Ruff", "mypy": "mypy",
    "bandit": "Bandit", "checkstyle": "Checkstyle", "spotbugs": "SpotBugs", "pmd": "PMD",
}
_FORMATTERS = {
    "prettier": "Prettier", "black": "Black", "isort": "isort",
    "autopep8": "autopep8", "yapf": "YAPF",
}
_DATABASES = {
    # PostgreSQL
    "psycopg2": "PostgreSQL", "psycopg2-binary": "PostgreSQL", "psycopg": "PostgreSQL",
    "asyncpg": "PostgreSQL", "pg": "PostgreSQL", "postgresql": "PostgreSQL",
    # MySQL / MariaDB
    "pymysql": "MySQL", "mysqlclient": "MySQL", "mysql-connector-python": "MySQL",
    "aiomysql": "MySQL", "mysql2": "MySQL", "mysql": "MySQL",
    "mysql-connector-j": "MySQL", "mysql-connector-java": "MySQL",
    "mariadb-java-client": "MariaDB",
    # MongoDB
    "pymongo": "MongoDB", "motor": "MongoDB", "mongoose": "MongoDB", "mongodb": "MongoDB",
    # Redis
    "redis": "Redis", "ioredis": "Redis", "aioredis": "Redis",
    # SQLite / embebidas
    "aiosqlite": "SQLite", "better-sqlite3": "SQLite", "sqlite3": "SQLite", "h2": "H2",
    # Outras
    "oracledb": "Oracle", "cx-oracle": "Oracle", "ojdbc8": "Oracle",
    "mssql-jdbc": "SQL Server", "elasticsearch": "Elasticsearch",
}

# ficheiro (nome) -> gestor de pacotes
_PACKAGE_MANAGER_FILES = {
    "package.json": "npm", "package-lock.json": "npm", "npm-shrinkwrap.json": "npm",
    "yarn.lock": "Yarn", "pnpm-lock.yaml": "pnpm",
    "requirements.txt": "pip", "Pipfile": "Pipenv", "Pipfile.lock": "Pipenv",
    "poetry.lock": "Poetry", "uv.lock": "uv", "pdm.lock": "PDM",
    "pom.xml": "Maven", "build.gradle": "Gradle", "build.gradle.kts": "Gradle",
    "settings.gradle": "Gradle", "settings.gradle.kts": "Gradle", "gradle.lockfile": "Gradle",
}
# ficheiro (nome) -> ferramenta de build
_BUILD_FILES = {
    "pom.xml": "Maven", "build.gradle": "Gradle", "build.gradle.kts": "Gradle",
    "setup.py": "setuptools", "setup.cfg": "setuptools",
}

def _normalize(name: str) -> str:
    """Minúsculas e '_' -> '-' (scikit_learn == scikit-learn). Mantém '.' e ':' das coordenadas Maven."""
    return name.strip().lower().replace("_", "-")

def _lookup(table: dict[str, str], dep_name: str) -> str | None:
    key = _normalize(dep_name)
    if key in table:
        return table[key]
    if ":" in key:                       # Maven/Gradle: tenta só o artifactId
        return table.get(key.split(":")[-1])
    return None


def map_stack_and_tooling(metrics: Metrics) -> SignalGroup:
    raw = _section(metrics, "frameworks_dependencies")
    if raw is None:
        return _unavailable("Dependency collector unavailable", StackAndToolingData().model_dump())

    manifests: list[dict[str, Any]] = raw.get("manifests", [])

    testing: set[str] = set()
    build: set[str] = set()
    linters: set[str] = set()
    formatters: set[str] = set()
    databases: set[str] = set()
    package_managers: set[str] = set()
    evidence: list[str] = []

    for manifest in manifests:
        file = manifest.get("file", "")
        filename = Path(file).name
        evidence.append(file)

        if filename in _PACKAGE_MANAGER_FILES:
            package_managers.add(_PACKAGE_MANAGER_FILES[filename])
        elif manifest.get("ecosystem") == "Python (pip)":      # requirements-*.txt
            package_managers.add("pip")
        if filename in _BUILD_FILES:
            build.add(_BUILD_FILES[filename])

        for dep in manifest.get("dependencies", []):
            name = dep.get("name") or ""
            for table, bucket in (
                (_TESTING, testing), (_BUILD, build), (_LINTERS, linters),
                (_FORMATTERS, formatters), (_DATABASES, databases),
            ):
                if (label := _lookup(table, name)):
                    bucket.add(label)

    # frameworks "puros": o que o coletor detetou menos o que já é tooling
    tooling_labels = testing | build | linters | formatters | databases
    frameworks = [f for f in raw.get("detected_frameworks", []) if f not in tooling_labels]

    data = StackAndToolingData(
        frameworks=sorted(frameworks),
        testing_libraries=sorted(testing),
        build_tools=sorted(build),
        linters=sorted(linters),
        formatters=sorted(formatters),
        databases=sorted(databases),
        package_managers=sorted(package_managers),
    )

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED if manifests else ConfidenceLevel.LOW,
        confidence_source=(
            "Declared dependencies and manifest/lockfile names matched against known tools; "
            "declared is not necessarily used"
        ),
        data=data.model_dump(),
        evidence_paths=sorted(set(evidence)),
    )


# ---------------------------------------------------------------------------
# 4 · CI/CD & Operations   <- cicd_configuration, infrastructure, frameworks_dependencies
# ---------------------------------------------------------------------------
# Campo Pydantic                            Fonte (metrics)
# cicd_tool / cicd_description              cicd_configuration.ci_systems_detected / ci_config_files_by_system
# has_test_step_in_ci / has_deploy_step     cicd_configuration.ci_has_test_step / ci_has_deploy_step
# has_containerization                      infrastructure.has_containerization
# dockerfile_path                           infrastructure.dockerfile_paths[0]
# has_iac / iac_tools                       infrastructure.iac_tools
# has_monitoring_config / monitoring_tools  dependências declaradas (_MONITORING)
# has_documentation / documentation_notes   documentation_inventory (por mapear)
# ---------------------------------------------------------------------------


# chave normalizada (minúsculas, "_" -> "-") -> nome a mostrar.
# Para Maven/Gradle compara-se a coordenada completa e o artifactId.
_MONITORING = {
    # Prometheus
    "prometheus-client": "Prometheus", "prom-client": "Prometheus",
    "prometheus-fastapi-instrumentator": "Prometheus",
    "micrometer-registry-prometheus": "Prometheus",
    # Micrometer / Spring Boot Actuator
    "micrometer-core": "Micrometer",
    "spring-boot-starter-actuator": "Spring Boot Actuator",
    # Sentry
    "sentry-sdk": "Sentry", "@sentry/node": "Sentry", "@sentry/browser": "Sentry",
    "@sentry/react": "Sentry", "@sentry/nextjs": "Sentry",
    "sentry-spring-boot-starter": "Sentry",
    # Datadog
    "ddtrace": "Datadog", "dd-trace": "Datadog", "datadog": "Datadog",
    "dd-trace-api": "Datadog",
    # New Relic
    "newrelic": "New Relic", "newrelic-api": "New Relic",
    # Elastic APM
    "elastic-apm": "Elastic APM", "elastic-apm-node": "Elastic APM",
    "apm-agent-api": "Elastic APM",
    # OpenTelemetry
    "opentelemetry-api": "OpenTelemetry", "opentelemetry-sdk": "OpenTelemetry",
    "@opentelemetry/api": "OpenTelemetry", "@opentelemetry/sdk-node": "OpenTelemetry",
    "opentelemetry-sdk-trace": "OpenTelemetry",
    # Outros
    "statsd": "StatsD", "hot-shots": "StatsD",
    "rollbar": "Rollbar", "bugsnag": "Bugsnag", "@bugsnag/js": "Bugsnag",
}

_DOC_LABELS = (
    ("readme", "README"), ("docs_dir", "docs folder"), ("adr", "ADRs"),
    ("runbook", "runbooks"), ("install_onboarding", "install/onboarding guides"),
    ("changelog", "changelog"),
)


def _documentation_flags(metrics: Metrics) -> tuple[bool, str | None]:
    raw = _section(metrics, "documentation_inventory")
    if raw is None:
        return False, "Documentation collector unavailable"
    by_category = raw.get("files_by_category", {})
    present = [label for key, label in _DOC_LABELS if by_category.get(key, 0) > 0]
    if not present:
        return False, "No README, docs folder, ADRs, runbooks or onboarding docs detected"
    return True, "Detected: " + ", ".join(present)


def map_cicd_and_operations(metrics: Metrics) -> SignalGroup:
    ci = _section(metrics, "cicd_configuration")
    infra = _section(metrics, "infrastructure")
    deps = _section(metrics, "frameworks_dependencies")

    if ci is None and infra is None:
        return _unavailable("CI/CD and infrastructure collectors unavailable",
                            CICDAndOperationsData().model_dump())

    ci, infra = ci or {}, infra or {}

    # --- CI/CD ---
    systems: list[str] = ci.get("ci_systems_detected", [])
    by_system: dict[str, list[str]] = ci.get("ci_config_files_by_system", {})
    description = (
        "; ".join(f"{s}: {len(by_system.get(s, []))} config file(s)" for s in systems)
        if systems else None
    )

    # --- Containers e IaC ---
    container_files: list[str] = infra.get("container_files", [])
    dockerfile_paths: list[str] = infra.get("dockerfile_paths", [])
    iac_tools: list[str] = infra.get("iac_tools", [])
    iac_files = [f for files in infra.get("iac_files_by_tool", {}).values() for f in files]

    # --- Monitorização ---
    monitoring: set[str] = set()
    for manifest in (deps or {}).get("manifests", []):
        for dep in manifest.get("dependencies", []):
            if label := _lookup(_MONITORING, dep.get("name") or ""):
                monitoring.add(label)

    has_docs, docs_notes = _documentation_flags(metrics)

    data = CICDAndOperationsData(
        cicd_tool=", ".join(systems) or None,
        cicd_description=description,
        has_containerization=bool(infra.get("has_containerization", False)),
        dockerfile_path=dockerfile_paths[0] if dockerfile_paths else None,
        has_documentation=has_docs,
        documentation_notes=docs_notes,
        has_test_step_in_ci=bool(ci.get("ci_has_test_step", False)),
        has_deploy_step_in_ci=bool(ci.get("ci_has_deploy_step", False)),
        has_monitoring_config=bool(monitoring),
        monitoring_tools=sorted(monitoring),
        has_iac=bool(iac_tools),
        iac_tools=iac_tools,
    )

    evidence = [f for files in by_system.values() for f in files] + container_files + iac_files

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED,
        confidence_source=(
            "CI/infra detected by file name/path; CI steps by keyword search; "
            "monitoring from declared dependencies; presence is not execution"
        ),
        data=data.model_dump(),
        evidence_paths=sorted(set(evidence)),
    )


# ---------------------------------------------------------------------------
# 5 · Quality Indicators   <- test_inventory, cicd_configuration
# ---------------------------------------------------------------------------
# Campo Pydantic            Fonte (metrics)
# test_to_code_file_ratio   test_inventory.test_to_code_file_ratio
# test_file_count           test_inventory.test_files_count
# source_file_count         test_inventory.source_file_count
# executed_coverage         não medido (None)
# has_quality_gate          False por omissão (sem deteção)
# quality_gate_notes        cicd_configuration.quality_config_files (tooling de cobertura)
# has_code_style_config     cicd_configuration.quality_config_files
# code_style_tools          cicd_configuration.quality_config_files
# ---------------------------------------------------------------------------

# ficheiro de configuração -> ferramenta de estilo (só o que é estilo/lint/format)
_STYLE_FILES = {
    ".flake8": "Flake8", ".pylintrc": "Pylint", "mypy.ini": "mypy",
    "ruff.toml": "Ruff", ".ruff.toml": "Ruff", ".editorconfig": "EditorConfig",
    "tslint.json": "TSLint", "biome.json": "Biome",
    ".pre-commit-config.yaml": "pre-commit",
}
_STYLE_PREFIXES = (
    (".eslintrc", "ESLint"), ("eslint.config.", "ESLint"),
    (".prettierrc", "Prettier"), ("prettier.config.", "Prettier"),
)
# ficheiro de configuração -> ferramenta de cobertura
_COVERAGE_FILES = {
    ".coveragerc": "coverage.py", "codecov.yml": "Codecov", ".codecov.yml": "Codecov",
}


def _style_tool(filename: str) -> str | None:
    if filename in _STYLE_FILES:
        return _STYLE_FILES[filename]
    for prefix, label in _STYLE_PREFIXES:
        if filename.startswith(prefix):
            return label
    return None


def map_quality_indicators(metrics: Metrics) -> SignalGroup:
    tests = _section(metrics, "test_inventory")
    ci = _section(metrics, "cicd_configuration")

    if tests is None and ci is None:
        return _unavailable("Test and CI collectors unavailable",
                            QualityIndicatorsData().model_dump())

    tests, ci = tests or {}, ci or {}

    style_tools: set[str] = set()
    coverage_tools: set[str] = set()
    evidence: list[str] = []

    for f in ci.get("quality_config_files", []):
        name = PurePosixPath(f).name
        if tool := _style_tool(name):
            style_tools.add(tool)
            evidence.append(f)
        if tool := _COVERAGE_FILES.get(name):
            coverage_tools.add(tool)
            evidence.append(f)

    notes = (
        "Coverage tooling configured (" + ", ".join(sorted(coverage_tools))
        + "); coverage value not measured; quality gate not detected"
        if coverage_tools else None
    )

    data = QualityIndicatorsData(
        test_to_code_file_ratio=tests.get("test_to_code_file_ratio"),
        test_file_count=tests.get("test_files_count", 0),
        source_file_count=tests.get("source_file_count", 0),
        executed_coverage=None,             # não medido
        has_quality_gate=True if coverage_tools else False,
        quality_gate_notes=notes,
        has_code_style_config=bool(style_tools),
        code_style_tools=sorted(style_tools),
    )

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED,
        confidence_source=(
            "Test files by name/path; style and coverage tooling by config file names; "
            "coverage not measured; quality gate not assessed"
        ),
        data=data.model_dump(),
        evidence_paths=sorted(set(evidence)),
    )


# ---------------------------------------------------------------------------
# 7 · Technical Debt   <- metrics["technical_debt_markers"]
# ---------------------------------------------------------------------------
# Campo Pydantic            Fonte (metrics)
# total_markers             technical_debt_markers.total_markers
# files_with_markers        technical_debt_markers.files_with_markers
# marker_counts             technical_debt_markers.marker_counts   (dict -> lista ordenada)
# top_files                 technical_debt_markers.top_files
# occurrences               technical_debt_markers.occurrences
# occurrences_truncated     technical_debt_markers.occurrences_truncated
# ---------------------------------------------------------------------------

def map_technical_debt(metrics: Metrics) -> SignalGroup:
    raw = _section(metrics, "technical_debt_markers")
    if raw is None:
        return _unavailable("Technical debt collector unavailable",
                            TechnicalDebtData().model_dump())

    counts: dict[str, int] = raw.get("marker_counts", {})
    marker_counts = [
        MarkerCount(marker=marker, count=count)
        for marker, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    top_files = [
        DebtHotspot(file=item["file"], markers=item["markers"])
        for item in raw.get("top_files", [])
        if "file" in item
    ]
    occurrences = [
        DebtOccurrence(marker=o["marker"], file=o["file"], line=o["line"])
        for o in raw.get("occurrences", [])
        if {"marker", "file", "line"} <= o.keys()
    ]

    data = TechnicalDebtData(
        total_markers=raw.get("total_markers", 0),
        files_with_markers=raw.get("files_with_markers", 0),
        marker_counts=marker_counts,
        top_files=top_files,
        occurrences=occurrences,
        occurrences_truncated=bool(raw.get("occurrences_truncated", False)),
    )

    evidence = {h.file for h in top_files} | {o.file for o in occurrences}

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED,
        confidence_source=(
            "Case-sensitive count of TODO/FIXME/HACK/XXX/WORKAROUND in text files; "
            "a proxy for technical debt, not a complete measure"
        ),
        data=data.model_dump(),
        evidence_paths=sorted(evidence),
    )


# ---------------------------------------------------------------------------
# 8 · Documentation   <- metrics["documentation_inventory"]
# ---------------------------------------------------------------------------
# Campo Pydantic                 Fonte (metrics)
# documentation_files_count      documentation_inventory.documentation_files_count
# has_readme / has_changelog…    documentation_inventory.files_by_category (contagem completa)
# files_by_category              documentation_inventory.files_by_category
# documentation_files            documentation_inventory.documentation_files (truncada)
# documentation_files_truncated  documentation_inventory.documentation_files_truncated
# commits_touching_docs          documentation_inventory.change_frequency.commits_touching_docs
# share_of_commits               documentation_inventory.change_frequency.share_of_commits
# most_changed_files             documentation_inventory.change_frequency.most_changed_files
# ---------------------------------------------------------------------------

# categorias com valor informativo (exclui "other", que é qualquer .md solto)
_KEY_DOC_CATEGORIES = ("readme", "changelog", "adr", "runbook", "install_onboarding")


def map_documentation(metrics: Metrics) -> SignalGroup:
    raw = _section(metrics, "documentation_inventory")
    if raw is None:
        return _unavailable("Documentation collector unavailable", DocumentationData().model_dump())

    # Os has_* usam a contagem completa, não a lista (que está truncada).
    by_category: dict[str, int] = raw.get("files_by_category", {})
    freq: dict[str, Any] = raw.get("change_frequency") or {}

    files = [
        DocumentationFile(file=item["file"], categories=list(item.get("categories", [])))
        for item in raw.get("documentation_files", [])
        if "file" in item
    ]
    most_changed = [
        DocumentationChangedFile(
            file=item["file"],
            commits=item.get("commits", 0),
            last_change_date=item.get("last_change_date"),
        )
        for item in freq.get("most_changed_files", [])
        if "file" in item
    ]

    data = DocumentationData(
        documentation_files_count=raw.get("documentation_files_count", 0),
        has_readme=by_category.get("readme", 0) > 0,
        has_changelog=by_category.get("changelog", 0) > 0,
        has_adr=by_category.get("adr", 0) > 0,
        has_runbooks=by_category.get("runbook", 0) > 0,
        has_onboarding_docs=by_category.get("install_onboarding", 0) > 0,
        has_docs_directory=by_category.get("docs_dir", 0) > 0,
        files_by_category=dict(by_category),
        documentation_files=files,
        commits_touching_docs=freq.get("commits_touching_docs", 0),
        share_of_commits=freq.get("share_of_commits"),
        most_changed_files=most_changed,
    )

    # Evidência: só os documentos-chave, para não devolver centenas de caminhos.
    evidence = sorted(
        f.file for f in files if any(c in _KEY_DOC_CATEGORIES for c in f.categories)
    )[:50]

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED,
        confidence_source=(
            "Documentation files by name/extension/directory; change frequency from the "
            "analyzed commit history; existence does not imply the docs are current or useful"
        ),
        data=data.model_dump(),
        evidence_paths=evidence,
    )


# ---------------------------------------------------------------------------
# 9 · Fixes & Reverts   <- metrics["fixes_and_reverts"], metrics["history_window"]
# ---------------------------------------------------------------------------
# Campo Pydantic        Fonte (metrics)
# commits_analyzed      fixes_and_reverts.commits_analyzed
# fix_commits / ratio   fixes_and_reverts.fix_commits / fix_ratio
# fixes_by_month        fixes_and_reverts.fixes_by_month
# revert_commits / ratio fixes_and_reverts.revert_commits / revert_ratio
# reverts_by_month      fixes_and_reverts.reverts_by_month
# fix_evidence          fixes_and_reverts.fix_evidence      (cortada a MAX_EVIDENCE_RETURNED)
# revert_evidence       fixes_and_reverts.revert_evidence   (cortada a MAX_EVIDENCE_RETURNED)
# evidence_truncated    fixes_and_reverts.evidence_truncated OU corte feito aqui
# ---------------------------------------------------------------------------

MAX_EVIDENCE_RETURNED = 100      # o coletor guarda até 200; para a UI chegam os mais recentes


def _commit_evidence(items: list[dict[str, Any]]) -> list[CommitEvidence]:
    return [
        CommitEvidence(
            date=item["date"],
            message=item["message"],
            matched_term=item.get("matched_term"),
        )
        for item in items
        if {"date", "message"} <= item.keys()
    ]


def map_fixes_and_reverts(metrics: Metrics) -> SignalGroup:
    raw = _section(metrics, "fixes_and_reverts")
    if raw is None:
        return _unavailable("Fixes and reverts collector unavailable",
                            FixesAndRevertsData().model_dump())

    fix_items: list[dict[str, Any]] = raw.get("fix_evidence", [])
    revert_items: list[dict[str, Any]] = raw.get("revert_evidence", [])

    # O coletor guarda a evidência do mais recente para o mais antigo: ficam os 20 mais recentes.
    truncated_here = (len(fix_items) > MAX_EVIDENCE_RETURNED
                      or len(revert_items) > MAX_EVIDENCE_RETURNED)

    data = FixesAndRevertsData(
        commits_analyzed=raw.get("commits_analyzed", 0),
        fix_commits=raw.get("fix_commits", 0),
        fix_ratio=raw.get("fix_ratio"),
        fixes_by_month=dict(raw.get("fixes_by_month", {})),
        revert_commits=raw.get("revert_commits", 0),
        revert_ratio=raw.get("revert_ratio"),
        reverts_by_month=dict(raw.get("reverts_by_month", {})),
        fix_evidence=_commit_evidence(fix_items[:MAX_EVIDENCE_RETURNED]),
        revert_evidence=_commit_evidence(revert_items[:MAX_EVIDENCE_RETURNED]),
        evidence_truncated=bool(raw.get("evidence_truncated", False)) or truncated_here,
    )

    # Sem commits analisados não há nada a concluir.
    if data.commits_analyzed == 0:
        return SignalGroup(
            confidence=ConfidenceLevel.LOW,
            confidence_source="No commits analyzed (empty history or filters excluded everything)",
            data=data.model_dump(),
        )

    window = metrics.get("history_window") or {}
    repo = _section(metrics, "repository") or {}
    partial = window.get("truncated_by_max_commits") or repo.get("is_shallow_clone")

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED,
        confidence_source=(
            "Commit subjects matched against fix/revert keywords; heuristic, not a bug tracker"
            + ("; history is partial (shallow clone or max-commits limit)" if partial else "")
        ),
        data=data.model_dump(),
        evidence_paths=[],     # commits não têm caminhos de ficheiros
    )


# ---------------------------------------------------------------------------
# 10 · File Churn   <- metrics["file_churn"], metrics["history_window"], metrics["repository"]
# ---------------------------------------------------------------------------
# Campo Pydantic              Fonte (metrics)
# files_with_changes          file_churn.files_with_changes
# lines_added_total           file_churn.lines_added_total
# lines_deleted_total         file_churn.lines_deleted_total
# lines_changed_total         calculado (added + deleted)
# top_files_share_of_churn    file_churn.top_files_share_of_churn
# top_files[]                 file_churn.top_files
# ---------------------------------------------------------------------------

def map_file_churn(metrics: Metrics) -> SignalGroup:
    raw = _section(metrics, "file_churn")
    if raw is None:
        return _unavailable("File churn collector unavailable", FileChurnData().model_dump())

    top_files = [
        ChurnedFile(
            file=item["file"],
            lines_added=item.get("lines_added", 0),
            lines_deleted=item.get("lines_deleted", 0),
            lines_changed=item.get("lines_changed", 0),
            commits=item.get("commits", 0),
        )
        for item in raw.get("top_files", [])
        if "file" in item
    ]

    added = raw.get("lines_added_total", 0)
    deleted = raw.get("lines_deleted_total", 0)

    data = FileChurnData(
        files_with_changes=raw.get("files_with_changes", 0),
        lines_added_total=added,
        lines_deleted_total=deleted,
        lines_changed_total=added + deleted,
        top_files_share_of_churn=raw.get("top_files_share_of_churn"),
        top_files=top_files,
    )

    # Sem ficheiros alterados não há nada a concluir.
    if data.files_with_changes == 0:
        return SignalGroup(
            confidence=ConfidenceLevel.LOW,
            confidence_source="No file changes in the analyzed history (empty history or all files filtered)",
            data=data.model_dump(),
        )

    return SignalGroup(
        confidence=ConfidenceLevel.ESTIMATED,
        confidence_source=(
            "Lines added+deleted per file from git numstat over the analyzed commits; "
        ),
        data=data.model_dump(),
        evidence_paths=sorted(f.file for f in top_files),
    )


# ---------------------------------------------------------------------------
# Repository e Scope
# ---------------------------------------------------------------------------

def get_repository_name(url: str) -> str:
    """Obtém o nome do repositório a partir do URL Git."""

    path = urlparse(url).path.rstrip("/")
    name = Path(path).name

    if name.endswith(".git"):
        name = name[:-4]

    return name


def map_repository(metrics: Metrics, url: str | None, scan_id: str, type: str) -> RepositoryInfo:
    """`base` traz o que não vem do metrics (name, source_type, clone_url)."""
    repo = _section(metrics, "repository") or {}
    if url:
        name = get_repository_name(url)
        clone_url = url
    else:
        name = "zip_upload"  # fallback para upload de ficheiro zip (sem URL Git)
        clone_url = None

    return RepositoryInfo(
        name=name,
        branch=repo.get("branch"),
        commit_hash=repo.get("head_sha"),
        source_type=type,
        clone_url=clone_url,
        scan_id=scan_id,
    )


def map_scope(metrics: Metrics) -> ScopeAssessment:
    languages = _section(metrics, "files_by_language") or {}
    repo = _section(metrics, "repository") or {}
    window = metrics.get("history_window") or {}
    excluded_items = metrics.get("excluded_items") or 0

    supported = languages.get("recognized_source_files", 0)

    warnings: list[str] = []
    if repo.get("is_shallow_clone"):
        warnings.append("Shallow clone: history-based metrics are partial.")
    if window.get("truncated_by_max_commits"):
        warnings.append("History truncated by max commits limit.")
    if supported == 0:
        warnings.append("No supported source files (.py, .js, .jsx, .ts, .tsx, .java) found.")

    return ScopeAssessment(
        eligible_for_poc=supported > 0,
        supported_code_files=supported,
        excluded_items=excluded_items,
        exclusion_rules=settings.excluded_extensions + settings.excluded_dirs,
        scope_warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Montagem final
# ---------------------------------------------------------------------------

def build_scanner_output(metrics: Metrics, url: str | None, scan_id: str, type: str) -> ScannerOutput:
    languages = map_languages(metrics)
    size = map_size_and_structure(metrics)
    stack = map_stack_and_tooling(metrics)
    cicd = map_cicd_and_operations(metrics)
    quality = map_quality_indicators(metrics)
    technical_debt = map_technical_debt(metrics)
    documentation = map_documentation(metrics)
    fixes_and_reverts = map_fixes_and_reverts(metrics)
    repository_info = map_repository(metrics, url, scan_id, type)
    scope = map_scope(metrics)
    file_churn = map_file_churn(metrics)

    return ScannerOutput(
        repository=repository_info,
        scope=scope,
        languages=languages,
        size_and_structure=size,
        stack_and_tooling=stack,
        cicd_and_operations=cicd,
        quality_indicators=quality,
        technical_debt=technical_debt,
        documentation=documentation,
        fixes_and_reverts=fixes_and_reverts,
        file_churn=file_churn
    )
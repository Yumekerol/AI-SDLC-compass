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

from pathlib import Path
from typing import Any, Callable

from ..models.scanner_output import (
    ConfidenceLevel,
    LanguageBreakdown,
    LanguagesData,
    SizeAndStructureData,
    StackAndToolingData,
    CICDAndOperationsData,
    QualityIndicatorsData,
    ScannerWarning,
    WarningsAndGapsData,
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
        evidence_paths=[],   # o coletor só devolve contagens
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

    data = CICDAndOperationsData(
        cicd_tool=", ".join(systems) or None,
        cicd_description=description,
        has_containerization=bool(infra.get("has_containerization", False)),
        dockerfile_path=dockerfile_paths[0] if dockerfile_paths else None,
        has_documentation=False,              # TODO: documentation_inventory
        documentation_notes=None,
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
# 3 a 6 · Por mapear (copiar o padrão acima)
# ---------------------------------------------------------------------------
# Stack & Tooling   <- frameworks_dependencies, test_inventory, cicd_configuration
# CI/CD & Ops       <- cicd_configuration, infrastructure, documentation_inventory
# Quality           <- test_inventory, cicd_configuration
# Warnings & Gaps   <- derivado dos restantes grupos já mapeados (ver build_scanner_output)

#map_stack_and_tooling = _not_implemented("Stack & Tooling")
map_cicd_and_operations = _not_implemented("CI/CD & Operations")
map_quality_indicators = _not_implemented("Quality Indicators")
map_warnings_and_gaps = _not_implemented("Warnings & Gaps")


# ---------------------------------------------------------------------------
# Repository e Scope
# ---------------------------------------------------------------------------

def map_repository(metrics: Metrics, base: RepositoryInfo) -> RepositoryInfo:
    """`base` traz o que não vem do metrics (name, source_type, clone_url)."""
    repo = _section(metrics, "repository") or {}
    return base.model_copy(update={
        "branch": repo.get("branch"),
        "commit_hash": repo.get("head_sha"),
    })


def map_scope(metrics: Metrics) -> ScopeAssessment:
    languages = _section(metrics, "files_by_language") or {}
    repo = _section(metrics, "repository") or {}
    window = metrics.get("history_window") or {}

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
        # excluded_items e exclusion_rules: por preencher (ver nota na correlação)
        scope_warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Montagem final
# ---------------------------------------------------------------------------

def build_scanner_output(metrics: Metrics, repository: RepositoryInfo) -> ScannerOutput:
    languages = map_languages(metrics)
    size = map_size_and_structure(metrics)
    stack = map_stack_and_tooling(metrics)
    cicd = map_cicd_and_operations(metrics)
    quality = map_quality_indicators(metrics)

    return ScannerOutput(
        repository=map_repository(metrics, repository),
        scope=map_scope(metrics),
        languages=languages,
        size_and_structure=size,
        stack_and_tooling=stack,
        cicd_and_operations=cicd,
        quality_indicators=quality,
        # Warnings & Gaps no fim: no futuro recebe os grupos já mapeados
        warnings_and_gaps=map_warnings_and_gaps(metrics),
    )
"""
Tech Stack Detection Module

Detects programming languages, frameworks, databases, build tools,
linters, and formatters by parsing manifest files and file extensions.

This module is deterministic — no AI involved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models.scanner_output import (
    ConfidenceLevel,
    LanguageBreakdown,
    LanguagesData,
    SignalGroup,
    StackAndToolingData,
)


# ─── Language Detection by File Extension ─────────────────────────────

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C",
    ".hpp": "C++",
    ".swift": "Swift",
    ".scala": "Scala",
    ".r": "R",
    ".R": "R",
    ".dart": "Dart",
    ".lua": "Lua",
    ".pl": "Perl",
    ".sh": "Shell",
    ".bash": "Shell",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


# ─── Framework Detection from Manifest Files ─────────────────────────

# Python frameworks (from requirements.txt, pyproject.toml, setup.py)
PYTHON_FRAMEWORKS = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "tornado": "Tornado",
    "sanic": "Sanic",
    "aiohttp": "aiohttp",
    "bottle": "Bottle",
    "falcon": "Falcon",
    "quart": "Quart",
    "litestar": "Litestar",
}

PYTHON_TEST_LIBS = {
    "pytest": "pytest",
    "unittest": "unittest",
    "nose": "nose",
    "nose2": "nose2",
    "hypothesis": "hypothesis",
    "robot": "Robot Framework",
    "behave": "behave",
}

PYTHON_LINTERS = {
    "flake8": "flake8",
    "pylint": "pylint",
    "ruff": "ruff",
    "mypy": "mypy",
    "pyright": "pyright",
    "bandit": "bandit",
}

PYTHON_FORMATTERS = {
    "black": "Black",
    "autopep8": "autopep8",
    "yapf": "yapf",
    "isort": "isort",
}

PYTHON_DB_DRIVERS = {
    "sqlalchemy": "SQLAlchemy",
    "psycopg2": "PostgreSQL",
    "psycopg": "PostgreSQL",
    "pymongo": "MongoDB",
    "motor": "MongoDB",
    "redis": "Redis",
    "mysql-connector": "MySQL",
    "pymysql": "MySQL",
    "sqlite3": "SQLite",
    "aiosqlite": "SQLite",
    "prisma": "Prisma",
    "tortoise-orm": "Tortoise ORM",
    "peewee": "Peewee",
    "mongoengine": "MongoDB",
}

# JavaScript/TypeScript frameworks (from package.json)
JS_FRAMEWORKS = {
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "@angular/core": "Angular",
    "svelte": "Svelte",
    "express": "Express",
    "fastify": "Fastify",
    "nestjs": "NestJS",
    "@nestjs/core": "NestJS",
    "koa": "Koa",
    "hapi": "Hapi",
    "gatsby": "Gatsby",
    "remix": "Remix",
    "astro": "Astro",
    "solid-js": "SolidJS",
}

JS_TEST_LIBS = {
    "jest": "Jest",
    "mocha": "Mocha",
    "vitest": "Vitest",
    "cypress": "Cypress",
    "playwright": "Playwright",
    "@playwright/test": "Playwright",
    "@testing-library/react": "React Testing Library",
    "@testing-library/vue": "Vue Testing Library",
    "jasmine": "Jasmine",
    "karma": "Karma",
    "ava": "AVA",
    "tap": "tap",
}

JS_LINTERS = {
    "eslint": "ESLint",
    "@eslint/js": "ESLint",
    "tslint": "TSLint",
    "standard": "Standard",
    "xo": "XO",
    "biome": "Biome",
    "@biomejs/biome": "Biome",
}

JS_FORMATTERS = {
    "prettier": "Prettier",
    "biome": "Biome",
    "@biomejs/biome": "Biome",
}

JS_BUILD_TOOLS = {
    "vite": "Vite",
    "webpack": "Webpack",
    "esbuild": "esbuild",
    "rollup": "Rollup",
    "parcel": "Parcel",
    "turbo": "Turborepo",
    "nx": "Nx",
    "gulp": "Gulp",
    "grunt": "Grunt",
    "tsup": "tsup",
    "swc": "SWC",
    "@swc/core": "SWC",
}

JS_DB_DRIVERS = {
    "pg": "PostgreSQL",
    "mysql2": "MySQL",
    "mongodb": "MongoDB",
    "mongoose": "MongoDB",
    "redis": "Redis",
    "ioredis": "Redis",
    "prisma": "Prisma",
    "@prisma/client": "Prisma",
    "sequelize": "Sequelize",
    "typeorm": "TypeORM",
    "knex": "Knex",
    "drizzle-orm": "Drizzle",
    "better-sqlite3": "SQLite",
}

# Java frameworks (from pom.xml, build.gradle)
JAVA_FRAMEWORKS = {
    "spring-boot": "Spring Boot",
    "spring-webmvc": "Spring MVC",
    "spring-webflux": "Spring WebFlux",
    "quarkus": "Quarkus",
    "micronaut": "Micronaut",
    "jakarta.servlet": "Jakarta EE",
    "javax.servlet": "Java EE",
}


def detect_languages(code_files: list[Path]) -> SignalGroup:
    """
    Detect programming languages from file extensions.

    Returns a SignalGroup with LanguagesData.
    """
    lang_counts: dict[str, int] = {}
    evidence_paths: list[str] = []

    for file_path in code_files:
        ext = file_path.suffix.lower()
        if ext in LANGUAGE_EXTENSIONS:
            lang = LANGUAGE_EXTENSIONS[ext]
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    total_files = sum(lang_counts.values())
    breakdown = []
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        pct = round((count / total_files) * 100, 1) if total_files > 0 else 0
        breakdown.append(LanguageBreakdown(language=lang, files=count, percentage=pct))

    primary = breakdown[0].language if breakdown else None

    # Collect some evidence paths
    seen_langs = set()
    for file_path in code_files:
        ext = file_path.suffix.lower()
        lang = LANGUAGE_EXTENSIONS.get(ext)
        if lang and lang not in seen_langs:
            evidence_paths.append(str(file_path))
            seen_langs.add(lang)
            if len(seen_langs) >= 5:
                break

    data = LanguagesData(primary_language=primary, breakdown=breakdown)

    return SignalGroup(
        confidence=ConfidenceLevel.HIGH,
        confidence_source="File extensions",
        data=data.model_dump(),
        evidence_paths=evidence_paths,
    )


def _parse_requirements_txt(file_path: Path) -> list[str]:
    """Parse a requirements.txt file to extract package names."""
    packages = []
    try:
        for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Extract package name (before any version specifier)
            match = re.match(r'^([a-zA-Z0-9_-]+)', line)
            if match:
                packages.append(match.group(1).lower())
    except Exception:
        pass
    return packages


def _parse_package_json(file_path: Path) -> dict:
    """Parse a package.json to extract all dependency names."""
    try:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
        deps = set()
        for key in ["dependencies", "devDependencies", "peerDependencies"]:
            if key in data:
                deps.update(data[key].keys())
        return {
            "packages": [p.lower() for p in deps],
            "scripts": data.get("scripts", {}),
        }
    except Exception:
        return {"packages": [], "scripts": {}}


def _parse_pyproject_toml(file_path: Path) -> list[str]:
    """Simple parser for pyproject.toml dependency extraction."""
    packages = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        # Simple regex to find dependencies in pyproject.toml
        # Handles both [project.dependencies] and [tool.poetry.dependencies]
        in_deps_section = False
        for line in content.splitlines():
            if re.match(r'\[(project\.)?dependencies\]', line) or \
               re.match(r'\[tool\.poetry\.dependencies\]', line):
                in_deps_section = True
                continue
            if line.startswith("[") and in_deps_section:
                in_deps_section = False
                continue
            if in_deps_section:
                # Try to extract package name
                match = re.match(r'^"?([a-zA-Z0-9_-]+)"?\s*[>=<~!]', line)
                if match:
                    packages.append(match.group(1).lower())
                # Poetry style: package = "^version"
                match2 = re.match(r'^([a-zA-Z0-9_-]+)\s*=', line)
                if match2:
                    packages.append(match2.group(1).lower())
    except Exception:
        pass
    return packages


def _detect_from_packages(
    packages: list[str],
    framework_map: dict,
    test_map: dict,
    linter_map: dict,
    formatter_map: dict,
    db_map: dict,
) -> dict:
    """Match a list of package names against known library maps."""
    result = {
        "frameworks": [],
        "testing_libraries": [],
        "linters": [],
        "formatters": [],
        "databases": [],
    }
    for pkg in packages:
        pkg_lower = pkg.lower()
        if pkg_lower in framework_map:
            result["frameworks"].append(framework_map[pkg_lower])
        if pkg_lower in test_map:
            result["testing_libraries"].append(test_map[pkg_lower])
        if pkg_lower in linter_map:
            result["linters"].append(linter_map[pkg_lower])
        if pkg_lower in formatter_map:
            result["formatters"].append(formatter_map[pkg_lower])
        if pkg_lower in db_map:
            result["databases"].append(db_map[pkg_lower])

    # Deduplicate
    for key in result:
        result[key] = list(dict.fromkeys(result[key]))

    return result


def detect_stack_and_tooling(workspace: Path, code_files: list[Path]) -> SignalGroup:
    """
    Detect frameworks, testing libraries, build tools, linters, formatters,
    and databases from manifest files.
    """
    all_frameworks = []
    all_test_libs = []
    all_linters = []
    all_formatters = []
    all_databases = []
    all_build_tools = []
    all_pkg_managers = []
    evidence_paths = []

    # ── Python manifests ──────────────────────────────────────────────
    for req_file in workspace.rglob("requirements*.txt"):
        packages = _parse_requirements_txt(req_file)
        detected = _detect_from_packages(
            packages, PYTHON_FRAMEWORKS, PYTHON_TEST_LIBS,
            PYTHON_LINTERS, PYTHON_FORMATTERS, PYTHON_DB_DRIVERS,
        )
        all_frameworks.extend(detected["frameworks"])
        all_test_libs.extend(detected["testing_libraries"])
        all_linters.extend(detected["linters"])
        all_formatters.extend(detected["formatters"])
        all_databases.extend(detected["databases"])
        all_pkg_managers.append("pip")
        evidence_paths.append(str(req_file.relative_to(workspace)))

    for pyproject in workspace.rglob("pyproject.toml"):
        packages = _parse_pyproject_toml(pyproject)
        detected = _detect_from_packages(
            packages, PYTHON_FRAMEWORKS, PYTHON_TEST_LIBS,
            PYTHON_LINTERS, PYTHON_FORMATTERS, PYTHON_DB_DRIVERS,
        )
        all_frameworks.extend(detected["frameworks"])
        all_test_libs.extend(detected["testing_libraries"])
        all_linters.extend(detected["linters"])
        all_formatters.extend(detected["formatters"])
        all_databases.extend(detected["databases"])
        evidence_paths.append(str(pyproject.relative_to(workspace)))

    # ── JavaScript/TypeScript manifests ───────────────────────────────
    for pkg_json in workspace.rglob("package.json"):
        # Skip node_modules
        if "node_modules" in str(pkg_json):
            continue
        parsed = _parse_package_json(pkg_json)
        detected = _detect_from_packages(
            parsed["packages"], JS_FRAMEWORKS, JS_TEST_LIBS,
            JS_LINTERS, JS_FORMATTERS, JS_DB_DRIVERS,
        )
        all_frameworks.extend(detected["frameworks"])
        all_test_libs.extend(detected["testing_libraries"])
        all_linters.extend(detected["linters"])
        all_formatters.extend(detected["formatters"])
        all_databases.extend(detected["databases"])

        # Build tools
        for pkg in parsed["packages"]:
            if pkg.lower() in JS_BUILD_TOOLS:
                all_build_tools.append(JS_BUILD_TOOLS[pkg.lower()])

        all_pkg_managers.append("npm")
        evidence_paths.append(str(pkg_json.relative_to(workspace)))

    # ── Java manifests ────────────────────────────────────────────────
    for pom in workspace.rglob("pom.xml"):
        try:
            content = pom.read_text(encoding="utf-8", errors="ignore")
            for key, name in JAVA_FRAMEWORKS.items():
                if key in content:
                    all_frameworks.append(name)
            if "junit" in content.lower():
                all_test_libs.append("JUnit")
            if "mockito" in content.lower():
                all_test_libs.append("Mockito")
            all_pkg_managers.append("Maven")
            evidence_paths.append(str(pom.relative_to(workspace)))
        except Exception:
            pass

    for gradle in workspace.rglob("build.gradle*"):
        try:
            content = gradle.read_text(encoding="utf-8", errors="ignore")
            for key, name in JAVA_FRAMEWORKS.items():
                if key in content:
                    all_frameworks.append(name)
            if "junit" in content.lower():
                all_test_libs.append("JUnit")
            all_pkg_managers.append("Gradle")
            evidence_paths.append(str(gradle.relative_to(workspace)))
        except Exception:
            pass

    # ── Go manifests ──────────────────────────────────────────────────
    for go_mod in workspace.rglob("go.mod"):
        all_pkg_managers.append("Go Modules")
        evidence_paths.append(str(go_mod.relative_to(workspace)))

    # ── Linter/formatter config files (language-agnostic) ─────────────
    config_checks = {
        ".eslintrc": "ESLint", ".eslintrc.js": "ESLint", ".eslintrc.json": "ESLint",
        ".eslintrc.yml": "ESLint", "eslint.config.js": "ESLint", "eslint.config.mjs": "ESLint",
        ".prettierrc": "Prettier", ".prettierrc.json": "Prettier", ".prettierrc.js": "Prettier",
        "biome.json": "Biome", "biome.jsonc": "Biome",
        ".flake8": "flake8", "setup.cfg": None,  # may contain flake8 config
        "ruff.toml": "ruff", ".ruff.toml": "ruff",
        ".editorconfig": "EditorConfig",
    }
    for filename, tool_name in config_checks.items():
        if (workspace / filename).exists():
            if tool_name:
                if tool_name in ("ESLint", "flake8", "ruff", "Biome"):
                    all_linters.append(tool_name)
                elif tool_name in ("Prettier", "Biome"):
                    all_formatters.append(tool_name)
            evidence_paths.append(filename)

    # Deduplicate
    all_frameworks = list(dict.fromkeys(all_frameworks))
    all_test_libs = list(dict.fromkeys(all_test_libs))
    all_linters = list(dict.fromkeys(all_linters))
    all_formatters = list(dict.fromkeys(all_formatters))
    all_databases = list(dict.fromkeys(all_databases))
    all_build_tools = list(dict.fromkeys(all_build_tools))
    all_pkg_managers = list(dict.fromkeys(all_pkg_managers))

    data = StackAndToolingData(
        frameworks=all_frameworks,
        testing_libraries=all_test_libs,
        build_tools=all_build_tools,
        linters=all_linters,
        formatters=all_formatters,
        databases=all_databases,
        package_managers=all_pkg_managers,
    )

    confidence = ConfidenceLevel.HIGH if evidence_paths else ConfidenceLevel.LOW

    return SignalGroup(
        confidence=confidence,
        confidence_source="Dependency manifests",
        data=data.model_dump(),
        evidence_paths=evidence_paths[:10],  # Limit evidence paths shown
    )

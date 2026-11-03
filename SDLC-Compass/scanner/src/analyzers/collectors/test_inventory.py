from __future__ import annotations

import logging
import re

from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from .__common__ import _resolve_files, _relative_path, LANGUAGE_BY_EXTENSION, MAX_LISTED_ITEMS, _is_test_file

logger = logging.getLogger(__name__)


NON_CODE_EXTENSIONS = {".md", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css", ".scss"}

E2E_DIR_MARKERS = {"e2e", "end-to-end", "end_to_end", "cypress", "playwright", "selenium",
                   "puppeteer", "acceptance"}
INTEGRATION_DIR_MARKERS = {"integration", "integrations", "integration_tests", "integration-tests",
                           "itests"}
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


def _classify_test_type(relative: str) -> str:
    path = PurePosixPath(relative)
    dirs = {part.lower() for part in path.parts[:-1]}
    name = path.name.lower()

    # E2E
    e2e_patterns = [
        r"(^|[._-])e2e([._-]|$)",
        r"end[-_]to[-_]end",
        r"\.cy\.",
    ]

    if dirs & E2E_DIR_MARKERS or any(
        re.search(pattern, name) for pattern in e2e_patterns
    ):
        return "e2e"

    # Integration
    integration_patterns = [
        r"(^|[._-])integration([._-]|$)",
        r"(^|[._-])int([._-]|$)",
        r"(^|[._-])it_test([._-]|$)",
    ]

    if dirs & INTEGRATION_DIR_MARKERS or any(
        re.search(pattern, name) for pattern in integration_patterns
    ):
        return "integration"

    if re.search(r"it(case)?\.(java|kt|scala)$", name):
        return "integration"

    # Unit
    unit_patterns = [
        r"(^|[._-])unit([._-]|$)",
    ]

    if dirs & UNIT_DIR_MARKERS or any(
        re.search(pattern, name) for pattern in unit_patterns
    ):
        return "unit"

    return "unclassified"


def collect_test_inventory(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    tests: dict[str, str] = {}
    configs: list[dict[str, str]] = []
    code_files_non_test = 0

    for path in _resolve_files(repo_path, files):
        relative = _relative_path(repo_path, path)
        suffix = path.suffix.lower()

        # Detectar configurações de frameworks
        for pattern, framework in TEST_CONFIG_PATTERNS:
            if pattern.match(path.name):
                configs.append({"file": relative, "framework": framework})
                break

        # Considerar apenas ficheiros de código no inventário
        if suffix not in LANGUAGE_BY_EXTENSION:
            continue

        if _is_test_file(relative):
            tests[relative] = _classify_test_type(relative)
        else:
            code_files_non_test += 1

    by_type = Counter(tests.values())
    ordered = sorted(tests.items())
    return {
        "code_files_non_test_count": code_files_non_test,
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

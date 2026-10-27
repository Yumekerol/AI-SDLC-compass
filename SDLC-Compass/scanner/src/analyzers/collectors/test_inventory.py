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

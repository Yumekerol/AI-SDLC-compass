from __future__ import annotations

import logging

from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


from .__common__ import _resolve_files, _relative_path

logger = logging.getLogger(__name__)



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


from __future__ import annotations

import logging
import re

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

# ─── Deteção de passos de test/deploy no conteúdo dos ficheiros de CI ──

MAX_CI_FILE_BYTES = 256_000   # evita ler ficheiros gigantes
MAX_EVIDENCE_PER_KIND = 10     # evidências devolvidas por tipo (poupa tokens na LLM)
MAX_SNIPPET_CHARS = 100

# Comandos de teste (o que é executado, não só nomes de jobs)
TEST_PATTERNS = [
    r"\bpytest\b", r"\bpy\.test\b", r"\bunittest\b",
    r"\btox\s+(run|run-parallel|-e|-p|r)\b", r"\btox\s*$", r"\buv\s+run\b.*\btox\b",
    r"\bnox\s+(-s|--session|-e)\b", r"\bnox\s*$",
    r"\bnpm\s+(run\s+)?test\b", r"\byarn\s+(run\s+)?test\b", r"\bpnpm\s+(run\s+)?test\b",
    r"\bjest\b", r"\bvitest\b", r"\bmocha\b", r"\bcypress\s+run\b", r"\bplaywright\s+test\b",
    r"\bgo\s+test\b", r"\bcargo\s+(test|nextest)\b",
    r"\bmvn\w*\s+.*\b(test|verify)\b", r"\bgradle\w*\s+.*\b(test|check)\b",
    r"\bdotnet\s+test\b", r"\brspec\b", r"\bphpunit\b", r"\bctest\b",
    r"\bmake\s+(\S+\s+)*(test|tests|check)\b",
    r"\bbundle\s+exec\s+rake\s+test\b", r"\brake\s+(test|spec)\b",
]

# Deploy forte: comandos/ações que efetivamente publicam/implantam algo
DEPLOY_STRONG_PATTERNS = [
    r"\bkubectl\s+(apply|rollout|set\s+image)\b", r"\bhelm\s+(upgrade|install)\b",
    r"\bterraform\s+apply\b", r"\bserverless\s+deploy\b", r"\bsls\s+deploy\b",
    r"\bcdk\s+deploy\b", r"\bpulumi\s+up\b", r"\bansible-playbook\b",
    r"\bgcloud\s+.*\bdeploy\b", r"\baws\s+.*\bdeploy\b", r"\baz\s+.*\bdeploy\b",
    r"\bflyctl\s+deploy\b", r"\bfly\s+deploy\b", r"\bheroku\b.*\b(push|release)\b",
    r"\bvercel\b.*--prod", r"\bnetlify\s+deploy\b", r"\bfirebase\s+deploy\b",
    r"\bcap\s+\w+\s+deploy\b", r"\bargocd\s+app\s+sync\b",
    r"azure/webapps-deploy", r"aws-actions/amazon-ecs-deploy",
    r"google-github-actions/deploy", r"google-github-actions/deploy-cloudrun",
]

# Deploy fraco: nomes de jobs/stages/ambientes e publicação de imagens
DEPLOY_WEAK_PATTERNS = [
    r"\bdocker\s+push\b",
    r"^\s*-?\s*stage:\s*['\"]?deploy",
    r"^\s*deploy(ment)?[\w-]*\s*:\s*$",          # job chamado deploy / deploy-prod
    r"\benvironment:\s*['\"]?(prod|production|staging)\b",
]

# Reusable workflows / includes: a lógica real pode estar noutro repositório
EXTERNAL_LOGIC_PATTERNS = [
    r"\buses:\s*[\w.-]+/[\w.-]+/\.github/workflows/[\w./-]+@",   # GitHub reusable workflow
    r"^\s*include\s*:",                                          # GitLab include
    r"@Library\s*\(",                                            # Jenkins shared library
    r"\blibrary\s*\(\s*['\"]",                                   # Jenkins library()
]

_TEST_RE = [re.compile(p, re.IGNORECASE) for p in TEST_PATTERNS]
_DEPLOY_STRONG_RE = [re.compile(p, re.IGNORECASE) for p in DEPLOY_STRONG_PATTERNS]
_DEPLOY_WEAK_RE = [re.compile(p, re.IGNORECASE) for p in DEPLOY_WEAK_PATTERNS]
_EXTERNAL_RE = [re.compile(p, re.IGNORECASE) for p in EXTERNAL_LOGIC_PATTERNS]


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


def _first_match(regexes: list[re.Pattern], line: str) -> bool:
    return any(rx.search(line) for rx in regexes)


_COMMAND_LINE_RE = re.compile(
    r"^\s*(-\s*)?(run|script|command|commands)\s*:|^\s*-\s+\S|^\s*(\$|>)\s"
)


def _evidence_rank(evidence: str) -> int:
    """0 = parece um comando executado, 1 = o resto. Serve para ordenar a evidência."""
    snippet = evidence.split(" ", 1)[1] if " " in evidence else evidence
    return 0 if _COMMAND_LINE_RE.search(snippet) else 1


def _scan_ci_file(path: Path, relative: str) -> dict[str, list[str]]:
    """
    Procura padrões de test/deploy num ficheiro de CI.
    Devolve evidência como strings curtas: "ficheiro:linha snippet".
    """
    hits: dict[str, list[str]] = {
        "test": [], "deploy_strong": [], "deploy_weak": [], "external": [],
    }
    try:
        if path.stat().st_size > MAX_CI_FILE_BYTES:
            logger.warning("Ficheiro de CI demasiado grande, ignorado: %s", relative)
            return hits
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        logger.warning("Não foi possível ler %s", relative)
        return hits

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue  # ignora comentários e linhas vazias

        evidence = f"{relative}:{lineno} {stripped[:MAX_SNIPPET_CHARS]}"

        if _first_match(_TEST_RE, line):
            hits["test"].append(evidence)
        if _first_match(_DEPLOY_STRONG_RE, line):
            hits["deploy_strong"].append(evidence)
        elif _first_match(_DEPLOY_WEAK_RE, line):
            hits["deploy_weak"].append(evidence)
        if _first_match(_EXTERNAL_RE, line):
            hits["external"].append(evidence)

    return hits


def collect_cicd_configuration(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    by_system: dict[str, list[str]] = defaultdict(list)
    ci_files: list[tuple[Path, str]] = []   # guardado para não reler/resolver duas vezes
    quality: list[str] = []
    build_tasks: list[str] = []

    for path in _resolve_files(repo_path, files):
        relative = _relative_path(repo_path, path)
        system = _classify_ci(relative)
        if system:
            by_system[system].append(relative)
            ci_files.append((path, relative))
        if path.name in BUILD_TASK_FILE_NAMES:
            build_tasks.append(relative)
        if path.name in QUALITY_CONFIG_NAMES or path.name.startswith(QUALITY_CONFIG_PREFIXES):
            quality.append(relative)

    # Fase 2: analisar o conteúdo dos ficheiros de CI
    test_evidence: list[str] = []
    deploy_strong: list[str] = []
    deploy_weak: list[str] = []
    external_logic: list[str] = []

    for path, relative in ci_files:
        hits = _scan_ci_file(path, relative)
        test_evidence.extend(hits["test"])
        deploy_strong.extend(hits["deploy_strong"])
        deploy_weak.extend(hits["deploy_weak"])
        external_logic.extend(hits["external"])

        test_evidence.sort(key=_evidence_rank)   # sort é estável: mantém a ordem original em empates

    has_deploy = bool(deploy_strong or deploy_weak)
    if deploy_strong:
        deploy_strength = "strong"
    elif deploy_weak:
        deploy_strength = "weak"
    else:
        deploy_strength = None

    deploy_evidence = (deploy_strong + deploy_weak)[:MAX_EVIDENCE_PER_KIND]

    return {
        "ci_systems_detected": sorted(by_system),
        "ci_config_files_count": sum(len(v) for v in by_system.values()),
        "ci_config_files_by_system": {k: sorted(v) for k, v in sorted(by_system.items())},
        "build_task_files": sorted(build_tasks),
        "quality_config_files": sorted(quality),
        "has_test_step_in_ci": bool(test_evidence),
        "has_deploy_step_in_ci": has_deploy,
        "deploy_detection_strength": deploy_strength,   # "strong" | "weak" | None
        "test_step_evidence": test_evidence[:MAX_EVIDENCE_PER_KIND],
        "deploy_step_evidence": deploy_evidence,
        "uses_external_ci_logic": bool(external_logic),
        "external_ci_logic_evidence": external_logic[:MAX_EVIDENCE_PER_KIND],
        "limitations": (
            "Deteção por nome/caminho e por palavras-chave no conteúdo dos ficheiros de CI. "
            "A presença de configuração não demonstra que os pipelines são executados nem que "
            "passam. A deteção de deploy 'weak' baseia-se em nomes de jobs/ambientes e pode "
            "ser falso positivo. Reusable workflows, 'include:' (GitLab) e shared libraries "
            "(Jenkins) escondem lógica noutros repositórios, que não é analisada. Se "
            "settings.excluded_dirs incluir '.github' ou similares, essas configurações não "
            "serão vistas."
        ),
    }
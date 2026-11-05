"""
Project Profiler: extracts semantic project context from the README and
deterministic scanner signals before specialists execute.

Grounds downstream specialists (especially DevOps & Monitoring and QA) in what
the project actually is (e.g. an internal library vs. a deployed cloud service),
preventing irrelevant or nonsensical clarifying questions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from .config import settings
from .context import RunContext

logger = logging.getLogger(__name__)

MAX_README_CHARS = 5000

COMMON_README_NAMES = ("README.md", "README.rst", "README.txt", "README")


class ProjectProfile(BaseModel):
    """Semantic profile describing project nature, purpose, and operational scope."""

    project_type: str = Field(
        description=(
            "Categorization of project (e.g., 'Standalone Library', 'Web API / Backend Service', "
            "'CLI Utility', 'Frontend Application', 'Fullstack Application', 'Data Science / Prototype')"
        )
    )
    summary: str = Field(
        description="2-3 concise sentences summarizing what the application actually does and its purpose."
    )
    distribution_target: str = Field(
        description=(
            "Distribution or execution model (e.g., 'Local execution / Internal only', "
            "'Package Registry (PyPI/npm/crates.io)', 'Cloud / Containerized Service', 'Not distributed')"
        )
    )
    operational_scope: str = Field(
        description=(
            "Guidance on whether deployment, CI/CD, or production monitoring apply to this repository "
            "(e.g. 'Local library without server deployment or runtime monitoring requirements')."
        )
    )
    has_deployment_target: bool = Field(
        description="True if project is intended to be deployed to servers/cloud; False for standalone libraries, CLI tools, or prototypes."
    )


PROFILER_SYSTEM_PROMPT = """You are the Project Profiler for an AI-SDLC diagnostic engine.
Your job is to read a repository's README along with structural scanner facts (languages, frameworks, build tools, and whether container/deployment configs exist) to establish the project's identity and operational scope.

Specialists (Requirements, Code Hygiene, QA, DevOps) will rely on your profile to steer their assessment.
Specifically:
1. Determine the accurate project type and write a clear 2-3 sentence summary of what the code does.
2. Determine if the project is a deployed web/cloud service or if it is a standalone library, CLI tool, or local utility.
3. If it has no containerization, no deployment pipeline, and is just a library or script, explicitly state that in operational_scope and set has_deployment_target to false so DevOps specialists do not ask irrelevant questions about cloud deployments or incident management."""


def find_readme_path(ctx: RunContext) -> Path | None:
    """Locate the README file using scanner signals first, then filesystem check."""
    # 1. Check scanner documentation signals
    doc_data = (ctx.scan_output or {}).get("documentation", {}).get("data", {})
    if doc_data.get("has_readme"):
        for doc_item in doc_data.get("documentation_files", []):
            if "readme" in [cat.lower() for cat in doc_item.get("categories", [])]:
                candidate = ctx.root / doc_item.get("file", "")
                if candidate.is_file():
                    return candidate

    # 2. Filesystem fallback (case-insensitive check for common names)
    try:
        entries = {p.name.lower(): p for p in ctx.root.iterdir() if p.is_file()}
        for name in COMMON_README_NAMES:
            if name.lower() in entries:
                return entries[name.lower()]
    except Exception as exc:
        logger.warning("Failed filesystem search for README in %s: %s", ctx.root, exc)

    return None


def read_readme_content(readme_path: Path | None, max_chars: int = MAX_README_CHARS) -> str | None:
    """Read the top portion of the README file."""
    if not readme_path or not readme_path.is_file():
        return None
    try:
        text = readme_path.read_text(encoding="utf-8", errors="replace")
        text = text.strip()
        if not text:
            return None
        return text[:max_chars]
    except Exception as exc:
        logger.warning("Could not read README at %s: %s", readme_path, exc)
        return None


def extract_scanner_context(scan_output: dict[str, Any]) -> dict[str, Any]:
    """Extract key structural facts from scanner output."""
    if not scan_output:
        return {}

    lang_data = scan_output.get("languages", {}).get("data", {})
    stack_data = scan_output.get("stack_and_tooling", {}).get("data", {})
    ops_data = scan_output.get("cicd_and_operations", {}).get("data", {})
    size_data = scan_output.get("size_and_structure", {}).get("data", {})

    return {
        "primary_language": lang_data.get("primary_language"),
        "frameworks": stack_data.get("frameworks", []),
        "package_managers": stack_data.get("package_managers", []),
        "build_tools": stack_data.get("build_tools", []),
        "cicd_tool": ops_data.get("cicd_tool"),
        "has_containerization": ops_data.get("has_containerization", False),
        "dockerfile_path": ops_data.get("dockerfile_path"),
        "has_deploy_step_in_ci": ops_data.get("has_deploy_step_in_ci", False),
        "has_iac": ops_data.get("has_iac", False),
        "has_monitoring_config": ops_data.get("has_monitoring_config", False),
        "code_files": size_data.get("code_files", 0),
        "loc_estimate": size_data.get("loc_estimate", 0),
    }


def heuristic_profile(scanner_context: dict[str, Any], has_readme: bool) -> ProjectProfile:
    """Generate a safe baseline heuristic profile when LLM or README is unavailable."""
    primary_lang = scanner_context.get("primary_language") or "Unknown"
    frameworks = scanner_context.get("frameworks", [])
    has_containers = scanner_context.get("has_containerization", False)
    has_deploy = scanner_context.get("has_deploy_step_in_ci", False)
    has_iac = scanner_context.get("has_iac", False)

    # Web/service frameworks check
    web_framework_hints = {"fastapi", "django", "flask", "express", "nestjs", "spring", "spring boot", "rails"}
    has_web_framework = any(f.lower() in web_framework_hints for f in frameworks)

    is_deployed_service = has_containers or has_deploy or has_iac or has_web_framework

    if is_deployed_service:
        project_type = "Web Service / Application"
        distribution_target = "Cloud / Server Deployment"
        operational_scope = (
            "Service application: deployment configuration, CI/CD gating, and operational readiness apply."
        )
        has_deployment_target = True
    else:
        project_type = "Standalone Library / Utility"
        distribution_target = "Local execution / Package distribution"
        operational_scope = (
            "Standalone library or tool: server deployment and cloud monitoring are not required. "
            "Focus on code hygiene, packaging, and automated testing."
        )
        has_deployment_target = False

    summary = (
        f"A {primary_lang} codebase with {len(frameworks)} detected framework(s). "
        + ("No README was found in the repository." if not has_readme else "README is present.")
    )

    return ProjectProfile(
        project_type=project_type,
        summary=summary,
        distribution_target=distribution_target,
        operational_scope=operational_scope,
        has_deployment_target=has_deployment_target,
    )


async def profile_repository(ctx: RunContext) -> ProjectProfile:
    """Produce a ProjectProfile for the repository using README and scanner facts."""
    readme_path = find_readme_path(ctx)
    readme_content = read_readme_content(readme_path)
    scanner_facts = extract_scanner_context(ctx.scan_output)

    if not readme_content:
        logger.info(
            "No README content available for %s; using scanner-derived heuristic profile.",
            ctx.root.name,
        )
        return heuristic_profile(scanner_facts, has_readme=False)

    user_prompt = (
        f"### DETECTED SCANNER SIGNALS:\n{json.dumps(scanner_facts, indent=2)}\n\n"
        f"### REPOSITORY README ({readme_path.name if readme_path else 'README'}):\n"
        f"{readme_content}\n\n"
        "Generate the ProjectProfile matching the schema."
    )

    try:
        model = ChatOllama(
            model=settings.chat_model,
            base_url=settings.ollama_host,
            temperature=0.0,
            num_ctx=settings.num_ctx,
            num_predict=1200,
            reasoning=False,
            keep_alive=settings.keep_alive,
        )
        structured_model = model.with_structured_output(ProjectProfile)
        result: ProjectProfile = await structured_model.ainvoke(
            [
                {"role": "system", "content": PROFILER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        logger.info(
            "Generated project profile for %s: %s (deployment_target=%s)",
            ctx.root.name,
            result.project_type,
            result.has_deployment_target,
        )
        return result
    except Exception as exc:
        logger.warning(
            "Project profiler LLM call failed for %s (%s). Falling back to heuristic profile.",
            ctx.root.name,
            exc,
        )
        return heuristic_profile(scanner_facts, has_readme=True)

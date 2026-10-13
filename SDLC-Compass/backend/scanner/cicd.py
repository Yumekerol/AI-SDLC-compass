"""
CI/CD & Operations Scanner Module

Detects CI/CD pipeline definitions, containerization files (Docker),
monitoring configurations, and Infrastructure as Code (IaC).

This module is deterministic — no AI involved.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models.scanner_output import (
    CICDAndOperationsData,
    ConfidenceLevel,
    SignalGroup,
)


CICD_FILES = {
    ".github/workflows": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    "bitbucket-pipelines.yml": "Bitbucket Pipelines",
    ".circleci/config.yml": "CircleCI",
    ".travis.yml": "Travis CI",
    "azure-pipelines.yml": "Azure Pipelines",
    "Jenkinsfile": "Jenkins",
    ".drone.yml": "Drone CI",
}

MONITORING_CONFIGS = {
    "prometheus.yml": "Prometheus",
    "prometheus.yaml": "Prometheus",
    "datadog.yaml": "Datadog",
    "datadog.yml": "Datadog",
    "newrelic.yml": "New Relic",
    "newrelic.ini": "New Relic",
    "sentry.properties": "Sentry",
    "otel-collector.yaml": "OpenTelemetry",
    "otel-collector.yml": "OpenTelemetry",
}

IAC_PATTERNS = {
    "terraform": "Terraform",
    "pulumi": "Pulumi",
    "helm": "Helm",
    "kubernetes": "Kubernetes",
    "ansible": "Ansible",
    "cloudformation": "CloudFormation",
}


def _scan_ci_file_content(file_path: Path) -> tuple[bool, bool]:
    """Scan CI workflow YAML/Jenkinsfile for test and deployment steps."""
    has_test = False
    has_deploy = False
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        if re.search(r'\b(test|pytest|npm run test|npm test|mvn test|gradle test|cargo test|go test|vitest|jest)\b', content):
            has_test = True
        if re.search(r'\b(deploy|deployment|publish|release|kubectl apply|helm upgrade|terraform apply|aws s3 sync|gcloud app deploy)\b', content):
            has_deploy = True
    except Exception:
        pass
    return has_test, has_deploy


def detect_cicd_and_operations(
    workspace: Path,
    has_documentation: bool = False,
    documentation_notes: str | None = None,
) -> SignalGroup:
    """
    Detect CI/CD tools, containerization, monitoring, and IaC signals.
    """
    detected_cicd_tool = None
    cicd_descriptions = []
    has_test_in_ci = False
    has_deploy_in_ci = False
    evidence_paths: list[str] = []

    # 1. CI/CD Pipelines
    for rel_path, tool in CICD_FILES.items():
        candidate = workspace / rel_path
        if candidate.exists():
            if not detected_cicd_tool:
                detected_cicd_tool = tool

            if candidate.is_dir():
                # e.g., .github/workflows directory
                wf_files = list(candidate.glob("*.yml")) + list(candidate.glob("*.yaml"))
                if wf_files:
                    cicd_descriptions.append(f"{tool} with {len(wf_files)} workflow file(s)")
                    for wf in wf_files:
                        evidence_paths.append(str(wf.relative_to(workspace)))
                        t, d = _scan_ci_file_content(wf)
                        if t:
                            has_test_in_ci = True
                        if d:
                            has_deploy_in_ci = True
            else:
                cicd_descriptions.append(f"{tool} config file found")
                evidence_paths.append(rel_path)
                t, d = _scan_ci_file_content(candidate)
                if t:
                    has_test_in_ci = True
                if d:
                    has_deploy_in_ci = True

    # 2. Containerization
    has_container = False
    dockerfile_path = None
    docker_candidates = [
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "compose.yaml", "Containerfile",
    ]
    for dc in docker_candidates:
        candidate = workspace / dc
        if candidate.exists():
            has_container = True
            if not dockerfile_path and "Dockerfile" in dc:
                dockerfile_path = dc
            evidence_paths.append(dc)

    # Search for subfolder Dockerfiles if none found at root
    if not has_container:
        for df in list(workspace.rglob("Dockerfile*"))[:2]:
            if "node_modules" not in str(df) and ".git" not in str(df):
                has_container = True
                dockerfile_path = str(df.relative_to(workspace))
                evidence_paths.append(dockerfile_path)
                break

    # 3. Monitoring & Observability
    detected_monitoring: list[str] = []
    for rel_path, tool in MONITORING_CONFIGS.items():
        if (workspace / rel_path).exists():
            detected_monitoring.append(tool)
            evidence_paths.append(rel_path)

    # 4. Infrastructure as Code (IaC)
    detected_iac: list[str] = []
    # Terraform
    if list(workspace.glob("*.tf")) or list(workspace.rglob("terraform/*.tf")):
        detected_iac.append("Terraform")
        evidence_paths.append("Terraform (.tf files)")
    # Helm
    if (workspace / "Chart.yaml").exists() or list(workspace.rglob("charts/*/Chart.yaml")):
        detected_iac.append("Helm")
        evidence_paths.append("Helm Chart.yaml")
    # Kubernetes manifests
    if (workspace / "k8s").exists() or (workspace / "kubernetes").exists():
        detected_iac.append("Kubernetes")
        evidence_paths.append("Kubernetes manifests")
    # Pulumi
    if (workspace / "Pulumi.yaml").exists():
        detected_iac.append("Pulumi")
        evidence_paths.append("Pulumi.yaml")
    # Ansible
    if (workspace / "ansible.cfg").exists() or (workspace / "playbook.yml").exists():
        detected_iac.append("Ansible")
        evidence_paths.append("Ansible configuration")

    detected_iac = list(dict.fromkeys(detected_iac))
    detected_monitoring = list(dict.fromkeys(detected_monitoring))

    data = CICDAndOperationsData(
        cicd_tool=detected_cicd_tool,
        cicd_description="; ".join(cicd_descriptions) if cicd_descriptions else "No CI/CD pipeline found",
        has_containerization=has_container,
        dockerfile_path=dockerfile_path,
        has_documentation=has_documentation,
        documentation_notes=documentation_notes,
        has_test_step_in_ci=has_test_in_ci,
        has_deploy_step_in_ci=has_deploy_in_ci,
        has_monitoring_config=len(detected_monitoring) > 0,
        monitoring_tools=detected_monitoring,
        has_iac=len(detected_iac) > 0,
        iac_tools=detected_iac,
    )

    if detected_cicd_tool or has_container:
        confidence = ConfidenceLevel.HIGH
        confidence_source = "CI/CD and container file parsing"
    else:
        confidence = ConfidenceLevel.LOW
        confidence_source = "Absence of recognized CI/CD or container files"

    return SignalGroup(
        confidence=confidence,
        confidence_source=confidence_source,
        data=data.model_dump(),
        evidence_paths=list(dict.fromkeys(evidence_paths))[:10],
    )

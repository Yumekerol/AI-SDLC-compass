from __future__ import annotations

import logging

from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .__common__ import _resolve_files, _relative_path, MAX_LISTED_ITEMS

logger = logging.getLogger(__name__)



INFRA_FILE_NAMES = {
    # Docker / Containers
    "Dockerfile",
    "Containerfile",
    ".dockerignore",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",

    # Kubernetes
    "deployment.yaml",
    "deployment.yml",
    "service.yaml",
    "service.yml",
    "statefulset.yaml",
    "statefulset.yml",
    "daemonset.yaml",
    "daemonset.yml",
    "ingress.yaml",
    "ingress.yml",
    "configmap.yaml",
    "configmap.yml",
    "namespace.yaml",
    "namespace.yml",
    "kustomization.yaml",
    "kustomization.yml",

    # Helm
    "Chart.yaml",
    "values.yaml",

    # Terraform / OpenTofu
    "main.tf",
    "variables.tf",
    "outputs.tf",
    "providers.tf",
    "versions.tf",
    "backend.tf",
    "terraform.tf",
    "terraform.tfvars",

    # Ansible
    "ansible.cfg",
    "playbook.yml",
    "playbook.yaml",
    "inventory.ini",

    # Cloud / Serverless
    "cloudformation.yaml",
    "cloudformation.yml",
    "serverless.yml",
    "serverless.yaml",

    # Servidores / Reverse proxies
    "nginx.conf",
    "httpd.conf",
    "Caddyfile",
    "haproxy.cfg",

    # Automatização de ambiente
    "Vagrantfile",
}


COMPOSE_NAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
K8S_NAMES = {f"{n}.{ext}" for n in ("deployment", "service", "statefulset", "daemonset",
                                     "ingress", "configmap", "namespace")
             for ext in ("yaml", "yml")}
PROXY_NAMES = {"nginx.conf": "Nginx", "httpd.conf": "Apache HTTP Server",
               "caddyfile": "Caddy", "haproxy.cfg": "HAProxy"}


def _is_dockerfile(name: str) -> bool:
    lower = name.lower()
    return (lower in {"dockerfile", "containerfile"}
            or lower.startswith(("dockerfile.", "containerfile."))
            or lower.endswith((".dockerfile", ".containerfile")))


def _iac_tool(name: str, suffix: str, dirs: set[str]) -> str | None:
    lower = name.lower()
    if suffix == ".tf" or lower == "terraform.tfvars":
        return "Terraform"
    if lower == "chart.yaml":                      # values.yaml sozinho é demasiado genérico
        return "Helm"
    if lower in {"kustomization.yaml", "kustomization.yml"}:
        return "Kustomize"
    if lower in K8S_NAMES or dirs & {"k8s", "kubernetes"}:
        return "Kubernetes"
    if lower in {"ansible.cfg", "playbook.yml", "playbook.yaml", "inventory.ini"}:
        return "Ansible"
    if lower in {"cloudformation.yaml", "cloudformation.yml"}:
        return "CloudFormation"
    if lower in {"serverless.yml", "serverless.yaml"}:
        return "Serverless Framework"
    if lower == "vagrantfile":
        return "Vagrant"
    return None


def collect_infrastructure(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    found: set[str] = set()
    container_files: set[str] = set()
    dockerfiles: set[str] = set()
    iac_files: dict[str, set[str]] = defaultdict(set)
    proxies: set[str] = set()

    for path in _resolve_files(repo_path, files):
        relative = _relative_path(repo_path, path)
        dirs = {p.lower() for p in PurePosixPath(relative).parts[:-1]}
        name, suffix = path.name, path.suffix.lower()

        dockerfile = _is_dockerfile(name)
        if not (dockerfile or name in INFRA_FILE_NAMES or suffix == ".tf"
                or dirs & {"k8s", "kubernetes"}):
            continue

        found.add(relative)

        if dockerfile:
            dockerfiles.add(relative)
            container_files.add(relative)
        elif name.lower() in COMPOSE_NAMES:
            container_files.add(relative)

        if tool := _iac_tool(name, suffix, dirs):
            iac_files[tool].add(relative)

        if name.lower() in PROXY_NAMES:
            proxies.add(PROXY_NAMES[name.lower()])

    ordered = sorted(found)
    return {
        "infrastructure_files_count": len(found),
        "infrastructure_files": ordered[:MAX_LISTED_ITEMS],
        "infrastructure_files_truncated": len(ordered) > MAX_LISTED_ITEMS,
        "has_containerization": bool(container_files),
        "container_files": sorted(container_files)[:MAX_LISTED_ITEMS],
        "dockerfile_paths": sorted(dockerfiles, key=lambda f: (len(PurePosixPath(f).parts), f))[:MAX_LISTED_ITEMS],
        "iac_tools": sorted(iac_files),
        "iac_files_by_tool": {t: sorted(f)[:MAX_LISTED_ITEMS] for t, f in sorted(iac_files.items())},
        "reverse_proxies": sorted(proxies),
    }


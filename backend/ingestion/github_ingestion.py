"""
GitHub Repository Ingestion Module

Clones remote Git repositories shallowly (depth=1) with optional
access token authentication for private repositories.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from ..config import settings
from ..models.scanner_output import RepositoryInfo

logger = logging.getLogger(__name__)


def extract_repo_name(git_url: str) -> str:
    """Extract repository name from a git URL."""
    clean_url = git_url.strip().rstrip("/")
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]
    parts = clean_url.split("/")
    return parts[-1] if parts else "unknown-repo"


def inject_auth_token(git_url: str, token: str) -> str:
    """
    Inject personal access token into HTTPS git URL for private repo authentication.
    e.g., https://github.com/org/repo.git -> https://token@github.com/org/repo.git
    """
    parsed = urlparse(git_url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        return git_url

    netloc = f"{token}@{parsed.netloc}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def clone_github_repo(
    git_url: str,
    target_dir: Path,
    access_token: str | None = None,
) -> tuple[Path, RepositoryInfo]:
    """
    Shallow-clone a Git repository to target_dir.

    Returns:
    - Path to the cloned workspace
    - RepositoryInfo model with branch and commit metadata
    """
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    repo_name = extract_repo_name(git_url)
    auth_url = inject_auth_token(git_url, access_token) if access_token else git_url

    logger.info(f"Cloning {git_url} to {target_dir} (shallow clone)")

    cmd = [
        "git",
        "clone",
        "--depth",
        "1",
        auth_url,
        str(target_dir),
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=settings.github_clone_timeout,
            check=True,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise TimeoutError(f"Git clone timed out after {settings.github_clone_timeout} seconds")
    except subprocess.CalledProcessError as e:
        shutil.rmtree(target_dir, ignore_errors=True)
        # Redact token from error message if present
        err_msg = e.stderr or str(e)
        if access_token:
            err_msg = err_msg.replace(access_token, "***")
        raise RuntimeError(f"Git clone failed: {err_msg.strip()}")

    # Extract branch and commit hash
    branch = None
    commit_hash = None
    try:
        branch_res = subprocess.run(
            ["git", "-C", str(target_dir), "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if branch_res.returncode == 0:
            branch = branch_res.stdout.strip()

        commit_res = subprocess.run(
            ["git", "-C", str(target_dir), "rev-parse", "--short", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if commit_res.returncode == 0:
            commit_hash = commit_res.stdout.strip()
    except Exception as ex:
        logger.warning(f"Failed to read git commit metadata: {ex}")

    repo_info = RepositoryInfo(
        name=repo_name,
        branch=branch or "main",
        commit_hash=commit_hash,
        source_type="git",
        clone_url=git_url,
    )

    return target_dir, repo_info

"""
git_extract: clone a remote git repository into the scanner's tmp directory.

What this module does
  * validates and normalises the repository URL (https only, allow-listed hosts)
  * clones the FULL history (git log / blame / tags are needed by the collectors)
  * keeps the access token out of argv, logs, URLs and .git/config
  * never executes anything from the cloned repository
  * returns light metadata about the clone (HEAD sha, branch, commit count...)

What it does NOT do (yet): run the collectors. The API layer calls
`clone_repository()`, hands `CloneResult.path` to the collectors and finally
calls `cleanup_clone()`.

Location: scanner/src/services/git_extract.py (with an __init__.py)
Requires: git >= 2.31 (the token is passed via GIT_CONFIG_COUNT/KEY/VALUE).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ..config import settings

logger = logging.getLogger(__name__)

_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_ERROR_DETAIL_MAX = 400
# Optional: add `allowed_git_hosts: list[str]` to Settings to override.
_ALLOWED_HOSTS = tuple(
    getattr(settings, "allowed_git_hosts", ("github.com",))
)


# ---------------------------------------------------------------------------
# Errors. The API layer maps `kind` to an HTTP status.
# ---------------------------------------------------------------------------
class GitExtractError(Exception):
    kind = "clone_failed"


class InvalidRepoURL(GitExtractError):
    kind = "invalid_url"


class CloneAuthError(GitExtractError):
    kind = "auth"


class RepoNotFound(GitExtractError):
    kind = "not_found"


class CloneTimeout(GitExtractError):
    kind = "timeout"


class EmptyRepository(GitExtractError):
    kind = "empty"


class GitNotInstalled(GitExtractError):
    kind = "git_missing"


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CloneResult:
    scan_id: str
    path: Path               # internal only, do not expose to API clients
    repo_url: str            # normalised, never contains credentials
    head_sha: str
    branch: str | None       # None when HEAD is detached
    commits_total: int
    is_shallow: bool
    tracked_files: int       # raw `git ls-files` count, before scanner filters
    exceeds_poc_limit: bool  # tracked_files > settings.poc_max_files


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------
def normalise_repo_url(raw: str) -> str:
    """Return a canonical https clone URL (no credentials) or raise InvalidRepoURL.

    Accepts e.g. https://github.com/owner/repo, .../repo.git, .../repo/tree/main.
    Rejects every other scheme: git also supports ext::, file:// and ssh://,
    and ext:: can execute commands, so only https is ever allowed.
    """
    try:
        parts = urlsplit(raw.strip())
        port = parts.port
    except ValueError as exc:
        raise InvalidRepoURL("Malformed repository URL.") from exc

    if parts.scheme != "https":
        raise InvalidRepoURL("Only https:// repository URLs are accepted.")
    if parts.username or parts.password:
        raise InvalidRepoURL(
            "Do not embed credentials in the URL; use the 'token' field."
        )
    if parts.query or parts.fragment or port not in (None, 443):
        raise InvalidRepoURL(
            "URL must not contain a query string, fragment or custom port."
        )

    host = (parts.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise InvalidRepoURL(
            f"Host '{host}' is not allowed. "
            f"Allowed hosts: {', '.join(_ALLOWED_HOSTS)}."
        )

    segments = [s for s in parts.path.split("/") if s]
    if host == "github.com":
        segments = segments[:2]  # tolerate .../tree/main, .../issues, ...
    elif "-" in segments:
        segments = segments[: segments.index("-")]  # GitLab: .../-/tree/main
    if segments and segments[-1].endswith(".git"):
        segments[-1] = segments[-1][:-4]

    if len(segments) < 2 or any(
        s in (".", "..") or not _SEGMENT_RE.match(s) for s in segments
    ):
        raise InvalidRepoURL("Expected a URL like https://github.com/<owner>/<repo>.")

    return f"https://{host}/{'/'.join(segments)}.git"


# ---------------------------------------------------------------------------
# git plumbing
# ---------------------------------------------------------------------------
def _base_env() -> dict[str, str]:
    """Environment for every git call: no prompts, https only, no user config."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",         # never block asking for credentials
            "GIT_ALLOW_PROTOCOL": "https",      # blocks ext::, file://, ssh://
            "GIT_CONFIG_GLOBAL": os.devnull,    # ignore user config (insteadOf, helpers)
            "LC_ALL": "C",                      # stable stderr for classification
        }
    )
    return env


def _auth_env(host: str, token: str) -> dict[str, str]:
    """Pass the token as an HTTP header through env vars.

    Unlike `git clone https://token@host/...` or `-c http.extraHeader=...`,
    this does not show up in the process list and is not written to
    .git/config.
    """
    user = "x-access-token" if host == "github.com" else "oauth2"
    basic = base64.b64encode(f"{user}:{token}".encode()).decode()
    env = _base_env()
    env.update(
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}",
        }
    )
    return env


def _git(
    args: list[str],
    *,
    env: dict[str, str],
    cwd: Path | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _scrub(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text.strip()[:_ERROR_DETAIL_MAX]


def _classify(stderr: str) -> GitExtractError:
    low = stderr.lower()
    if any(
        marker in low
        for marker in (
            "authentication failed",
            "could not read username",
            "invalid username or password",
            "access denied",
            "terminal prompts disabled",
            "error: 403",
        )
    ):
        return CloneAuthError(
            "Repository requires authentication (or does not exist). "
            "Provide a token with read access."
        )
    if "repository not found" in low or "returned error: 404" in low:
        return RepoNotFound("Repository not found.")
    return GitExtractError(f"git clone failed: {stderr}")


def _tmp_root() -> Path:
    root = settings.tmp_dir or (settings.base_dir / "tmp")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _clone_blocking(clone_url: str, token: str | None, dest: Path) -> None:
    host = urlsplit(clone_url).hostname or ""
    env = _auth_env(host, token) if token else _base_env()
    args = [
        "-c", "credential.helper=",       # no system/OS credential managers
        "-c", "core.symlinks=false",      # symlinks become plain files: a hostile
                                          # repo cannot point collectors at /etc/...
        "-c", "http.lowSpeedLimit=1000",  # abort stalled transfers
        "-c", "http.lowSpeedTime=30",
        "clone", "--quiet", "--", clone_url, str(dest),
    ]
    try:
        proc = _git(args, env=env, timeout=settings.github_clone_timeout)
    except FileNotFoundError as exc:
        raise GitNotInstalled("The 'git' executable was not found on the server.") from exc

    if proc.returncode != 0:
        raise _classify(_scrub(proc.stderr, [token] if token else []))


def _inspect(dest: Path) -> dict[str, object]:
    env = _base_env()

    def run(*args: str) -> str | None:
        proc = _git(list(args), env=env, cwd=dest, timeout=60)
        return proc.stdout.strip() if proc.returncode == 0 else None

    head = run("rev-parse", "HEAD")
    if not head:
        raise EmptyRepository("The repository has no commits.")

    files = _git(["ls-files", "-z"], env=env, cwd=dest, timeout=60)
    return {
        "head_sha": head,
        "branch": run("symbolic-ref", "--short", "-q", "HEAD"),
        "commits_total": int(run("rev-list", "--count", "HEAD") or 0),
        "is_shallow": run("rev-parse", "--is-shallow-repository") == "true",
        "tracked_files": files.stdout.count("\0"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def clone_repository(url: str, token: str | None = None) -> CloneResult:
    """Clone `url` (full history) into <tmp_dir>/<scan_id> and return metadata.

    Runs git in a worker thread so the event loop is never blocked. This also
    works on Windows, where asyncio subprocesses are not available with the
    selector loop that uvicorn --reload uses.

    Raises a GitExtractError subclass on any failure. The partial clone is
    removed before the exception propagates.
    """
    clone_url = normalise_repo_url(url)
    scan_id = uuid.uuid4().hex
    dest = _tmp_root() / scan_id

    def _work() -> CloneResult:
        try:
            _clone_blocking(clone_url, token, dest)
            info = _inspect(dest)
        except subprocess.TimeoutExpired as exc:
            cleanup_dir(dest)
            raise CloneTimeout("Timed out while cloning or inspecting the repository.") from exc
        except Exception:
            cleanup_dir(dest)
            raise

        return CloneResult(
            scan_id=scan_id,
            path=dest,
            repo_url=clone_url,
            head_sha=str(info["head_sha"]),
            branch=info["branch"],  # type: ignore[arg-type]
            commits_total=int(info["commits_total"]),  # type: ignore[arg-type]
            is_shallow=bool(info["is_shallow"]),
            tracked_files=int(info["tracked_files"]),  # type: ignore[arg-type]
            exceeds_poc_limit=int(info["tracked_files"]) > settings.poc_max_files,  # type: ignore[arg-type]
        )

    logger.info("Cloning %s into tmp/%s", clone_url, scan_id)
    return await asyncio.to_thread(_work)


def _make_writable_and_retry(func, path, _exc) -> None:
    """rmtree error handler: .git objects are read-only on Windows."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def cleanup_dir(path: Path) -> None:
    """Delete a clone. Refuses to touch anything outside the tmp dir."""
    root = _tmp_root().resolve()
    target = Path(path).resolve()
    if root not in target.parents:
        raise ValueError(f"Refusing to delete a path outside the tmp dir: {target}")
    if not target.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(target, onexc=_make_writable_and_retry)
    else:
        shutil.rmtree(target, onerror=_make_writable_and_retry)
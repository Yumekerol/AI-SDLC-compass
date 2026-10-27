"""
Repo acquisition for the Agent Service.

The scanner service clones a repo into its own container's filesystem to run
its metrics, and the old backend ingestion flow did the same into the
backend's — neither is shared with this service (confirmed: no shared
volume in docker-compose.yml). So the agents service clones its own copy,
mirroring that same established pattern rather than depending on either of
them: given a git_url (+ optional access_token for private repos), produce a
real, readable directory under `settings.workspaces_dir`.

One clone per session_id, reused across the whole pipeline (4 specialists)
and later advisor-chat calls for that same session — never re-cloned once
present, so a resumed pipeline turn or a chat message after the report is
ready both just read what's already on disk.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from .config import settings

logger = logging.getLogger(__name__)


def _inject_token(git_url: str, token: str) -> str:
    """https://github.com/org/repo.git -> https://<token>@github.com/org/repo.git"""
    parsed = urlparse(git_url)
    if parsed.scheme not in ("http", "https"):
        return git_url
    netloc = f"{token}@{parsed.netloc}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


async def ensure_repo(session_id: str, git_url: str, access_token: str | None = None) -> Path:
    """Return a readable local directory for `git_url`, cloning it under
    `settings.workspaces_dir/<session_id>` if it isn't already there."""
    dest = settings.workspaces_dir / session_id

    if (dest / ".git").exists():
        logger.info("Reusing existing clone for session %s at %s", session_id, dest)
        return dest

    if dest.exists():
        # A partial/failed clone from an earlier attempt — start clean.
        import shutil

        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)

    clone_url = _inject_token(git_url, access_token) if access_token else git_url
    logger.info("Cloning %s for session %s", git_url, session_id)

    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "1", clone_url, str(dest),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=settings.git_clone_timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"Git clone timed out after {settings.git_clone_timeout}s")

    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace")
        if access_token:
            err_msg = err_msg.replace(access_token, "***")
        raise RuntimeError(f"Git clone failed: {err_msg.strip()}")

    return dest

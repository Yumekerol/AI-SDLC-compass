"""
ZIP Archive Ingestion Module

Safely extracts uploaded ZIP files into a local workspace directory,
preventing Zip Slip vulnerabilities and adjusting for top-level wrapping folders.
"""

from __future__ import annotations

import logging
import shutil
import zipfile
from pathlib import Path

from ..models.scanner_output import RepositoryInfo

logger = logging.getLogger(__name__)


def is_safe_zip_path(target_dir: Path, path: Path) -> bool:
    """Ensure extracted file path stays within target_dir (prevent Zip Slip)."""
    try:
        resolved_target = target_dir.resolve()
        resolved_path = path.resolve()
        return resolved_target in resolved_path.parents or resolved_target == resolved_path
    except Exception:
        return False


def extract_zip_archive(
    zip_path: Path,
    target_dir: Path,
    original_filename: str = "uploaded_archive.zip",
) -> tuple[Path, RepositoryInfo]:
    """
    Safely extract a ZIP archive into target_dir.

    Returns:
    - Path to the extracted workspace root
    - RepositoryInfo model
    """
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extracting {zip_path} to {target_dir}")

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target_path = target_dir / member.filename
            if not is_safe_zip_path(target_dir, target_path):
                raise ValueError(f"Unsafe ZIP archive entry detected: {member.filename}")
            zf.extract(member, target_dir)

    # Check if archive unpacked into a single top-level directory
    entries = [e for e in target_dir.iterdir() if not e.name.startswith("__MACOSX")]
    workspace_root = target_dir
    if len(entries) == 1 and entries[0].is_dir():
        workspace_root = entries[0]

    repo_name = Path(original_filename).stem

    repo_info = RepositoryInfo(
        name=repo_name,
        branch=None,
        commit_hash=None,
        source_type="zip",
        clone_url=None,
    )

    return workspace_root, repo_info

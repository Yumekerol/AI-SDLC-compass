"""
Codebase Inspection Tools for LangChain / LangGraph Agent

Provides safe filesystem inspection tools (read_file, list_files, directory_tree)
scoped to the target repository directory, plus auxiliary utilities.
"""

from __future__ import annotations

import contextvars
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

# Context variable to dynamically scope filesystem tools to the target repository
_repo_root_var: contextvars.ContextVar[Path] = contextvars.ContextVar(
    "_repo_root_var", default=Path.cwd().resolve()
)

IGNORE = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea"}
MAX_ENTRIES = 200
MAX_CHARS = 80000


def set_current_repo_root(root: Path) -> None:
    """Set the root directory that the filesystem tools are restricted to."""
    _repo_root_var.set(root.resolve())


def get_current_repo_root() -> Path:
    """Get the active repository root directory."""
    return _repo_root_var.get()


def _safe_path(p: str) -> Path:
    """Ensure path resolves within the allowed repository root directory."""
    root = get_current_repo_root()
    path = (root / p).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path is outside the allowed directory: {p}")
    return path


def _entries(d: Path) -> list[Path]:
    items = [p for p in d.iterdir() if p.name not in IGNORE]
    return sorted(items, key=lambda p: (not p.is_dir(), p.name.lower()))  # folders first


@tool
def list_files(directory: str = ".") -> str:
    """List the contents of ONE folder (not its subfolders).
    Folders end with '/'. Use this when the user asks what is in a specific folder.
    For a recursive overview or to find where something is, use directory_tree instead.
    """
    try:
        d = _safe_path(directory)
        items = _entries(d)
    except (FileNotFoundError, NotADirectoryError, PermissionError, ValueError) as e:
        return f"Error: {e}"
    if not items:
        return "(empty folder)"
    lines = [p.name + ("/" if p.is_dir() else "") for p in items[:MAX_ENTRIES]]
    if len(items) > MAX_ENTRIES:
        lines.append(f"...[{len(items) - MAX_ENTRIES} more not shown]")
    return "\n".join(lines)


@tool
def directory_tree(directory: str = ".", max_depth: int = 2) -> str:
    """Show a recursive tree of a folder, up to max_depth levels (default 2, max 4).
    Use this to get an overview of the project layout or to find where a file or
    folder is. To see everything in one specific folder, use list_files instead.
    """
    try:
        root = _safe_path(directory)
        if not root.is_dir():
            return f"Error: not a directory: {directory}"
    except ValueError as e:
        return f"Error: {e}"

    max_depth = max(1, min(max_depth, 4))
    lines = [f"{root.name or str(root)}/"]
    count = 0

    def walk(d: Path, prefix: str, depth: int):
        nonlocal count
        try:
            items = _entries(d)
        except PermissionError:
            return
        for i, p in enumerate(items):
            if count >= MAX_ENTRIES:
                return
            last = i == len(items) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{p.name}{'/' if p.is_dir() else ''}")
            count += 1
            if p.is_dir() and not p.is_symlink() and depth < max_depth:
                walk(p, prefix + ("    " if last else "│   "), depth + 1)

    walk(root, "", 1)
    if count >= MAX_ENTRIES:
        lines.append("...[truncated; call again with a subfolder or a smaller max_depth]")
    return "\n".join(lines)


@tool
def current_time() -> str:
    """Return the current local date and time.
    Use this when the user asks what time or date it is.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def word_count(text: str) -> int:
    """Count the number of words in a piece of text.
    Use this when the user asks how long a piece of writing is,
    or asks you to count the words in something they've shared.
    Returns the word count as an integer.
    """
    return len(text.split())


@tool
def read_file(filename: str) -> str:
    """Read a text file (path relative to the repository working directory).
    Long files are truncated. Use list_files or directory_tree first if unsure of the path.
    """
    try:
        text = _safe_path(filename).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: file not found: {filename}"
    except (UnicodeDecodeError, IsADirectoryError, PermissionError, ValueError) as e:
        return f"Error: {e}"
    if len(text) > MAX_CHARS:
        return text[:MAX_CHARS] + f"\n...[truncated, {len(text)} chars total]"
    return text


@tool
def current_dir() -> str:
    """Return the current repository directory as a string.
    Use this whenever you need to know the base repository directory.
    """
    return str(get_current_repo_root())


TOOLS = [current_time, word_count, read_file, list_files, current_dir, directory_tree]

"""
Codebase Inspection Tools for LangChain / LangGraph Agents

Provides safe filesystem inspection tools (read_file, list_files, directory_tree,
grep_search) plus scanner-signal access (get_scan), all scoped to one
`RunContext` per call via `build_tools()`. There is no shared global state here:
each pipeline run gets its own bound copies, so two runs targeting different
repositories can never cross-contaminate each other's "current repo" (the
failure mode of the previous `contextvars`-based version).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from .context import RunContext

IGNORE = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea"}
MAX_ENTRIES = 200
MAX_CHARS = 80000
MAX_GREP_MATCHES = 100
GREP_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".woff", ".woff2"}


def _safe_path(ctx: RunContext, p: str) -> Path:
    """Ensure path resolves within ctx.root."""
    path = (ctx.root / p).resolve()
    if not path.is_relative_to(ctx.root):
        raise ValueError(f"Path is outside the allowed directory: {p}")
    return path


def _entries(d: Path) -> list[Path]:
    items = [p for p in d.iterdir() if p.name not in IGNORE]
    return sorted(items, key=lambda p: (not p.is_dir(), p.name.lower()))  # folders first


def build_tools(ctx: RunContext) -> dict[str, BaseTool]:
    """Build the full set of filesystem/scan tools bound to one RunContext.

    A specialist only gets the subset named in its SpecialistSpec.tool_names;
    `note` and `ask_user` are added separately by the runner regardless of
    tool_names, since every specialist needs both.
    """

    @tool
    def list_files(directory: str = ".") -> str:
        """List the contents of ONE folder (not its subfolders).
        Folders end with '/'. Use this when the user asks what is in a specific folder.
        For a recursive overview or to find where something is, use directory_tree instead.
        """
        try:
            d = _safe_path(ctx, directory)
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
            root = _safe_path(ctx, directory)
            if not root.is_dir():
                return f"Error: not a directory: {directory}"
        except ValueError as e:
            return f"Error: {e}"

        depth_cap = max(1, min(max_depth, 4))
        lines = [f"{root.name or str(root)}/"]
        count = 0

        def walk(d: Path, prefix: str, depth: int) -> None:
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
                if p.is_dir() and not p.is_symlink() and depth < depth_cap:
                    walk(p, prefix + ("    " if last else "│   "), depth + 1)

        walk(root, "", 1)
        if count >= MAX_ENTRIES:
            lines.append("...[truncated; call again with a subfolder or a smaller max_depth]")
        return "\n".join(lines)

    @tool
    def read_file(filename: str) -> str:
        """Read a text file (path relative to the repository root).
        Long files are truncated. Use list_files or directory_tree first if unsure of the path.
        """
        try:
            text = _safe_path(ctx, filename).read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"Error: file not found: {filename}"
        except (UnicodeDecodeError, IsADirectoryError, PermissionError, ValueError) as e:
            return f"Error: {e}"
        if len(text) > MAX_CHARS:
            return text[:MAX_CHARS] + f"\n...[truncated, {len(text)} chars total]"
        return text

    @tool
    def grep_search(pattern: str, glob: str = "**/*") -> str:
        """Search file contents for a regular expression under the repository root.
        `glob` narrows which files are scanned (default: every file). Returns up to
        100 matches as "path:line: text". Use this to find where something is defined
        or referenced, rather than reading files one by one.
        """
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Error: invalid pattern: {e}"

        matches: list[str] = []
        try:
            candidates = list(ctx.root.glob(glob))
        except ValueError as e:
            return f"Error: invalid glob: {e}"

        for path in candidates:
            if len(matches) >= MAX_GREP_MATCHES:
                break
            if not path.is_file() or path.suffix.lower() in GREP_SKIP_SUFFIXES:
                continue
            if any(part in IGNORE for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            rel = path.relative_to(ctx.root)
            for lineno, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    matches.append(f"{rel}:{lineno}: {line.strip()[:200]}")
                    if len(matches) >= MAX_GREP_MATCHES:
                        break

        if not matches:
            return "(no matches)"
        if len(matches) >= MAX_GREP_MATCHES:
            matches.append(f"...[stopped at {MAX_GREP_MATCHES} matches; narrow `pattern` or `glob`]")
        return "\n".join(matches)

    @tool
    def get_scan() -> str:
        """Return the deterministic scanner's signal output for this repository
        (languages, size/structure, stack/tooling, CI/CD, quality indicators,
        warnings/gaps) as JSON. Check this before re-deriving the same facts by
        reading files yourself.
        """
        if not ctx.scan_output:
            return "(no scanner output available for this run)"
        return json.dumps(ctx.scan_output, default=str)

    @tool
    def current_time() -> str:
        """Return the current local date and time."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @tool
    def current_dir() -> str:
        """Return the repository root directory as a string."""
        return str(ctx.root)

    return {
        "list_files": list_files,
        "directory_tree": directory_tree,
        "read_file": read_file,
        "grep_search": grep_search,
        "get_scan": get_scan,
        "current_time": current_time,
        "current_dir": current_dir,
    }

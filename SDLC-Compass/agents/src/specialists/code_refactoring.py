from pathlib import Path

from .base import SpecialistSpec

SPEC = SpecialistSpec(
    role="code_refactoring",
    label="Code & Refactoring",
    prompt_path=Path(__file__).with_name("prompts") / "code_refactoring.md",
    tool_names=["get_scan", "read_file", "list_files", "directory_tree", "grep_search"],
    max_tool_calls=25,
)

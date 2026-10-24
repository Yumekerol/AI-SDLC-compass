from pathlib import Path

from .base import SpecialistSpec

SPEC = SpecialistSpec(
    role="devops_monitoring",
    label="DevOps & Monitoring",
    prompt_path=Path(__file__).with_name("prompts") / "devops_monitoring.md",
    tool_names=["get_scan", "read_file", "list_files", "directory_tree", "grep_search"],
    max_tool_calls=25,
)

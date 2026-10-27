from __future__ import annotations

import logging

from pathlib import Path, PurePosixPath
from typing import Any

from .__common__ import _resolve_files, LANGUAGE_BY_EXTENSION, _PathFilter, _relative_path, _is_test_file, _read_text, _count_loc

logger = logging.getLogger(__name__)


def collect_size_and_structure(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    all_files = _resolve_files(repo_path, files)

    code_files = 0
    code_files_read = 0
    unreadable = 0
    loc_total = 0
    module_dirs: set[str] = set()

    for path in all_files:
        suffix = path.suffix.lower()
        if suffix not in LANGUAGE_BY_EXTENSION or _PathFilter.is_generated(path.name):
            continue
        code_files += 1

        relative = _relative_path(repo_path, path)
        if not _is_test_file(relative):
            # "." representa a raiz do repositório
            module_dirs.add(PurePosixPath(relative).parent.as_posix())

        text = _read_text(path)
        if text is None:
            unreadable += 1
            continue
        loc_total += _count_loc(text, suffix)
        code_files_read += 1

    return {
        "total_files": len(all_files),
        "code_files": code_files,
        "loc_estimate": loc_total,
        "avg_file_size_loc": round(loc_total / code_files_read, 2) if code_files_read else None,
        "module_estimate": len(module_dirs),
        "code_files_unreadable": unreadable,
        "limitations": (
            "total_files conta os ficheiros que passam os filtros das Settings (não o total "
            "bruto do repositório). LOC = linhas não vazias e sem comentário de linha, só em "
            "ficheiros de código reconhecidos (inclui testes). Módulo = diretório com pelo "
            "menos um ficheiro de código que não seja de teste."
        ),
    }


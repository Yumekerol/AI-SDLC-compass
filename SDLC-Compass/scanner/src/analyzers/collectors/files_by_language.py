from __future__ import annotations

import logging

from collections import Counter
from pathlib import Path
from typing import Any

from .__common__ import LANGUAGE_BY_EXTENSION, _resolve_files, _count_loc

logger = logging.getLogger(__name__)


def collect_files_by_language(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    files_by_language: Counter[str] = Counter()
    loc_by_language: Counter[str] = Counter()
    files_of_code: list[str] = []

    for path in _resolve_files(repo_path, files):
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())

        if not language:
            continue

        files_by_language[language] += 1
        files_of_code.append(str(path.relative_to(repo_path)))

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            loc_by_language[language] += _count_loc(text, path.suffix.lower())
        except OSError:
            continue

    total_files = sum(files_by_language.values())
    total_loc = sum(loc_by_language.values())

    return {
        "files_by_language": dict(files_by_language.most_common()),
        "share_by_language": {
            lang: round(count / total_files, 4)
            for lang, count in files_by_language.most_common()
        } if total_files else {},
        "loc_by_language": dict(loc_by_language.most_common()),
        "loc_share_by_language": {
            lang: round(count / total_loc, 4)
            for lang, count in loc_by_language.most_common()
        } if total_loc else {},
        "recognized_source_files": total_files,
        "total_loc": total_loc,
        "files_of_code": files_of_code,
        "limitations": (
            "Classificação por extensão. LOC conta linhas não vazias "
            "que não começam com os prefixos de comentário definidos "
            "na heurística; não identifica extensões desconhecidas."
        ),
    }


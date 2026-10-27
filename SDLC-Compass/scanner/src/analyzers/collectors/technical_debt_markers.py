from __future__ import annotations

import logging
import re

from collections import Counter
from pathlib import Path
from typing import Any

from .__common__ import _resolve_files, _PathFilter, _read_text, _relative_path, MAX_LISTED_ITEMS, TOP_N_DEFAULT

logger = logging.getLogger(__name__)



TECH_DEBT_MARKERS = re.compile(r"\b(TODO|FIXME|HACK|XXX|WORKAROUND)\b")
MAX_LINE_LENGTH_SCANNED = 2000    # ignora linhas gigantes (minificados/dados)


def collect_technical_debt_markers(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    per_file: Counter[str] = Counter()
    occurrences: list[dict[str, Any]] = []

    for path in _resolve_files(repo_path, files):
        if _PathFilter.is_generated(path.name):
            continue
        text = _read_text(path)
        if text is None:
            continue

        relative = _relative_path(repo_path, path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if len(line) > MAX_LINE_LENGTH_SCANNED:
                continue
            for match in TECH_DEBT_MARKERS.finditer(line):
                marker = match.group(1)
                counts[marker] += 1
                per_file[relative] += 1
                if len(occurrences) < MAX_LISTED_ITEMS:
                    occurrences.append({"marker": marker, "file": relative, "line": line_number})

    return {
        "marker_counts": dict(counts),
        "total_markers": sum(counts.values()),
        "files_with_markers": len(per_file),
        "top_files": [{"file": f, "markers": n} for f, n in per_file.most_common(TOP_N_DEFAULT)],
        "occurrences": occurrences,
        "occurrences_truncated": sum(counts.values()) > MAX_LISTED_ITEMS,
        "limitations": (
            "Apenas ficheiro e linha (o conteúdo das linhas não é devolvido). Marcadores em "
            "maiúsculas; não são uma medida completa da dívida técnica."
        ),
    }


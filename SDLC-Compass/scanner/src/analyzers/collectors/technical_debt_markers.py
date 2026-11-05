from __future__ import annotations

import logging
import re

from collections import Counter
from pathlib import Path
from typing import Any

from .__common__ import (
    _resolve_files,
    _PathFilter,
    _read_text,
    _relative_path,
    _is_test_config_file,
    MAX_LISTED_ITEMS,
    TOP_N_DEFAULT,
)

logger = logging.getLogger(__name__)


TECH_DEBT_MARKERS = re.compile(r"\b(TODO|FIXME|HACK|XXX|WORKAROUND)\b")
MAX_LINE_LENGTH_SCANNED = 2000    # ignora linhas gigantes (minificados/dados)


def collect_technical_debt_markers(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    per_file: Counter[str] = Counter()
    occurrences: list[dict[str, Any]] = []
    config_files_skipped = 0

    for path in _resolve_files(repo_path, files):
        if _PathFilter.is_generated(path.name):
            continue

        relative = _relative_path(repo_path, path)

        # Configs de testes (jest.config.js, jest-e2e.js...) são boilerplate copiado
        if _is_test_config_file(relative):
            config_files_skipped += 1
            continue

        text = _read_text(path)
        if text is None:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if len(line) > MAX_LINE_LENGTH_SCANNED:
                continue
            for match in TECH_DEBT_MARKERS.finditer(line):
                marker = match.group(1)
                counts[marker] += 1
                per_file[relative] += 1
                occurrences.append({"marker": marker, "file": relative, "line": line_number})

    # Ordenar tudo ANTES de cortar, para o resultado ser determinístico
    occurrences.sort(key=lambda x: (x["file"], x["line"], x["marker"]))
    top_files = sorted(per_file.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N_DEFAULT]

    return {
        "marker_counts": dict(sorted(counts.items())),
        "total_markers": sum(counts.values()),
        "files_with_markers": len(per_file),
        "config_files_skipped": config_files_skipped,
        "top_files": [{"file": f, "markers": n} for f, n in top_files],
        "occurrences": occurrences[:MAX_LISTED_ITEMS],
        "occurrences_truncated": len(occurrences) > MAX_LISTED_ITEMS,
        "limitations": (
            "Apenas ficheiro e linha (o conteúdo das linhas não é devolvido). Marcadores em "
            "maiúsculas; não são uma medida completa da dívida técnica. Ficheiros de "
            "configuração de testes (jest, vitest, etc.) são ignorados por serem boilerplate "
            "copiado entre projetos."
        ),
    }
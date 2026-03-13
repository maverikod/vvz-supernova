"""
Clean atomic lines and write data/ CSVs.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads raw NIST ASD HTML from raw/atomic_lines_raw/; parses tables; normalizes
columns per IMPLEMENTATION_SPEC; computes frequency_hz; cleans numerics;
deduplicates; writes atomic_lines_clean.csv, atomic_lines_by_element.csv,
atomic_transition_summary.csv. When raw has no parseable line data, writes
schema-only CSVs so downstream can run.
Run: python scripts/clean_atomic_data.py
"""

from __future__ import annotations

import math
from pathlib import Path

from supernova_atomic.atomic_schema import (
    ATOMIC_LINE_COLUMNS,
    SUMMARY_COLUMNS,
    build_summary_rows,
    write_csv,
)
from supernova_atomic.nist_parser import read_raw_atomic_lines


def project_root() -> Path:
    """Project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def main() -> None:
    """Read raw atomic data, clean, dedupe, write data/ CSVs and summary."""
    root = project_root()
    raw_dir = root / "raw" / "atomic_lines_raw"
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    lines = read_raw_atomic_lines(raw_dir)

    def _norm(v: object) -> str:
        if v is None:
            return "nan"
        if isinstance(v, float) and math.isnan(v):
            return "nan"
        return str(v)

    seen: set[tuple[tuple[str, str], ...]] = set()
    unique: list[dict] = []
    for row in lines:
        key = tuple((k, _norm(v)) for k, v in sorted(row.items()))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    lines = unique

    write_csv(data_dir / "atomic_lines_clean.csv", ATOMIC_LINE_COLUMNS, lines)
    by_el = sorted(
        lines,
        key=lambda r: (str(r.get("element", "")), str(r.get("ion_state", ""))),
    )
    write_csv(data_dir / "atomic_lines_by_element.csv", ATOMIC_LINE_COLUMNS, by_el)
    summary_rows = build_summary_rows(lines)
    write_csv(data_dir / "atomic_transition_summary.csv", SUMMARY_COLUMNS, summary_rows)


if __name__ == "__main__":
    main()

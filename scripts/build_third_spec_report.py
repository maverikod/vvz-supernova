"""
Build Third spec reports: data_report.md, missingness_report.csv, source_manifest.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Writes report/ with load/drop/remain counts and missingness.
Run: python scripts/build_third_spec_report.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _count_csv_rows(path: Path) -> int:
    """Return number of data rows (excluding header)."""
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def _count_non_empty_column(path: Path, column: str) -> int:
    """Count rows where column is non-empty and not 'nan'."""
    if not path.exists():
        return 0
    count = 0
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = (row.get(column) or "").strip().lower()
            if v and v not in ("nan", ""):
                count += 1
    return count


def main() -> None:
    """Build report/data_report.md, missingness_report.csv, source_manifest.csv."""
    root = project_root()
    data_dir = root / "data"
    raw_dir = root / "raw"
    report_dir = root / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    n_atomic_clean = _count_csv_rows(data_dir / "atomic_lines_clean.csv")
    n_atomic_events = _count_csv_rows(data_dir / "atomic_transition_events.csv")
    n_sn_summary = _count_csv_rows(data_dir / "supernova_event_summary.csv")
    n_sn_events = _count_csv_rows(data_dir / "supernova_transient_events.csv")
    n_cluster = _count_csv_rows(data_dir / "cluster_ready_events.csv")

    # Source manifest from raw manifests
    source_rows: list[dict[str, str]] = []
    atomic_manifest_path = raw_dir / "atomic_lines_raw" / "manifest.json"
    if atomic_manifest_path.exists():
        try:
            m = json.loads(atomic_manifest_path.read_text(encoding="utf-8"))
            source_rows.append(
                {
                    "source": m.get("source_catalog", "NIST ASD"),
                    "url": m.get("source_url", ""),
                    "download_date_utc": m.get("download_date_utc", ""),
                    "files_count": str(len(m.get("files", []))),
                    "note": "atomic lines",
                }
            )
        except (json.JSONDecodeError, OSError):
            pass
    sn_manifest_path = raw_dir / "supernova_raw" / "manifest.json"
    if sn_manifest_path.exists():
        try:
            m = json.loads(sn_manifest_path.read_text(encoding="utf-8"))
            for s in m.get("sources_used", []):
                source_rows.append(
                    {
                        "source": s.get("name", ""),
                        "url": s.get("url", ""),
                        "download_date_utc": m.get("download_date_utc", ""),
                        "files_count": "1",
                        "note": s.get("raw_file", ""),
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass

    with (report_dir / "source_manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=["source", "url", "download_date_utc", "files_count", "note"],
        )
        w.writeheader()
        w.writerows(source_rows)

    # Missingness: atomic_transition_events and supernova_transient_events
    missing_rows: list[dict[str, str]] = []
    for name, path in [
        ("atomic_transition_events", data_dir / "atomic_transition_events.csv"),
        ("supernova_transient_events", data_dir / "supernova_transient_events.csv"),
    ]:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            total = sum(1 for _ in reader)
        for col in cols:
            non_empty = _count_non_empty_column(path, col)
            missing_rows.append(
                {
                    "dataset": name,
                    "column": col,
                    "count_non_empty": str(non_empty),
                    "count_empty": str(total - non_empty),
                }
            )

    with (report_dir / "missingness_report.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=["dataset", "column", "count_non_empty", "count_empty"],
        )
        w.writeheader()
        w.writerows(missing_rows)

    # data_report.md
    dropped_atomic = n_atomic_clean - n_atomic_events
    dropped_sn = n_sn_summary - n_sn_events
    lines = [
        "# Third tech spec — data report",
        "",
        "## Counts",
        "",
        "| Stage | Loaded | Dropped | Remaining |",
        "|-------|--------|---------|-----------|",
        f"| atomic_lines_clean | {n_atomic_clean} | — | {n_atomic_clean} |",
        f"| atomic_transition_events | {n_atomic_clean} | {dropped_atomic} | "
        f"{n_atomic_events} |",
        f"| supernova_event_summary | {n_sn_summary} | — | {n_sn_summary} |",
        f"| supernova_transient_events | {n_sn_summary} | {dropped_sn} | "
        f"{n_sn_events} |",
        f"| cluster_ready_events | — | — | {n_cluster} |",
        "",
        "## Drop reasons",
        "",
        "- **Atomic:** Rows without valid wavelength or Aki are dropped.",
        "- **Supernova:** Events without peak_abs_mag are dropped.",
        "",
        "## Field presence",
        "",
        "See missingness_report.csv for per-column non-empty vs empty.",
        "",
    ]
    (report_dir / "data_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

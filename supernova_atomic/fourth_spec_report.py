"""
Fourth-spec report logic: completeness counts, missingness, source manifest,
verification.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Used by scripts/build_fourth_spec_report.py. Per §10.4: observable completeness,
transition-passport completeness, invalidated rows, c_theta_pending.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

OBSERVABLE_ARTIFACTS = [
    "atomic_lines_clean.csv",
    "atomic_lines_by_element.csv",
    "atomic_transition_summary.csv",
    "atomic_transition_events.csv",
    "astrophysical_transient_catalog_clean.csv",
    "astrophysical_transient_lightcurves_long.csv",
    "astrophysical_transient_events.csv",
]
PASSPORT_ARTIFACTS = [
    "atomic_transition_passports.csv",
    "astrophysical_flash_transition_passports.csv",
    "unified_transition_passports.csv",
]
CLUSTER_ARTIFACT = "cluster_ready_transition_passports.csv"
PASSPORT_STATUS_COL = "passport_status"
C_THETA_PENDING = "c_theta_pending"


def count_csv_rows(path: Path) -> int:
    """Return number of data rows (excluding header)."""
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def count_non_empty_column(path: Path, column: str) -> int:
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


def count_status(path: Path, status_col: str, status_value: str) -> int:
    """Count rows where status_col equals status_value."""
    if not path.exists():
        return 0
    value_norm = status_value.strip().lower()
    count = 0
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = (row.get(status_col) or "").strip().lower()
            if v == value_norm:
                count += 1
    return count


def observable_completeness(data_dir: Path) -> dict[str, int]:
    """Row counts for each observable artifact; missing -> 0."""
    return {name: count_csv_rows(data_dir / name) for name in OBSERVABLE_ARTIFACTS}


def passport_completeness(
    data_dir: Path,
) -> tuple[dict[str, int], dict[str, int]]:
    """Row counts and c_theta_pending counts. Returns (row_counts, c_theta_counts)."""
    row_counts: dict[str, int] = {}
    c_theta_counts: dict[str, int] = {}
    for name in PASSPORT_ARTIFACTS + [CLUSTER_ARTIFACT]:
        p = data_dir / name
        row_counts[name] = count_csv_rows(p)
        c_theta_counts[name] = count_status(p, PASSPORT_STATUS_COL, C_THETA_PENDING)
    return row_counts, c_theta_counts


def invalidated_rows(data_dir: Path) -> tuple[int, int]:
    """(atomic_dropped, astro_dropped) during event->passport translation."""
    n_ev_atomic = count_csv_rows(data_dir / "atomic_transition_events.csv")
    n_ev_astro = count_csv_rows(data_dir / "astrophysical_transient_events.csv")
    n_pass_atomic = count_csv_rows(data_dir / "atomic_transition_passports.csv")
    n_pass_astro = count_csv_rows(
        data_dir / "astrophysical_flash_transition_passports.csv"
    )
    atomic_dropped = max(0, n_ev_atomic - n_pass_atomic) if n_ev_atomic else 0
    astro_dropped = max(0, n_ev_astro - n_pass_astro) if n_ev_astro else 0
    return atomic_dropped, astro_dropped


def _manifest_dataset_id(m: dict, default: str) -> str:
    """Extract dataset identifier from manifest."""
    if m.get("files"):
        return str(len(m["files"])) + "_files"
    return str(m.get("dataset_id", default))


def source_manifest_rows(raw_dir: Path) -> list[dict[str, str]]:
    """Build source_manifest rows from raw manifests per §12."""
    rows: list[dict[str, str]] = []
    atomic_manifest = raw_dir / "atomic_lines_raw" / "manifest.json"
    if atomic_manifest.exists():
        try:
            m = json.loads(atomic_manifest.read_text(encoding="utf-8"))
            rows.append(
                {
                    "source": m.get("source_catalog", "NIST ASD"),
                    "url": m.get("source_url", ""),
                    "download_date_utc": m.get("download_date_utc", ""),
                    "dataset_id": _manifest_dataset_id(m, "atomic"),
                    "note": "atomic lines",
                }
            )
        except (json.JSONDecodeError, OSError):
            pass
    for subdir in ("astrophysical_transient_raw", "supernova_raw"):
        astro_manifest = raw_dir / subdir / "manifest.json"
        if not astro_manifest.exists():
            continue
        try:
            m = json.loads(astro_manifest.read_text(encoding="utf-8"))
            download_date = m.get("download_date_utc", "")
            for s in m.get("sources_used", []):
                rows.append(
                    {
                        "source": s.get("name", ""),
                        "url": s.get("url", ""),
                        "download_date_utc": download_date,
                        "dataset_id": s.get("raw_file", "") or subdir,
                        "note": s.get("raw_file", subdir),
                    }
                )
            if not m.get("sources_used"):
                rows.append(
                    {
                        "source": m.get("source_catalog", ""),
                        "url": m.get("source_url", ""),
                        "download_date_utc": download_date,
                        "dataset_id": subdir,
                        "note": subdir,
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass
        break
    return rows


def missingness_rows(data_dir: Path) -> list[dict[str, str]]:
    """Missingness per dataset/column for key tables."""
    missing: list[dict[str, str]] = []
    tables = (
        "atomic_transition_events.csv",
        "astrophysical_transient_events.csv",
        "atomic_transition_passports.csv",
        "astrophysical_flash_transition_passports.csv",
        "unified_transition_passports.csv",
        "cluster_ready_transition_passports.csv",
    )
    for filename in tables:
        path = data_dir / filename
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            total = sum(1 for _ in reader)
        dataset = filename.replace(".csv", "")
        for col in cols:
            non_empty = count_non_empty_column(path, col)
            missing.append(
                {
                    "dataset": dataset,
                    "column": col,
                    "count_non_empty": str(non_empty),
                    "count_empty": str(total - non_empty),
                }
            )
    return missing


def write_data_report(
    report_dir: Path,
    obs_counts: dict[str, int],
    pass_counts: dict[str, int],
    c_theta_counts: dict[str, int],
    invalidated_atomic: int,
    invalidated_astro: int,
) -> None:
    """Write report/data_report.md with four required sections per §10.4."""
    total_c_theta = sum(c_theta_counts.get(a, 0) for a in PASSPORT_ARTIFACTS)
    lines = [
        "# Fourth tech spec — data report",
        "",
        "## 1. Observable completeness",
        "",
        "Row counts for observable-domain artifacts (§10.1).",
        "",
        "| Artifact | Rows |",
        "|----------|------|",
    ]
    for name in OBSERVABLE_ARTIFACTS:
        lines.append(f"| {name} | {obs_counts.get(name, 0)} |")
    lines.extend(
        [
            "",
            "## 2. Transition-passport completeness",
            "",
            "Row counts and c_theta_pending counts for passport outputs "
            "(§10.2, §10.3).",
            "",
            "| Artifact | Rows | c_theta_pending |",
            "|----------|------|----------------|",
        ]
    )
    for name in PASSPORT_ARTIFACTS + [CLUSTER_ARTIFACT]:
        r, c = pass_counts.get(name, 0), c_theta_counts.get(name, 0)
        lines.append(f"| {name} | {r} | {c} |")
    lines.extend(
        [
            "",
            "## 3. Rows invalidated during transition-passport translation",
            "",
            "Rows dropped when building passports from events (no synthetic fill).",
            "",
            f"- **Atomic:** {invalidated_atomic} rows (atomic_transition_events → "
            "atomic_transition_passports).",
            f"- **Astrophysical:** {invalidated_astro} rows "
            "(astrophysical_transient_events → "
            "astrophysical_flash_transition_passports).",
            "",
            "## 4. Rows left in c_theta_pending",
            "",
            "Total passport rows with passport_status = c_theta_pending "
            f"(unified scope): {total_c_theta}.",
            "",
            "Per-file counts are in the transition-passport completeness table above.",
            "",
            "---",
            "",
            "**§13.11:** This report states what is observed (observable tables), "
            "what is inferred (passport tables), and what remains unavailable "
            "(c_theta_pending, invalidated rows).",
            "",
        ]
    )
    (report_dir / "data_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_completeness_verification(report_dir: Path) -> None:
    """Verify report files exist and data_report has four required sections."""
    data_report = report_dir / "data_report.md"
    missingness = report_dir / "missingness_report.csv"
    manifest = report_dir / "source_manifest.csv"
    if not report_dir.is_dir():
        print(
            "Completeness verification failed: report/ is not a directory.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not data_report.exists():
        print(
            "Completeness verification failed: report/data_report.md missing.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not missingness.exists():
        print(
            "Completeness verification failed: "
            "report/missingness_report.csv missing.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not manifest.exists():
        print(
            "Completeness verification failed: " "report/source_manifest.csv missing.",
            file=sys.stderr,
        )
        sys.exit(1)
    text = data_report.read_text(encoding="utf-8")
    for phrase in [
        "Observable completeness",
        "Transition-passport completeness",
        "Rows invalidated during",
        "Rows left in c_theta_pending",
    ]:
        if phrase not in text:
            print(
                "Completeness verification failed: data_report.md missing required "
                f"section '{phrase}'.",
                file=sys.stderr,
            )
            sys.exit(1)
    for path, expected_cols in [
        (missingness, ["dataset", "column", "count_non_empty", "count_empty"]),
        (manifest, ["source", "url", "download_date_utc", "dataset_id", "note"]),
    ]:
        with path.open(newline="", encoding="utf-8") as f:
            fn = (csv.DictReader(f).fieldnames) or []
            for c in expected_cols:
                if c not in fn:
                    print(
                        f"Completeness verification failed: {path.name} missing "
                        f"column '{c}'.",
                        file=sys.stderr,
                    )
                    sys.exit(1)


def run_fill_validation(report_dir: Path) -> None:
    """Emit message for each output CSV column that is completely empty."""
    for filename in ("missingness_report.csv", "source_manifest.csv"):
        path = report_dir / filename
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            rows = list(reader)
        for col in cols:
            if not col:
                continue
            if sum(1 for r in rows if (r.get(col) or "").strip()) == 0 and rows:
                print(
                    f"Column '{col}' in {path} is completely empty.",
                    file=sys.stderr,
                )

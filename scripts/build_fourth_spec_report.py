"""
Build fourth-spec reports: data_report.md, missingness_report.csv, source_manifest.csv.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads observable and transition-passport outputs per §10; produces report/ with
observable completeness, transition-passport completeness, invalidated rows,
c_theta_pending counts, and normalized-only run-mode context.

Run: python scripts/build_fourth_spec_report.py
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
MISSINGNESS_COLUMNS = ["dataset", "column", "count_non_empty", "count_empty"]
MANIFEST_COLUMNS = ["source", "url", "download_date_utc", "dataset_id", "note"]
C_THETA_PENDING = "c_theta_pending"


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def count_csv_rows(path: Path) -> int:
    """Return number of data rows in a CSV file."""
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def count_status(path: Path, status_value: str) -> int:
    """Count rows where passport_status equals the given value."""
    if not path.exists():
        return 0
    matched = 0
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("passport_status") or "").strip().lower() == status_value:
                matched += 1
    return matched


def count_non_empty_column(path: Path, column: str) -> int:
    """Count rows where the given column is non-empty and not `nan`."""
    if not path.exists():
        return 0
    matched = 0
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            value = (row.get(column) or "").strip().lower()
            if value and value != "nan":
                matched += 1
    return matched


def observable_completeness(data_dir: Path) -> dict[str, int]:
    """Return row counts for observable artifacts."""
    return {name: count_csv_rows(data_dir / name) for name in OBSERVABLE_ARTIFACTS}


def passport_completeness(data_dir: Path) -> tuple[dict[str, int], dict[str, int]]:
    """Return row counts and c_theta_pending counts for passport artifacts."""
    row_counts: dict[str, int] = {}
    c_theta_counts: dict[str, int] = {}
    for name in PASSPORT_ARTIFACTS + [CLUSTER_ARTIFACT]:
        path = data_dir / name
        row_counts[name] = count_csv_rows(path)
        c_theta_counts[name] = count_status(path, C_THETA_PENDING)
    return row_counts, c_theta_counts


def invalidated_rows(data_dir: Path) -> tuple[int, int]:
    """Return rows dropped during event -> passport translation."""
    atomic_dropped = max(
        0,
        count_csv_rows(data_dir / "atomic_transition_events.csv")
        - count_csv_rows(data_dir / "atomic_transition_passports.csv"),
    )
    astro_dropped = max(
        0,
        count_csv_rows(data_dir / "astrophysical_transient_events.csv")
        - count_csv_rows(data_dir / "astrophysical_flash_transition_passports.csv"),
    )
    return atomic_dropped, astro_dropped


def source_manifest_rows(raw_dir: Path) -> list[dict[str, str]]:
    """Build source manifest rows from raw manifests without inventing provenance."""
    rows: list[dict[str, str]] = []
    manifest_paths = [
        raw_dir / "atomic_lines_raw" / "manifest.json",
        raw_dir / "astrophysical_transient_raw" / "manifest.json",
        raw_dir / "supernova_raw" / "manifest.json",
    ]
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(manifest, dict):
            continue
        if "artifacts" in manifest:
            rows.append(
                {
                    "source": str(manifest.get("source_catalog", "")),
                    "url": str(manifest.get("source_url", "")),
                    "download_date_utc": str(manifest.get("download_date_utc", "")),
                    "dataset_id": str(manifest.get("dataset_identifier", "")),
                    "note": manifest_path.parent.name,
                }
            )
            continue
        if "files" in manifest:
            rows.append(
                {
                    "source": str(manifest.get("source_catalog", "NIST ASD")),
                    "url": str(manifest.get("source_url", "")),
                    "download_date_utc": str(manifest.get("download_date_utc", "")),
                    "dataset_id": f"{len(manifest.get('files', []))}_files",
                    "note": manifest_path.parent.name,
                }
            )
            continue
        for source in manifest.get("sources_used", []):
            if not isinstance(source, dict):
                continue
            rows.append(
                {
                    "source": str(
                        source.get("name", manifest.get("source_catalog", ""))
                    ),
                    "url": str(source.get("url", manifest.get("source_url", ""))),
                    "download_date_utc": str(manifest.get("download_date_utc", "")),
                    "dataset_id": str(
                        source.get("raw_file", manifest_path.parent.name)
                    ),
                    "note": str(source.get("raw_file", manifest_path.parent.name)),
                }
            )
    return rows


def missingness_rows(data_dir: Path) -> list[dict[str, str]]:
    """Build missingness rows for key observable and passport outputs."""
    rows: list[dict[str, str]] = []
    tables = [
        "atomic_transition_events.csv",
        "astrophysical_transient_events.csv",
        "atomic_transition_passports.csv",
        "astrophysical_flash_transition_passports.csv",
        "unified_transition_passports.csv",
        "cluster_ready_transition_passports.csv",
    ]
    for filename in tables:
        path = data_dir / filename
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            total = sum(1 for _ in reader)
        dataset = filename.replace(".csv", "")
        for column in columns:
            non_empty = count_non_empty_column(path, column)
            rows.append(
                {
                    "dataset": dataset,
                    "column": column,
                    "count_non_empty": str(non_empty),
                    "count_empty": str(total - non_empty),
                }
            )
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """Write a CSV with the provided rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_data_report(
    report_dir: Path,
    obs_counts: dict[str, int],
    pass_counts: dict[str, int],
    c_theta_counts: dict[str, int],
    invalidated_atomic: int,
    invalidated_astro: int,
) -> None:
    """Write the markdown report with the required four separations."""
    cluster_rows = pass_counts.get(CLUSTER_ARTIFACT, 0)
    run_mode = "normalized-only" if cluster_rows == 0 else "physical-enabled"
    total_c_theta = sum(c_theta_counts.get(name, 0) for name in PASSPORT_ARTIFACTS)
    lines = [
        "# Fourth tech spec — data report",
        "",
        f"Run mode: **{run_mode}**.",
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
            (
                "Row counts and c_theta_pending counts for passport outputs "
                "(§10.2, §10.3)."
            ),
            "",
            "| Artifact | Rows | c_theta_pending |",
            "|----------|------|----------------|",
        ]
    )
    for name in PASSPORT_ARTIFACTS + [CLUSTER_ARTIFACT]:
        lines.append(
            f"| {name} | {pass_counts.get(name, 0)} | {c_theta_counts.get(name, 0)} |"
        )
    lines.extend(
        [
            "",
            "## 3. Rows invalidated during transition-passport translation",
            "",
            (
                f"- **Atomic:** {invalidated_atomic} rows "
                "(atomic_transition_events -> atomic_transition_passports)."
            ),
            (
                f"- **Astrophysical:** {invalidated_astro} rows "
                "(astrophysical_transient_events -> "
                "astrophysical_flash_transition_passports)."
            ),
            "",
            "## 4. Rows left in c_theta_pending",
            "",
            (
                "Total passport rows with passport_status = c_theta_pending "
                f"(unified scope): {total_c_theta}."
            ),
            "",
            "Per-file counts are in the transition-passport completeness table above.",
            "",
            "## 5. Cluster-ready note",
            "",
        ]
    )
    if cluster_rows == 0:
        lines.append(
            "cluster_ready_transition_passports.csv is header-only because "
            "c_theta was not provided, so L_eff_m and kappa_eff_m^-1 could "
            "not be emitted."
        )
    else:
        lines.append(
            "cluster_ready_transition_passports.csv contains physical-layer rows."
        )
    lines.extend(
        [
            "",
            "---",
            "",
            (
                "**§13.11:** This report states what is observed "
                "(observable tables), what is inferred (passport tables), "
                "and what remains unavailable "
                "(c_theta_pending, invalidated rows)."
            ),
            "",
        ]
    )
    (report_dir / "data_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_completeness_verification(report_dir: Path) -> None:
    """Verify required report files and required report sections."""
    required_paths = {
        "data_report.md": report_dir / "data_report.md",
        "missingness_report.csv": report_dir / "missingness_report.csv",
        "source_manifest.csv": report_dir / "source_manifest.csv",
    }
    for name, path in required_paths.items():
        if not path.exists():
            print(
                f"Completeness verification failed: report/{name} missing.",
                file=sys.stderr,
            )
            sys.exit(1)
    text = required_paths["data_report.md"].read_text(encoding="utf-8")
    for phrase in [
        "Observable completeness",
        "Transition-passport completeness",
        "Rows invalidated during transition-passport translation",
        "Rows left in c_theta_pending",
    ]:
        if phrase not in text:
            print(
                "Completeness verification failed: data_report.md missing "
                f"section '{phrase}'.",
                file=sys.stderr,
            )
            sys.exit(1)
    for path, columns in [
        (required_paths["missingness_report.csv"], MISSINGNESS_COLUMNS),
        (required_paths["source_manifest.csv"], MANIFEST_COLUMNS),
    ]:
        with path.open(newline="", encoding="utf-8") as handle:
            fieldnames = csv.DictReader(handle).fieldnames or []
        for column in columns:
            if column not in fieldnames:
                print(
                    "Completeness verification failed: "
                    f"{path.name} missing column '{column}'.",
                    file=sys.stderr,
                )
                sys.exit(1)


def run_fill_validation(report_dir: Path) -> None:
    """Print a message for every completely empty report CSV column."""
    for filename in ("missingness_report.csv", "source_manifest.csv"):
        path = report_dir / filename
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            rows = list(reader)
        for column in columns:
            if rows and not any((row.get(column) or "").strip() for row in rows):
                print(
                    f"Column '{column}' in {path} is completely empty.",
                    file=sys.stderr,
                )


def main() -> int:
    """Build report outputs; run completeness verification and fill validation."""
    root = project_root()
    data_dir = root / "data"
    raw_dir = root / "raw"
    report_dir = root / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    obs_counts = observable_completeness(data_dir)
    pass_counts, c_theta_counts = passport_completeness(data_dir)
    invalidated_atomic, invalidated_astro = invalidated_rows(data_dir)
    write_data_report(
        report_dir,
        obs_counts,
        pass_counts,
        c_theta_counts,
        invalidated_atomic,
        invalidated_astro,
    )
    write_csv(
        report_dir / "missingness_report.csv",
        MISSINGNESS_COLUMNS,
        missingness_rows(data_dir),
    )
    write_csv(
        report_dir / "source_manifest.csv",
        MANIFEST_COLUMNS,
        source_manifest_rows(raw_dir),
    )
    run_completeness_verification(report_dir)
    run_fill_validation(report_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

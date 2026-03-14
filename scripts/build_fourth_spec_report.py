"""
Build fourth-spec reports: data_report.md, missingness_report.csv, source_manifest.csv.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads observable and transition-passport outputs per §10; produces report/ with
observable completeness, transition-passport completeness, invalidated rows,
c_theta_pending counts. Implements completeness verification and fill validation.

Run: python scripts/build_fourth_spec_report.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from supernova_atomic.fourth_spec_report import (
    invalidated_rows,
    missingness_rows,
    observable_completeness,
    passport_completeness,
    run_completeness_verification,
    run_fill_validation,
    source_manifest_rows,
    write_data_report,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


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

    missing_rows = missingness_rows(data_dir)
    with (report_dir / "missingness_report.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=["dataset", "column", "count_non_empty", "count_empty"],
        )
        w.writeheader()
        w.writerows(missing_rows)

    manifest_fieldnames = [
        "source",
        "url",
        "download_date_utc",
        "dataset_id",
        "note",
    ]
    with (report_dir / "source_manifest.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=manifest_fieldnames)
        w.writeheader()
        w.writerows(source_manifest_rows(raw_dir))

    run_completeness_verification(report_dir)
    run_fill_validation(report_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

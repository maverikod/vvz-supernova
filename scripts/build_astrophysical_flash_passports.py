"""
Build astrophysical_flash_transition_passports.csv from astrophysical_transient_events.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads data/supernova_transient_events.csv and/or
data/astrophysical_transient_events.csv; applies translation formulas from
docs/TECH_SPEC.md §8.3–8.4; writes
data/astrophysical_flash_transition_passports.csv with columns per §11.2;
assigns passport_status per §8.4; runs completeness and fill validation.
Run: python scripts/build_astrophysical_flash_passports.py
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path

from supernova_atomic.astrophysical_passport_rows import (
    build_astrophysical_passport_rows,
    parse_float_or_nan,
)
from supernova_atomic.passport_schema import (
    ASTROPHYSICAL_FLASH_TRANSITION_PASSPORTS_COLUMNS,
    C_THETA_PENDING,
    COMPLETE,
    INVALID,
    KAPPA_EFF_M_INV,
    L_EFF_M,
)

DEFAULT_C_THETA_ENV_VAR = "SUPERNOVA_C_THETA"


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the build script."""
    parser = argparse.ArgumentParser(
        description="Build astrophysical flash transition passports."
    )
    parser.add_argument(
        "--c-theta",
        type=float,
        default=None,
        help=(
            "Physical-enabled run input. If omitted, the script falls back to "
            f"the {DEFAULT_C_THETA_ENV_VAR} environment variable."
        ),
    )
    return parser.parse_args(argv)


def _resolve_c_theta(cli_value: float | None) -> float | None:
    """Resolve c_theta from CLI first, then env var; reject non-positive values."""
    candidate = cli_value
    if candidate is None:
        candidate = parse_float_or_nan(os.environ.get(DEFAULT_C_THETA_ENV_VAR))
    if candidate is None or not math.isfinite(candidate) or candidate <= 0:
        return None
    return candidate


def _write_passports_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write astrophysical_flash_transition_passports.csv with §11.2 columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(ASTROPHYSICAL_FLASH_TRANSITION_PASSPORTS_COLUMNS),
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(rows)


def _completeness_verification(output_path: Path, rows: list[dict[str, str]]) -> None:
    """
    Verify output: file exists, required columns present; c_theta_pending rows
    have empty physical fields. Raises AssertionError on failure.
    """
    assert output_path.exists(), f"Output file does not exist: {output_path}"
    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
    for col in ASTROPHYSICAL_FLASH_TRANSITION_PASSPORTS_COLUMNS:
        assert col in cols, f"Missing required column: {col}"
    for row in rows:
        status = row.get("passport_status")
        if status == C_THETA_PENDING or status == INVALID:
            assert (
                row.get(L_EFF_M) or ""
            ).strip() == "", "c_theta_pending/invalid must have empty L_eff_m"
            assert (
                row.get(KAPPA_EFF_M_INV) or ""
            ).strip() == "", "c_theta_pending/invalid must have empty kappa_eff_m^-1"
        if status == COMPLETE:
            assert (
                row.get("c_theta") or ""
            ).strip() != "", "complete must have c_theta"
            assert (row.get(L_EFF_M) or "").strip() != "", "complete must have L_eff_m"
            assert (
                row.get(KAPPA_EFF_M_INV) or ""
            ).strip() != "", "complete must have kappa_eff_m^-1"


def _fill_validation(output_path: Path) -> None:
    """
    For each output column, if completely empty, print a clear message to stderr.
    """
    if not output_path.exists():
        return
    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = list(reader)
    for col in columns:
        non_empty = sum(1 for r in rows if (r.get(col) or "").strip() != "")
        if non_empty == 0:
            print(
                f"Column '{col}' in {output_path} is completely empty.",
                file=sys.stderr,
            )


def main(argv: list[str] | None = None) -> int:
    """Build flash passports CSV; run completeness and fill validation."""
    args = _parse_args(argv)
    c_theta = _resolve_c_theta(args.c_theta)
    root = project_root()
    data_dir = root / "data"
    supernova_events_path = data_dir / "supernova_transient_events.csv"
    astrophysical_events_path = data_dir / "astrophysical_transient_events.csv"
    output_path = data_dir / "astrophysical_flash_transition_passports.csv"

    if not supernova_events_path.exists() and not astrophysical_events_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        _write_passports_csv(output_path, [])
        print(
            "Neither supernova_transient_events.csv nor "
            "astrophysical_transient_events.csv exists; wrote header-only "
            "astrophysical_flash_transition_passports.csv",
            file=sys.stderr,
        )
        _fill_validation(output_path)
        return 1

    rows = build_astrophysical_passport_rows(
        supernova_events_path,
        astrophysical_events_path,
        c_theta,
    )
    _write_passports_csv(output_path, rows)
    _completeness_verification(output_path, rows)
    _fill_validation(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

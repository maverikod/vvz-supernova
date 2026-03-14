"""
Build unified_transition_passports.csv from atomic and astrophysical passport CSVs.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads data/atomic_transition_passports.csv and
data/astrophysical_flash_transition_passports.csv; merges into a single table with
shared columns per docs/tech_specs/TECH_SPEC.md §11.3;
writes data/unified_transition_passports.csv. No synthetic fill (§9). Runs completeness
verification and fill validation at end.
Run: python scripts/build_unified_transition_passports.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from supernova_atomic.passport_schema import (
    KAPPA_EFF_M_INV,
    L_EFF_M,
    UNIFIED_TRANSITION_PASSPORTS_COLUMNS,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read CSV into list of row dicts; return [] if file missing or empty."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _atomic_to_unified_row(row: dict[str, str]) -> dict[str, str]:
    """Map one atomic passport row to unified schema §11.3; set class_hint."""
    element = (row.get("element") or "").strip()
    ion_stage = (row.get("ion_stage") or "").strip()
    if element or ion_stage:
        class_hint = f"atomic:{element or '?'}:{ion_stage or '?'}"
    else:
        class_hint = "atomic_transition"
    return {
        "object_id": (row.get("object_id") or "").strip(),
        "domain": (row.get("domain") or "").strip(),
        "omega_mode": (row.get("omega_mode") or "").strip(),
        "t_char_s": (row.get("t_char_s") or "").strip(),
        "Q_eff": (row.get("Q_eff") or "").strip(),
        "chi_loss": (row.get("chi_loss") or "").strip(),
        "c_theta": (row.get("c_theta") or "").strip(),
        L_EFF_M: (row.get(L_EFF_M) or "").strip(),
        KAPPA_EFF_M_INV: (row.get(KAPPA_EFF_M_INV) or "").strip(),
        "tail_strength": (row.get("tail_strength") or "").strip(),
        "tail_energy_proxy": (row.get("tail_energy_proxy") or "").strip(),
        "shape_1": (row.get("shape_1") or "").strip(),
        "shape_2": (row.get("shape_2") or "").strip(),
        "passport_status": (row.get("passport_status") or "").strip(),
        "class_hint": class_hint,
        "source_catalog": (row.get("source_catalog") or "").strip(),
    }


def _astrophysical_to_unified_row(row: dict[str, str]) -> dict[str, str]:
    """Map one astrophysical passport row to unified schema §11.3; set class_hint."""
    transient_class = (row.get("transient_class") or "").strip()
    class_hint = transient_class if transient_class else "stellar_transient"
    return {
        "object_id": (row.get("object_id") or "").strip(),
        "domain": (row.get("domain") or "").strip(),
        "omega_mode": (row.get("omega_mode") or "").strip(),
        "t_char_s": (row.get("t_char_s") or "").strip(),
        "Q_eff": (row.get("Q_eff") or "").strip(),
        "chi_loss": (row.get("chi_loss") or "").strip(),
        "c_theta": (row.get("c_theta") or "").strip(),
        L_EFF_M: (row.get(L_EFF_M) or "").strip(),
        KAPPA_EFF_M_INV: (row.get(KAPPA_EFF_M_INV) or "").strip(),
        "tail_strength": (row.get("tail_strength") or "").strip(),
        "tail_energy_proxy": (row.get("tail_energy_proxy") or "").strip(),
        "shape_1": (row.get("shape_1") or "").strip(),
        "shape_2": (row.get("shape_2") or "").strip(),
        "passport_status": (row.get("passport_status") or "").strip(),
        "class_hint": class_hint,
        "source_catalog": (row.get("source_catalog") or "").strip(),
    }


def _build_unified_rows(
    atomic_path: Path,
    astro_path: Path,
) -> list[dict[str, str]]:
    """
    Read both passport CSVs and merge into unified rows per §11.3.
    No synthetic fill; missing columns in one input yield empty in unified row.
    """
    atomic_rows = _read_csv_rows(atomic_path)
    astro_rows = _read_csv_rows(astro_path)
    out: list[dict[str, str]] = []
    for r in atomic_rows:
        out.append(_atomic_to_unified_row(r))
    for r in astro_rows:
        out.append(_astrophysical_to_unified_row(r))
    return out


def _write_unified_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write unified_transition_passports.csv with §11.3 columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(UNIFIED_TRANSITION_PASSPORTS_COLUMNS),
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(rows)


def _completeness_verification(
    output_path: Path,
    expected_count: int,
) -> None:
    """
    Verify output: file exists, required columns present, row count equals
    sum of input row counts. Raises AssertionError on failure.
    """
    assert output_path.exists(), f"Output file does not exist: {output_path}"
    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        rows = list(reader)
    for col in UNIFIED_TRANSITION_PASSPORTS_COLUMNS:
        assert col in cols, f"Missing required column: {col}"
    assert (
        len(rows) == expected_count
    ), f"Row count mismatch: expected {expected_count}, got {len(rows)}"


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


def main() -> int:
    """Merge atomic and astrophysical passports; verify and validate."""
    root = project_root()
    data_dir = root / "data"
    atomic_path = data_dir / "atomic_transition_passports.csv"
    astro_path = data_dir / "astrophysical_flash_transition_passports.csv"
    output_path = data_dir / "unified_transition_passports.csv"

    if not atomic_path.exists() and not astro_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        _write_unified_csv(output_path, [])
        print(
            "Both atomic_transition_passports.csv and "
            "astrophysical_flash_transition_passports.csv missing; "
            "wrote header-only unified_transition_passports.csv",
            file=sys.stderr,
        )
        _fill_validation(output_path)
        return 1

    unified_rows = _build_unified_rows(atomic_path, astro_path)
    expected_count = len(unified_rows)
    _write_unified_csv(output_path, unified_rows)
    _completeness_verification(output_path, expected_count)
    _fill_validation(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

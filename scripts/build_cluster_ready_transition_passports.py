"""
Build cluster_ready_transition_passports.csv from unified_transition_passports.csv.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads data/unified_transition_passports.csv; computes log-scale features only for rows
with finite required values; writes data/cluster_ready_transition_passports.csv per
docs/TECH_SPEC.md §11.4. Rows without c_theta (hence no L_eff or kappa) are
excluded and reported. Implements completeness verification and fill validation.
Run: python scripts/build_cluster_ready_transition_passports.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from supernova_atomic.passport_schema import (
    CLUSTER_READY_TRANSITION_PASSPORTS_COLUMNS,
    KAPPA_EFF_M_INV,
    L_EFF_M,
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


def _parse_positive_finite(value: str | None) -> float | None:
    """
    Parse string to float; return value if positive and finite, else None.
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    try:
        x = float(value)
        if math.isfinite(x) and x > 0:
            return x
    except (TypeError, ValueError):
        pass
    return None


def _row_to_cluster_ready(
    row: dict[str, str],
) -> dict[str, str] | tuple[None, str]:
    """
    Convert one unified passport row to cluster-ready row if all required
    numeric fields are positive and finite. Otherwise return (None, reason).
    Per §11.4: exclude rows without c_theta (no L_eff/kappa); no fake logs.
    """
    omega = _parse_positive_finite(row.get("omega_mode"))
    t_char = _parse_positive_finite(row.get("t_char_s"))
    q_eff = _parse_positive_finite(row.get("Q_eff"))
    tail_s = _parse_positive_finite(row.get("tail_strength"))
    l_eff = _parse_positive_finite(row.get(L_EFF_M))
    kappa = _parse_positive_finite(row.get(KAPPA_EFF_M_INV))

    if omega is None:
        return (None, "omega_mode missing or non-positive or non-finite")
    if t_char is None:
        return (None, "t_char_s missing or non-positive or non-finite")
    if q_eff is None:
        return (None, "Q_eff missing or non-positive or non-finite")
    if tail_s is None:
        return (None, "tail_strength missing or non-positive or non-finite")
    # §11.4: clustering schema needs L_eff and kappa → require c_theta available
    if l_eff is None:
        return (None, "L_eff_m missing or non-positive (c_theta unavailable)")
    if kappa is None:
        return (None, "kappa_eff_m^-1 missing or non-positive (c_theta unavailable)")

    def str_or_empty(key: str) -> str:
        """Return row[key] stripped, or empty string if missing or None."""
        v = row.get(key)
        return (v or "").strip() if v is not None else ""

    return {
        "object_id": str_or_empty("object_id"),
        "domain": str_or_empty("domain"),
        "log_omega": str(math.log10(omega)),
        "log_t": str(math.log10(t_char)),
        "log_Q": str(math.log10(q_eff)),
        "log_L_eff": str(math.log10(l_eff)),
        "log_kappa": str(math.log10(kappa)),
        "log_tail_strength": str(math.log10(tail_s)),
        "shape_1": str_or_empty("shape_1"),
        "shape_2": str_or_empty("shape_2"),
        "passport_status": str_or_empty("passport_status"),
        "class_hint": str_or_empty("class_hint"),
    }


def _build_cluster_ready_rows(
    unified_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], int, dict[str, int]]:
    """
    Convert unified rows to cluster-ready rows; exclude rows with missing or
    non-physical values. Return (cluster_ready_rows, excluded_count, reason_counts).
    """
    out: list[dict[str, str]] = []
    reason_counts: dict[str, int] = {}
    for row in unified_rows:
        result = _row_to_cluster_ready(row)
        if isinstance(result, dict):
            out.append(result)
        else:
            _, reason = result
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    excluded = sum(reason_counts.values())
    return out, excluded, reason_counts


def _write_cluster_ready_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write cluster_ready_transition_passports.csv with §11.4 columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(CLUSTER_READY_TRANSITION_PASSPORTS_COLUMNS),
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(rows)


def _completeness_verification(
    output_path: Path,
    cluster_ready_rows: list[dict[str, str]],
    excluded_count: int,
    reason_counts: dict[str, int],
) -> None:
    """
    Verify output: file exists, required columns present, no non-finite log
    in required log columns; exclusion reason documented.
    """
    assert output_path.exists(), f"Output file does not exist: {output_path}"
    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        rows = list(reader)
    for col in CLUSTER_READY_TRANSITION_PASSPORTS_COLUMNS:
        assert col in cols, f"Missing required column: {col}"
    assert len(rows) == len(
        cluster_ready_rows
    ), f"Row count mismatch: expected {len(cluster_ready_rows)}, got {len(rows)}"
    log_cols = [
        "log_omega",
        "log_t",
        "log_Q",
        "log_L_eff",
        "log_kappa",
        "log_tail_strength",
    ]
    for r in rows:
        for col in log_cols:
            val = r.get(col, "").strip()
            if val == "":
                continue
            try:
                x = float(val)
                assert math.isfinite(x), f"Non-finite log in column {col}"
            except ValueError:
                raise AssertionError(f"Non-numeric log in column {col}: {val!r}")
    # Exclusion reason documented (printed below; we just ensure we have the data)
    assert excluded_count >= 0 and reason_counts is not None


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
    """Build cluster-ready passports from unified; verify and validate."""
    root = project_root()
    data_dir = root / "data"
    input_path = data_dir / "unified_transition_passports.csv"
    output_path = data_dir / "cluster_ready_transition_passports.csv"

    unified_rows = _read_csv_rows(input_path)
    if not unified_rows:
        data_dir.mkdir(parents=True, exist_ok=True)
        _write_cluster_ready_csv(output_path, [])
        print(
            "unified_transition_passports.csv missing or empty; "
            "wrote header-only cluster_ready_transition_passports.csv",
            file=sys.stderr,
        )
        _completeness_verification(output_path, [], 0, {})
        _fill_validation(output_path)
        return 0

    cluster_ready_rows, excluded_count, reason_counts = _build_cluster_ready_rows(
        unified_rows
    )
    _write_cluster_ready_csv(output_path, cluster_ready_rows)

    if excluded_count > 0:
        print(
            f"Excluded {excluded_count} row(s) (no fake logs; §11.4):",
            file=sys.stderr,
        )
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"  {count}: {reason}", file=sys.stderr)

    _completeness_verification(
        output_path, cluster_ready_rows, excluded_count, reason_counts
    )
    _fill_validation(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

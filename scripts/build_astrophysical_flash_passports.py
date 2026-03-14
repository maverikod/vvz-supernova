"""
Build astrophysical_flash_transition_passports.csv from astrophysical_transient_events.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads data/astrophysical_transient_events.csv; applies translation formulas from
docs/tech_specs/TECH_SPEC.md §8.3–8.4; writes
data/astrophysical_flash_transition_passports.csv with columns per §11.2;
assigns passport_status per §8.4; runs completeness and fill validation.
Run: python scripts/build_astrophysical_flash_passports.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from supernova_atomic.passport_schema import (
    ASTROPHYSICAL_FLASH_TRANSITION_PASSPORTS_COLUMNS,
    C_THETA_PENDING,
    INVALID,
    KAPPA_EFF_M_INV,
    L_EFF_M,
)

DOMAIN_ASTROPHYSICAL = "astrophysical"
SECONDS_PER_DAY = 86400.0
TWO_PI = 2.0 * math.pi


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _parse_f(s: str | float | None) -> float:
    """Parse to float; return nan if missing or invalid."""
    if s is None or (isinstance(s, str) and s.strip() in ("", "nan", "NaN")):
        return float("nan")
    try:
        x = float(s)
        return x if math.isfinite(x) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _to_csv_value(v: float | str | int | None) -> str:
    """Serialize for CSV; nan or None -> empty string."""
    if v is None:
        return ""
    if isinstance(v, float):
        return "" if math.isnan(v) else str(v)
    s = str(v).strip()
    return "" if s.lower() in ("nan", "") else s


def _astrophysical_passport_status(
    t_char_s: float,
    q_eff: float,
    has_tail_strength: bool,
    has_tail_energy: bool,
    has_shape1: bool,
    has_shape2: bool,
) -> str:
    """
    Assign passport_status per §8.4.
    invalid if t_char_s <= 0 or Q_eff <= 0 or observables insufficient;
    c_theta_pending when normalized valid but c_theta unavailable.
    """
    if t_char_s <= 0 or q_eff <= 0 or math.isnan(t_char_s) or math.isnan(q_eff):
        return INVALID
    if not (has_tail_strength and has_tail_energy and has_shape1 and has_shape2):
        return INVALID
    return C_THETA_PENDING


def _build_passport_rows(events_path: Path) -> list[dict[str, str]]:
    """
    Read astrophysical_transient_events.csv and build passport rows per §8.3–8.4, §11.2.
    Physical fields (c_theta, L_eff_m, kappa_eff_m^-1) left empty per §9.
    """
    if not events_path.exists():
        return []

    rows_out: list[dict[str, str]] = []
    with events_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_id = (row.get("event_id") or "").strip() or "unknown"
            name = (row.get("name") or "").strip()
            transient_class = (
                row.get("transient_class") or row.get("type") or ""
            ).strip()
            source_catalog = (row.get("source_catalog") or "").strip()

            t0_days = _parse_f(row.get("t0_days"))
            width_days = _parse_f(row.get("width_days"))
            width_norm = _parse_f(row.get("width_norm"))
            L_proxy = _parse_f(row.get("L_proxy"))
            event_strength = _parse_f(row.get("event_strength"))
            asymmetry = _parse_f(row.get("asymmetry"))
            number_of_points_raw = row.get("number_of_points")
            try:
                n_pts = (
                    int(float(number_of_points_raw)) if number_of_points_raw else None
                )
            except (ValueError, TypeError):
                n_pts = None

            t_char_s = _parse_f(row.get("t_char_s"))
            if math.isnan(t_char_s) and not math.isnan(t0_days) and t0_days > 0:
                t_char_s = t0_days * SECONDS_PER_DAY

            omega_mode = _parse_f(row.get("omega_mode"))
            if math.isnan(omega_mode) and not math.isnan(t_char_s) and t_char_s > 0:
                omega_mode = TWO_PI / t_char_s

            q_eff = _parse_f(row.get("Q_eff"))
            if math.isnan(q_eff):
                if width_norm > 0:
                    q_eff = 1.0 / width_norm
                elif width_days > 0 and not math.isnan(t0_days) and t0_days > 0:
                    q_eff = t0_days / width_days

            chi_loss = (
                (1.0 / (2.0 * q_eff))
                if not math.isnan(q_eff) and q_eff > 0
                else float("nan")
            )

            tail_strength = _parse_f(row.get("tail_strength"))
            if math.isnan(tail_strength):
                tail_strength = L_proxy

            tail_energy_proxy = _parse_f(row.get("tail_energy_proxy"))
            if math.isnan(tail_energy_proxy):
                tail_energy_proxy = event_strength

            shape_1 = _parse_f(row.get("shape_1"))
            if math.isnan(shape_1):
                shape_1 = asymmetry

            shape_2 = _parse_f(row.get("shape_2"))
            if math.isnan(shape_2) and n_pts is not None:
                shape_2 = float(n_pts)

            status = _astrophysical_passport_status(
                t_char_s,
                q_eff,
                has_tail_strength=not math.isnan(tail_strength),
                has_tail_energy=not math.isnan(tail_energy_proxy),
                has_shape1=not math.isnan(shape_1),
                has_shape2=not math.isnan(shape_2),
            )

            if status == INVALID:
                t_char_s = float("nan")
                omega_mode = float("nan")
                q_eff = float("nan")
                chi_loss = float("nan")
                tail_strength = float("nan")
                tail_energy_proxy = float("nan")
                shape_1 = float("nan")
                shape_2 = float("nan")

            out: dict[str, str] = {
                "object_id": event_id,
                "domain": DOMAIN_ASTROPHYSICAL,
                "name": name,
                "transient_class": transient_class,
                "omega_mode": _to_csv_value(omega_mode),
                "t_char_s": _to_csv_value(t_char_s),
                "Q_eff": _to_csv_value(q_eff),
                "chi_loss": _to_csv_value(chi_loss),
                "c_theta": "",
                L_EFF_M: "",
                KAPPA_EFF_M_INV: "",
                "tail_strength": _to_csv_value(tail_strength),
                "tail_energy_proxy": _to_csv_value(tail_energy_proxy),
                "shape_1": _to_csv_value(shape_1),
                "shape_2": _to_csv_value(shape_2),
                "passport_status": status,
                "source_catalog": source_catalog,
            }
            rows_out.append(out)
    return rows_out


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
    """Build flash passports CSV; run completeness and fill validation."""
    root = project_root()
    data_dir = root / "data"
    events_path = data_dir / "astrophysical_transient_events.csv"
    output_path = data_dir / "astrophysical_flash_transition_passports.csv"

    if not events_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        _write_passports_csv(output_path, [])
        print(
            "astrophysical_transient_events.csv missing; wrote header-only "
            "astrophysical_flash_transition_passports.csv",
            file=sys.stderr,
        )
        _fill_validation(output_path)
        return 1

    rows = _build_passport_rows(events_path)
    _write_passports_csv(output_path, rows)
    _completeness_verification(output_path, rows)
    _fill_validation(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

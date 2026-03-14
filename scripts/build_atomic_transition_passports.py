"""
Build atomic_transition_passports.csv from atomic_transition_events.csv.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads data/atomic_transition_events.csv and optionally data/atomic_lines_clean.csv;
applies translation formulas from docs/tech_specs/TECH_SPEC.md §7;
writes data/atomic_transition_passports.csv with columns per §11.1;
assigns passport_status per §7.4; runs completeness and fill validation.
Run: python scripts/build_atomic_transition_passports.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from supernova_atomic.atomic_schema import parse_float_or_nan
from supernova_atomic.passport_schema import (
    ATOMIC_TRANSITION_PASSPORTS_COLUMNS,
    C_THETA_PENDING,
    INVALID,
    KAPPA_EFF_M_INV,
    L_EFF_M,
)

DOMAIN_ATOMIC = "atomic"
TWO_PI = 2.0 * math.pi


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _parse_f(s: str | float | None) -> float:
    """Parse to float; return nan if missing or invalid."""
    return parse_float_or_nan(s)


def _source_catalog_lookup(lines_path: Path) -> dict[tuple[str, str, str], str]:
    """
    Build (element, ion_stage, wavelength_nm) -> source_catalog from atomic_lines_clean.
    First match per key wins.
    """
    out: dict[tuple[str, str, str], str] = {}
    if not lines_path.exists():
        return out
    try:
        with lines_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                el = (row.get("element") or "").strip()
                ion = (row.get("ion_state") or "").strip()
                wv = parse_float_or_nan(row.get("wavelength_vac_nm"))
                wa = parse_float_or_nan(row.get("wavelength_air_nm"))
                wl_nm = ""
                if not math.isnan(wv) and wv > 0:
                    wl_nm = str(wv)
                elif not math.isnan(wa) and wa > 0:
                    wl_nm = str(wa)
                if not wl_nm:
                    continue
                key = (el or "unknown", ion or "I", wl_nm)
                if key not in out:
                    out[key] = (row.get("source_catalog") or "").strip()
    except (OSError, csv.Error):
        pass
    return out


def _source_catalog_for_row(
    element: str,
    ion_stage: str,
    wavelength_nm: str,
    lookup: dict[tuple[str, str, str], str],
) -> str:
    """Return source_catalog from lookup by (element, ion_stage, wavelength_nm)."""
    if not wavelength_nm or wavelength_nm.strip() == "":
        return ""
    key = (element or "unknown", ion_stage or "I", wavelength_nm.strip())
    return lookup.get(key, "")


def _to_csv_value(v: float | str | None) -> str:
    """Serialize for CSV; nan or None -> empty string."""
    if v is None:
        return ""
    if isinstance(v, float):
        return "" if math.isnan(v) else str(v)
    return str(v).strip()


def _passport_status(
    omega_mode: float, t_char_s: float, _c_theta_available: bool
) -> str:
    """
    Assign passport_status per §7.4.
    invalid if omega_mode <= 0 or t_char_s <= 0;
    c_theta_pending when normalized valid but c_theta unavailable;
    complete when all required (including physical) present (not used here: no c_theta).
    """
    if omega_mode <= 0 or t_char_s <= 0:
        return INVALID
    return C_THETA_PENDING


def _build_passport_rows(
    events_path: Path,
    lines_path: Path,
) -> list[dict[str, str]]:
    """
    Read events CSV and build list of passport row dicts with §11.1 columns.
    Physical fields (c_theta, L_eff_m, kappa_eff_m^-1) left empty when c_theta not set.
    """
    if not events_path.exists():
        return []
    lookup = _source_catalog_lookup(lines_path)
    rows_out: list[dict[str, str]] = []
    with events_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transition_id = (row.get("transition_id") or "").strip() or "unknown"
            element = (row.get("element") or "").strip() or "unknown"
            ion_stage = (row.get("ion_stage") or "").strip() or "I"
            nu_hz = _parse_f(row.get("nu_Hz"))
            tau_s = _parse_f(row.get("tau_s"))
            aki = _parse_f(row.get("Aki"))
            delta_e = _parse_f(row.get("deltaE_eV"))
            delta_j = row.get("deltaJ")
            parity_change = row.get("parity_change")
            wavelength_nm = (row.get("wavelength_nm") or "").strip()

            omega_mode = (
                TWO_PI * nu_hz if not math.isnan(nu_hz) and nu_hz > 0 else float("nan")
            )
            t_char_s = tau_s if not math.isnan(tau_s) and tau_s > 0 else float("nan")

            status = _passport_status(omega_mode, t_char_s, False)

            if status == INVALID:
                omega_mode = float("nan")
                t_char_s = float("nan")

            q_eff = float("nan")
            if (
                not math.isnan(omega_mode)
                and omega_mode > 0
                and not math.isnan(t_char_s)
                and t_char_s > 0
            ):
                q_eff = omega_mode * t_char_s / 2.0
            chi_loss = (
                (1.0 / (2.0 * q_eff))
                if not math.isnan(q_eff) and q_eff > 0
                else float("nan")
            )

            tail_strength = aki if not math.isnan(aki) else float("nan")
            tail_energy_proxy = delta_e
            shape_1 = (
                _parse_f(delta_j)
                if delta_j is not None and str(delta_j).strip() != ""
                else float("nan")
            )
            shape_2 = (
                _parse_f(parity_change)
                if parity_change is not None and str(parity_change).strip() != ""
                else float("nan")
            )

            source_catalog = _source_catalog_for_row(
                element, ion_stage, wavelength_nm, lookup
            )

            out: dict[str, str] = {
                "object_id": transition_id,
                "domain": DOMAIN_ATOMIC,
                "element": element,
                "ion_stage": ion_stage,
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
    """Write atomic_transition_passports.csv with §11.1 columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(ATOMIC_TRANSITION_PASSPORTS_COLUMNS),
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(rows)


def _completeness_verification(output_path: Path, rows: list[dict[str, str]]) -> None:
    """
    Verify output: file exists, required columns present, no synthetic physical fill
    when c_theta_pending. Raises AssertionError on failure.
    """
    assert output_path.exists(), f"Output file does not exist: {output_path}"
    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
    for col in ATOMIC_TRANSITION_PASSPORTS_COLUMNS:
        assert col in cols, f"Missing required column: {col}"
    for row in rows:
        if row.get("passport_status") == C_THETA_PENDING:
            assert (
                row.get(L_EFF_M) or ""
            ).strip() == "", "c_theta_pending must have empty L_eff_m"
            assert (
                row.get(KAPPA_EFF_M_INV) or ""
            ).strip() == "", "c_theta_pending must have empty kappa_eff_m^-1"


def _fill_validation(output_path: Path) -> None:
    """
    For each output column, if completely empty (zero non-empty values), print
    a clear message to stderr.
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
                f"Column '{col}' in {output_path} is completely empty.", file=sys.stderr
            )


def main() -> int:
    """Build atomic_transition_passports.csv; run verification and fill validation."""
    root = project_root()
    data_dir = root / "data"
    events_path = data_dir / "atomic_transition_events.csv"
    lines_path = data_dir / "atomic_lines_clean.csv"
    output_path = data_dir / "atomic_transition_passports.csv"

    if not events_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        _write_passports_csv(output_path, [])
        msg = (
            "atomic_transition_events.csv missing; wrote header-only "
            "atomic_transition_passports.csv"
        )
        print(msg, file=sys.stderr)
        _fill_validation(output_path)
        return 1

    rows = _build_passport_rows(events_path, lines_path)
    _write_passports_csv(output_path, rows)
    _completeness_verification(output_path, rows)
    _fill_validation(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Build atomic_transition_events.csv from atomic_lines_clean.csv (Third tech spec).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads data/atomic_lines_clean.csv; drops rows without wavelength or Aki;
computes parity, deltaE_eV, tau_s, nu_Hz, Q_proxy, deltaJ, parity_change;
writes data/atomic_transition_events.csv.
Run: python scripts/build_atomic_transition_events.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from supernova_atomic.atomic_schema import C_M_PER_S, parse_float_or_nan
from supernova_atomic.third_spec_schema import (
    ATOMIC_TRANSITION_EVENTS_COLUMNS,
    deltaE_eV,
    parity_from_term,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _parse_j_to_float(j_str: str | float | None) -> float:
    """Parse J string (e.g. '1/2', '3/2') to float; return nan if invalid."""
    if j_str is None:
        return float("nan")
    s = str(j_str).strip()
    if not s or s.lower() == "nan":
        return float("nan")
    if "/" in s:
        parts = s.split("/", 1)
        try:
            num = float(parts[0].strip())
            den = float(parts[1].strip())
            return num / den if den != 0 else float("nan")
        except (ValueError, IndexError):
            return float("nan")
    return parse_float_or_nan(s)


def _has_wavelength(row: dict[str, str]) -> bool:
    """True if row has at least one valid positive wavelength."""
    wv = parse_float_or_nan(row.get("wavelength_vac_nm"))
    wa = parse_float_or_nan(row.get("wavelength_air_nm"))
    return (not math.isnan(wv) and wv > 0) or (not math.isnan(wa) and wa > 0)


def _has_aki(row: dict[str, str]) -> bool:
    """True if row has valid positive Aki."""
    a = parse_float_or_nan(row.get("Aki_s^-1"))
    return not math.isnan(a) and a > 0


def _wavelength_nm(row: dict[str, str]) -> float:
    """Return wavelength in nm (vac preferred, else air)."""
    wv = parse_float_or_nan(row.get("wavelength_vac_nm"))
    wa = parse_float_or_nan(row.get("wavelength_air_nm"))
    if not math.isnan(wv) and wv > 0:
        return wv
    if not math.isnan(wa) and wa > 0:
        return wa
    return float("nan")


def _nu_hz(row: dict[str, str], wavelength_nm: float) -> float:
    """Frequency in Hz from frequency_hz column or c/wavelength."""
    f = parse_float_or_nan(row.get("frequency_hz"))
    if not math.isnan(f) and f > 0:
        return f
    if not math.isnan(wavelength_nm) and wavelength_nm > 0:
        return C_M_PER_S / (wavelength_nm * 1e-9)
    return float("nan")


def _to_output_value(v: float) -> str:
    """Serialize float for CSV; nan -> empty string."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return str(v)


def main() -> None:
    """Build atomic_transition_events.csv from atomic_lines_clean.csv."""
    root = project_root()
    data_dir = root / "data"
    input_path = data_dir / "atomic_lines_clean.csv"
    output_path = data_dir / "atomic_transition_events.csv"

    if not input_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=ATOMIC_TRANSITION_EVENTS_COLUMNS)
            w.writeheader()
        return

    rows_out: list[dict[str, str]] = []
    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_index, row in enumerate(reader):
            if not _has_wavelength(row) or not _has_aki(row):
                continue
            element = (row.get("element") or "").strip() or "unknown"
            ion = (row.get("ion_state") or "").strip() or "I"
            aki = parse_float_or_nan(row.get("Aki_s^-1"))
            tau_s = 1.0 / aki if aki > 0 else float("nan")
            wl_nm = _wavelength_nm(row)
            nu_hz = _nu_hz(row, wl_nm)
            Q_proxy = (
                nu_hz * tau_s
                if not math.isnan(nu_hz) and not math.isnan(tau_s) and tau_s > 0
                else float("nan")
            )
            ei = parse_float_or_nan(row.get("Ei_cm1"))
            ek = parse_float_or_nan(row.get("Ek_cm1"))
            dE = deltaE_eV(ei, ek)
            lower_term = (row.get("lower_term") or "").strip()
            upper_term = (row.get("upper_term") or "").strip()
            p_lo = parity_from_term(lower_term)
            p_hi = parity_from_term(upper_term)
            parity_change = 1 if p_lo != p_hi else 0
            j_lo = _parse_j_to_float(row.get("lower_J"))
            j_hi = _parse_j_to_float(row.get("upper_J"))
            dJ = (
                (j_hi - j_lo)
                if not math.isnan(j_lo) and not math.isnan(j_hi)
                else float("nan")
            )
            transition_id = f"{element}_{ion}_0_1_{row_index}"

            out_row: dict[str, str] = {
                "transition_id": transition_id,
                "element": element,
                "ion_stage": ion,
                "deltaE_eV": _to_output_value(dE),
                "tau_s": _to_output_value(tau_s),
                "nu_Hz": _to_output_value(nu_hz),
                "Q_proxy": _to_output_value(Q_proxy),
                "deltaJ": _to_output_value(dJ),
                "parity_change": str(parity_change),
                "wavelength_nm": _to_output_value(wl_nm),
                "Aki": _to_output_value(aki),
            }
            rows_out.append(out_row)

    data_dir.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ATOMIC_TRANSITION_EVENTS_COLUMNS)
        w.writeheader()
        w.writerows(rows_out)


if __name__ == "__main__":
    main()

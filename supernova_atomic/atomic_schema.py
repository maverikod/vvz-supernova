"""
Atomic line and summary schema and CSV helpers.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Constants and functions for cleaning, normalizing, and writing atomic CSVs
per IMPLEMENTATION_SPEC Sections 3.2, 3.4.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

# Speed of light in m/s (SI)
C_M_PER_S = 299_792_458

# Schema per IMPLEMENTATION_SPEC Sections 3.2, 3.4
ATOMIC_LINE_COLUMNS = [
    "element",
    "ion_state",
    "wavelength_vac_nm",
    "wavelength_air_nm",
    "frequency_hz",
    "wavenumber_cm1",
    "Aki_s^-1",
    "intensity",
    "Ei_cm1",
    "Ek_cm1",
    "lower_configuration",
    "upper_configuration",
    "lower_term",
    "upper_term",
    "lower_J",
    "upper_J",
    "line_type",
    "source_catalog",
    "source_url",
]

SUMMARY_COLUMNS = [
    "element",
    "n_lines",
    "freq_min_hz",
    "freq_max_hz",
    "freq_median_hz",
    "Aki_median",
    "Aki_max",
    "wavelength_min_nm",
    "wavelength_max_nm",
]


def clean_numeric(value: str | float | None) -> float:
    """
    Strip Excel-style artifacts, normalize decimals, return float or NaN.
    Does not drop rows; missing/invalid -> float('nan').
    """
    if value is None:
        return float("nan")
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return value
        return float(value)
    s = str(value).strip().strip("'\"").strip()
    s = re.sub(r"^=\s*", "", s)
    s = s.replace(",", ".")
    if not s or s.lower() in ("nan", "n/a", "-", ""):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def parse_float_or_nan(value: str | float | None) -> float:
    """Parse to float or return NaN; used for wavelength/frequency."""
    if value is None:
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value) if not math.isnan(value) else value
    x = clean_numeric(value)
    return x if x == x else float("nan")  # noqa: E711


def row_to_schema(row: dict[str, str | float]) -> dict[str, str | float]:
    """Ensure row has all ATOMIC_LINE_COLUMNS; NaN for missing; clean numerics."""
    out: dict[str, str | float] = {}
    str_cols = (
        "element",
        "ion_state",
        "lower_configuration",
        "upper_configuration",
        "lower_term",
        "upper_term",
        "lower_J",
        "upper_J",
        "line_type",
        "source_catalog",
        "source_url",
    )
    for col in ATOMIC_LINE_COLUMNS:
        v = row.get(col)
        if v is None or v == "":
            out[col] = float("nan") if col not in str_cols else ""
        elif col in (
            "wavelength_vac_nm",
            "wavelength_air_nm",
            "frequency_hz",
            "wavenumber_cm1",
            "Aki_s^-1",
            "intensity",
            "Ei_cm1",
            "Ek_cm1",
        ):
            out[col] = (
                parse_float_or_nan(v)
                if isinstance(v, str)
                else (
                    float(v)
                    if isinstance(v, (int, float)) and not math.isnan(v)
                    else float("nan")
                )
            )
        else:
            out[col] = v if isinstance(v, (str, int, float)) else str(v)
    if out.get("element") == "":
        out["element"] = str(row.get("element", ""))
    if out.get("ion_state") == "":
        out["ion_state"] = str(row.get("ion_state", ""))
    return out


def compute_frequency(row: dict[str, str | float]) -> None:
    """Compute frequency_hz = c / wavelength_vac_nm (in m) if missing."""
    wl = row.get("wavelength_vac_nm")
    if wl is None or (isinstance(wl, float) and math.isnan(wl)):
        return
    try:
        w = float(wl)
        if w > 0:
            row["frequency_hz"] = C_M_PER_S / (w * 1e-9)
    except (TypeError, ValueError):
        pass


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    """Write CSV with header and rows; create parent dirs. Use 'nan' for NaN."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out_row = {}
            for k in columns:
                v = r.get(k)
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    out_row[k] = "nan"
                else:
                    out_row[k] = v
            w.writerow(out_row)


def build_summary_rows(lines: list[dict]) -> list[dict]:
    """Build one row per element: n_lines, freq_min/max/median, Aki, wavelength."""
    from collections import defaultdict

    by_el: dict[str, list[dict]] = defaultdict(list)
    for row in lines:
        el = row.get("element") or ""
        if el:
            by_el[str(el)].append(row)
    out = []
    for element, group in sorted(by_el.items()):
        freqs: list[float] = []
        akis: list[float] = []
        wavs: list[float] = []
        for r in group:
            try:
                f = float(r.get("frequency_hz") or 0)
                if f > 0 and not math.isnan(f):
                    freqs.append(f)
            except (TypeError, ValueError):
                pass
            try:
                a = float(r.get("Aki_s^-1") or 0)
                if not math.isnan(a):
                    akis.append(a)
            except (TypeError, ValueError):
                pass
            for k in ("wavelength_vac_nm", "wavelength_air_nm"):
                try:
                    w = float(r.get(k) or 0)
                    if w > 0 and not math.isnan(w):
                        wavs.append(w)
                        break
                except (TypeError, ValueError):
                    pass
        n = len(group)
        freq_min = min(freqs) if freqs else float("nan")
        freq_max = max(freqs) if freqs else float("nan")
        freq_median = sorted(freqs)[len(freqs) // 2] if freqs else float("nan")
        aki_median = sorted(akis)[len(akis) // 2] if akis else float("nan")
        aki_max = max(akis) if akis else float("nan")
        wav_min = min(wavs) if wavs else float("nan")
        wav_max = max(wavs) if wavs else float("nan")
        out.append(
            {
                "element": element,
                "n_lines": n,
                "freq_min_hz": freq_min,
                "freq_max_hz": freq_max,
                "freq_median_hz": freq_median,
                "Aki_median": aki_median,
                "Aki_max": aki_max,
                "wavelength_min_nm": wav_min,
                "wavelength_max_nm": wav_max,
            }
        )
    return out

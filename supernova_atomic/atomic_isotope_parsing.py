"""
Isotope raw-data parsing helpers for two-frequency atomic analysis.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

from supernova_atomic.atomic_isotope_download import isotope_raw_dir
from supernova_atomic.atomic_schema import C_M_PER_S, parse_float_or_nan
from supernova_atomic.nist_parser import parse_nist_payload


def _serialize_float(value: float) -> str:
    """Serialize finite floats for CSV output."""
    return "" if not math.isfinite(value) else str(value)


def _geometric_median_scale(values: list[float]) -> float:
    """Return a robust positive carrier-scale proxy in omega-space."""
    positives = [value for value in values if value > 0.0 and math.isfinite(value)]
    if not positives:
        return float("nan")
    ordered_logs = sorted(math.log10(value) for value in positives)
    middle = len(ordered_logs) // 2
    if len(ordered_logs) % 2:
        median_log = float(ordered_logs[middle])
    else:
        median_log = float((ordered_logs[middle - 1] + ordered_logs[middle]) / 2.0)
    return float(10.0**median_log)


def _parse_nist_isotope_filename(filename: str) -> tuple[int, str, str] | None:
    """Extract isotope mass, element, and ion stage from a stored NIST filename."""
    stem = Path(filename).stem
    match = re.fullmatch(r"(\d+)([a-z]+)_([ivx]+)", stem, flags=re.IGNORECASE)
    if not match:
        return None
    isotope_mass = int(match.group(1))
    element = match.group(2).capitalize()
    ion_stage = match.group(3).upper()
    return isotope_mass, element, ion_stage


def _parse_kurucz_fixed_width_rows(
    text: str,
    element: str,
    ion_stage: str,
    source_catalog: str,
    source_file: str,
) -> list[dict[str, str]]:
    """Parse 160-column Kurucz isotope line rows."""
    rows: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        padded = raw_line.rstrip("\n").ljust(160)
        if not padded.strip():
            continue
        wavelength_nm = parse_float_or_nan(padded[0:11])
        if wavelength_nm <= 0.0:
            continue
        iso_primary = int(padded[106:109].strip() or "0")
        iso_secondary = int(padded[115:118].strip() or "0")
        isotope_mass = iso_secondary or iso_primary
        if isotope_mass <= 0:
            continue
        isotope_shift_mA = parse_float_or_nan(padded[154:160])
        rows.append(
            {
                "source_catalog": source_catalog,
                "element": element,
                "ion_stage": ion_stage,
                "isotope_mass": str(isotope_mass),
                "wavelength_vac_nm": _serialize_float(wavelength_nm),
                "frequency_hz": _serialize_float(C_M_PER_S / (wavelength_nm * 1e-9)),
                "isotope_shift_mA": _serialize_float(isotope_shift_mA),
                "source_file": source_file,
            }
        )
    return rows


def _parse_ca_isoshifts_rows(text: str, source_file: str) -> list[dict[str, str]]:
    """Parse the small Kurucz `isoshifts2001.dat` table for Ca II."""
    rows: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        if not re.match(r"^\s*\d+\s", raw_line):
            continue
        parts = raw_line.split()
        if len(parts) < 11:
            continue
        isotope_mass = int(parts[0])
        wavelength_nm = parse_float_or_nan(parts[10])
        shift_digit = parse_float_or_nan(parts[11]) if len(parts) > 11 else float("nan")
        if wavelength_nm <= 0.0:
            continue
        rows.append(
            {
                "source_catalog": "Kurucz isotope artifacts",
                "element": "Ca",
                "ion_stage": "II",
                "isotope_mass": str(isotope_mass),
                "wavelength_vac_nm": _serialize_float(wavelength_nm),
                "frequency_hz": _serialize_float(C_M_PER_S / (wavelength_nm * 1e-9)),
                "isotope_shift_mA": _serialize_float(shift_digit * 10.0),
                "source_file": source_file,
            }
        )
    return rows


def build_isotope_line_rows(root: Path) -> list[dict[str, str]]:
    """Parse all downloaded raw isotope artifacts into one clean line table."""
    raw_dir = isotope_raw_dir(root)
    rows: list[dict[str, str]] = []
    nist_dir = raw_dir / "nist"
    if nist_dir.exists():
        for path in sorted(nist_dir.glob("*.txt")):
            meta = _parse_nist_isotope_filename(path.name)
            if meta is None:
                continue
            isotope_mass, element, ion_stage = meta
            payload = path.read_text(encoding="utf-8", errors="replace")
            parsed_rows = parse_nist_payload(
                payload=payload,
                element=element,
                ion_state=ion_stage,
                source_catalog="NIST ASD isotope query",
                source_url=str(path),
            )
            for parsed in parsed_rows:
                wavelength_nm = parse_float_or_nan(parsed.get("wavelength_vac_nm"))
                frequency_hz = parse_float_or_nan(parsed.get("frequency_hz"))
                if (
                    not math.isfinite(frequency_hz) or frequency_hz <= 0.0
                ) and wavelength_nm > 0.0:
                    frequency_hz = C_M_PER_S / (wavelength_nm * 1e-9)
                if (
                    wavelength_nm <= 0.0
                    or not math.isfinite(frequency_hz)
                    or frequency_hz <= 0.0
                ):
                    continue
                rows.append(
                    {
                        "source_catalog": "NIST ASD isotope query",
                        "element": element,
                        "ion_stage": ion_stage,
                        "isotope_mass": str(isotope_mass),
                        "wavelength_vac_nm": _serialize_float(wavelength_nm),
                        "frequency_hz": _serialize_float(frequency_hz),
                        "isotope_shift_mA": "",
                        "source_file": path.relative_to(raw_dir).as_posix(),
                    }
                )
    kurucz_dir = raw_dir / "kurucz"
    if kurucz_dir.exists():
        for path in sorted(kurucz_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if path.stem == "gf2601iso_all":
                rows.extend(
                    _parse_kurucz_fixed_width_rows(
                        text,
                        "Fe",
                        "I",
                        "Kurucz isotope artifacts",
                        path.relative_to(raw_dir).as_posix(),
                    )
                )
            elif path.stem == "gf2801iso_pos":
                rows.extend(
                    _parse_kurucz_fixed_width_rows(
                        text,
                        "Ni",
                        "II",
                        "Kurucz isotope artifacts",
                        path.relative_to(raw_dir).as_posix(),
                    )
                )
            elif path.stem == "isoshifts2001_dat":
                rows.extend(
                    _parse_ca_isoshifts_rows(
                        text=text,
                        source_file=path.relative_to(raw_dir).as_posix(),
                    )
                )
    return rows


def build_isotope_envelope_rows(
    isotope_line_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Aggregate isotope-specific rows into carrier-envelope summaries."""
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in isotope_line_rows:
        key = (
            row["source_catalog"],
            row["element"],
            row["ion_stage"],
            row["isotope_mass"],
        )
        frequency_hz = parse_float_or_nan(row["frequency_hz"])
        if frequency_hz > 0.0:
            grouped[key].append(2.0 * math.pi * frequency_hz)
    rows: list[dict[str, str]] = []
    for key in sorted(grouped):
        rows.append(
            {
                "source_catalog": key[0],
                "element": key[1],
                "ion_stage": key[2],
                "isotope_mass": key[3],
                "line_count": str(len(grouped[key])),
                "omega_theta_env": _serialize_float(
                    _geometric_median_scale(grouped[key])
                ),
            }
        )
    return rows

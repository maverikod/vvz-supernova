"""
Parse NIST ASD HTML and load raw atomic lines.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads manifest and HTML files from raw/atomic_lines_raw/, parses tables,
normalizes to atomic schema. Used by scripts/clean_atomic_data.py.
"""

from __future__ import annotations

import json
import math
from html.parser import HTMLParser
from pathlib import Path

from supernova_atomic.atomic_schema import (
    C_M_PER_S,
    compute_frequency,
    parse_float_or_nan,
    row_to_schema,
)


class _NISTTableParser(HTMLParser):
    """Extract table rows (list of list of cell texts) from NIST ASD HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_table = False
        self._in_tr = False
        self._in_td = False
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
        elif self._in_table and tag == "tr":
            self._in_tr = True
            self._current_row = []
        elif self._in_tr and tag == "td":
            self._in_td = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self._in_table = False
        elif tag == "tr":
            if self._current_row:
                self.rows.append(self._current_row)
            self._in_tr = False
        elif tag == "td":
            self._in_td = False
            self._current_row.append(" ".join(self._current_cell).strip())

    def handle_data(self, data: str) -> None:
        if self._in_td:
            self._current_cell.append(data)


def _parse_nist_html(
    html_text: str,
    element: str,
    ion_state: str,
    source_catalog: str,
    source_url: str,
) -> list[dict[str, str | float]]:
    """
    Parse NIST ASD HTML page into list of line rows (dicts with schema keys).
    Returns empty list if page is an error message or has no data table.
    """
    if (
        not html_text
        or "Error Message" in html_text
        or "Unknown parameter" in html_text
    ):
        return []
    parser = _NISTTableParser()
    try:
        parser.feed(html_text)
    except Exception:
        return []
    if not parser.rows:
        return []
    data_rows: list[list[str]] = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        first = (row[0].strip() if row else "") or ""
        if first.upper() in ("ION", "OBSERVED", "RITZ", "SPEC", "WAVELENGTH"):
            continue
        has_num = False
        for cell in row[:5]:
            v = parse_float_or_nan(cell)
            if not math.isnan(v) and v > 0:
                has_num = True
                break
        if has_num:
            data_rows.append(row)
    out: list[dict[str, str | float]] = []
    for row in data_rows:
        n = len(row)
        wl_vac = parse_float_or_nan(row[0] if n > 0 else None)
        if n > 1 and (math.isnan(wl_vac) or wl_vac <= 0):
            wl_vac = parse_float_or_nan(row[1])
        wl_air = float("nan")
        intensity = parse_float_or_nan(row[2] if n > 2 else None)
        if math.isnan(intensity) and n > 1:
            intensity = parse_float_or_nan(row[1])
        aki = parse_float_or_nan(row[3] if n > 3 else None)
        if math.isnan(aki) and n > 4:
            aki = parse_float_or_nan(row[4])
        ei = parse_float_or_nan(row[4] if n > 4 else None)
        if math.isnan(ei) and n > 5:
            ei = parse_float_or_nan(row[5])
        ek = parse_float_or_nan(row[5] if n > 5 else None)
        if math.isnan(ek) and n > 6:
            ek = parse_float_or_nan(row[6])
        lower_conf = str(row[6]).strip() if n > 6 else ""
        upper_conf = str(row[7]).strip() if n > 7 else ""
        lower_term = str(row[8]).strip() if n > 8 else ""
        upper_term = str(row[9]).strip() if n > 9 else ""
        lower_j = str(row[10]).strip() if n > 10 else ""
        upper_j = str(row[11]).strip() if n > 11 else ""
        line_type = str(row[12]).strip() if n > 12 else ""
        if not math.isnan(wl_vac) and wl_vac > 0:
            if wl_vac > 1000:
                wl_vac = wl_vac / 10.0
        else:
            wl_vac = float("nan")
        freq_hz = float("nan")
        if not math.isnan(wl_vac) and wl_vac > 0:
            wavelength_m = wl_vac * 1e-9
            freq_hz = C_M_PER_S / wavelength_m
        wavenum = float("nan")
        if not math.isnan(wl_vac) and wl_vac > 0:
            wavenum = 1e7 / wl_vac
        rec: dict[str, str | float] = {
            "element": element,
            "ion_state": ion_state,
            "wavelength_vac_nm": wl_vac,
            "wavelength_air_nm": wl_air,
            "frequency_hz": freq_hz,
            "wavenumber_cm1": wavenum,
            "Aki_s^-1": aki,
            "intensity": intensity,
            "Ei_cm1": ei,
            "Ek_cm1": ek,
            "lower_configuration": lower_conf if lower_conf else "",
            "upper_configuration": upper_conf if upper_conf else "",
            "lower_term": lower_term if lower_term else "",
            "upper_term": upper_term if upper_term else "",
            "lower_J": lower_j if lower_j else "",
            "upper_J": upper_j if upper_j else "",
            "line_type": line_type if line_type else "",
            "source_catalog": source_catalog,
            "source_url": source_url,
        }
        out.append(rec)
    return out


def filename_to_spectrum(fname: str) -> tuple[str, str]:
    """From 'Fe_I.html' or 'H_II.html' return (element, ion_state)."""
    base = fname.replace(".html", "").replace(".HTML", "")
    parts = base.split("_", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return base, "I"


def read_raw_atomic_lines(raw_dir: Path) -> list[dict[str, str | float]]:
    """
    Read atomic lines from raw dir: manifest + HTML files.
    Parse each HTML; normalize to schema; return combined list (no dedupe yet).
    """
    all_lines: list[dict[str, str | float]] = []
    manifest_path = raw_dir / "manifest.json"
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    source_catalog = "NIST ASD"
    source_url = "https://physics.nist.gov/PhysRefData/ASD/lines_form.html"
    if isinstance(manifest.get("source_url"), str):
        source_url = str(manifest["source_url"])
    if isinstance(manifest.get("source_catalog"), str):
        source_catalog = str(manifest["source_catalog"])
    files_info: list[tuple[str, str, str]] = []
    if "files" in manifest and isinstance(manifest["files"], list):
        for entry in manifest["files"]:
            if not isinstance(entry, dict):
                continue
            spec = entry.get("spectrum") or entry.get("file", "")
            fname = str(entry.get("file", ""))
            if not fname.endswith(".html"):
                fname = fname + ".html" if not fname else fname
            el, ion = filename_to_spectrum(fname)
            if " " in str(spec):
                parts = str(spec).split(" ", 1)
                el, ion = parts[0], parts[1]
            files_info.append((fname, el, ion))
    if not files_info:
        for p in sorted(raw_dir.iterdir()):
            if p.suffix.lower() == ".html":
                el, ion = filename_to_spectrum(p.name)
                files_info.append((p.name, el, ion))
    for fname, element, ion_state in files_info:
        path = raw_dir / fname
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        file_url = source_url
        if "files" in manifest and isinstance(manifest["files"], list):
            for entry in manifest["files"]:
                if isinstance(entry, dict) and entry.get("file") == fname:
                    file_url = str(entry.get("source_url", source_url))
                    break
        rows = _parse_nist_html(text, element, ion_state, source_catalog, file_url)
        for row in rows:
            compute_frequency(row)
            normalized = row_to_schema(row)
            all_lines.append(normalized)
    return all_lines

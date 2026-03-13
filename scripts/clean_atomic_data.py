"""
Clean atomic lines and write data/ CSVs.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Reads raw NIST ASD HTML from raw/atomic_lines_raw/; parses tables; normalizes
columns per IMPLEMENTATION_SPEC; computes frequency_hz; cleans numerics;
deduplicates; writes atomic_lines_clean.csv, atomic_lines_by_element.csv,
atomic_transition_summary.csv. When raw has no parseable line data, writes
schema-only CSVs so downstream can run.
Run: python scripts/clean_atomic_data.py
"""

from __future__ import annotations

import csv
import json
import math
import re
from html.parser import HTMLParser
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


def project_root() -> Path:
    """Project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _clean_numeric(value: str | float | None) -> float:
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
    # Remove leading = and similar
    s = re.sub(r"^=\s*", "", s)
    s = s.replace(",", ".")
    if not s or s.lower() in ("nan", "n/a", "-", ""):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _parse_float_or_nan(value: str | float | None) -> float:
    """Parse to float or return NaN; used for wavelength/frequency."""
    if value is None:
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value) if not math.isnan(value) else value
    x = _clean_numeric(value)
    return x if x == x else float("nan")  # noqa: E711


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
    # Heuristic: first row may be header; data rows have numeric first columns
    data_rows: list[list[str]] = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        # Skip header-like row (all short strings, no numeric)
        first = (row[0].strip() if row else "") or ""
        if first.upper() in ("ION", "OBSERVED", "RITZ", "SPEC", "WAVELENGTH"):
            continue
        # Accept row if at least one cell looks like a number (wavelength or Aki)
        has_num = False
        for cell in row[:5]:
            v = _parse_float_or_nan(cell)
            if not math.isnan(v) and v > 0:
                has_num = True
                break
        if has_num:
            data_rows.append(row)
    out: list[dict[str, str | float]] = []
    for row in data_rows:
        # NIST order: Observed/Ritz, Rel Int, Aki, Ei, Ek, conf, term, J, type
        n = len(row)
        wl_vac = _parse_float_or_nan(row[0] if n > 0 else None)
        if n > 1 and (math.isnan(wl_vac) or wl_vac <= 0):
            wl_vac = _parse_float_or_nan(row[1])
        wl_air = float("nan")
        intensity = _parse_float_or_nan(row[2] if n > 2 else None)
        if math.isnan(intensity) and n > 1:
            intensity = _parse_float_or_nan(row[1])
        aki = _parse_float_or_nan(row[3] if n > 3 else None)
        if math.isnan(aki) and n > 4:
            aki = _parse_float_or_nan(row[4])
        ei = _parse_float_or_nan(row[4] if n > 4 else None)
        if math.isnan(ei) and n > 5:
            ei = _parse_float_or_nan(row[5])
        ek = _parse_float_or_nan(row[5] if n > 5 else None)
        if math.isnan(ek) and n > 6:
            ek = _parse_float_or_nan(row[6])
        lower_conf = str(row[6]).strip() if n > 6 else ""
        upper_conf = str(row[7]).strip() if n > 7 else ""
        lower_term = str(row[8]).strip() if n > 8 else ""
        upper_term = str(row[9]).strip() if n > 9 else ""
        lower_j = str(row[10]).strip() if n > 10 else ""
        upper_j = str(row[11]).strip() if n > 11 else ""
        line_type = str(row[12]).strip() if n > 12 else ""
        if not lower_conf and n > 6:
            lower_conf = str(row[6]).strip()
        if not upper_conf and n > 7:
            upper_conf = str(row[7]).strip()
        # Wavelength in nm; if > 1000 might be in Angstrom, convert
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


def _filename_to_spectrum(fname: str) -> tuple[str, str]:
    """From 'Fe_I.html' or 'H_II.html' return (element, ion_state)."""
    base = fname.replace(".html", "").replace(".HTML", "")
    parts = base.split("_", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return base, "I"


def _row_to_schema(row: dict[str, str | float]) -> dict[str, str | float]:
    """Ensure row has all ATOMIC_LINE_COLUMNS; NaN for missing; clean numerics."""
    out: dict[str, str | float] = {}
    for col in ATOMIC_LINE_COLUMNS:
        v = row.get(col)
        if v is None or v == "":
            out[col] = (
                float("nan")
                if col
                not in (
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
                else ""
            )
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
                _parse_float_or_nan(v)
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


def _compute_frequency(row: dict[str, str | float]) -> None:
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
            el, ion = _filename_to_spectrum(fname)
            if " " in str(spec):
                parts = str(spec).split(" ", 1)
                el, ion = parts[0], parts[1]
            files_info.append((fname, el, ion))
    if not files_info:
        for p in sorted(raw_dir.iterdir()):
            if p.suffix.lower() == ".html":
                el, ion = _filename_to_spectrum(p.name)
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
            _compute_frequency(row)
            normalized = _row_to_schema(row)
            all_lines.append(normalized)
    return all_lines


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


def main() -> None:
    """Read raw atomic data, clean, dedupe, write data/ CSVs and summary."""
    root = project_root()
    raw_dir = root / "raw" / "atomic_lines_raw"
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    lines = read_raw_atomic_lines(raw_dir)
    # Dedupe: exact duplicate rows (by all field values)
    seen: set[tuple[tuple[str, str], ...]] = set()
    unique: list[dict[str, str | float]] = []
    for row in lines:

        def _norm(v: object) -> str:
            if v is None:
                return "nan"
            if isinstance(v, float) and math.isnan(v):
                return "nan"
            return str(v)

        key = tuple((k, _norm(v)) for k, v in sorted(row.items()))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    lines = unique

    write_csv(data_dir / "atomic_lines_clean.csv", ATOMIC_LINE_COLUMNS, lines)
    by_el = sorted(
        lines,
        key=lambda r: (str(r.get("element", "")), str(r.get("ion_state", ""))),
    )
    write_csv(data_dir / "atomic_lines_by_element.csv", ATOMIC_LINE_COLUMNS, by_el)
    summary_rows = build_summary_rows(lines)
    write_csv(data_dir / "atomic_transition_summary.csv", SUMMARY_COLUMNS, summary_rows)


if __name__ == "__main__":
    main()

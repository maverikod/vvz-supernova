"""
Clean astrophysical transient data and write data/ CSVs.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/clean_astrophysical_transient_data.py
Input: raw/astrophysical_transient_raw/ (osc_catalog.json and optional manifest).
Output: data/astrophysical_transient_catalog_clean.csv,
        data/astrophysical_transient_lightcurves_long.csv
Per spec §10.1, §8.1, §13: no synthetic fill; missing values remain empty.
Completeness verification and fill validation run at end of script.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path


def project_root() -> Path:
    """Project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


# MJD epoch: 1858-11-17 00:00 UTC
_MJD_EPOCH = date(1858, 11, 17)

# Catalog columns per spec §8.1 observable-domain outputs.
CATALOG_COLUMNS = [
    "event_id",
    "name",
    "transient_class",
    "ra",
    "dec",
    "redshift",
    "peak_mag",
    "peak_abs_mag",
    "flux",
    "band",
    "distance_Mpc",
    "rise_time_days",
    "decay_time_days",
    "width_days",
    "number_of_points",
    "source_catalog",
    "discovery_mjd",
    "peak_mjd",
    "host_galaxy",
]

LIGHTCURVE_COLUMNS = [
    "event_id",
    "mjd",
    "mag",
    "mag_err",
    "flux",
    "flux_err",
    "band",
    "instrument",
    "source_catalog",
]

OSC_SOURCE = "Open Supernova Catalog"


def _first_value(obj: object, key: str) -> str | None:
    """Get first value from OSC-style list of dicts with 'value' key."""
    if not isinstance(obj, list) or not obj:
        return None
    first = obj[0]
    if not isinstance(first, dict):
        return None
    v = first.get("value")
    return str(v).strip() if v is not None else None


def _parse_ra_hms(s: str) -> float | None:
    """Parse RA string to decimal degrees (0–360)."""
    if not s or not s.strip():
        return None
    parts = s.replace(",", ".").split(":")
    try:
        h = float(parts[0])
        m = float(parts[1]) if len(parts) > 1 else 0.0
        sec = float(parts[2]) if len(parts) > 2 else 0.0
        deg = 15.0 * (h + m / 60.0 + sec / 3600.0)
        return deg % 360.0 if math.isfinite(deg) else None
    except (ValueError, IndexError):
        return None


def _parse_dec_dms(s: str) -> float | None:
    """Parse Dec string to decimal degrees (-90–90)."""
    if not s or not s.strip():
        return None
    sign = 1.0
    if s.startswith("-"):
        sign = -1.0
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]
    parts = s.replace(",", ".").split(":")
    try:
        d = float(parts[0])
        m = float(parts[1]) if len(parts) > 1 else 0.0
        sec = float(parts[2]) if len(parts) > 2 else 0.0
        deg = sign * (d + m / 60.0 + sec / 3600.0)
        return deg if math.isfinite(deg) and abs(deg) <= 90.0 else None
    except (ValueError, IndexError):
        return None


def _date_to_mjd(y: int, m: int, d: int) -> float | None:
    """Convert calendar date (UTC 0h) to MJD."""
    try:
        dt = date(y, m, d)
        mjd = (dt - _MJD_EPOCH).days
        return float(mjd) if -1e6 < mjd < 1e6 else None
    except (ValueError, OverflowError):
        return None


def _parse_date_mjd(s: str) -> float | None:
    """Parse OSC date 'YYYY/MM/DD' to MJD."""
    if not s or not s.strip():
        return None
    parts = s.strip().split("/")
    if len(parts) != 3:
        return None
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return _date_to_mjd(y, m, d)
    except (ValueError, TypeError):
        return None


def _safe_float(s: str | None, default: float = float("nan")) -> float:
    """Convert string to float; return default (NaN) on failure."""
    if s is None or (isinstance(s, str) and not s.strip()):
        return default
    try:
        v = float(str(s).replace(",", ".").strip())
        return v if math.isfinite(v) else default
    except (ValueError, TypeError):
        return default


def _safe_int(s: str | float | None, default: int = 0) -> int:
    """Convert to int; return default on failure."""
    if s is None:
        return default
    try:
        if isinstance(s, float) and (math.isnan(s) or not math.isfinite(s)):
            return default
        return int(float(str(s).replace(",", ".").strip()))
    except (ValueError, TypeError):
        return default


def _row_to_tuple(row: dict, columns: list[str]) -> tuple:
    """Hashable tuple of row values for exact-duplicate detection."""
    return tuple(
        (k, None if (isinstance(v, float) and v != v) else v)
        for k, v in sorted(row.items())
        if k in columns
    )


def _osc_entry_to_catalog_row(entry: object) -> dict | None:
    """Map one OSC catalog entry to astrophysical catalog schema (§8.1)."""
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if not name or not str(name).strip():
        return None
    name_str = str(name).strip()
    event_id = name_str  # name as event_id per spec
    ra_s = _first_value(entry.get("ra"), "ra")
    dec_s = _first_value(entry.get("dec"), "dec")
    discovery_s = _first_value(entry.get("discoverdate"), "discoverdate")
    peak_s = _first_value(entry.get("maxdate"), "maxdate")
    peak_mag_s = _first_value(entry.get("maxappmag"), "maxappmag")
    host_s = _first_value(entry.get("host"), "host")
    z_s = _first_value(entry.get("redshift"), "redshift")
    lum_s = _first_value(entry.get("lumdist"), "lumdist")
    claimed_s = _first_value(entry.get("claimedtype"), "claimedtype")

    ra = _parse_ra_hms(ra_s) if ra_s else float("nan")
    dec = _parse_dec_dms(dec_s) if dec_s else float("nan")
    discovery_mjd = _parse_date_mjd(discovery_s) if discovery_s else float("nan")
    peak_mjd = _parse_date_mjd(peak_s) if peak_s else float("nan")
    peak_mag = _safe_float(peak_mag_s)
    redshift = _safe_float(z_s)
    lumdist = _safe_float(lum_s)
    distance_Mpc = lumdist if math.isfinite(lumdist) else float("nan")
    # peak_abs_mag, rise/decay/width_days: leave empty if not in raw
    peak_abs_mag = float("nan")
    rise_time_days = float("nan")
    decay_time_days = float("nan")
    width_days = float("nan")
    number_of_points = 0

    return {
        "event_id": event_id,
        "name": name_str,
        "transient_class": claimed_s if claimed_s else "",
        "ra": ra,
        "dec": dec,
        "redshift": redshift,
        "peak_mag": peak_mag,
        "peak_abs_mag": peak_abs_mag,
        "flux": float("nan"),
        "band": "",
        "distance_Mpc": distance_Mpc,
        "rise_time_days": rise_time_days,
        "decay_time_days": decay_time_days,
        "width_days": width_days,
        "number_of_points": number_of_points,
        "source_catalog": OSC_SOURCE,
        "discovery_mjd": discovery_mjd,
        "peak_mjd": peak_mjd,
        "host_galaxy": host_s if host_s else "",
    }


def _ensure_catalog_columns(row: dict) -> dict:
    """Ensure all CATALOG_COLUMNS exist; missing as NaN or empty (no synthetic)."""
    out: dict = {}
    for col in CATALOG_COLUMNS:
        if col in row:
            v = row[col]
            if col in (
                "event_id",
                "name",
                "transient_class",
                "band",
                "source_catalog",
                "host_galaxy",
            ):
                out[col] = (
                    ""
                    if v is None or (isinstance(v, float) and math.isnan(v))
                    else str(v)
                )
            elif col == "number_of_points":
                out[col] = _safe_int(v, 0)
            else:
                out[col] = (
                    v
                    if isinstance(v, (int, float)) and math.isfinite(v)
                    else (_safe_float(v) if isinstance(v, str) else float("nan"))
                )
        else:
            if col in (
                "event_id",
                "name",
                "transient_class",
                "band",
                "source_catalog",
                "host_galaxy",
            ):
                out[col] = ""
            elif col == "number_of_points":
                out[col] = 0
            else:
                out[col] = float("nan")
    return out


def _ensure_lightcurve_columns(row: dict) -> dict:
    """Ensure LIGHTCURVE_COLUMNS exist; missing as NaN or empty (no synthetic)."""
    out: dict = {}
    for col in LIGHTCURVE_COLUMNS:
        if col in row:
            v = row[col]
            if col in ("event_id", "band", "instrument", "source_catalog"):
                out[col] = (
                    ""
                    if v is None or (isinstance(v, float) and math.isnan(v))
                    else str(v)
                )
            else:
                out[col] = (
                    v
                    if isinstance(v, (int, float)) and math.isfinite(v)
                    else (_safe_float(v) if isinstance(v, str) else float("nan"))
                )
        else:
            if col in ("event_id", "band", "instrument", "source_catalog"):
                out[col] = ""
            else:
                out[col] = float("nan")
    return out


def load_osc_catalog(raw_dir: Path) -> list[dict]:
    """Load and normalize catalog from osc_catalog.json. Returns list of rows."""
    path = raw_dir / "osc_catalog.json"
    if not path.is_file():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    catalog: list[dict] = []
    for entry in data:
        row = _osc_entry_to_catalog_row(entry)
        if row is not None:
            catalog.append(_ensure_catalog_columns(row))
    return catalog


def load_osc_lightcurves(_raw_dir: Path) -> list[dict]:
    """Load light-curves from raw. OSC bulk has no photometry; return empty."""
    return []


def read_raw_astrophysical_transient(raw_dir: Path) -> tuple[list[dict], list[dict]]:
    """Read catalog and light-curves from raw dir. Return (catalog_rows, lc_rows)."""
    catalog = load_osc_catalog(raw_dir)
    lightcurves = load_osc_lightcurves(raw_dir)
    return catalog, lightcurves


def remove_exact_duplicates_catalog(rows: list[dict]) -> list[dict]:
    """Remove exact duplicate catalog rows (by all column values)."""
    seen: set[tuple] = set()
    unique: list[dict] = []
    for row in rows:
        key = _row_to_tuple(row, CATALOG_COLUMNS)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def remove_exact_duplicates_lightcurves(rows: list[dict]) -> list[dict]:
    """Remove exact duplicate light-curve rows."""
    seen: set[tuple] = set()
    unique: list[dict] = []
    for row in rows:
        key = _row_to_tuple(row, LIGHTCURVE_COLUMNS)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    """Write CSV with header and rows; create parent dirs. Missing/NaN as empty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            out: dict = {}
            for k in columns:
                v = row.get(k)
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    out[k] = ""
                else:
                    out[k] = v
            w.writerow(out)


def verify_completeness(
    catalog_path: Path,
    lightcurves_path: Path,
    required_catalog_columns: list[str],
    required_lightcurve_columns: list[str],
) -> None:
    """
    Completeness verification: both outputs exist; required columns present;
    no synthetic fill in key fields (we do not invent; empty/NaN is allowed).
    Raises AssertionError if verification fails.
    """
    assert catalog_path.exists(), f"Catalog output missing: {catalog_path}"
    assert lightcurves_path.exists(), f"Lightcurves output missing: {lightcurves_path}"
    with open(catalog_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        catalog_headers = list(reader.fieldnames or [])
    for col in required_catalog_columns:
        assert col in catalog_headers, f"Catalog missing required column: {col}"
    with open(lightcurves_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        lc_headers = list(reader.fieldnames or [])
    for col in required_lightcurve_columns:
        assert col in lc_headers, f"Lightcurves missing required column: {col}"


def run_fill_validation(catalog_path: Path, lightcurves_path: Path) -> None:
    """
    For each column of each output CSV, if the column is completely empty,
    output a clear message. No exception; informational only.
    """
    for path, columns in [
        (catalog_path, CATALOG_COLUMNS),
        (lightcurves_path, LIGHTCURVE_COLUMNS),
    ]:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames or [])
            rows = list(reader)
        for col in columns:
            if col not in headers:
                continue
            all_empty = True
            for row in rows:
                v = row.get(col, "")
                if v is None:
                    continue
                s = str(v).strip()
                if s and s.lower() not in ("nan", "none"):
                    all_empty = False
                    break
            if all_empty:
                print(f"Column '{col}' in {path} is completely empty.")


def main() -> None:
    """Read raw astrophysical transient data, clean, dedupe, write data/ CSVs."""
    root = project_root()
    raw_dir = root / "raw" / "astrophysical_transient_raw"
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    catalog_path = data_dir / "astrophysical_transient_catalog_clean.csv"
    lightcurves_path = data_dir / "astrophysical_transient_lightcurves_long.csv"

    if not raw_dir.is_dir():
        print(
            f"Raw directory missing: {raw_dir}. "
            "Writing minimal CSVs (headers only). Run step 03 to populate raw."
        )
        write_csv(catalog_path, CATALOG_COLUMNS, [])
        write_csv(lightcurves_path, LIGHTCURVE_COLUMNS, [])
    else:
        catalog, lightcurves = read_raw_astrophysical_transient(raw_dir)
        catalog = remove_exact_duplicates_catalog(catalog)
        lightcurves = remove_exact_duplicates_lightcurves(lightcurves)
        write_csv(catalog_path, CATALOG_COLUMNS, catalog)
        write_csv(lightcurves_path, LIGHTCURVE_COLUMNS, lightcurves)

    verify_completeness(
        catalog_path,
        lightcurves_path,
        CATALOG_COLUMNS,
        LIGHTCURVE_COLUMNS,
    )
    run_fill_validation(catalog_path, lightcurves_path)


if __name__ == "__main__":
    main()

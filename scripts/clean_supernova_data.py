"""
Clean supernova data and write data/ CSVs.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/clean_supernova_data.py
Input: raw/supernova_raw/ (osc_catalog.json and optional manifest).
Output: data/supernova_catalog_clean.csv, data/supernova_lightcurves_long.csv
Normalizes OSC catalog to schema (4.2, 4.3); units MJD, Mpc; removes exact duplicates.
When raw has no catalog data, writes schema-only CSVs so downstream can run.
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

CATALOG_COLUMNS = [
    "sn_name",
    "source_catalog",
    "ra",
    "dec",
    "redshift",
    "host_galaxy",
    "sn_type",
    "discovery_mjd",
    "peak_mjd",
    "peak_mag",
    "band",
    "distance_modulus",
    "luminosity_distance_Mpc",
    "lightcurve_points_count",
]

LIGHTCURVE_COLUMNS = [
    "sn_name",
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
    """Parse RA string 'HH:MM:SS.s' or 'HH:MM:SS' to decimal degrees (0–360)."""
    if not s or not s.strip():
        return None
    parts = s.replace(",", ".").split(":")
    try:
        h = float(parts[0])
        m = float(parts[1]) if len(parts) > 1 else 0.0
        sec = float(parts[2]) if len(parts) > 2 else 0.0
        deg = 15.0 * (h + m / 60.0 + sec / 3600.0)
        if not math.isfinite(deg):
            return None
        return deg % 360.0
    except (ValueError, IndexError):
        return None


def _parse_dec_dms(s: str) -> float | None:
    """Parse Dec string '+DD:MM:SS.s' or '-DD:MM:SS' to decimal degrees (-90–90)."""
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
        if not math.isfinite(deg) or abs(deg) > 90.0:
            return None
        return deg
    except (ValueError, IndexError):
        return None


def _date_to_mjd(y: int, m: int, d: int) -> float | None:
    """Convert calendar date (UTC 0h) to MJD. Returns None if invalid."""
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
    s = s.strip()
    parts = s.split("/")
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
        if isinstance(s, float):
            if math.isnan(s) or not math.isfinite(s):
                return default
            return int(s)
        v = int(float(str(s).replace(",", ".").strip()))
        return v
    except (ValueError, TypeError):
        return default


def _row_to_tuple(row: dict, columns: list[str]) -> tuple:
    """Hashable tuple of row values for exact-duplicate detection."""
    return tuple(
        (k, None if v != v else v)  # normalize NaN
        for k, v in sorted(row.items())
        if k in columns
    )


def _osc_entry_to_catalog_row(entry: object) -> dict | None:
    """Map one OSC catalog entry to our catalog schema. Returns None if no name."""
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if not name or not str(name).strip():
        return None
    sn_name = str(name).strip()
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
    # OSC lumdist is typically in Mpc (documented in OSC).
    luminosity_distance_Mpc = lumdist if math.isfinite(lumdist) else float("nan")
    # distance_modulus = 5 * log10(lumdist_Mpc * 1e6 / 10) when lumdist in Mpc.
    distance_modulus = float("nan")
    if math.isfinite(luminosity_distance_Mpc) and luminosity_distance_Mpc > 0:
        try:
            distance_modulus = 5.0 * math.log10(luminosity_distance_Mpc * 1e6 / 10.0)
        except (ValueError, ZeroDivisionError):
            pass

    return {
        "sn_name": sn_name,
        "source_catalog": OSC_SOURCE,
        "ra": ra,
        "dec": dec,
        "redshift": redshift,
        "host_galaxy": host_s if host_s else "",
        "sn_type": claimed_s if claimed_s else "",
        "discovery_mjd": discovery_mjd,
        "peak_mjd": peak_mjd,
        "peak_mag": peak_mag,
        "band": "",
        "distance_modulus": distance_modulus,
        "luminosity_distance_Mpc": luminosity_distance_Mpc,
        "lightcurve_points_count": 0,
    }


def _ensure_catalog_columns(row: dict) -> dict:
    """Ensure all CATALOG_COLUMNS exist; fill missing with NaN or empty string."""
    out: dict = {}
    for col in CATALOG_COLUMNS:
        if col in row:
            v = row[col]
            if col in ("sn_name", "source_catalog", "host_galaxy", "sn_type", "band"):
                out[col] = (
                    ""
                    if v is None or (isinstance(v, float) and math.isnan(v))
                    else str(v)
                )
            elif col == "lightcurve_points_count":
                out[col] = _safe_int(v, 0)
            else:
                out[col] = (
                    v
                    if isinstance(v, (int, float)) and math.isfinite(v)
                    else (_safe_float(v) if isinstance(v, str) else float("nan"))
                )
        else:
            if col in ("sn_name", "source_catalog", "host_galaxy", "sn_type", "band"):
                out[col] = ""
            elif col == "lightcurve_points_count":
                out[col] = 0
            else:
                out[col] = float("nan")
    return out


def _ensure_lightcurve_columns(row: dict) -> dict:
    """Ensure all LIGHTCURVE_COLUMNS exist; fill missing with NaN or empty string."""
    out: dict = {}
    for col in LIGHTCURVE_COLUMNS:
        if col in row:
            v = row[col]
            if col in ("sn_name", "band", "instrument", "source_catalog"):
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
            if col in ("sn_name", "band", "instrument", "source_catalog"):
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


def read_raw_supernova(raw_dir: Path) -> tuple[list[dict], list[dict]]:
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


def main() -> None:
    """Read raw supernova data, clean, dedupe, write data/ CSVs."""
    root = project_root()
    raw_dir = root / "raw" / "supernova_raw"
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    catalog, lightcurves = read_raw_supernova(raw_dir)
    catalog = remove_exact_duplicates_catalog(catalog)
    lightcurves = remove_exact_duplicates_lightcurves(lightcurves)

    write_csv(
        data_dir / "supernova_catalog_clean.csv",
        CATALOG_COLUMNS,
        catalog,
    )
    write_csv(
        data_dir / "supernova_lightcurves_long.csv",
        LIGHTCURVE_COLUMNS,
        lightcurves,
    )


if __name__ == "__main__":
    main()

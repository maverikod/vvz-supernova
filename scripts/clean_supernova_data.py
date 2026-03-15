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
import math
from pathlib import Path

from supernova_atomic.supernova_raw_ingest import (
    ingest_raw_supernova,
    load_osc_bulk_catalog,
)


def project_root() -> Path:
    """Project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


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
        (k, None if isinstance(v, float) and v != v else v)
        for k, v in sorted(row.items())
        if k in columns
    )


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
    """Load and normalize catalog from osc_catalog.json (dict or list root)."""
    raw_rows = load_osc_bulk_catalog(raw_dir)
    return [_ensure_catalog_columns(row) for row in raw_rows]


def load_osc_lightcurves(raw_dir: Path) -> list[dict]:
    """Load light-curves from raw via helper (OSC bulk + curated artifacts)."""
    _, lightcurves = ingest_raw_supernova(raw_dir)
    return [_ensure_lightcurve_columns(row) for row in lightcurves]


def read_raw_supernova(raw_dir: Path) -> tuple[list[dict], list[dict]]:
    """Read catalog and light-curves from raw dir via helper. Return (catalog, lc)."""
    catalog, lightcurves = ingest_raw_supernova(raw_dir)
    catalog = [_ensure_catalog_columns(row) for row in catalog]
    lightcurves = [_ensure_lightcurve_columns(row) for row in lightcurves]
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

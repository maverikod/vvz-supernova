"""
Raw-to-clean supernova ingestion: OSC bulk + curated OAC artifacts.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Loads raw/supernova_raw/manifest.json, osc_catalog.json, and curated event
artifacts; normalizes to catalog and long-table photometry rows; deduplicates
and recomputes lightcurve_points_count. Used by scripts/clean_supernova_data.py.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

_MJD_EPOCH = date(1858, 11, 17)
OAC_SOURCE = "Open Astronomy Catalog API"
OSC_SOURCE = "Open Supernova Catalog"

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
LIGHTCURVE_DEDUPE_KEY = tuple(LIGHTCURVE_COLUMNS)


def _first_value(obj: object, key: str) -> str | None:
    """First 'value' from OSC-style list of dicts."""
    if not isinstance(obj, list) or not obj:
        return None
    first = obj[0] if isinstance(obj[0], dict) else None
    if first is None:
        return None
    v = first.get("value")
    return str(v).strip() if v is not None else None


def load_manifest(raw_dir: Path) -> dict:
    """Read raw_dir/manifest.json; return {} if missing or invalid."""
    path = raw_dir / "manifest.json"
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def load_curated_artifact_rows(
    raw_dir: Path, manifest: dict
) -> tuple[list[dict], list[dict]]:
    """Load catalog and light-curve rows from manifest artifacts.
    Raise if a photometry-bearing artifact yields 0 rows."""
    catalog_rows: list[dict] = []
    lightcurve_rows: list[dict] = []
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return catalog_rows, lightcurve_rows
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        cat_rows, lc_rows = _load_one_artifact(raw_dir, artifact)
        catalog_rows.extend(cat_rows)
        lightcurve_rows.extend(lc_rows)
    return catalog_rows, lightcurve_rows


def _parse_ra_hms(s: str) -> float | None:
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
    if not s or not s.strip():
        return None
    sign = -1.0 if s.strip().startswith("-") else 1.0
    parts = s.strip().lstrip("+-").replace(",", ".").split(":")
    try:
        d = float(parts[0])
        m = float(parts[1]) if len(parts) > 1 else 0.0
        sec = float(parts[2]) if len(parts) > 2 else 0.0
        deg = sign * (d + m / 60.0 + sec / 3600.0)
        return deg if math.isfinite(deg) and abs(deg) <= 90.0 else None
    except (ValueError, IndexError):
        return None


def _parse_date_mjd(s: str) -> float | None:
    if not s or not s.strip() or len(s.strip().split("/")) != 3:
        return None
    try:
        parts = s.strip().split("/")
        dt = date(int(parts[0]), int(parts[1]), int(parts[2]))
        mjd = (dt - _MJD_EPOCH).days
        return float(mjd) if -1e6 < mjd < 1e6 else None
    except (ValueError, TypeError, OverflowError):
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


def _osc_entry_to_catalog_row(entry: object) -> dict | None:
    """Map one OSC catalog entry to catalog schema. Returns None if no name."""
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
    luminosity_distance_Mpc = lumdist if math.isfinite(lumdist) else float("nan")
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


def load_osc_bulk_catalog(raw_dir: Path) -> list[dict]:
    """Load catalog from osc_catalog.json: dict->values(), list->items, else []."""
    path = raw_dir / "osc_catalog.json"
    if not path.is_file():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    entries: list[object]
    if isinstance(data, dict):
        entries = list(data.values())
    elif isinstance(data, list):
        entries = data
    else:
        return []
    catalog: list[dict] = []
    for entry in entries:
        row = _osc_entry_to_catalog_row(entry)
        if row is not None:
            catalog.append(row)
    return catalog


def _normalize_photometry_row(event_name: str, sample: dict) -> dict | None:
    """Normalize one photometry sample to long-table row.
    Require finite time and (mag or flux)."""
    time_val = sample.get("time")
    if time_val is None:
        return None
    try:
        mjd = float(str(time_val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None
    if not math.isfinite(mjd):
        return None
    mag = _safe_float(sample.get("magnitude"), default=float("nan"))
    flux = _safe_float(sample.get("flux"), default=float("nan"))
    if not math.isfinite(mag) and not math.isfinite(flux):
        return None
    mag_err = _safe_float(sample.get("e_magnitude"), default=float("nan"))
    flux_err = _safe_float(sample.get("e_flux"), default=float("nan"))
    band = str(sample.get("band", "")).strip() if sample.get("band") is not None else ""
    inst = sample.get("instrument")
    tel = sample.get("telescope")
    instrument = (
        str(inst).strip()
        if inst is not None and str(inst).strip()
        else (str(tel).strip() if tel is not None else "")
    )
    return {
        "sn_name": event_name,
        "mjd": mjd,
        "mag": mag if math.isfinite(mag) else float("nan"),
        "mag_err": mag_err if math.isfinite(mag_err) else float("nan"),
        "flux": flux if math.isfinite(flux) else float("nan"),
        "flux_err": flux_err if math.isfinite(flux_err) else float("nan"),
        "band": band,
        "instrument": instrument,
        "source_catalog": OAC_SOURCE,
    }


def _block_val(block: dict, key: str) -> str:
    """First 'value' from block[key] (OSC-style list or plain)."""
    v = _first_value(block.get(key), key)
    return v or ""


def _nf(x: float | None) -> float:
    """None -> NaN for numeric row fields."""
    return x if x is not None else float("nan")


def _artifact_catalog_row(event_name: str, event_block: dict) -> dict[str, str | float]:
    """Build one catalog row from OAC event block."""
    ra_s, dec_s, z_s = (
        _block_val(event_block, "ra"),
        _block_val(event_block, "dec"),
        _block_val(event_block, "redshift"),
    )
    ra = _nf(_parse_ra_hms(ra_s) if ra_s else None)
    dec = _nf(_parse_dec_dms(dec_s) if dec_s else None)
    z = _safe_float(z_s) if z_s else float("nan")
    host, claimed = _block_val(event_block, "host"), _block_val(
        event_block, "claimedtype"
    )
    disc_s, maxd_s = _block_val(event_block, "discoverdate"), _block_val(
        event_block, "maxdate"
    )
    disc_mjd = _nf(_parse_date_mjd(disc_s) if disc_s else None)
    peak_mjd = _nf(_parse_date_mjd(maxd_s) if maxd_s else None)
    lumdist = _safe_float(_block_val(event_block, "lumdist"))
    dm = float("nan")
    if math.isfinite(lumdist) and lumdist > 0:
        try:
            dm = 5.0 * math.log10(lumdist * 1e6 / 10.0)
        except (ValueError, ZeroDivisionError):
            pass
    return {
        "sn_name": event_name,
        "source_catalog": OAC_SOURCE,
        "ra": ra,
        "dec": dec,
        "redshift": z,
        "host_galaxy": host,
        "sn_type": claimed,
        "discovery_mjd": disc_mjd,
        "peak_mjd": peak_mjd,
        "peak_mag": float("nan"),
        "band": "",
        "distance_modulus": dm,
        "luminosity_distance_Mpc": lumdist,
        "lightcurve_points_count": 0,
    }


def _load_one_artifact(raw_dir: Path, artifact: dict) -> tuple[list[dict], list[dict]]:
    """Load one artifact; raise if usable_photometry_points > 0 but 0 cleaned rows."""
    event_name = str(artifact.get("event_name", "")).strip()
    if not event_name:
        return [], []
    raw_file = str(artifact.get("raw_file", "")).strip()
    if not raw_file:
        return [], []
    path = raw_dir / raw_file
    if not path.is_file():
        return [], []
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError):
        return [], []
    if not isinstance(payload, dict) or event_name not in payload:
        return [], []
    event_block = payload[event_name]
    if not isinstance(event_block, dict):
        return [], []
    photometry = event_block.get("photometry")
    if not isinstance(photometry, list):
        return [_artifact_catalog_row(event_name, event_block)], []

    lightcurves: list[dict] = []
    for sample in photometry:
        if not isinstance(sample, dict):
            continue
        row = _normalize_photometry_row(event_name, sample)
        if row is not None:
            lightcurves.append(row)

    usable = _safe_int(artifact.get("usable_photometry_points"))
    if usable > 0 and len(lightcurves) == 0:
        raise ValueError(
            f"Artifact '{event_name}' has usable_photometry_points={usable} "
            "but produced zero cleaned lightcurve rows."
        )
    catalog_rows = [_artifact_catalog_row(event_name, event_block)]
    return catalog_rows, lightcurves


def _row_to_tuple(row: dict, columns: list[str]) -> tuple:
    """Hashable tuple for exact-duplicate detection."""
    return tuple(
        (k, None if isinstance(v, float) and v != v else v)
        for k, v in sorted(row.items())
        if k in columns
    )


def _dedupe_catalog(rows: list[dict]) -> list[dict]:
    """Remove exact duplicate catalog rows."""
    seen: set[tuple] = set()
    unique: list[dict] = []
    for row in rows:
        key = _row_to_tuple(row, CATALOG_COLUMNS)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def _dedupe_lightcurves(rows: list[dict]) -> list[dict]:
    """Remove exact duplicate lightcurve rows."""
    seen: set[tuple] = set()
    unique: list[dict] = []
    for row in rows:
        key = _row_to_tuple(row, LIGHTCURVE_COLUMNS)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def _recompute_lightcurve_counts(
    catalog: list[dict], lightcurves: list[dict]
) -> list[dict]:
    """Set lightcurve_points_count per sn_name from lightcurve row count."""
    counts: dict[str, int] = {}
    for row in lightcurves:
        n = str(row.get("sn_name", "")).strip()
        if n:
            counts[n] = counts.get(n, 0) + 1
    return [
        {
            **r,
            "lightcurve_points_count": counts.get(str(r.get("sn_name", "")).strip(), 0),
        }
        for r in catalog
    ]


def remove_exact_duplicates_catalog(rows: list[dict]) -> list[dict]:
    """Remove exact duplicate catalog rows by full schema tuple."""
    return _dedupe_catalog(rows)


def remove_exact_duplicates_lightcurves(rows: list[dict]) -> list[dict]:
    """Remove exact duplicate light-curve rows by LIGHTCURVE_DEDUPE_KEY."""
    return _dedupe_lightcurves(rows)


def recompute_lightcurve_points_count(
    catalog_rows: list[dict], lightcurve_rows: list[dict]
) -> list[dict]:
    """Return catalog with lightcurve_points_count set to long-table row count
    per sn_name."""
    return _recompute_lightcurve_counts(catalog_rows, lightcurve_rows)


def ingest_raw_supernova(raw_dir: Path) -> tuple[list[dict], list[dict]]:
    """Load OSC + curated artifacts; merge, dedupe, recompute.
    Raises if a photometry-bearing artifact yields 0 rows."""
    catalog = load_osc_bulk_catalog(raw_dir)
    manifest = load_manifest(raw_dir)
    curated_cat, lightcurves = load_curated_artifact_rows(raw_dir, manifest)
    catalog.extend(curated_cat)
    catalog = remove_exact_duplicates_catalog(catalog)
    lightcurves = remove_exact_duplicates_lightcurves(lightcurves)
    catalog = recompute_lightcurve_points_count(catalog, lightcurves)
    return catalog, lightcurves

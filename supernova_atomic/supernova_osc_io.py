"""
OSC bulk catalog loading: read osc_catalog.json (dict or list root).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Internal module for supernova_raw_ingest. Maps OSC entries to catalog schema.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

OSC_SOURCE = "Open Supernova Catalog"
_MJD_EPOCH = date(1858, 11, 17)


def _first_value(obj: object) -> str | None:
    if not isinstance(obj, list) or not obj or not isinstance(obj[0], dict):
        return None
    v = obj[0].get("value")
    return str(v).strip() if v is not None else None


def _parse_ra_hms(s: str) -> float | None:
    if not s or not s.strip():
        return None
    parts = s.replace(",", ".").split(":")
    try:
        h, m = float(parts[0]), float(parts[1]) if len(parts) > 1 else 0.0
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
        d, m = float(parts[0]), float(parts[1]) if len(parts) > 1 else 0.0
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
    if s is None or (isinstance(s, str) and not s.strip()):
        return default
    try:
        v = float(str(s).replace(",", ".").strip())
        return v if math.isfinite(v) else default
    except (ValueError, TypeError):
        return default


def _osc_entry_to_row(entry: object) -> dict | None:
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if not name or not str(name).strip():
        return None
    sn_name = str(name).strip()
    ra = _parse_ra_hms(_first_value(entry.get("ra")) or "") or float("nan")
    dec = _parse_dec_dms(_first_value(entry.get("dec")) or "") or float("nan")
    discovery_mjd = _parse_date_mjd(
        _first_value(entry.get("discoverdate")) or ""
    ) or float("nan")
    peak_mjd = _parse_date_mjd(_first_value(entry.get("maxdate")) or "") or float("nan")
    peak_mag = _safe_float(_first_value(entry.get("maxappmag")))
    redshift = _safe_float(_first_value(entry.get("redshift")))
    lumdist = _safe_float(_first_value(entry.get("lumdist")))
    lum_mpc = lumdist if math.isfinite(lumdist) else float("nan")
    dm = float("nan")
    if math.isfinite(lum_mpc) and lum_mpc > 0:
        try:
            dm = 5.0 * math.log10(lum_mpc * 1e6 / 10.0)
        except (ValueError, ZeroDivisionError):
            pass
    host = _first_value(entry.get("host")) or ""
    claimed = _first_value(entry.get("claimedtype")) or ""
    return {
        "sn_name": sn_name,
        "source_catalog": OSC_SOURCE,
        "ra": ra,
        "dec": dec,
        "redshift": redshift,
        "host_galaxy": host,
        "sn_type": claimed,
        "discovery_mjd": discovery_mjd,
        "peak_mjd": peak_mjd,
        "peak_mag": peak_mag,
        "band": "",
        "distance_modulus": dm,
        "luminosity_distance_Mpc": lum_mpc,
        "lightcurve_points_count": 0,
    }


def load_osc_bulk_catalog(raw_dir: Path) -> list[dict]:
    """Load catalog from osc_catalog.json.
    Dict root -> values(); list root -> list; else []."""
    path = raw_dir / "osc_catalog.json"
    if not path.is_file():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    entries = (
        list(data.values())
        if isinstance(data, dict)
        else (data if isinstance(data, list) else [])
    )
    return [r for e in entries if (r := _osc_entry_to_row(e)) is not None]

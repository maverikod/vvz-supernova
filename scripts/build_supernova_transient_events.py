"""
Build supernova_transient_events.csv from catalog, event summary, lightcurves.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Third tech spec: reads supernova_event_summary.csv (and catalog/lightcurves);
computes peak_abs_mag, L_proxy, t0_days, asymmetry, width_norm, event_strength;
filters rows without peak_abs_mag; writes data/supernova_transient_events.csv.
Run: python scripts/build_supernova_transient_events.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from supernova_atomic.third_spec_schema import (
    MIN_LIGHTCURVE_POINTS_VALID,
    SUPERNOVA_TRANSIENT_EVENTS_COLUMNS,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _float(s: str | None) -> float | None:
    """Parse string to float; return None for empty or non-numeric."""
    if s is None or str(s).strip() in ("", "nan", "NaN"):
        return None
    try:
        v = float(str(s).strip())
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def _int(s: str | None) -> int | None:
    """Parse string to int; return None for empty or non-numeric."""
    f = _float(s)
    if f is None:
        return None
    try:
        return int(f)
    except (ValueError, OverflowError):
        return None


def _str_val(v: float | int | None) -> str:
    """Serialize number for CSV; None/nan -> empty."""
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return ""
    return str(v)


def _peak_abs_mag(
    peak_mag: float | None, luminosity_distance_Mpc: float | None
) -> float | None:
    """Compute peak absolute magnitude from peak_mag and luminosity_distance_Mpc."""
    if (
        peak_mag is None
        or luminosity_distance_Mpc is None
        or luminosity_distance_Mpc <= 0
    ):
        return None
    try:
        # distance modulus: DM = 5 * log10(d_pc / 10) = 5 * (log10(d_Mpc) + 5)
        dm = 5.0 * (math.log10(luminosity_distance_Mpc) + 5.0)
        return peak_mag - dm
    except (ValueError, ZeroDivisionError):
        return None


def main() -> None:
    """
    Build supernova_transient_events.csv from event summary and lightcurves.

    Contract (projection only; no timing recomputation):
    - Point count: from supernova_lightcurves_long.csv when present, else
      lightcurve_points_count from supernova_event_summary.csv.
    - number_of_points: that count for each row.
    - has_lightcurve: 1 iff number_of_points >= MIN_LIGHTCURVE_POINTS_VALID, else 0.
    - Timing fields (rise_time_days, decay_time_days, width_days): from summary as-is.
    - Rows without computable peak_abs_mag (peak_mag + luminosity_distance_Mpc)
      are dropped.
    """
    root = project_root()
    data_dir = root / "data"
    summary_path = data_dir / "supernova_event_summary.csv"
    output_path = data_dir / "supernova_transient_events.csv"

    if not summary_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SUPERNOVA_TRANSIENT_EVENTS_COLUMNS)
            w.writeheader()
        return

    # Count points per SN from long table (repaired timing coverage from upstream).
    lc_path = data_dir / "supernova_lightcurves_long.csv"
    points_per_sn: dict[str, int] = {}
    if lc_path.exists():
        with lc_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = (row.get("sn_name") or "").strip()
                if name:
                    points_per_sn[name] = points_per_sn.get(name, 0) + 1

    rows_out: list[dict[str, str]] = []
    name_count: dict[str, int] = {}

    with summary_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("sn_name") or "").strip()
            if not name:
                continue
            peak_mag = _float(row.get("peak_mag"))
            lum_dist = _float(row.get("luminosity_distance_Mpc"))
            peak_abs = _peak_abs_mag(peak_mag, lum_dist)
            if peak_abs is None:
                continue
            L_proxy = 10 ** (-0.4 * peak_abs)
            rise = _float(row.get("rise_time_days"))
            decay = _float(row.get("decay_time_days"))
            width = _float(row.get("peak_width_days"))
            # Point count: long-table if present, else summary lightcurve_points_count.
            n_pts_summary = _int(row.get("lightcurve_points_count"))
            n_pts = points_per_sn.get(
                name, n_pts_summary if n_pts_summary is not None else 0
            )
            # has_lightcurve = 1 iff number_of_points >= MIN_LIGHTCURVE_POINTS_VALID.
            has_lc = n_pts >= MIN_LIGHTCURVE_POINTS_VALID
            t0 = (
                (rise + decay) / 2.0
                if rise is not None and decay is not None
                else None
            )
            asymmetry = (
                decay / rise
                if (rise is not None and decay is not None and rise and rise > 0)
                else None
            )
            width_norm = (
                (width / t0)
                if (t0 is not None and width is not None and t0 > 0)
                else None
            )
            event_strength = (L_proxy * t0) if t0 is not None else None

            name_count[name] = name_count.get(name, 0) + 1
            idx = name_count[name] - 1
            event_id = name if name_count[name] == 1 else f"{name}_{idx}"

            out_row: dict[str, str] = {
                "event_id": event_id,
                "name": name,
                "type": (row.get("sn_type") or "").strip(),
                "redshift": _str_val(_float(row.get("redshift"))),
                "distance_Mpc": _str_val(lum_dist),
                "peak_abs_mag": _str_val(peak_abs),
                "L_proxy": _str_val(L_proxy),
                "rise_time_days": _str_val(rise),
                "decay_time_days": _str_val(decay),
                "width_days": _str_val(width),
                "t0_days": _str_val(t0),
                "asymmetry": _str_val(asymmetry),
                "width_norm": _str_val(width_norm),
                "event_strength": _str_val(event_strength),
                "has_lightcurve": "1" if has_lc else "0",
                "number_of_points": str(n_pts),
            }
            rows_out.append(out_row)

    data_dir.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUPERNOVA_TRANSIENT_EVENTS_COLUMNS)
        w.writeheader()
        w.writerows(rows_out)


if __name__ == "__main__":
    main()

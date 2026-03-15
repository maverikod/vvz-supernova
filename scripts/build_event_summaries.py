"""
Build supernova event summary from catalog and light-curves.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/build_event_summaries.py
Input: data/supernova_catalog_clean.csv, data/supernova_lightcurves_long.csv
Output: data/supernova_event_summary.csv

Per-SN summary: peak_mjd, peak_mag, rise_time_days, decay_time_days, peak_width_days,
lightcurve_points_count, redshift, luminosity_distance_Mpc. Rise/decay/width are
computed from light-curves when possible (see docstrings below); otherwise NaN.

Definitions (magnitude-based):
- Rise: days from the first epoch before peak at which magnitude is within 1 mag
  of peak (mag <= peak_mag + 1) to peak_mjd. Linear interpolation between
  light-curve points when the threshold is crossed between two epochs; else NaN.
- Decay: days from peak_mjd to the first epoch after peak at which magnitude has
  faded by 1 mag (mag >= peak_mag + 1). Same interpolation rule.
- Peak width: rise_time_days + decay_time_days (full width at 1 mag from peak).
"""

from __future__ import annotations

import csv
from pathlib import Path


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


SUMMARY_COLUMNS = [
    "sn_name",
    "sn_type",
    "source_catalog",
    "peak_mjd",
    "peak_mag",
    "rise_time_days",
    "decay_time_days",
    "peak_width_days",
    "lightcurve_points_count",
    "redshift",
    "luminosity_distance_Mpc",
]


def _float(s: str) -> float | None:
    """Parse string to float; return None for empty or non-numeric."""
    if s is None or str(s).strip() == "":
        return None
    try:
        v = float(s)
        return v if __import__("math").isfinite(v) else None
    except (ValueError, TypeError):
        return None


def _int(s: str) -> int | None:
    """Parse string to int; return None for empty or non-numeric."""
    v = _float(s)
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, OverflowError):
        return None


def load_catalog(path: Path) -> list[dict[str, str]]:
    """Load supernova catalog CSV into list of row dicts (all values as strings)."""
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            for row in reader:
                rows.append(dict(row))
    return rows


def load_lightcurves(path: Path) -> list[dict[str, str]]:
    """Load light-curves long CSV into list of row dicts (all values as strings)."""
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            for row in reader:
                rows.append(dict(row))
    return rows


def _mjd_at_mag_threshold(
    points: list[tuple[float, float]],
    peak_mjd: float,
    mag_threshold: float,
    before: bool,
) -> float | None:
    """
    Find MJD at which magnitude crosses mag_threshold using linear interpolation.

    points: list of (mjd, mag) sorted by mjd. Mag is magnitude (lower = brighter).
    peak_mjd: epoch of peak (min mag).
    mag_threshold: target magnitude (e.g. peak_mag + 1).
    before: if True, look for crossing before peak_mjd; else after.

    Returns MJD of crossing or None if not determinable.
    """
    if not points or mag_threshold is None:
        return None
    if before:
        segment = [(m, mag) for m, mag in points if m < peak_mjd]
        segment.sort(key=lambda x: x[0])
    else:
        segment = [(m, mag) for m, mag in points if m > peak_mjd]
        segment.sort(key=lambda x: x[0])
    if not segment:
        return None
    for i in range(len(segment) - 1):
        m1, mag1 = segment[i]
        m2, mag2 = segment[i + 1]
        if mag1 is None or mag2 is None:
            continue
        # Crossing: threshold between mag1 and mag2
        if (mag1 - mag_threshold) * (mag2 - mag_threshold) <= 0:
            if mag2 == mag1:
                return m1
            t = (mag_threshold - mag1) / (mag2 - mag1)
            return m1 + t * (m2 - m1)
    # Check if first/last point is already past threshold
    if (
        before
        and segment
        and segment[0][1] is not None
        and segment[0][1] >= mag_threshold
    ):
        return segment[0][0]
    if (
        not before
        and segment
        and segment[-1][1] is not None
        and segment[-1][1] >= mag_threshold
    ):
        return segment[-1][0]
    return None


def compute_rise_decay_width(
    lc_points: list[tuple[float, float]], peak_mjd: float | None, peak_mag: float | None
) -> tuple[float | None, float | None, float | None]:
    """
    Compute rise_time_days, decay_time_days, peak_width_days from light-curve.

    Operates on a single-band (mjd, mag) series. Uses 1-mag threshold definition:
    rise/decay from/to first epoch at which mag is within 1 mag of peak.

    lc_points: list of (mjd, mag) for one SN and one band; mag can be None.
    peak_mjd, peak_mag: from catalog or inferred from LC (peak = min mag).

    Returns (rise_days, decay_days, width_days); each None if not computable.
    """
    # Drop points with missing mag or mjd
    points = []
    for mjd, mag in lc_points:
        m = _float(str(mjd)) if isinstance(mjd, str) else mjd
        mag_val = _float(str(mag)) if isinstance(mag, str) else mag
        if m is not None and mag_val is not None:
            points.append((m, mag_val))
    if not points:
        return (None, None, None)
    # Infer peak from LC if not provided
    use_peak_mjd = peak_mjd
    use_peak_mag = peak_mag
    if use_peak_mag is None or use_peak_mjd is None:
        min_mag = min(p[1] for p in points)
        min_points = [p for p in points if p[1] == min_mag]
        if use_peak_mjd is None and min_points:
            use_peak_mjd = min_points[0][0]
        if use_peak_mag is None:
            use_peak_mag = min_mag
    if use_peak_mjd is None or use_peak_mag is None:
        return (None, None, None)
    threshold = use_peak_mag + 1.0
    mjd_rise = _mjd_at_mag_threshold(points, use_peak_mjd, threshold, before=True)
    mjd_decay = _mjd_at_mag_threshold(points, use_peak_mjd, threshold, before=False)
    rise = (use_peak_mjd - mjd_rise) if mjd_rise is not None else None
    decay = (mjd_decay - use_peak_mjd) if mjd_decay is not None else None
    width = None
    if rise is not None and decay is not None:
        width = rise + decay
    return (rise, decay, width)


def _choose_band(
    lc_by_band: dict[str, list[tuple[float, float]]],
    catalog_peak_mag: float | None,
) -> str:
    """
    Choose exactly one band for timing using deterministic tie-break rule.

    Rule: (1) prefer band with largest number of valid (mjd, mag) rows;
    (2) if tied, prefer band that contains a finite catalog peak_mag match;
    (3) if still tied, lexicographically smallest band string;
    (4) if all valid rows have empty band, use the empty-string bucket.
    """
    if not lc_by_band:
        return ""

    def has_peak_mag_match(points: list[tuple[float, float]]) -> bool:
        if catalog_peak_mag is None:
            return False
        return any(p[1] == catalog_peak_mag for p in points)

    def key(band: str) -> tuple[int, int, str]:
        pts = lc_by_band[band]
        n = len(pts)
        match = 1 if has_peak_mag_match(pts) else 0
        return (n, match, band)

    bands_sorted = sorted(
        lc_by_band.keys(),
        key=lambda b: (-key(b)[0], -key(b)[1], key(b)[2]),
    )
    return bands_sorted[0]


def _infer_peak_from_points(
    points: list[tuple[float, float]],
) -> tuple[float | None, float | None]:
    """
    Infer (peak_mjd, peak_mag) from series: minimum magnitude; if tie, earliest mjd.
    """
    if not points:
        return (None, None)
    min_mag = min(p[1] for p in points)
    min_points = [p for p in points if p[1] == min_mag]
    peak_mjd = min(p[0] for p in min_points)
    return (peak_mjd, min_mag)


def _str_num(v: float | int | None) -> str:
    """Convert numeric value to string for CSV; None becomes empty string."""
    if v is None:
        return ""
    return str(v)


def build_summary_rows(
    catalog: list[dict[str, str]], lightcurves: list[dict[str, str]]
) -> list[dict[str, str]]:
    """
    Build one summary row per catalog entry from catalog + light-curves.

    Groups light-curve rows by sn_name then by band; chooses exactly one band
    per object (largest point count, then catalog peak_mag match, then lex
    smallest band). Rise/decay/width are computed from that band only.
    Uses catalog for sn_name, sn_type, source_catalog, peak_mjd, peak_mag,
    lightcurve_points_count, redshift, luminosity_distance_Mpc.
    """
    # Filter: finite mjd, finite mag, non-empty sn_name. Group by sn_name, band.
    lc_by_sn_band: dict[str, dict[str, list[tuple[float, float]]]] = {}
    for row in lightcurves:
        name = (row.get("sn_name") or "").strip()
        if not name:
            continue
        mjd = _float(row.get("mjd") or "")
        mag = _float(row.get("mag") or "")
        if mjd is None or mag is None:
            continue
        band = (row.get("band") or "").strip()
        lc_by_sn_band.setdefault(name, {}).setdefault(band, []).append((mjd, mag))

    out: list[dict[str, str]] = []
    for row in catalog:
        sn_name = (row.get("sn_name") or "").strip()
        if not sn_name:
            continue
        catalog_peak_mjd = _float(row.get("peak_mjd") or "")
        catalog_peak_mag = _float(row.get("peak_mag") or "")
        lc_by_band = lc_by_sn_band.get(sn_name, {})
        chosen_band = _choose_band(lc_by_band, catalog_peak_mag)
        points = lc_by_band.get(chosen_band, [])
        points = sorted(points, key=lambda p: p[0])

        use_peak_mjd: float | None
        use_peak_mag: float | None
        if catalog_peak_mjd is not None and catalog_peak_mag is not None:
            use_peak_mjd = catalog_peak_mjd
            use_peak_mag = catalog_peak_mag
        else:
            use_peak_mjd, use_peak_mag = _infer_peak_from_points(points)

        rise, decay, width = compute_rise_decay_width(
            points, use_peak_mjd, use_peak_mag
        )

        lc_count = _int(row.get("lightcurve_points_count") or "")
        if lc_count is not None and lc_count > 0:
            pass
        else:
            lc_count = len(points) if points else 0

        out.append(
            {
                "sn_name": sn_name,
                "sn_type": (row.get("sn_type") or "").strip() or "",
                "source_catalog": (row.get("source_catalog") or "").strip() or "",
                "peak_mjd": _str_num(use_peak_mjd),
                "peak_mag": _str_num(use_peak_mag),
                "rise_time_days": _str_num(rise),
                "decay_time_days": _str_num(decay),
                "peak_width_days": _str_num(width),
                "lightcurve_points_count": str(lc_count),
                "redshift": (row.get("redshift") or "").strip() or "",
                "luminosity_distance_Mpc": (
                    row.get("luminosity_distance_Mpc") or ""
                ).strip()
                or "",
            }
        )
    return out


def write_summary_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write summary rows to CSV with SUMMARY_COLUMNS header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in SUMMARY_COLUMNS})


def main() -> None:
    """Load catalog and light-curves, build event summary, write CSV."""
    root = project_root()
    data_dir = root / "data"
    catalog_path = data_dir / "supernova_catalog_clean.csv"
    lightcurves_path = data_dir / "supernova_lightcurves_long.csv"
    summary_path = data_dir / "supernova_event_summary.csv"

    if not catalog_path.is_file():
        raise SystemExit(f"Missing input: {catalog_path}")
    if not lightcurves_path.is_file():
        raise SystemExit(f"Missing input: {lightcurves_path}")

    catalog = load_catalog(catalog_path)
    lightcurves = load_lightcurves(lightcurves_path)
    summary_rows = build_summary_rows(catalog, lightcurves)
    write_summary_csv(summary_path, summary_rows)


if __name__ == "__main__":
    main()

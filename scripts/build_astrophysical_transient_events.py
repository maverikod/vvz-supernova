"""
Build astrophysical_transient_events.csv from catalog and lightcurves.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Fourth tech spec §8.3, §8.5: reads astrophysical_transient_catalog_clean.csv and
astrophysical_transient_lightcurves_long.csv; computes L_proxy, t0_days,
asymmetry, width_norm, event_strength, t_char_s, omega_mode, Q_eff, chi_loss,
tail_strength, tail_energy_proxy, shape_1, shape_2; enforces number_of_points >= 20;
writes data/astrophysical_transient_events.csv. Includes completeness verification
and fill validation.
Run: python scripts/build_astrophysical_transient_events.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from supernova_atomic.third_spec_schema import MIN_LIGHTCURVE_POINTS_VALID

# Output columns for step 06 (passport builder) per §8.3 and §10.1
ASTROPHYSICAL_TRANSIENT_EVENTS_COLUMNS = [
    "event_id",
    "name",
    "transient_class",
    "redshift",
    "distance_Mpc",
    "peak_abs_mag",
    "L_proxy",
    "rise_time_days",
    "decay_time_days",
    "width_days",
    "t0_days",
    "asymmetry",
    "width_norm",
    "event_strength",
    "t_char_s",
    "omega_mode",
    "Q_eff",
    "chi_loss",
    "tail_strength",
    "tail_energy_proxy",
    "shape_1",
    "shape_2",
    "number_of_points",
]


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
    peak_mag: float | None,
    distance_Mpc: float | None,
) -> float | None:
    """Compute peak absolute magnitude from peak_mag and distance_Mpc (§8.3)."""
    if peak_mag is None or distance_Mpc is None or distance_Mpc <= 0:
        return None
    try:
        dm = 5.0 * (math.log10(distance_Mpc) + 5.0)
        return peak_mag - dm
    except (ValueError, ZeroDivisionError):
        return None


def _count_lightcurve_points(lc_path: Path, id_key: str) -> dict[str, int]:
    """Aggregate number of light-curve points per event from long table."""
    points_per_event: dict[str, int] = {}
    if not lc_path.exists():
        return points_per_event
    with lc_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = (row.get(id_key) or "").strip()
            if eid:
                points_per_event[eid] = points_per_event.get(eid, 0) + 1
    return points_per_event


def _run_completeness_verification(output_path: Path) -> bool:
    """Verify output exists, has required columns, no row with number_of_points < 20."""
    if not output_path.exists():
        print(
            "Completeness verification failed: output file does not exist.",
            file=sys.stderr,
        )
        return False
    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for c in ASTROPHYSICAL_TRANSIENT_EVENTS_COLUMNS:
            if c not in cols:
                print(
                    f"Completeness verification failed: missing column '{c}'.",
                    file=sys.stderr,
                )
                return False
        for row in reader:
            n_pts = _int(row.get("number_of_points"))
            if n_pts is not None and n_pts < MIN_LIGHTCURVE_POINTS_VALID:
                print(
                    "Completeness verification failed: row with number_of_points < 20.",
                    file=sys.stderr,
                )
                return False
    return True


def _run_fill_validation(output_path: Path) -> None:
    """For each output column, if completely empty, print a clear message."""
    if not output_path.exists():
        return
    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    for col in fieldnames:
        if not col:
            continue
        if all((row.get(col) or "").strip() == "" for row in rows):
            print(
                f"Column '{col}' in {output_path} is completely empty.",
                file=sys.stderr,
            )


def main() -> None:
    """Build astrophysical_transient_events.csv per §8.3 and §8.5."""
    root = project_root()
    data_dir = root / "data"
    catalog_path = data_dir / "astrophysical_transient_catalog_clean.csv"
    lc_path = data_dir / "astrophysical_transient_lightcurves_long.csv"
    output_path = data_dir / "astrophysical_transient_events.csv"

    if not catalog_path.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=ASTROPHYSICAL_TRANSIENT_EVENTS_COLUMNS)
            w.writeheader()
        print("Catalog missing; wrote minimal CSV (header only).", file=sys.stderr)
        if not _run_completeness_verification(output_path):
            sys.exit(1)
        _run_fill_validation(output_path)
        return

    # Prefer event_id for lightcurve grouping; fallback to name
    points_per_event: dict[str, int] = {}
    if lc_path.exists():
        with lc_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            id_key = (
                "event_id"
                if reader.fieldnames and "event_id" in reader.fieldnames
                else "name"
            )
        points_per_event = _count_lightcurve_points(lc_path, id_key)

    rows_out: list[dict[str, str]] = []
    name_count: dict[str, int] = {}

    with catalog_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_id_raw = (row.get("event_id") or "").strip()
            name = (row.get("name") or event_id_raw or "").strip()
            if not name:
                continue
            n_pts_catalog = _int(row.get("number_of_points"))
            n_pts = points_per_event.get(
                event_id_raw or name, points_per_event.get(name, n_pts_catalog or 0)
            )
            if n_pts is None:
                n_pts = 0
            if n_pts < MIN_LIGHTCURVE_POINTS_VALID:
                continue
            peak_abs = _float(row.get("peak_abs_mag"))
            if peak_abs is None:
                peak_mag = _float(row.get("peak_mag"))
                dist = _float(row.get("distance_Mpc")) or _float(
                    row.get("luminosity_distance_Mpc")
                )
                peak_abs = _peak_abs_mag(peak_mag, dist)
            if peak_abs is None:
                continue
            L_proxy = 10 ** (-0.4 * peak_abs)
            rise = _float(row.get("rise_time_days"))
            decay = _float(row.get("decay_time_days"))
            width = _float(row.get("width_days"))
            t0 = (
                (rise + decay) / 2.0
                if (rise is not None and decay is not None and rise > 0)
                else None
            )
            asymmetry = (
                (decay / rise)
                if (rise is not None and decay is not None and rise and rise > 0)
                else None
            )
            width_norm = (
                (width / t0)
                if (t0 is not None and width is not None and t0 > 0)
                else None
            )
            event_strength = (
                (L_proxy * t0) if (L_proxy is not None and t0 is not None) else None
            )
            t_char_s = (t0 * 86400.0) if t0 is not None else None
            omega_mode = (
                (2.0 * math.pi / t_char_s)
                if (t_char_s is not None and t_char_s > 0)
                else None
            )
            Q_eff = None
            if width_norm is not None and width_norm > 0:
                Q_eff = 1.0 / width_norm
            elif width is not None and t0 is not None and width > 0 and t0 > 0:
                Q_eff = t0 / width
            chi_loss = (
                (1.0 / (2.0 * Q_eff)) if (Q_eff is not None and Q_eff > 0) else None
            )
            tail_strength = L_proxy
            tail_energy_proxy = event_strength
            shape_1 = asymmetry
            shape_2 = float(n_pts) if n_pts is not None else None

            name_count[name] = name_count.get(name, 0) + 1
            idx = name_count[name] - 1
            event_id = name if name_count[name] == 1 else f"{name}_{idx}"

            out_row: dict[str, str] = {
                "event_id": event_id,
                "name": name,
                "transient_class": (row.get("transient_class") or "").strip(),
                "redshift": _str_val(_float(row.get("redshift"))),
                "distance_Mpc": _str_val(
                    _float(row.get("distance_Mpc"))
                    or _float(row.get("luminosity_distance_Mpc"))
                ),
                "peak_abs_mag": _str_val(peak_abs),
                "L_proxy": _str_val(L_proxy),
                "rise_time_days": _str_val(rise),
                "decay_time_days": _str_val(decay),
                "width_days": _str_val(width),
                "t0_days": _str_val(t0),
                "asymmetry": _str_val(asymmetry),
                "width_norm": _str_val(width_norm),
                "event_strength": _str_val(event_strength),
                "t_char_s": _str_val(t_char_s),
                "omega_mode": _str_val(omega_mode),
                "Q_eff": _str_val(Q_eff),
                "chi_loss": _str_val(chi_loss),
                "tail_strength": _str_val(tail_strength),
                "tail_energy_proxy": _str_val(tail_energy_proxy),
                "shape_1": _str_val(shape_1),
                "shape_2": _str_val(shape_2),
                "number_of_points": str(n_pts) if n_pts is not None else "",
            }
            rows_out.append(out_row)

    data_dir.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ASTROPHYSICAL_TRANSIENT_EVENTS_COLUMNS)
        w.writeheader()
        w.writerows(rows_out)

    if not _run_completeness_verification(output_path):
        sys.exit(1)
    _run_fill_validation(output_path)


if __name__ == "__main__":
    main()

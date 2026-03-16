"""
Build astrophysical_transient_events.csv from catalog and lightcurves.
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
Computes §8.3 observables, enforces §8.5 number_of_points >= 20,
runs completeness verification and fill validation.
Run: python scripts/build_astrophysical_transient_events.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

from supernova_atomic.third_spec_schema import MIN_LIGHTCURVE_POINTS_VALID

SECONDS_PER_DAY = 86400.0
TWO_PI = 2.0 * math.pi

# Output columns for step 06 (passport builder) per §8.3 and §10.1
ASTROPHYSICAL_TRANSIENT_EVENTS_COLUMNS = [
    "event_id",
    "name",
    "transient_class",
    "source_catalog",
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


def _write_output_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write the astrophysical transient events CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=ASTROPHYSICAL_TRANSIENT_EVENTS_COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _load_lightcurve_point_counts(lc_path: Path) -> tuple[dict[str, int], int]:
    """Read the long light-curve table and count rows per event identifier."""
    points_per_event: dict[str, int] = {}
    if not lc_path.exists():
        return points_per_event, 0

    with lc_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        id_key = "event_id" if "event_id" in fieldnames else "name"
        lightcurve_rows = 0
        for row in reader:
            lightcurve_rows += 1
            event_key = (row.get(id_key) or "").strip()
            if event_key:
                points_per_event[event_key] = points_per_event.get(event_key, 0) + 1

    return points_per_event, lightcurve_rows


def _run_completeness_verification(
    output_path: Path,
    *,
    catalog_exists: bool,
    lightcurve_rows: int,
    processable_rows: int,
    excluded_low_points: int,
    excluded_missing_peak_abs_mag: int,
) -> bool:
    """Verify structure and that zero rows are explained by real validity rules."""
    if not output_path.exists():
        print(
            "Completeness verification failed: output file does not exist.",
            file=sys.stderr,
        )
        return False

    with output_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        rows = list(reader)

    for c in ASTROPHYSICAL_TRANSIENT_EVENTS_COLUMNS:
        if c not in cols:
            print(
                f"Completeness verification failed: missing column '{c}'.",
                file=sys.stderr,
            )
            return False

    for row in rows:
        n_pts = _int(row.get("number_of_points"))
        if n_pts is None:
            print(
                "Completeness verification failed: missing number_of_points in row.",
                file=sys.stderr,
            )
            return False
        if n_pts < MIN_LIGHTCURVE_POINTS_VALID:
            print(
                "Completeness verification failed: row with number_of_points < 20.",
                file=sys.stderr,
            )
            return False

    if rows or not catalog_exists:
        return True

    if lightcurve_rows == 0:
        print(
            "Completeness verification failed: empty output caused by missing or "
            "header-only lightcurve rows.",
            file=sys.stderr,
        )
        return False

    explained_exclusions = excluded_low_points + excluded_missing_peak_abs_mag
    if processable_rows > 0 and explained_exclusions != processable_rows:
        print(
            "Completeness verification failed: empty output is not fully explained "
            "by the §8.5 light-curve validity filter or missing peak_abs_mag.",
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


def main() -> int:
    """Build astrophysical_transient_events.csv per §8.3 and §8.5."""
    root = project_root()
    data_dir = root / "data"
    catalog_path = data_dir / "astrophysical_transient_catalog_clean.csv"
    lc_path = data_dir / "astrophysical_transient_lightcurves_long.csv"
    output_path = data_dir / "astrophysical_transient_events.csv"

    if not catalog_path.exists():
        _write_output_csv(output_path, [])
        print(
            "Catalog missing; wrote minimal astrophysical_transient_events.csv.",
            file=sys.stderr,
        )
        if not _run_completeness_verification(
            output_path,
            catalog_exists=False,
            lightcurve_rows=0,
            processable_rows=0,
            excluded_low_points=0,
            excluded_missing_peak_abs_mag=0,
        ):
            return 1
        _run_fill_validation(output_path)
        return 1

    if not lc_path.exists():
        _write_output_csv(output_path, [])
        print(
            "Lightcurve file missing; astrophysical event building cannot continue.",
            file=sys.stderr,
        )
        _run_fill_validation(output_path)
        return 1

    points_per_event, lightcurve_rows = _load_lightcurve_point_counts(lc_path)
    if lightcurve_rows == 0:
        _write_output_csv(output_path, [])
        print(
            "Lightcurve table contains no data rows; upstream source is "
            "insufficient for astrophysical event building.",
            file=sys.stderr,
        )
        _run_fill_validation(output_path)
        return 1

    rows_out: list[dict[str, str]] = []
    event_id_count: dict[str, int] = {}
    processable_rows = 0
    excluded_low_points = 0
    excluded_missing_peak_abs_mag = 0

    with catalog_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_id_raw = (row.get("event_id") or "").strip()
            name = (row.get("name") or event_id_raw).strip()
            base_event_id = event_id_raw or name
            if not base_event_id:
                continue

            processable_rows += 1
            n_pts_catalog = _int(row.get("number_of_points")) or 0
            n_pts = points_per_event.get(
                base_event_id, points_per_event.get(name, n_pts_catalog)
            )
            if n_pts < MIN_LIGHTCURVE_POINTS_VALID:
                excluded_low_points += 1
                continue

            peak_abs = _float(row.get("peak_abs_mag"))
            peak_mag = _float(row.get("peak_mag"))
            distance_Mpc = _float(row.get("distance_Mpc")) or _float(
                row.get("luminosity_distance_Mpc")
            )
            if peak_abs is None:
                peak_abs = _peak_abs_mag(peak_mag, distance_Mpc)
            if peak_abs is None:
                excluded_missing_peak_abs_mag += 1
                continue

            L_proxy = 10 ** (-0.4 * peak_abs) if peak_abs is not None else None
            rise = _float(row.get("rise_time_days"))
            decay = _float(row.get("decay_time_days"))
            width = _float(row.get("width_days"))
            flux = _float(row.get("flux"))

            t0 = None
            if rise is not None and decay is not None and rise > 0 and decay > 0:
                t0 = (rise + decay) / 2.0

            asymmetry = None
            if rise is not None and decay is not None and rise > 0 and decay > 0:
                asymmetry = decay / rise

            width_norm = None
            if width is not None and width > 0 and t0 is not None and t0 > 0:
                width_norm = width / t0

            event_strength = None
            if L_proxy is not None and t0 is not None:
                event_strength = L_proxy * t0

            t_char_s = t0 * SECONDS_PER_DAY if t0 is not None else None
            omega_mode = (
                (TWO_PI / t_char_s) if (t_char_s is not None and t_char_s > 0) else None
            )
            Q_eff = None
            if width_norm is not None and width_norm > 0:
                Q_eff = 1.0 / width_norm
            elif width is not None and t0 is not None and width > 0 and t0 > 0:
                Q_eff = t0 / width
            chi_loss = (
                (1.0 / (2.0 * Q_eff)) if (Q_eff is not None and Q_eff > 0) else None
            )
            tail_strength = L_proxy if L_proxy is not None else flux
            tail_energy_proxy = event_strength
            shape_1 = asymmetry
            shape_2 = float(n_pts)

            event_id_count[base_event_id] = event_id_count.get(base_event_id, 0) + 1
            idx = event_id_count[base_event_id] - 1
            event_id = base_event_id if idx == 0 else f"{base_event_id}_{idx}"

            out_row: dict[str, str] = {
                "event_id": event_id,
                "name": name,
                "transient_class": (
                    row.get("transient_class") or row.get("type") or ""
                ).strip(),
                "source_catalog": (row.get("source_catalog") or "").strip(),
                "redshift": _str_val(_float(row.get("redshift"))),
                "distance_Mpc": _str_val(distance_Mpc),
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

    _write_output_csv(output_path, rows_out)

    if not _run_completeness_verification(
        output_path,
        catalog_exists=True,
        lightcurve_rows=lightcurve_rows,
        processable_rows=processable_rows,
        excluded_low_points=excluded_low_points,
        excluded_missing_peak_abs_mag=excluded_missing_peak_abs_mag,
    ):
        return 1

    if not rows_out:
        print(
            "No astrophysical transient events were produced after applying the "
            "§8.5 light-curve validity rule and peak_abs_mag requirement.",
            file=sys.stderr,
        )

    _run_fill_validation(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

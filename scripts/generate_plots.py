"""
Quality control metrics and generate six required plots (Part D).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/generate_plots.py
Reads: data/atomic_lines_clean.csv, data/atomic_transition_summary.csv,
  data/supernova_catalog_clean.csv, data/supernova_event_summary.csv,
  data/supernova_lightcurves_long.csv
Outputs: QC metrics to stdout; six PNGs under plots/.
Creates plots/ if missing. Does not modify any CSV.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

# Matplotlib used only for plot generation; import at top per project rules.
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Paths relative to project root
DATA_DIR = Path("data")
PLOTS_DIR = Path("plots")

ATOMIC_CLEAN = DATA_DIR / "atomic_lines_clean.csv"
ATOMIC_SUMMARY = DATA_DIR / "atomic_transition_summary.csv"
SN_CATALOG = DATA_DIR / "supernova_catalog_clean.csv"
SN_EVENT_SUMMARY = DATA_DIR / "supernova_event_summary.csv"
SN_LIGHTCURVES = DATA_DIR / "supernova_lightcurves_long.csv"

PLOT_FILES = [
    "atomic_frequency_histogram.png",
    "atomic_Aki_histogram.png",
    "supernova_peak_mag_histogram.png",
    "supernova_rise_time_histogram.png",
    "supernova_decay_time_histogram.png",
    "example_lightcurves.png",
]


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _parse_float(s: str | None) -> float | None:
    """Parse string to float; return None for empty or non-numeric."""
    if s is None or str(s).strip() in ("", "nan", "NaN"):
        return None
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def _load_csv(path: Path) -> list[dict[str, str]]:
    """Load CSV into list of row dicts. Return [] if file missing or empty."""
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            for row in reader:
                rows.append(dict(row))
    return rows


def _sources_used(
    rows: list[dict[str, str]], column: str = "source_catalog"
) -> set[str]:
    """Return set of non-empty source_catalog values from rows."""
    out: set[str] = set()
    for row in rows:
        v = (row.get(column) or "").strip()
        if v:
            out.add(v)
    return out


def run_qc_metrics(root: Path) -> None:
    """
    Load required CSVs, compute six Part D metrics, print to stdout.
    """
    # 1. Elements count (from atomic_transition_summary)
    summary_rows = _load_csv(root / ATOMIC_SUMMARY)
    n_elements = len(summary_rows)
    print(f"1. Elements with atomic lines: {n_elements}")

    # 2. Total atomic lines
    atomic_rows = _load_csv(root / ATOMIC_CLEAN)
    n_lines = len(atomic_rows)
    print(f"2. Total atomic lines: {n_lines}")

    # 3. Supernovae in catalog
    catalog_rows = _load_csv(root / SN_CATALOG)
    n_sn = len(catalog_rows)
    print(f"3. Supernovae in catalog: {n_sn}")

    # 4. Supernovae with at least one light-curve point
    lc_rows = _load_csv(root / SN_LIGHTCURVES)
    sn_with_lc = len(
        {r.get("sn_name", "").strip() for r in lc_rows if r.get("sn_name", "").strip()}
    )
    print(f"4. Supernovae with light-curve: {sn_with_lc}")

    # 5. Supernovae with non-NaN rise_time_days
    event_rows = _load_csv(root / SN_EVENT_SUMMARY)
    with_rise = sum(
        1 for r in event_rows if _parse_float(r.get("rise_time_days")) is not None
    )
    print(f"5. Supernovae with rise_time_days: {with_rise}")

    # 6. Sources actually used (atomic + supernova)
    atomic_sources = _sources_used(atomic_rows)
    sn_sources = (
        _sources_used(catalog_rows) | _sources_used(event_rows) | _sources_used(lc_rows)
    )
    all_sources = sorted(atomic_sources | sn_sources)
    print("6. Sources used in final datasets:")
    for src in all_sources:
        print(f"   - {src}")
    print("---")


def _plot_histogram(
    values: list[float],
    title: str,
    xlabel: str,
    out_path: Path,
    *,
    bins: int = 50,
    log: bool = False,
) -> None:
    """Draw histogram and save to out_path. Skip if values empty."""
    if not values:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_title(title)
        fig.savefig(out_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        return
    fig, ax = plt.subplots()
    ax.hist(values, bins=bins, edgecolor="black", alpha=0.7)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    if log:
        ax.set_yscale("log")
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def _plot_atomic_frequency(root: Path) -> None:
    """Histogram of line frequencies from atomic_lines_clean.csv."""
    rows = _load_csv(root / ATOMIC_CLEAN)
    key = "frequency_hz"
    values = []
    for r in rows:
        v = _parse_float(r.get(key))
        if v is not None and v > 0:
            values.append(v)
    _plot_histogram(
        values,
        "Atomic line frequencies",
        "Frequency (Hz)",
        root / PLOTS_DIR / "atomic_frequency_histogram.png",
        log=True,
    )


def _plot_atomic_aki(root: Path) -> None:
    """Histogram of Aki (s^-1) from atomic_lines_clean.csv."""
    rows = _load_csv(root / ATOMIC_CLEAN)
    key = "Aki_s^-1"
    values = []
    for r in rows:
        v = _parse_float(r.get(key))
        if v is not None and v >= 0:
            values.append(v)
    _plot_histogram(
        values,
        "Atomic Aki (Einstein A coefficient)",
        "Aki (s⁻¹)",
        root / PLOTS_DIR / "atomic_Aki_histogram.png",
        log=True,
    )


def _plot_supernova_peak_mag(root: Path) -> None:
    """Histogram of peak magnitudes from supernova_event_summary.csv."""
    rows = _load_csv(root / SN_EVENT_SUMMARY)
    values = []
    for r in rows:
        v = _parse_float(r.get("peak_mag"))
        if v is not None:
            values.append(v)
    _plot_histogram(
        values,
        "Supernova peak magnitude",
        "Peak magnitude (mag)",
        root / PLOTS_DIR / "supernova_peak_mag_histogram.png",
    )


def _plot_supernova_rise_time(root: Path) -> None:
    """Histogram of rise_time_days (omit NaN)."""
    rows = _load_csv(root / SN_EVENT_SUMMARY)
    values = []
    for r in rows:
        v = _parse_float(r.get("rise_time_days"))
        if v is not None and v >= 0:
            values.append(v)
    _plot_histogram(
        values,
        "Supernova rise time",
        "Rise time (days)",
        root / PLOTS_DIR / "supernova_rise_time_histogram.png",
    )


def _plot_supernova_decay_time(root: Path) -> None:
    """Histogram of decay_time_days (omit NaN)."""
    rows = _load_csv(root / SN_EVENT_SUMMARY)
    values = []
    for r in rows:
        v = _parse_float(r.get("decay_time_days"))
        if v is not None and v >= 0:
            values.append(v)
    _plot_histogram(
        values,
        "Supernova decay time",
        "Decay time (days)",
        root / PLOTS_DIR / "supernova_decay_time_histogram.png",
    )


def _plot_example_lightcurves(root: Path) -> None:
    """
    Example light-curves: time vs mag for a few SNe.
    Picks up to 6 SNe that have at least 3 points with valid mag.
    """
    lc_rows = _load_csv(root / SN_LIGHTCURVES)
    # Group by sn_name, collect (mjd, mag)
    by_sn: dict[str, list[tuple[float, float]]] = {}
    for r in lc_rows:
        name = (r.get("sn_name") or "").strip()
        if not name:
            continue
        mjd = _parse_float(r.get("mjd"))
        mag = _parse_float(r.get("mag"))
        if mjd is not None and mag is not None:
            by_sn.setdefault(name, []).append((mjd, mag))
    # Keep only SNe with at least 3 points; sort by mjd per SN
    candidates = [
        (name, sorted(points, key=lambda p: p[0]))
        for name, points in by_sn.items()
        if len(points) >= 3
    ]
    # Take up to 6
    selected = candidates[:6]
    out_path = root / PLOTS_DIR / "example_lightcurves.png"
    fig, ax = plt.subplots()
    for name, points in selected:
        mjds = [p[0] for p in points]
        mags = [p[1] for p in points]
        ax.plot(mjds, mags, "o-", label=name, alpha=0.8)
    if not selected:
        ax.text(0.5, 0.5, "No light-curve data", ha="center", va="center")
    else:
        ax.legend(loc="best", fontsize=8)
    ax.set_xlabel("MJD")
    ax.set_ylabel("Magnitude (mag)")
    ax.set_title("Example light-curves")
    ax.invert_yaxis()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def generate_all_plots(root: Path) -> None:
    """Create plots/ if missing; generate all six PNGs."""
    plots_dir = root / PLOTS_DIR
    plots_dir.mkdir(parents=True, exist_ok=True)
    _plot_atomic_frequency(root)
    _plot_atomic_aki(root)
    _plot_supernova_peak_mag(root)
    _plot_supernova_rise_time(root)
    _plot_supernova_decay_time(root)
    _plot_example_lightcurves(root)


def main() -> int:
    """Run QC metrics and generate plots. Return 0 on success."""
    root = project_root()
    data_dir = root / DATA_DIR
    if not data_dir.is_dir():
        print("Error: data/ directory not found.", file=sys.stderr)
        return 1
    required = [
        (root / ATOMIC_CLEAN, "atomic_lines_clean.csv"),
        (root / ATOMIC_SUMMARY, "atomic_transition_summary.csv"),
        (root / SN_CATALOG, "supernova_catalog_clean.csv"),
        (root / SN_EVENT_SUMMARY, "supernova_event_summary.csv"),
    ]
    for path, name in required:
        if not path.exists():
            print(f"Error: missing required input: {name}", file=sys.stderr)
            return 1
    print("--- QC metrics (Part D) ---")
    run_qc_metrics(root)
    generate_all_plots(root)
    print(f"Plots written to {root / PLOTS_DIR}/")
    for name in PLOT_FILES:
        p = root / PLOTS_DIR / name
        print(f"  {name}: {'OK' if p.exists() else 'MISSING'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

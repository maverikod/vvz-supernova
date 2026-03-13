"""
Verify pipeline downloads and outputs (raw, data, plots).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run from project root: python scripts/verify_pipeline_data.py
Checks: raw/ dirs, data/ CSVs (columns, row counts), plots/.
Exit: 0 if all expected artifacts present and valid, 1 otherwise.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def project_root() -> Path:
    """Resolve project root (parent of scripts/)."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent


# Expected paths (relative to project root)
RAW_ATOMIC_DIR = Path("raw/atomic_lines_raw")
RAW_SUPERNOVA_DIR = Path("raw/supernova_raw")
DATA_DIR = Path("data")
PLOTS_DIR = Path("plots")

DATA_FILES = [
    "atomic_lines_clean.csv",
    "atomic_lines_by_element.csv",
    "atomic_transition_summary.csv",
    "supernova_catalog_clean.csv",
    "supernova_lightcurves_long.csv",
    "supernova_event_summary.csv",
]

# Minimal required columns per task (at least one identifier + key fields)
REQUIRED_COLUMNS: dict[str, list[str]] = {
    "atomic_lines_clean.csv": ["element", "frequency_hz"],
    "atomic_lines_by_element.csv": ["element"],
    "atomic_transition_summary.csv": [
        "element",
        "n_lines",
        "freq_min_hz",
        "freq_max_hz",
    ],
    "supernova_catalog_clean.csv": ["sn_name", "source_catalog"],
    "supernova_lightcurves_long.csv": ["sn_name", "mjd", "band"],
    "supernova_event_summary.csv": [
        "sn_name",
        "sn_type",
        "source_catalog",
        "peak_mjd",
        "rise_time_days",
        "decay_time_days",
    ],
}

PLOT_FILES = [
    "atomic_frequency_histogram.png",
    "atomic_Aki_histogram.png",
    "supernova_peak_mag_histogram.png",
    "supernova_rise_time_histogram.png",
    "supernova_decay_time_histogram.png",
    "example_lightcurves.png",
]


def check_raw_dirs(root: Path) -> tuple[bool, list[str]]:
    """Check raw directories exist and are non-empty. Return (ok, messages)."""
    messages: list[str] = []
    ok = True
    for name, rel in [
        ("atomic", RAW_ATOMIC_DIR),
        ("supernova", RAW_SUPERNOVA_DIR),
    ]:
        d = root / rel
        if not d.is_dir():
            messages.append(f"Missing: {rel}/")
            ok = False
        else:
            files = list(d.iterdir())
            messages.append(f"  {rel}: {len(files)} file(s)")
            if len(files) == 0:
                messages.append(f"  WARNING: {rel}/ is empty")
    return ok, messages


def check_data_csv(root: Path) -> tuple[bool, list[str]]:
    """Check data CSVs: exist, headers, required columns. Return (ok, msgs)."""
    messages: list[str] = []
    ok = True
    for filename in DATA_FILES:
        path = root / DATA_DIR / filename
        if not path.exists():
            messages.append(f"Missing: {DATA_DIR / filename}")
            ok = False
            continue
        required = REQUIRED_COLUMNS.get(filename, [])
        try:
            with path.open(newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    messages.append(f"Empty or no header: {path}")
                    ok = False
                    continue
                header_set = {c.strip() for c in header}
                missing = [c for c in required if c not in header_set]
                if missing:
                    messages.append(f"{filename}: missing columns: {missing}")
                    ok = False
                row_count = sum(1 for _ in reader)
                messages.append(f"  {filename}: {row_count} row(s)")
        except Exception as e:
            messages.append(f"Error reading {path}: {e}")
            ok = False
    return ok, messages


def check_plots(root: Path) -> tuple[bool, list[str]]:
    """Check plot files exist. Return (ok, messages)."""
    messages: list[str] = []
    ok = True
    for name in PLOT_FILES:
        path = root / PLOTS_DIR / name
        if not path.exists():
            messages.append(f"Missing plot: {PLOTS_DIR / name}")
            ok = False
        else:
            messages.append(f"  {name}: OK")
    return ok, messages


def print_summary_from_data(root: Path) -> None:
    """Print quality-control summary from data/ CSVs (task Part D)."""
    summary_path = root / DATA_DIR / "supernova_event_summary.csv"
    catalog_path = root / DATA_DIR / "supernova_catalog_clean.csv"
    atomic_clean_path = root / DATA_DIR / "atomic_lines_clean.csv"
    atomic_summary_path = root / DATA_DIR / "atomic_transition_summary.csv"

    def read_csv_header_and_count(path: Path) -> tuple[list[str], int]:
        if not path.exists():
            return [], 0
        with path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            header = r.fieldnames or []
            return header, sum(1 for _ in r)

    print("\n--- Quality summary (Part D) ---")
    # Atomic
    if atomic_summary_path.exists():
        _, n_summary = read_csv_header_and_count(atomic_summary_path)
        print(f"1. Elements with atomic lines (summary): {n_summary}")
    else:
        print("1. Elements with atomic lines: (no atomic summary file)")
    if atomic_clean_path.exists():
        _, n_lines = read_csv_header_and_count(atomic_clean_path)
        print(f"2. Total atomic lines: {n_lines}")
    else:
        print("2. Total atomic lines: (no atomic_lines_clean.csv)")
    # Supernova
    if catalog_path.exists():
        header, n_cat = read_csv_header_and_count(catalog_path)
        print(f"3. Supernovae in catalog: {n_cat}")
        lc_path = root / DATA_DIR / "supernova_lightcurves_long.csv"
        if lc_path.exists():
            _, n_lc_rows = read_csv_header_and_count(lc_path)
            with lc_path.open(newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                sn_with_lc = len({row.get("sn_name", "") for row in r})
            print(f"4. SNe with light-curve: {sn_with_lc} (points: {n_lc_rows})")
        else:
            print("4. Supernovae with light-curve: (no lightcurves file)")
    else:
        print("3. Supernovae in catalog: (no catalog)")
        print("4. Supernovae with light-curve: (no catalog)")
    if summary_path.exists():
        header, _ = read_csv_header_and_count(summary_path)
        if header and "rise_time_days" in header:
            with summary_path.open(newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                with_rise = sum(
                    1
                    for row in r
                    if row.get("rise_time_days", "").strip() not in ("", "nan", "NaN")
                )
            print(f"5. Supernovae with rise_time_days: {with_rise}")
        else:
            print("5. Supernovae with rise_time_days: (column not found)")
    else:
        print("5. Supernovae with rise_time_days: (no event summary)")
    print("6. Sources: (see source_catalog in data files)")
    print("---")


def main() -> int:
    """Run all checks; print summary; return 0 if ok else 1."""
    root = project_root()
    print(f"Project root: {root}")
    all_ok = True

    print("\n--- Raw directories ---")
    ok, msgs = check_raw_dirs(root)
    for m in msgs:
        print(m)
    if not ok:
        all_ok = False

    print("\n--- Data CSVs ---")
    ok, msgs = check_data_csv(root)
    for m in msgs:
        print(m)
    if not ok:
        all_ok = False

    print("\n--- Plots ---")
    ok, msgs = check_plots(root)
    for m in msgs:
        print(m)
    if not ok:
        all_ok = False

    print_summary_from_data(root)

    if all_ok:
        print("\nResult: OK (all checks passed)")
        return 0
    print("\nResult: FAIL (see missing or invalid artifacts above)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

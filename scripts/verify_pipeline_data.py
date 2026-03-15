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
import json
import sys
from pathlib import Path

from supernova_atomic.nist_parser import is_nist_error_text


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
ATOMIC_DATA_FILES = {
    "atomic_lines_clean.csv",
    "atomic_lines_by_element.csv",
    "atomic_transition_summary.csv",
}

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
        "peak_width_days",
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


def read_csv_header_and_count(path: Path) -> tuple[list[str], int]:
    """Read one CSV header and count data rows; return empty header if missing."""
    if not path.exists():
        return [], 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), sum(1 for _ in reader)


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
            files = [path for path in d.iterdir() if not path.name.startswith(".")]
            messages.append(f"  {rel}: {len(files)} visible file(s)")
            if len(files) == 0:
                messages.append(f"  WARNING: {rel}/ is empty")
    return ok, messages


def check_atomic_raw_payloads(root: Path) -> tuple[bool, list[str]]:
    """Validate atomic raw payload presence and reject NIST error-page responses."""
    raw_dir = root / RAW_ATOMIC_DIR
    manifest_path = raw_dir / "manifest.json"
    messages: list[str] = []
    if not raw_dir.is_dir():
        return False, [f"Missing atomic raw directory: {RAW_ATOMIC_DIR}/"]
    if not manifest_path.exists():
        return False, [f"Missing atomic manifest: {manifest_path}"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, [f"Unreadable atomic manifest: {exc}"]

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return False, ["Atomic manifest has no file entries"]

    ok = True
    valid_count = 0
    invalid_count = 0
    for entry in files:
        if not isinstance(entry, dict):
            ok = False
            invalid_count += 1
            continue
        filename = str(entry.get("file", ""))
        spectrum = str(entry.get("spectrum", filename or "<unknown>"))
        path = raw_dir / filename
        if not path.is_file():
            messages.append(f"Missing atomic raw file for {spectrum}: {filename}")
            ok = False
            invalid_count += 1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        manifest_valid = entry.get("valid_payload")
        if manifest_valid is False or is_nist_error_text(text):
            messages.append(f"Invalid atomic raw payload: {spectrum} -> {filename}")
            ok = False
            invalid_count += 1
            continue
        valid_count += 1

    messages.append(
        f"  atomic raw payloads: {valid_count} valid, {invalid_count} invalid"
    )
    if valid_count == 0:
        ok = False
        messages.append("  No valid atomic raw payloads detected")
    return ok, messages


def _supernova_manifest_has_curated_photometry(root: Path) -> bool:
    """
    Return True if raw/supernova_raw/manifest.json has at least one artifact
    with usable_photometry_points > 0 (per step 02 contract).
    """
    manifest_path = root / RAW_SUPERNOVA_DIR / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(manifest, dict):
        return False
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    for entry in artifacts:
        if not isinstance(entry, dict):
            continue
        try:
            n = int(entry.get("usable_photometry_points", 0))
        except (TypeError, ValueError):
            continue
        if n > 0:
            return True
    return False


def check_data_csv(root: Path) -> tuple[bool, list[str]]:
    """Check data CSVs: exist, headers, required columns. Return (ok, msgs)."""
    messages: list[str] = []
    ok = True
    has_curated_photometry = _supernova_manifest_has_curated_photometry(root)
    lc_data_rows: int | None = None
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
                if filename in ATOMIC_DATA_FILES and row_count == 0:
                    messages.append(
                        f"  {filename}: atomic data file has header only or no rows"
                    )
                    ok = False
                if filename == "supernova_lightcurves_long.csv":
                    lc_data_rows = row_count
        except Exception as e:
            messages.append(f"Error reading {path}: {e}")
            ok = False

    if has_curated_photometry and lc_data_rows is not None and lc_data_rows == 0:
        messages.append(
            "  supernova_lightcurves_long.csv: curated photometry-bearing raw "
            "artifacts exist but light-curve data has zero rows (sufficiency gate)"
        )
        ok = False

    summary_path = root / DATA_DIR / "supernova_event_summary.csv"
    if summary_path.exists():
        try:
            with summary_path.open(newline="", encoding="utf-8") as sum_f:
                sum_reader = csv.DictReader(sum_f)
                if sum_reader.fieldnames:
                    rise_n = decay_n = peak_width_n = 0
                    for row in sum_reader:
                        v = (row.get("rise_time_days") or "").strip()
                        if v and v not in ("nan", "NaN"):
                            rise_n += 1
                        v = (row.get("decay_time_days") or "").strip()
                        if v and v not in ("nan", "NaN"):
                            decay_n += 1
                        v = (row.get("peak_width_days") or "").strip()
                        if v and v not in ("nan", "NaN"):
                            peak_width_n += 1
                    if rise_n == 0 and decay_n == 0 and peak_width_n == 0:
                        messages.append(
                            "  supernova_event_summary.csv: zero non-empty values "
                            "across rise_time_days, decay_time_days, peak_width_days "
                            "(timing coverage gate)"
                        )
                        ok = False
        except Exception as e:
            messages.append(f"Error reading event summary for timing gate: {e}")
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


def _non_empty_timing(s: str) -> bool:
    """Return True if value is non-empty and not nan."""
    v = (s or "").strip()
    return bool(v and v not in ("nan", "NaN"))


def print_summary_from_data(root: Path) -> None:
    """Print quality-control summary from data/ CSVs (task Part D)."""
    summary_path = root / DATA_DIR / "supernova_event_summary.csv"
    catalog_path = root / DATA_DIR / "supernova_catalog_clean.csv"
    atomic_clean_path = root / DATA_DIR / "atomic_lines_clean.csv"
    atomic_summary_path = root / DATA_DIR / "atomic_transition_summary.csv"

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
    # Supernova: explicit catalog, unique SNe with LC, long-table count, timing
    if catalog_path.exists():
        _, n_cat = read_csv_header_and_count(catalog_path)
        print(f"3. Supernova catalog rows: {n_cat}")
    else:
        print("3. Supernova catalog rows: (no catalog)")
    lc_path = root / DATA_DIR / "supernova_lightcurves_long.csv"
    if lc_path.exists():
        _, n_lc_rows = read_csv_header_and_count(lc_path)
        with lc_path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            sn_with_lc = len({row.get("sn_name", "") for row in r})
        print(f"4. Unique supernovae with light-curve rows: {sn_with_lc}")
        print(f"5. Supernova long-table row count: {n_lc_rows}")
    else:
        print("4. Unique supernovae with light-curve rows: (no lightcurves file)")
        print("5. Supernova long-table row count: (no lightcurves file)")
    if summary_path.exists():
        with summary_path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            with_rise = sum(
                1 for row in r if _non_empty_timing(row.get("rise_time_days", ""))
            )
        with summary_path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            with_decay = sum(
                1 for row in r if _non_empty_timing(row.get("decay_time_days", ""))
            )
        with summary_path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            with_peak_width = sum(
                1 for row in r if _non_empty_timing(row.get("peak_width_days", ""))
            )
        print(f"6. Rows with non-empty rise_time_days: {with_rise}")
        print(f"7. Rows with non-empty decay_time_days: {with_decay}")
        print(f"8. Rows with non-empty peak_width_days: {with_peak_width}")
    else:
        print("6. Rows with non-empty rise_time_days: (no event summary)")
        print("7. Rows with non-empty decay_time_days: (no event summary)")
        print("8. Rows with non-empty peak_width_days: (no event summary)")
    print("9. Sources: (see source_catalog in data files)")
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

    print("\n--- Atomic raw payloads ---")
    ok, msgs = check_atomic_raw_payloads(root)
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

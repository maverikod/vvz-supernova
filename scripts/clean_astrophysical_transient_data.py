"""
Clean astrophysical transient data and write data/ CSVs.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/clean_astrophysical_transient_data.py
Input: raw/astrophysical_transient_raw/ created by step 03.
Output: data/astrophysical_transient_catalog_clean.csv,
        data/astrophysical_transient_lightcurves_long.csv
No synthetic fill; missing values remain empty.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_COLUMNS = (
    "event_id name transient_class ra dec redshift peak_mag peak_abs_mag flux "
    "band distance_Mpc rise_time_days decay_time_days width_days "
    "number_of_points source_catalog discovery_mjd peak_mjd host_galaxy"
).split()
LIGHTCURVE_COLUMNS = (
    "event_id mjd mag mag_err flux flux_err band instrument source_catalog".split()
)
MANIFEST_FIELDS = (
    "source_catalog source_url download_date_utc dataset_identifier artifacts".split()
)
ARTIFACT_FIELDS = ("event_name", "raw_file", "usable_photometry_points")
RawStats = tuple[int, set[float], set[float], set[str]]

_MJD_EPOCH = date(1858, 11, 17)


def safe_float(value: object) -> float | None:
    """Convert a raw value to a finite float or None."""
    if value is None:
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_int(value: object) -> int:
    """Convert a raw value to int or zero."""
    number = safe_float(value)
    return int(number) if number is not None else 0


def clean_string(value: object) -> str:
    """Convert a raw value to a stripped string without synthetic defaults."""
    return str(value).strip() if value is not None else ""


def first_value(value: object) -> str:
    """Return the first OSC-style `value` entry or a plain string."""
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return clean_string(first.get("value"))
    return clean_string(value)


def parse_ra_hms(value: object) -> float | None:
    """Parse RA string `HH:MM:SS` to decimal degrees."""
    parts = first_value(value).replace(",", ".").split(":")
    if not parts or not parts[0]:
        return None
    try:
        hours = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0.0
        seconds = float(parts[2]) if len(parts) > 2 else 0.0
    except (ValueError, IndexError):
        return None
    degrees = 15.0 * (hours + minutes / 60.0 + seconds / 3600.0)
    return degrees if math.isfinite(degrees) else None


def parse_dec_dms(value: object) -> float | None:
    """Parse Dec string `DD:MM:SS` to decimal degrees."""
    raw = first_value(value)
    if not raw:
        return None
    sign = -1.0 if raw.startswith("-") else 1.0
    unsigned = raw[1:] if raw[:1] in "+-" else raw
    parts = unsigned.replace(",", ".").split(":")
    try:
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0.0
        seconds = float(parts[2]) if len(parts) > 2 else 0.0
    except (ValueError, IndexError):
        return None
    dec = sign * (degrees + minutes / 60.0 + seconds / 3600.0)
    return dec if math.isfinite(dec) else None


def parse_date_mjd(value: object) -> float | None:
    """Parse `YYYY/MM/DD` into MJD."""
    raw = first_value(value)
    parts = raw.split("/")
    if len(parts) != 3:
        return None
    try:
        year, month, day = (int(part) for part in parts)
        return float((date(year, month, day) - _MJD_EPOCH).days)
    except (TypeError, ValueError, OverflowError):
        return None


def csv_cell(value: object) -> object:
    """Convert missing numeric values to empty CSV cells."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return ""
    return value


def remove_exact_duplicates(
    rows: list[dict[str, object]], columns: list[str]
) -> list[dict[str, object]]:
    """Remove exact duplicates while preserving order."""
    seen: set[tuple[object, ...]] = set()
    unique_rows: list[dict[str, object]] = []
    for row in rows:
        key = tuple(csv_cell(row.get(column)) for column in columns)
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    return unique_rows


def read_json_dict(path: Path) -> dict[str, object]:
    """Read a JSON file and require a dictionary root object."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root in '{path.name}' must be an object.")
    return payload


def write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    """Write a CSV file with the provided rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: csv_cell(row.get(column)) for column in columns})


def read_manifest(raw_dir: Path) -> dict[str, object]:
    """Read and validate the step-03 manifest."""
    manifest_path = raw_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file is missing: {manifest_path}")
    manifest = read_json_dict(manifest_path)
    for field in MANIFEST_FIELDS:
        if field not in manifest:
            raise ValueError(f"Manifest is missing required field '{field}'.")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Manifest contains no raw photometry artifacts.")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("Manifest contains a non-dictionary artifact entry.")
        for field in ARTIFACT_FIELDS:
            if field not in artifact:
                raise ValueError(f"Artifact is missing required field '{field}'.")
    return manifest


def build_lightcurve_row(
    event_name: str,
    source_catalog: str,
    sample: dict[str, object],
) -> dict[str, object] | None:
    """Normalize one photometry sample to the long-format schema."""
    if clean_string(sample.get("u_time")).upper() != "MJD":
        return None
    mjd = safe_float(sample.get("time"))
    if mjd is None:
        return None
    mag = safe_float(sample.get("magnitude"))
    flux = safe_float(sample.get("flux"))
    if mag is None and flux is None:
        return None
    flux_err = safe_float(sample.get("e_flux"))
    band = clean_string(sample.get("band"))
    instrument = clean_string(sample.get("instrument")) or clean_string(
        sample.get("telescope")
    )
    return {
        "event_id": event_name,
        "mjd": mjd,
        "mag": mag,
        "mag_err": safe_float(sample.get("e_magnitude")),
        "flux": flux,
        "flux_err": flux_err,
        "band": band,
        "instrument": instrument,
        "source_catalog": source_catalog,
    }


def load_artifact_rows(
    raw_dir: Path,
    artifact: dict[str, object],
    source_catalog: str,
) -> tuple[dict[str, object], list[dict[str, object]], RawStats]:
    """Load one raw artifact and return catalog row, lightcurves, and raw stats."""
    event_name = clean_string(artifact.get("event_name"))
    raw_file = clean_string(artifact.get("raw_file"))
    artifact_path = raw_dir / raw_file
    if not artifact_path.exists():
        raise FileNotFoundError(f"Raw artifact file is missing: {artifact_path}")
    payload = read_json_dict(artifact_path)
    event_block = payload.get(event_name)
    if not isinstance(event_block, dict):
        raise ValueError(f"Event '{event_name}' is missing from '{raw_file}'.")
    photometry = event_block.get("photometry")
    if not isinstance(photometry, list):
        raise ValueError(f"Event '{event_name}' has no photometry list.")

    lightcurves: list[dict[str, object]] = []
    raw_mjds: set[float] = set()
    raw_mags: set[float] = set()
    raw_bands: set[str] = set()
    for sample in photometry:
        if not isinstance(sample, dict):
            continue
        lightcurve_row = build_lightcurve_row(event_name, source_catalog, sample)
        if lightcurve_row is None:
            continue
        lightcurves.append(lightcurve_row)
        mjd = safe_float(lightcurve_row.get("mjd"))
        if mjd is not None:
            raw_mjds.add(mjd)
        mag = safe_float(lightcurve_row.get("mag"))
        if mag is not None:
            raw_mags.add(mag)
        band = clean_string(lightcurve_row.get("band"))
        if band:
            raw_bands.add(band)

    usable_points = safe_int(artifact.get("usable_photometry_points"))
    if usable_points > 0 and not lightcurves:
        raise ValueError(
            f"Artifact '{event_name}' is photometry-bearing but produced no rows."
        )

    peak_sample = min(
        (row for row in lightcurves if safe_float(row.get("mag")) is not None),
        key=lambda row: safe_float(row.get("mag")) or math.inf,
        default={},
    )
    min_mjd = min(raw_mjds) if raw_mjds else None
    max_mjd = max(raw_mjds) if raw_mjds else None
    peak_mjd = safe_float(peak_sample.get("mjd"))
    if peak_mjd is None:
        peak_mjd = parse_date_mjd(event_block.get("maxdate"))
    rise_time_days = None
    decay_time_days = None
    width_days = None
    if min_mjd is not None and max_mjd is not None and max_mjd > min_mjd:
        width_days = max_mjd - min_mjd
    if peak_mjd is not None and min_mjd is not None and peak_mjd > min_mjd:
        rise_time_days = peak_mjd - min_mjd
    if peak_mjd is not None and max_mjd is not None and max_mjd > peak_mjd:
        decay_time_days = max_mjd - peak_mjd
    catalog_row: dict[str, object] = {
        "event_id": event_name,
        "name": event_name,
        "transient_class": first_value(event_block.get("claimedtype")),
        "ra": parse_ra_hms(event_block.get("ra")),
        "dec": parse_dec_dms(event_block.get("dec")),
        "redshift": safe_float(first_value(event_block.get("redshift"))),
        "peak_mag": safe_float(peak_sample.get("mag")),
        "peak_abs_mag": safe_float(first_value(event_block.get("maxabsmag"))),
        "flux": None,
        "band": clean_string(peak_sample.get("band")),
        "distance_Mpc": safe_float(first_value(event_block.get("lumdist"))),
        "rise_time_days": rise_time_days,
        "decay_time_days": decay_time_days,
        "width_days": width_days,
        "number_of_points": len(lightcurves),
        "source_catalog": source_catalog,
        "discovery_mjd": parse_date_mjd(event_block.get("discoverdate")),
        "peak_mjd": peak_mjd,
        "host_galaxy": first_value(event_block.get("host")),
    }
    return catalog_row, lightcurves, (usable_points, raw_mjds, raw_mags, raw_bands)


def load_clean_outputs(
    raw_dir: Path, manifest: dict[str, object]
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, RawStats]]:
    """Load all raw artifacts and return cleaned catalog/lightcurve rows."""
    source_catalog = clean_string(manifest.get("source_catalog"))
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("Manifest artifacts must be a list.")
    catalog_rows: list[dict[str, object]] = []
    lightcurve_rows: list[dict[str, object]] = []
    raw_stats: dict[str, RawStats] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        catalog_row, event_lightcurves, event_stats = load_artifact_rows(
            raw_dir=raw_dir,
            artifact=artifact,
            source_catalog=source_catalog,
        )
        catalog_rows.append(catalog_row)
        lightcurve_rows.extend(event_lightcurves)
        raw_stats[clean_string(catalog_row["event_id"])] = event_stats
    catalog_rows = remove_exact_duplicates(catalog_rows, CATALOG_COLUMNS)
    lightcurve_rows = remove_exact_duplicates(lightcurve_rows, LIGHTCURVE_COLUMNS)
    counts_by_event: dict[str, int] = {}
    for row in lightcurve_rows:
        event_id = clean_string(row.get("event_id"))
        counts_by_event[event_id] = counts_by_event.get(event_id, 0) + 1
    for row in catalog_rows:
        row["number_of_points"] = counts_by_event.get(
            clean_string(row.get("event_id")), 0
        )
    return catalog_rows, lightcurve_rows, raw_stats


def read_csv_rows(path: Path, required_columns: list[str]) -> list[dict[str, str]]:
    """Read a CSV file and verify that all required columns exist."""
    if not path.exists():
        raise RuntimeError(f"Required output does not exist: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        for column in required_columns:
            if column not in headers:
                raise RuntimeError(
                    f"Output '{path.name}' is missing column '{column}'."
                )
        return list(reader)


def verify_completeness(
    catalog_path: Path,
    lightcurves_path: Path,
    manifest: dict[str, object],
    raw_stats: dict[str, RawStats],
) -> None:
    """Verify output completeness and reject metadata-only success states."""
    catalog_rows = read_csv_rows(catalog_path, CATALOG_COLUMNS)
    lightcurve_rows = read_csv_rows(lightcurves_path, LIGHTCURVE_COLUMNS)
    counts_by_event: dict[str, int] = {}
    for row in lightcurve_rows:
        event_id = clean_string(row.get("event_id"))
        if not event_id:
            raise RuntimeError("Lightcurve row has an empty event_id.")
        if safe_float(row.get("mjd")) is None:
            raise RuntimeError(f"Lightcurve row for '{event_id}' has invalid mjd.")
        if safe_float(row.get("mag")) is None and safe_float(row.get("flux")) is None:
            raise RuntimeError(
                f"Lightcurve row for '{event_id}' has neither mag nor flux."
            )
        counts_by_event[event_id] = counts_by_event.get(event_id, 0) + 1

    for row in catalog_rows:
        event_id = clean_string(row.get("event_id"))
        stats = raw_stats.get(event_id)
        if stats is None:
            raise RuntimeError(f"Catalog row references unknown event '{event_id}'.")
        _, raw_mjds, raw_mags, raw_bands = stats
        if clean_string(row.get("name")) != event_id:
            raise RuntimeError(f"Catalog row name/event_id mismatch for '{event_id}'.")
        if clean_string(row.get("source_catalog")) != clean_string(
            manifest.get("source_catalog")
        ):
            raise RuntimeError(f"Catalog row source_catalog mismatch for '{event_id}'.")
        if safe_int(row.get("number_of_points")) != counts_by_event.get(event_id, 0):
            raise RuntimeError(f"Catalog number_of_points mismatch for '{event_id}'.")
        peak_mag = safe_float(row.get("peak_mag"))
        peak_mjd = safe_float(row.get("peak_mjd"))
        if peak_mag is not None and peak_mag not in raw_mags:
            raise RuntimeError(
                f"Catalog peak_mag was not observed in raw '{event_id}'."
            )
        if peak_mjd is not None and peak_mjd not in raw_mjds:
            raise RuntimeError(
                f"Catalog peak_mjd was not observed in raw '{event_id}'."
            )
        band = clean_string(row.get("band"))
        if band and band not in raw_bands:
            raise RuntimeError(f"Catalog band was not observed in raw '{event_id}'.")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise RuntimeError("Manifest artifacts must be a list.")
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        event_name = clean_string(artifact.get("event_name"))
        usable_points = safe_int(artifact.get("usable_photometry_points"))
        if usable_points > 0 and counts_by_event.get(event_name, 0) == 0:
            raise RuntimeError(
                f"Photometry-bearing event '{event_name}' produced no lightcurve rows."
            )

    if (
        any(
            isinstance(artifact, dict)
            and safe_int(artifact.get("usable_photometry_points")) > 0
            for artifact in artifacts
        )
        and not lightcurve_rows
    ):
        raise RuntimeError(
            "Photometry-bearing raw input produced a header-only lightcurve table."
        )


def run_fill_validation(*paths: tuple[Path, list[str]]) -> None:
    """Print a message for each output column that is completely empty."""
    for path, columns in paths:
        if not path.exists():
            continue
        rows = read_csv_rows(path, columns)
        for column in columns:
            if not any(clean_string(row.get(column)) for row in rows):
                print(f"Column '{column}' in {path} is completely empty.")


def main() -> int:
    """Clean astrophysical transient raw data and verify produced outputs."""
    raw_dir = ROOT / "raw" / "astrophysical_transient_raw"
    data_dir = ROOT / "data"
    catalog_path = data_dir / "astrophysical_transient_catalog_clean.csv"
    lightcurves_path = data_dir / "astrophysical_transient_lightcurves_long.csv"
    output_paths = (
        (catalog_path, CATALOG_COLUMNS),
        (lightcurves_path, LIGHTCURVE_COLUMNS),
    )

    try:
        if not raw_dir.exists():
            write_csv(catalog_path, CATALOG_COLUMNS, [])
            write_csv(lightcurves_path, LIGHTCURVE_COLUMNS, [])
            raise FileNotFoundError(f"Raw directory is missing: {raw_dir}")
        manifest = read_manifest(raw_dir)
        catalog_rows, lightcurve_rows, raw_stats = load_clean_outputs(raw_dir, manifest)
        write_csv(catalog_path, CATALOG_COLUMNS, catalog_rows)
        write_csv(lightcurves_path, LIGHTCURVE_COLUMNS, lightcurve_rows)
        verify_completeness(catalog_path, lightcurves_path, manifest, raw_stats)
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ) as exc:
        print(f"Astrophysical transient cleaning failed: {exc}", file=sys.stderr)
        run_fill_validation(*output_paths)
        return 1

    run_fill_validation(*output_paths)
    print(f"Wrote {catalog_path}")
    print(f"Wrote {lightcurves_path}")
    print("Astrophysical transient completeness verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

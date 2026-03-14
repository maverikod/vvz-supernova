"""
Download astrophysical transient data into raw/astrophysical_transient_raw/.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Downloads from allowed sources (Open Supernova Catalog per §8.2 / §12.2).
Writes manifest with provenance per §12.3: source_catalog, source_url,
download_date_utc, dataset_identifier. Implements completeness verification
and fill validation at end of script.

Run: python scripts/download_astrophysical_transient_data.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Open Supernova Catalog: bulk JSON (allowed source per TECH_SPEC §12.2).
OSC_CATALOG_URL = (
    "https://raw.githubusercontent.com/astrocatalogs/supernovae/"
    "master/output/catalog.json"
)
OSC_SOURCE_CATALOG = "Open Supernova Catalog"
OSC_SOURCE_URL = "https://sne.space/"
OSC_DATASET_IDENTIFIER = "osc_catalog.json"
USER_AGENT = "supernova-atomic-pipeline/1.0"
MANIFEST_FILENAME = "manifest.json"

DOWNLOAD_CHUNK_BYTES = 256 * 1024
REQUEST_TIMEOUT_SEC = 300

REQUIRED_MANIFEST_FIELDS = (
    "source_catalog",
    "source_url",
    "download_date_utc",
    "dataset_identifier",
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def ensure_raw_dir(raw_dir: Path) -> None:
    """Create raw/astrophysical_transient_raw/ if missing."""
    raw_dir.mkdir(parents=True, exist_ok=True)


def download_osc_catalog(raw_dir: Path) -> tuple[bool, str]:
    """
    Download OSC bulk catalog.json to raw_dir.
    Saves as osc_catalog.json. Returns (success, message).
    """
    out_path = raw_dir / OSC_DATASET_IDENTIFIER
    try:
        req = urllib.request.Request(
            OSC_CATALOG_URL,
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            total = 0
            with open(out_path, "wb") as f:
                while True:
                    chunk = resp.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)
        return True, f"Downloaded {total} bytes to {out_path.name}"
    except Exception as e:
        return False, str(e)


def build_manifest() -> dict[str, str]:
    """Build manifest dict with provenance fields per §12.3."""
    return {
        "source_catalog": OSC_SOURCE_CATALOG,
        "source_url": OSC_SOURCE_URL,
        "download_date_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_identifier": OSC_DATASET_IDENTIFIER,
    }


def write_manifest(raw_dir: Path, manifest: dict[str, str]) -> Path:
    """Write manifest.json to raw_dir. Returns path to manifest."""
    path = raw_dir / MANIFEST_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path


def verify_completeness(raw_dir: Path, manifest_path: Path) -> tuple[bool, str]:
    """
    Verify manifest exists, has required provenance fields, and at least one
    data file exists. Returns (passed, message).
    """
    if not manifest_path.exists():
        return False, "Manifest file does not exist."
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Manifest invalid or unreadable: {e}"
    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in data:
            return False, f"Manifest missing required field: {field}"
        if not isinstance(data[field], str) or not data[field].strip():
            return False, f"Manifest field '{field}' is empty or not a string."
    dataset_id = data.get("dataset_identifier", "").strip()
    if not dataset_id:
        return False, "dataset_identifier is empty; cannot verify data file."
    data_file = raw_dir / dataset_id
    if not data_file.exists() or not data_file.is_file():
        return False, f"Data file '{dataset_id}' missing or not a file."
    return True, "Completeness verification passed."


def run_fill_validation(manifest_path: Path) -> None:
    """
    At end of script: for each required manifest field, if completely empty
    or missing, output a clear message.
    """
    if not manifest_path.exists():
        print("Field 'manifest' is completely empty (file missing).", file=sys.stderr)
        return
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        print(
            "Fill validation skipped: manifest invalid or unreadable.",
            file=sys.stderr,
        )
        return
    for field in REQUIRED_MANIFEST_FIELDS:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            print(
                f"Field '{field}' in manifest is completely empty.",
                file=sys.stderr,
            )


def main() -> int:
    """Download astrophysical transient raw data and write manifest with provenance."""
    root = project_root()
    raw_dir = root / "raw" / "astrophysical_transient_raw"
    ensure_raw_dir(raw_dir)

    ok, msg = download_osc_catalog(raw_dir)
    if not ok:
        print(f"Download failed: {msg}", file=sys.stderr)
        return 1

    print(msg)
    manifest = build_manifest()
    manifest_path = write_manifest(raw_dir, manifest)
    print(f"Manifest written to {manifest_path}")

    passed, verify_msg = verify_completeness(raw_dir, manifest_path)
    if not passed:
        print(f"Completeness verification failed: {verify_msg}", file=sys.stderr)
        return 1
    print(verify_msg)

    run_fill_validation(manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

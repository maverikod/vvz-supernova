"""
Verify raw download artifacts produced by Wave 1 download scripts.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run from project root: python scripts/verify_raw_downloads.py
Checks:
- atomic raw manifest structure and expected spectrum coverage;
- atomic payload file presence, non-empty size, and NIST payload validity;
- supernova raw manifest structure and raw file presence;
- Open Supernova Catalog JSON readability and non-empty top-level object.
Exit: 0 if all raw download checks pass, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.download_atomic_data import build_spectra_list, safe_filename
from scripts.verify_pipeline_data import check_atomic_raw_payloads
from supernova_atomic.oac_event_artifacts import (
    CURATED_OAC_EVENTS,
    event_name_to_raw_filename,
    verify_artifact,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> Any:
    """Load JSON from a UTF-8 file path."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_atomic_downloads(root: Path) -> tuple[bool, list[str]]:
    """Validate atomic raw files and manifest consistency after download."""
    raw_dir = root / "raw" / "atomic_lines_raw"
    manifest_path = raw_dir / "manifest.json"
    messages: list[str] = []
    ok = True

    if not raw_dir.is_dir():
        return False, [f"Missing atomic raw directory: {raw_dir}"]
    if not manifest_path.is_file():
        return False, [f"Missing atomic manifest: {manifest_path}"]

    try:
        manifest = _load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"Unreadable atomic manifest: {exc}"]

    if not isinstance(manifest, dict):
        return False, ["Atomic manifest root must be a JSON object"]

    files = manifest.get("files")
    if not isinstance(files, list):
        return False, ["Atomic manifest field 'files' must be a list"]

    expected_spectra = build_spectra_list()
    expected_set = set(expected_spectra)
    seen_spectra: set[str] = set()

    if manifest.get("source_catalog") != "NIST ASD":
        messages.append("Atomic manifest source_catalog must be 'NIST ASD'")
        ok = False

    download_date = manifest.get("download_date_utc")
    if not isinstance(download_date, str) or not download_date.strip():
        messages.append("Atomic manifest download_date_utc must be a non-empty string")
        ok = False

    valid_payload_count = 0
    for entry in files:
        if not isinstance(entry, dict):
            messages.append("Atomic manifest contains a non-object file entry")
            ok = False
            continue

        spectrum = entry.get("spectrum")
        filename = entry.get("file")
        source_url = entry.get("source_url")
        valid_payload = entry.get("valid_payload")

        if not isinstance(spectrum, str) or not spectrum.strip():
            messages.append("Atomic manifest entry has empty spectrum")
            ok = False
            continue
        if not isinstance(filename, str) or not filename.strip():
            messages.append(f"Atomic manifest entry for {spectrum} has empty file name")
            ok = False
            continue
        if not isinstance(source_url, str) or not source_url.startswith(
            "https://physics.nist.gov/cgi-bin/ASD/lines1.pl?"
        ):
            messages.append(
                f"Atomic manifest entry for {spectrum} has unexpected source_url"
            )
            ok = False
        if not isinstance(valid_payload, bool):
            messages.append(
                f"Atomic manifest entry for {spectrum} has non-boolean valid_payload"
            )
            ok = False
        elif valid_payload:
            valid_payload_count += 1

        expected_filename = f"{safe_filename(spectrum)}.txt"
        if filename != expected_filename:
            messages.append(f"Atomic manifest file mismatch for {spectrum}: {filename}")
            ok = False

        if spectrum in seen_spectra:
            messages.append(f"Duplicate atomic manifest entry for spectrum: {spectrum}")
            ok = False
        seen_spectra.add(spectrum)

        if spectrum not in expected_set:
            messages.append(f"Unexpected spectrum in atomic manifest: {spectrum}")
            ok = False

        file_path = raw_dir / filename
        if not file_path.is_file():
            messages.append(f"Missing atomic raw file: {filename}")
            ok = False
        elif file_path.stat().st_size == 0:
            messages.append(f"Atomic raw file is empty: {filename}")
            ok = False

    missing_spectra = sorted(expected_set - seen_spectra)
    if missing_spectra:
        messages.append(
            "Missing spectra in atomic manifest: "
            + ", ".join(missing_spectra[:5])
            + (" ..." if len(missing_spectra) > 5 else "")
        )
        ok = False

    payload_ok, payload_messages = check_atomic_raw_payloads(root)
    messages.extend(payload_messages)
    ok = ok and payload_ok
    messages.append(
        "  atomic manifest entries: "
        f"{len(files)}; expected spectra: {len(expected_spectra)}"
    )
    messages.append(
        "  atomic manifest valid_payload=true count: " f"{valid_payload_count}"
    )
    return ok, messages


def _required_supernova_raw_files() -> list[str]:
    """Return exact list of required supernova raw filenames (OSC + curated events)."""
    files = ["osc_catalog.json"]
    for event_name in CURATED_OAC_EVENTS:
        files.append(event_name_to_raw_filename(event_name))
    return files


def check_supernova_downloads(root: Path) -> tuple[bool, list[str]]:
    """
    Validate supernova raw manifest, bulk OSC catalog, and curated OAC artifacts.

    Requires: osc_catalog.json plus the curated SN2014J/SN2011fe/SN1987A
    artifacts. Manifest may contain additional OAC artifacts, but the curated
    trio must always be present. Each listed artifact is verified via the OAC
    helper; missing file, unreadable JSON, empty photometry, or count mismatch
    causes failure. OSC bulk readability is necessary but not sufficient.
    """
    raw_dir = root / "raw" / "supernova_raw"
    manifest_path = raw_dir / "manifest.json"
    messages: list[str] = []
    ok = True

    if not raw_dir.is_dir():
        return False, [f"Missing supernova raw directory: {raw_dir}"]
    if not manifest_path.is_file():
        return False, [f"Missing supernova manifest: {manifest_path}"]

    try:
        manifest = _load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"Unreadable supernova manifest: {exc}"]

    if not isinstance(manifest, dict):
        return False, ["Supernova manifest root must be a JSON object"]

    used = manifest.get("sources_used")
    skipped = manifest.get("sources_skipped")
    if not isinstance(used, list):
        messages.append("Supernova manifest field 'sources_used' must be a list")
        ok = False
        used = []
    if not isinstance(skipped, list):
        messages.append("Supernova manifest field 'sources_skipped' must be a list")
        ok = False
        skipped = []

    download_date = manifest.get("download_date_utc")
    if not isinstance(download_date, str) or not download_date.strip():
        messages.append(
            "Supernova manifest download_date_utc must be a non-empty string"
        )
        ok = False

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        messages.append("Supernova manifest field 'artifacts' must be a list")
        ok = False
        artifacts = []
    if len(artifacts) < len(CURATED_OAC_EVENTS):
        messages.append(
            f"Supernova manifest must have at least 3 curated artifacts, "
            f"got {len(artifacts)}"
        )
        ok = False

    required_names = set(CURATED_OAC_EVENTS)
    seen_events: set[str] = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            messages.append("Supernova manifest contains a non-object artifact entry")
            ok = False
            continue
        event_name = entry.get("event_name")
        if not isinstance(event_name, str) or not event_name.strip():
            messages.append("Artifact entry has empty event_name")
            ok = False
            continue
        if event_name in seen_events:
            messages.append(f"Duplicate artifact event_name: {event_name}")
            ok = False
        seen_events.add(event_name)
    if not required_names.issubset(seen_events):
        missing = sorted(required_names - seen_events)
        if missing:
            messages.append(
                f"Manifest missing required curated events: {', '.join(missing)}"
            )
            ok = False

    required_files = _required_supernova_raw_files()
    for raw_file in required_files:
        file_path = raw_dir / raw_file
        if not file_path.is_file():
            messages.append(f"Missing required supernova raw file: {raw_file}")
            ok = False
        elif file_path.stat().st_size == 0:
            messages.append(f"Supernova raw file is empty: {raw_file}")
            ok = False

    osc_file_path = raw_dir / "osc_catalog.json"
    if osc_file_path.is_file():
        try:
            osc_catalog = _load_json(osc_file_path)
        except (OSError, json.JSONDecodeError) as exc:
            messages.append(f"Unreadable OSC catalog JSON: {exc}")
            ok = False
        else:
            if not isinstance(osc_catalog, (dict, list)):
                messages.append("OSC catalog root must be a JSON object or array")
                ok = False
            elif not osc_catalog:
                messages.append("OSC catalog JSON is empty")
                ok = False
            else:
                messages.append(f"  osc catalog records: {len(osc_catalog)}")
    else:
        messages.append("Required file osc_catalog.json is missing")
        ok = False

    verified_count = 0
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_ok, msg = verify_artifact(raw_dir, artifact)
        if not artifact_ok:
            messages.append(msg)
            ok = False
            continue
        usable = artifact.get("usable_photometry_points", 0)
        if not isinstance(usable, int) or usable <= 0:
            messages.append(
                f"Artifact '{artifact.get('event_name', '?')}' has "
                "usable_photometry_points <= 0; required for curated events."
            )
            ok = False
            continue
        verified_count += 1
        messages.append(f"  {msg}")

    messages.append(f"  sources_used: {len(used)}")
    messages.append(f"  sources_skipped: {len(skipped)}")
    messages.append(f"  verified artifacts: {verified_count}")
    return ok, messages


def main() -> int:
    """Run raw-download verification and return a process exit code."""
    root = project_root()
    print(f"Project root: {root}")
    all_ok = True

    print("\n--- Atomic downloads ---")
    ok, messages = check_atomic_downloads(root)
    for message in messages:
        print(message)
    if not ok:
        all_ok = False

    print("\n--- Supernova downloads ---")
    ok, messages = check_supernova_downloads(root)
    for message in messages:
        print(message)
    if not ok:
        all_ok = False

    if all_ok:
        print("\nResult: OK (raw download verification passed)")
        return 0

    print("\nResult: FAIL (see raw download issues above)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

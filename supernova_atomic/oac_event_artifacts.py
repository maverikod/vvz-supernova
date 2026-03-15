"""
OAC event-artifact helper: curated supernova events from Open Astronomy Catalog API.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Provides constants, URL builders, JSON fetch with retry, payload merge,
usable photometry counting, and artifact verification for use by
scripts/download_supernova_data.py and scripts/verify_raw_downloads.py.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Curated OAC event set (exact names for API and filenames).
CURATED_OAC_EVENTS = ("SN2014J", "SN2011fe", "SN1987A")
OAC_SOURCE_NAME = "Open Astronomy Catalog API"
OAC_SOURCE_URL = "https://api.astrocats.space/"
OAC_API_BASE_URL = "https://api.astrocats.space"

USER_AGENT = "supernova-atomic-pipeline/1.0"
REQUEST_TIMEOUT_SEC = 120
MAX_DOWNLOAD_ATTEMPTS = 3
SIGNAL_FIELDS = ("magnitude", "flux", "fluxdensity", "counts")


def event_name_to_raw_filename(event_name: str) -> str:
    """
    Return deterministic raw artifact filename for an event name.
    SN2014J -> sn2014j_event.json, SN2011fe -> sn2011fe_event.json, etc.
    """
    stem = "".join(c if c.isalnum() else "_" for c in event_name).strip("_").lower()
    return f"{stem}_event.json"


def build_metadata_url(event_name: str) -> str:
    """Build OAC metadata endpoint URL for one event."""
    quoted = urllib.parse.quote(event_name, safe="")
    return f"{OAC_API_BASE_URL}/{quoted}"


def build_photometry_url(event_name: str) -> str:
    """Build OAC photometry endpoint URL for one event."""
    quoted = urllib.parse.quote(event_name, safe="")
    return f"{OAC_API_BASE_URL}/{quoted}/photometry"


def fetch_json_bytes(url: str) -> bytes:
    """Download one JSON payload with retries. Raises RuntimeError on failure."""
    last_error = "Unknown download error."
    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
                return bytes(resp.read())
        except (
            TimeoutError,
            OSError,
            urllib.error.HTTPError,
            urllib.error.URLError,
        ) as exc:
            last_error = f"Attempt {attempt}/{MAX_DOWNLOAD_ATTEMPTS} failed: {exc}"
    raise RuntimeError(last_error)


def count_usable_photometry_points(photometry: list[object]) -> int:
    """
    Count rows with non-empty time and at least one non-empty signal field
    among magnitude, flux, fluxdensity, counts.
    """
    count = 0
    for row in photometry:
        if not isinstance(row, dict):
            continue
        time_val = row.get("time")
        has_time = isinstance(time_val, str) and bool(time_val.strip())
        has_signal = any(
            isinstance(row.get(f), str) and bool(row[f].strip()) for f in SIGNAL_FIELDS
        )
        if has_time and has_signal:
            count += 1
    return count


def merge_event_payload(
    metadata_payload: dict[str, Any],
    photometry_payload: dict[str, Any],
    event_name: str,
) -> tuple[dict[str, Any], int, int]:
    """
    Merge metadata and photometry into one JSON object with one top-level key
    equal to event_name and photometry list attached. Returns
    (merged_payload, photometry_points, usable_photometry_points).
    Raises ValueError if structure is invalid or photometry is empty/unusable.
    """
    meta_block = metadata_payload.get(event_name)
    photo_block = photometry_payload.get(event_name)
    if not isinstance(meta_block, dict):
        raise ValueError(f"Event '{event_name}' is missing from metadata payload.")
    if not isinstance(photo_block, dict):
        raise ValueError(f"Event '{event_name}' is missing from photometry payload.")
    photometry = photo_block.get("photometry")
    if not isinstance(photometry, list) or not photometry:
        raise ValueError(f"Event '{event_name}' has no photometry list.")

    merged_block = dict(meta_block)
    merged_block["photometry"] = photometry
    merged_payload: dict[str, Any] = {event_name: merged_block}
    photometry_points = len(photometry)
    usable_points = count_usable_photometry_points(photometry)
    if usable_points == 0:
        raise ValueError(
            f"Event '{event_name}' has no usable photometry rows with time and signal."
        )
    return merged_payload, photometry_points, usable_points


def download_event_artifact(
    raw_dir: Path,
    event_name: str,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """
    Download one OAC event (metadata + photometry), merge, write raw file.
    Returns (artifact_dict, None) on success or (None, failure_dict) on failure.
    Artifact dict has: event_name, metadata_url, photometry_url, raw_file,
    download_date_utc, photometry_points, usable_photometry_points, sha256.
    """
    metadata_url = build_metadata_url(event_name)
    photometry_url = build_photometry_url(event_name)
    raw_file = event_name_to_raw_filename(event_name)
    raw_path = raw_dir / raw_file
    download_date = datetime.now(timezone.utc).isoformat()

    try:
        meta_bytes = fetch_json_bytes(metadata_url)
        photo_bytes = fetch_json_bytes(photometry_url)
        metadata_payload = json.loads(meta_bytes.decode("utf-8"))
        photometry_payload = json.loads(photo_bytes.decode("utf-8"))
        if not isinstance(metadata_payload, dict) or not isinstance(
            photometry_payload, dict
        ):
            raise ValueError("Downloaded payload is not a JSON object.")
        merged_payload, photometry_points, usable_points = merge_event_payload(
            metadata_payload,
            photometry_payload,
            event_name,
        )
        raw_bytes = json.dumps(
            merged_payload,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return None, {
            "event_name": event_name,
            "metadata_url": metadata_url,
            "photometry_url": photometry_url,
            "download_date_utc": download_date,
            "reason": str(exc),
        }

    raw_path.write_bytes(raw_bytes)
    artifact = {
        "event_name": event_name,
        "metadata_url": metadata_url,
        "photometry_url": photometry_url,
        "raw_file": raw_file,
        "download_date_utc": download_date,
        "photometry_points": photometry_points,
        "usable_photometry_points": usable_points,
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
    }
    return artifact, None


def verify_artifact(
    raw_dir: Path,
    artifact: dict[str, Any],
) -> tuple[bool, str]:
    """
    Verify raw artifact: file exists, JSON object, event in payload,
    non-empty photometry, manifest photometry_points and usable_photometry_points
    match the raw file.
    """
    for key in (
        "event_name",
        "raw_file",
        "photometry_points",
        "usable_photometry_points",
    ):
        if key not in artifact:
            return False, f"Artifact is missing required field '{key}'."

    raw_file = artifact.get("raw_file")
    if not isinstance(raw_file, str) or not raw_file.strip():
        return False, "Artifact raw_file is empty."
    raw_path = raw_dir / raw_file
    if not raw_path.exists() or not raw_path.is_file():
        return False, f"Artifact file '{raw_file}' is missing."

    try:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Artifact file '{raw_file}' is unreadable: {exc}"

    if not isinstance(payload, dict):
        return False, "Artifact JSON root must be an object."

    event_name = artifact.get("event_name")
    if not isinstance(event_name, str) or not event_name.strip():
        return False, "Artifact event_name is empty."
    if event_name not in payload:
        return False, f"Event '{event_name}' is missing from the payload."

    event_block = payload[event_name]
    if not isinstance(event_block, dict):
        return False, f"Payload block for '{event_name}' is not an object."
    photometry = event_block.get("photometry")
    if not isinstance(photometry, list) or not photometry:
        return False, f"Event '{event_name}' has no photometry list."

    usable = count_usable_photometry_points(photometry)
    if artifact.get("photometry_points") != len(photometry):
        return False, (
            f"Artifact photometry_points does not match raw file for '{event_name}'."
        )
    if artifact.get("usable_photometry_points") != usable:
        return False, (
            "Artifact usable_photometry_points does not match raw file "
            f"for '{event_name}'."
        )
    return True, f"Artifact '{event_name}' verified with {usable} usable rows."

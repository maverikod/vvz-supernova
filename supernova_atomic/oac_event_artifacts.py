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
EXCLUDED_TYPE_MARKERS = ("candidate", "grb", "nova", "lgrb", "sn impostor")
GENERIC_EXCLUDED_TYPE_MARKERS = ("candidate",)


def event_name_to_raw_filename(event_name: str) -> str:
    """
    Return deterministic raw artifact filename for an event name.
    SN2014J -> sn2014j_event.json, SN2011fe -> sn2011fe_event.json, etc.
    """
    stem = "".join(c if c.isalnum() else "_" for c in event_name).strip("_").lower()
    return f"{stem}_event.json"


def _first_value(values: object) -> str:
    """Return the first OSC-style value string or empty string."""
    if not isinstance(values, list) or not values or not isinstance(values[0], dict):
        return ""
    value = values[0].get("value")
    return str(value).strip() if value is not None else ""


def _safe_sort_float(value: str) -> float:
    """Return a finite float for sorting or +inf when unavailable."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("inf")
    return number if number == number else float("inf")


def _is_extended_candidate(entry: dict[str, Any]) -> bool:
    """Return True when one OSC bulk entry is worth attempting via OAC API."""
    name = str(entry.get("name") or "").strip()
    if not name.startswith("SN") or name in CURATED_OAC_EVENTS:
        return False

    claimed_type = _first_value(entry.get("claimedtype")).lower()
    if not claimed_type or any(
        marker in claimed_type for marker in EXCLUDED_TYPE_MARKERS
    ):
        return False

    max_mag = _first_value(entry.get("maxappmag"))
    max_date = _first_value(entry.get("maxdate"))
    return bool(max_mag and max_date)


def _is_generic_transient_candidate(entry: dict[str, Any]) -> bool:
    """Return True when one OSC bulk entry is worth trying as a generic transient."""
    name = str(entry.get("name") or "").strip()
    if not name:
        return False

    claimed_type = _first_value(entry.get("claimedtype")).lower()
    if claimed_type and any(
        marker in claimed_type for marker in GENERIC_EXCLUDED_TYPE_MARKERS
    ):
        return False

    has_rankable_metadata = any(
        _first_value(entry.get(field))
        for field in ("claimedtype", "discoverdate", "maxdate", "maxappmag")
    )
    return has_rankable_metadata


def _event_family(name: str) -> str:
    """Group transient names into broad families for diversified selection."""
    upper_name = name.upper()
    for prefix, family in (
        ("SN", "sn"),
        ("ASASSN", "asas_sn"),
        ("GAIA", "gaia"),
        ("AT", "at"),
        ("PTF", "ptf"),
        ("PS1", "ps1"),
        ("PSC", "panstarrs"),
        ("VVV", "vvv"),
        ("SPIRITS", "spirits"),
    ):
        if upper_name.startswith(prefix):
            return family
    return "other"


def select_extended_oac_event_names(
    osc_catalog_path: Path,
    *,
    exclude_event_names: set[str] | None = None,
    limit: int,
) -> list[str]:
    """
    Select additional OSC event names for OAC photometry download.

    Deterministic policy:
    - keep only SN-prefixed objects with a non-empty claimed type;
    - reject obvious non-supernova classes like candidates, GRBs, and novae;
    - require both maxappmag and maxdate in OSC bulk metadata;
    - sort by brighter peak magnitude first, then by event name.
    """
    exclude = exclude_event_names or set()
    if limit <= 0 or not osc_catalog_path.is_file():
        return []

    try:
        payload = json.loads(osc_catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    entries: list[object]
    if isinstance(payload, dict):
        entries = list(payload.values())
    elif isinstance(payload, list):
        entries = payload
    else:
        return []

    ranked: list[tuple[float, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not _is_extended_candidate(entry):
            continue
        name = str(entry.get("name") or "").strip()
        if not name or name in exclude or name in seen:
            continue
        seen.add(name)
        ranked.append((_safe_sort_float(_first_value(entry.get("maxappmag"))), name))

    ranked.sort(key=lambda item: (item[0], item[1]))
    return [name for _, name in ranked[:limit]]


def select_extended_transient_event_names(
    osc_catalog_path: Path,
    *,
    exclude_event_names: set[str] | None = None,
    limit: int,
) -> list[str]:
    """
    Select additional transient event names for OAC photometry download.

    Generic policy for the astrophysical branch:
    - accept any named transient-like object, not just SN-prefixed entries;
    - reject obvious unresolved candidates;
    - prefer objects with brighter maxappmag when available;
    - require at least one rankable metadata field so downloads are not random noise.
    """
    exclude = exclude_event_names or set()
    if limit <= 0 or not osc_catalog_path.is_file():
        return []

    try:
        payload = json.loads(osc_catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    entries: list[object]
    if isinstance(payload, dict):
        entries = list(payload.values())
    elif isinstance(payload, list):
        entries = payload
    else:
        return []

    ranked_by_family: dict[str, list[tuple[float, str]]] = {}
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not _is_generic_transient_candidate(entry):
            continue
        name = str(entry.get("name") or "").strip()
        if not name or name in exclude or name in seen:
            continue
        seen.add(name)
        family = _event_family(name)
        ranked_by_family.setdefault(family, []).append(
            (_safe_sort_float(_first_value(entry.get("maxappmag"))), name)
        )

    family_order = [
        "sn",
        "gaia",
        "asas_sn",
        "at",
        "ptf",
        "ps1",
        "panstarrs",
        "vvv",
        "spirits",
        "other",
    ]
    available_families = [
        family for family in family_order if family in ranked_by_family
    ]
    for family in available_families:
        ranked_by_family[family].sort(key=lambda item: (item[0], item[1]))

    selected_names: list[str] = []
    family_index = 0
    while available_families and len(selected_names) < limit:
        family = available_families[family_index]
        family_ranked = ranked_by_family[family]
        _, name = family_ranked.pop(0)
        selected_names.append(name)
        if not family_ranked:
            available_families.pop(family_index)
            if not available_families:
                break
            family_index %= len(available_families)
            continue
        family_index = (family_index + 1) % len(available_families)
    return selected_names


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

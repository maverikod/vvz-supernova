"""
Download astrophysical transient event payloads into raw/astrophysical_transient_raw/.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Each raw artifact is a merged Open Astronomy Catalog event payload with metadata
and photometry for downstream cleaning. The script downloads the curated anchor
events and extends them with additional OSC/OAC events that have useful photometry.

Run: python scripts/download_astrophysical_transient_data.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from supernova_atomic.oac_event_artifacts import (
    CURATED_OAC_EVENTS,
    OAC_SOURCE_NAME,
    OAC_SOURCE_URL,
    download_event_artifact,
    select_extended_transient_event_names,
    verify_artifact,
)

OSC_CATALOG_URL = (
    "https://raw.githubusercontent.com/astrocatalogs/supernovae/"
    "master/output/catalog.json"
)
OSC_SOURCE_URL = "https://sne.space/"
USER_AGENT = "supernova-atomic-pipeline/1.0"
DOWNLOAD_CHUNK_BYTES = 256 * 1024
REQUEST_TIMEOUT_SEC = 300
MANIFEST_FILENAME = "manifest.json"
MIN_EXTENDED_USABLE_PHOTOMETRY_POINTS = 20
DEFAULT_EXTENDED_OAC_CANDIDATE_LIMIT = 500
DEFAULT_EXTENDED_OAC_TARGET_SUCCESS_COUNT = 150
DEFAULT_EXTENDED_OAC_WORKERS = 8
REQUIRED_MANIFEST_FIELDS = (
    "source_catalog",
    "source_url",
    "download_date_utc",
    "dataset_identifier",
)
REQUIRED_ARTIFACT_FIELDS = (
    "event_name",
    "metadata_url",
    "photometry_url",
    "raw_file",
    "download_date_utc",
    "photometry_points",
    "usable_photometry_points",
)


def project_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parent.parent


def utc_now_iso() -> str:
    """Return a stable UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _int_env(name: str, default: int) -> int:
    """Read a positive integer from environment or return the default."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def ensure_raw_dir(raw_dir: Path) -> None:
    """Create the raw output directory when missing."""
    raw_dir.mkdir(parents=True, exist_ok=True)


def download_osc_catalog(raw_dir: Path) -> tuple[bool, str]:
    """Download OSC bulk catalog.json to the astrophysical raw directory."""
    out_path = raw_dir / "osc_catalog.json"
    try:
        request = urllib.request.Request(
            OSC_CATALOG_URL,
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SEC) as response:
            total = 0
            with out_path.open("wb") as handle:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    handle.write(chunk)
                    total += len(chunk)
        return True, f"Downloaded {total} bytes to {out_path.name}"
    except Exception as exc:
        return False, str(exc)


def prune_unreferenced_event_files(
    raw_dir: Path, artifacts: list[dict[str, Any]]
) -> None:
    """Delete stale *_event.json files not referenced by the manifest."""
    keep_files = {str(artifact.get("raw_file", "")).strip() for artifact in artifacts}
    for path in raw_dir.glob("*_event.json"):
        if path.name not in keep_files and path.is_file():
            path.unlink()


def download_curated_artifacts(raw_dir: Path) -> list[dict[str, Any]]:
    """Download the curated anchor events; abort on any failure."""
    artifacts: list[dict[str, Any]] = []
    for event_name in CURATED_OAC_EVENTS:
        artifact, failure = download_event_artifact(raw_dir, event_name)
        if artifact is None:
            reason = failure["reason"] if failure is not None else "unknown error"
            raise RuntimeError(f"OAC download failed for {event_name}: {reason}")
        artifacts.append(artifact)
        print(
            f"Downloaded {artifact['event_name']} with "
            f"{artifact['usable_photometry_points']} usable photometry points."
        )
    return artifacts


def download_extended_oac_artifacts(raw_dir: Path) -> list[dict[str, Any]]:
    """Download additional OAC event artifacts with usable photometry."""
    candidate_limit = _int_env(
        "ASTRO_EXTENDED_OAC_CANDIDATE_LIMIT",
        DEFAULT_EXTENDED_OAC_CANDIDATE_LIMIT,
    )
    target_success_count = _int_env(
        "ASTRO_EXTENDED_OAC_TARGET_SUCCESS_COUNT",
        DEFAULT_EXTENDED_OAC_TARGET_SUCCESS_COUNT,
    )
    worker_count = _int_env(
        "ASTRO_EXTENDED_OAC_WORKERS",
        DEFAULT_EXTENDED_OAC_WORKERS,
    )
    osc_catalog_path = raw_dir / "osc_catalog.json"
    candidate_names = select_extended_transient_event_names(
        osc_catalog_path,
        exclude_event_names=set(CURATED_OAC_EVENTS),
        limit=candidate_limit,
    )
    if not candidate_names:
        return []

    rank = {name: index for index, name in enumerate(candidate_names)}
    artifacts: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        candidate_iter = iter(candidate_names)
        in_flight: dict[
            Future[tuple[dict[str, Any] | None, dict[str, str] | None]], str
        ] = {}

        def submit_until_full() -> None:
            while len(in_flight) < worker_count:
                try:
                    event_name = next(candidate_iter)
                except StopIteration:
                    return
                future = executor.submit(download_event_artifact, raw_dir, event_name)
                in_flight[future] = event_name

        submit_until_full()
        while in_flight and len(artifacts) < target_success_count:
            done, _ = wait(in_flight, return_when=FIRST_COMPLETED)
            for future in done:
                in_flight.pop(future, None)
                artifact, failure = future.result()
                if artifact is None or failure is not None:
                    continue
                usable_points = artifact.get("usable_photometry_points", 0)
                if (
                    not isinstance(usable_points, int)
                    or usable_points < MIN_EXTENDED_USABLE_PHOTOMETRY_POINTS
                ):
                    continue
                artifacts.append(artifact)
                print(
                    f"Downloaded extended {artifact['event_name']} with "
                    f"{artifact['usable_photometry_points']} usable photometry points."
                )
                if len(artifacts) >= target_success_count:
                    break
            submit_until_full()
        for future in in_flight:
            future.cancel()

    artifacts.sort(key=lambda artifact: rank.get(str(artifact["event_name"]), 10**9))
    return artifacts


def write_manifest(raw_dir: Path, artifacts: list[dict[str, Any]]) -> Path:
    """Write manifest.json for downstream cleaning and verification."""
    manifest = {
        "source_catalog": "Open Supernova Catalog via Open Astronomy Catalog API",
        "source_url": OAC_SOURCE_URL,
        "download_date_utc": utc_now_iso(),
        "dataset_identifier": ",".join(
            str(artifact["event_name"])
            for artifact in artifacts
            if artifact.get("event_name")
        ),
        "artifacts": artifacts,
        "sources_used": [
            {
                "name": "Open Supernova Catalog",
                "url": OSC_SOURCE_URL,
                "bulk_file_url": OSC_CATALOG_URL,
                "raw_file": "osc_catalog.json",
            },
            {
                "name": OAC_SOURCE_NAME,
                "url": OAC_SOURCE_URL,
                "dataset_identifier": (
                    "curated:SN2014J,SN2011fe,SN1987A;"
                    "extended:typed-sn-with-maxappmag-and-maxdate"
                ),
                "event_count": len(artifacts),
            },
        ],
        "skipped_artifacts": [],
    }
    manifest_path = raw_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def verify_completeness(raw_dir: Path, manifest_path: Path) -> tuple[bool, str]:
    """Verify manifest provenance and each referenced raw artifact."""
    if not manifest_path.exists():
        return False, "Manifest file does not exist."
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Manifest invalid or unreadable: {exc}"
    if not isinstance(manifest, dict):
        return False, "Manifest root object must be a dictionary."
    for field in REQUIRED_MANIFEST_FIELDS:
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            return False, f"Manifest field '{field}' is empty or missing."
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return (
            False,
            "Manifest artifacts list is empty; no usable raw photometry exists.",
        )
    verified_count = 0
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            return False, "Manifest contains a non-dictionary artifact entry."
        ok, message = verify_artifact(raw_dir, artifact)
        if not ok:
            return False, message
        verified_count += 1
    return (
        True,
        "Completeness verification passed for "
        f"{verified_count} raw photometry artifacts.",
    )


def run_fill_validation(manifest_path: Path) -> None:
    """Print a message for any empty manifest or artifact field."""
    if not manifest_path.exists():
        print("Field 'manifest' in manifest is completely empty.", file=sys.stderr)
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("Field 'manifest' in manifest is completely empty.", file=sys.stderr)
        return
    if not isinstance(manifest, dict):
        print("Field 'manifest' in manifest is completely empty.", file=sys.stderr)
        return
    for field in REQUIRED_MANIFEST_FIELDS:
        value = manifest.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            print(f"Field '{field}' in manifest is completely empty.", file=sys.stderr)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        print("Field 'artifacts' in manifest is completely empty.", file=sys.stderr)
        return
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            print("Field 'artifact' in manifest is completely empty.", file=sys.stderr)
            continue
        event_name = artifact.get("event_name", "<unknown>")
        for field in REQUIRED_ARTIFACT_FIELDS:
            value = artifact.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                print(
                    f"Field '{field}' in artifact '{event_name}' is completely empty.",
                    file=sys.stderr,
                )


def main() -> int:
    """Download raw astrophysical transient payloads and verify manifest coverage."""
    raw_dir = project_root() / "raw" / "astrophysical_transient_raw"
    ensure_raw_dir(raw_dir)

    ok, message = download_osc_catalog(raw_dir)
    if not ok:
        print(f"OSC download failed: {message}", file=sys.stderr)
        return 1
    print(message)

    try:
        artifacts = download_curated_artifacts(raw_dir)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    extended_artifacts = download_extended_oac_artifacts(raw_dir)
    artifacts.extend(extended_artifacts)
    prune_unreferenced_event_files(raw_dir, artifacts)
    print(
        "Extended OAC artifact coverage: "
        f"{len(extended_artifacts)} additional events with "
        f">= {MIN_EXTENDED_USABLE_PHOTOMETRY_POINTS} usable photometry points."
    )

    manifest_path = write_manifest(raw_dir, artifacts)
    print(f"Manifest written to {manifest_path}")

    passed, verify_message = verify_completeness(raw_dir, manifest_path)
    run_fill_validation(manifest_path)
    if not passed:
        print(f"Completeness verification failed: {verify_message}", file=sys.stderr)
        return 1
    print(verify_message)
    return 0


if __name__ == "__main__":
    sys.exit(main())

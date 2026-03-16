"""
Download supernova catalogs and light-curves into raw/supernova_raw/.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/download_supernova_data.py
Output: raw/supernova_raw/ with raw files and manifest (source, date, URL).
Sources: Open Supernova Catalog (OSC) bulk catalog.json; OAC API curated events
(SN2014J, SN2011fe, SN1987A). ASAS-SN, ZTF, Pan-STARRS: not implemented.
"""

from __future__ import annotations

import os
import json
import sys
import urllib.request
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

from supernova_atomic.oac_event_artifacts import (
    CURATED_OAC_EVENTS,
    OAC_SOURCE_NAME,
    OAC_SOURCE_URL,
    download_event_artifact,
    select_extended_oac_event_names,
)

# Open Supernova Catalog: bulk JSON from astrocatalogs/supernovae output.
OSC_CATALOG_URL = (
    "https://raw.githubusercontent.com/astrocatalogs/supernovae/"
    "master/output/catalog.json"
)
OSC_SOURCE_NAME = "Open Supernova Catalog"
OSC_SOURCE_URL = "https://sne.space/"
USER_AGENT = "supernova-atomic-pipeline/1.0"

# Chunk size for streaming large download (catalog.json is ~50MB).
DOWNLOAD_CHUNK_BYTES = 256 * 1024
REQUEST_TIMEOUT_SEC = 300
MIN_EXTENDED_USABLE_PHOTOMETRY_POINTS = 20
DEFAULT_EXTENDED_OAC_CANDIDATE_LIMIT = 250
DEFAULT_EXTENDED_OAC_TARGET_SUCCESS_COUNT = 60
DEFAULT_EXTENDED_OAC_WORKERS = 8


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def ensure_raw_dir(raw_dir: Path) -> None:
    """Create raw/supernova_raw/ if missing."""
    raw_dir.mkdir(parents=True, exist_ok=True)


def download_osc_catalog(raw_dir: Path) -> tuple[bool, str]:
    """
    Download OSC bulk catalog.json from GitHub raw to raw_dir.
    Saves as osc_catalog.json. Returns (success, message).
    """
    out_path = raw_dir / "osc_catalog.json"
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


def write_manifest(
    raw_dir: Path,
    sources_used: list[dict],
    sources_skipped: list[dict],
    artifacts: list[dict],
) -> None:
    """
    Write manifest.json with download_date_utc, sources_used, sources_skipped,
    artifacts, and note. Artifacts must have keys: event_name, metadata_url,
    photometry_url, raw_file, download_date_utc, photometry_points,
    usable_photometry_points, sha256.
    """
    manifest = {
        "download_date_utc": datetime.now(timezone.utc).isoformat(),
        "sources_used": sources_used,
        "sources_skipped": sources_skipped,
        "artifacts": artifacts,
        "note": "Raw files only; data/ and plots/ from other scripts.",
    }
    path = raw_dir / "manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _int_env(name: str, default: int) -> int:
    """Read a positive integer from environment or return default."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def prune_unreferenced_event_files(raw_dir: Path, artifacts: list[dict]) -> None:
    """Delete stale *_event.json files that are not referenced by the manifest."""
    keep_files = {str(artifact.get("raw_file", "")).strip() for artifact in artifacts}
    for path in raw_dir.glob("*_event.json"):
        if path.name not in keep_files and path.is_file():
            path.unlink()


def download_extended_oac_artifacts(raw_dir: Path) -> list[dict]:
    """
    Download additional OAC event artifacts beyond the curated subset.

    Candidate policy is deterministic and based on OSC bulk metadata:
    SN-prefixed events only, typed, and with both maxappmag and maxdate.
    Keep only artifacts with enough usable photometry to be time-domain useful.
    """
    candidate_limit = _int_env(
        "SUPERNOVA_EXTENDED_OAC_CANDIDATE_LIMIT",
        DEFAULT_EXTENDED_OAC_CANDIDATE_LIMIT,
    )
    target_success_count = _int_env(
        "SUPERNOVA_EXTENDED_OAC_TARGET_SUCCESS_COUNT",
        DEFAULT_EXTENDED_OAC_TARGET_SUCCESS_COUNT,
    )
    worker_count = _int_env(
        "SUPERNOVA_EXTENDED_OAC_WORKERS",
        DEFAULT_EXTENDED_OAC_WORKERS,
    )
    osc_catalog_path = raw_dir / "osc_catalog.json"
    candidate_names = select_extended_oac_event_names(
        osc_catalog_path,
        exclude_event_names=set(CURATED_OAC_EVENTS),
        limit=candidate_limit,
    )
    if not candidate_names:
        return []

    rank = {name: index for index, name in enumerate(candidate_names)}
    artifacts: list[dict] = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        candidate_iter = iter(candidate_names)
        in_flight: dict[Future[tuple[dict | None, dict | None]], str] = {}

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
                if not isinstance(usable_points, int):
                    continue
                if usable_points < MIN_EXTENDED_USABLE_PHOTOMETRY_POINTS:
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


def main() -> None:
    """Download supernova raw data (OSC bulk + OAC curated events) and manifest."""
    root = project_root()
    raw_dir = root / "raw" / "supernova_raw"
    ensure_raw_dir(raw_dir)

    sources_used: list[dict] = []
    sources_skipped: list[dict] = []

    # Open Supernova Catalog (bulk from GitHub).
    ok, msg = download_osc_catalog(raw_dir)
    if ok:
        sources_used.append(
            {
                "name": OSC_SOURCE_NAME,
                "url": OSC_SOURCE_URL,
                "bulk_file_url": OSC_CATALOG_URL,
                "raw_file": "osc_catalog.json",
            }
        )
        print(msg)
    else:
        sources_skipped.append(
            {
                "name": OSC_SOURCE_NAME,
                "url": OSC_SOURCE_URL,
                "reason": msg,
            }
        )
        print(f"OSC download failed: {msg}")
        sys.exit(1)

    # OAC curated events: all three must succeed with usable_photometry_points > 0.
    artifacts: list[dict] = []
    for event_name in CURATED_OAC_EVENTS:
        artifact, failure = download_event_artifact(raw_dir, event_name)
        if artifact is None and failure is not None:
            print(f"OAC download failed for {event_name}: {failure['reason']}")
            sys.exit(1)
        if artifact is None:
            print(f"OAC download failed for {event_name}: unknown error")
            sys.exit(1)
        if artifact.get("usable_photometry_points", 0) == 0:
            print(
                f"OAC artifact {event_name} has no usable photometry points; aborting."
            )
            sys.exit(1)
        artifacts.append(artifact)
        print(
            f"Downloaded {artifact['event_name']} with "
            f"{artifact['usable_photometry_points']} usable photometry points."
        )

    extended_artifacts = download_extended_oac_artifacts(raw_dir)
    artifacts.extend(extended_artifacts)
    prune_unreferenced_event_files(raw_dir, artifacts)
    print(
        "Extended OAC artifact coverage: "
        f"{len(extended_artifacts)} additional events with "
        f">= {MIN_EXTENDED_USABLE_PHOTOMETRY_POINTS} usable photometry points."
    )

    sources_used.append(
        {
            "name": OAC_SOURCE_NAME,
            "url": OAC_SOURCE_URL,
            "dataset_identifier": (
                "curated:SN2014J,SN2011fe,SN1987A;"
                "extended:typed-sn-with-maxappmag-and-maxdate"
            ),
            "event_count": len(artifacts),
        }
    )

    # Document other catalogs as not implemented (skip and document).
    for name, url in [
        ("ASAS-SN", "https://asas-sn.osu.edu/"),
        ("ZTF", "https://www.ztf.caltech.edu/"),
        ("Pan-STARRS", "https://panstarrs.stsci.edu/"),
    ]:
        sources_skipped.append(
            {
                "name": name,
                "url": url,
                "reason": "Not implemented in this script.",
            }
        )

    write_manifest(raw_dir, sources_used, sources_skipped, artifacts)
    print(f"Manifest written to {raw_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()

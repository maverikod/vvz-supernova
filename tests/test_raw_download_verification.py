"""
Raw download verification tests.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from scripts.download_atomic_data import build_spectra_list, safe_filename
from scripts.verify_raw_downloads import (
    check_atomic_downloads,
    check_supernova_downloads,
)


def _write_atomic_fixture(root: Path, *, omit_last_spectrum: bool = False) -> None:
    """Create a complete atomic raw fixture with valid manifest and payload files."""
    raw_dir = root / "raw" / "atomic_lines_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    spectra = build_spectra_list()
    if omit_last_spectrum:
        spectra = spectra[:-1]

    entries: list[dict[str, object]] = []
    payload = (
        "obs_wl_vac(nm)\tAki(s^-1)\tEi(cm-1)\tEk(cm-1)\tconf_i\tterm_i\tJ_i\t"
        "conf_k\tterm_k\tJ_k\tType\n"
        '"121.567"\t"1.0e+08"\t"0.0"\t"1.0"\t"1s"\t"2S"\t"1/2"\t"2p"\t'
        '"2P"\t"3/2"\t""\n'
    )

    for spectrum in spectra:
        filename = f"{safe_filename(spectrum)}.txt"
        (raw_dir / filename).write_text(payload, encoding="utf-8")
        entries.append(
            {
                "spectrum": spectrum,
                "file": filename,
                "source_url": (
                    "https://physics.nist.gov/cgi-bin/ASD/lines1.pl?"
                    f"spectra={spectrum.replace(' ', '+')}"
                ),
                "valid_payload": True,
            }
        )

    manifest = {
        "source_catalog": "NIST ASD",
        "source_url": "https://physics.nist.gov/PhysRefData/ASD/lines_form.html",
        "download_date_utc": "2026-03-15T00:00:00+00:00",
        "elements_requested": [],
        "ion_stages_requested": [],
        "files": entries,
    }
    (raw_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def _one_event_payload(
    event_name: str,
    usable_rows: int = 1,
) -> dict[str, Any]:
    """Build one event payload with given number of usable photometry rows."""
    if usable_rows <= 0:
        # No usable: empty or no time/signal.
        photometry = [{"time": "", "magnitude": ""}]
    else:
        photometry = [
            {"time": "57000.0", "magnitude": "12.5", "e_magnitude": "0.1"}
            for _ in range(usable_rows)
        ]
    return {
        event_name: {
            "name": event_name,
            "photometry": photometry,
        }
    }


def _artifact_entry(
    event_name: str,
    raw_file: str,
    *,
    photometry_points: int,
    usable_photometry_points: int,
    sha256_char: str = "0",
) -> dict[str, object]:
    """Build one manifest artifact entry."""
    return {
        "event_name": event_name,
        "metadata_url": f"https://api.astrocats.space/{event_name}",
        "photometry_url": f"https://api.astrocats.space/{event_name}/photometry",
        "raw_file": raw_file,
        "download_date_utc": "2026-03-15T00:00:00+00:00",
        "photometry_points": photometry_points,
        "usable_photometry_points": usable_photometry_points,
        "sha256": sha256_char * 64,
    }


def _write_supernova_fixture(
    root: Path,
    *,
    bad_catalog_json: bool = False,
    missing_raw_file: str | None = None,
    zero_usable_photometry_event: str | None = None,
    manifest_count_mismatch_event: str | None = None,
    artifacts_override: list[dict[str, object]] | None = None,
    omit_artifacts_key: bool = False,
    max_artifacts_in_manifest: int | None = None,
) -> None:
    """
    Minimal supernova raw fixture: OSC catalog, OAC event files, manifest.

    Optional tweaks for failure-mode tests:
    - missing_raw_file: do not write this event's raw file.
    - zero_usable_photometry_event: write this event's file with zero usable rows.
    - manifest_count_mismatch_event: manifest says usable_photometry_points=1,
      raw file has 2 usable rows.
    - artifacts_override: use this list as manifest['artifacts'] (e.g. [] or 2 entries).
    - omit_artifacts_key: do not include 'artifacts' in manifest.
    - max_artifacts_in_manifest: if set to 2, manifest gets only first two artifacts
      (all three raw files still written) to test "fewer than 3" failure.
    """
    raw_dir = root / "raw" / "supernova_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = raw_dir / "osc_catalog.json"
    if bad_catalog_json:
        catalog_path.write_text("{not-json", encoding="utf-8")
    else:
        catalog_path.write_text(
            json.dumps(
                {
                    "SN2024abc": {
                        "name": "SN2024abc",
                        "claimedtype": [{"value": "Ia"}],
                    }
                }
            ),
            encoding="utf-8",
        )

    curated = [
        ("SN2014J", "sn2014j_event.json"),
        ("SN2011fe", "sn2011fe_event.json"),
        ("SN1987A", "sn1987a_event.json"),
    ]
    artifacts: list[dict[str, object]] = []
    for event_name, raw_file in curated:
        if missing_raw_file == event_name:
            continue
        if zero_usable_photometry_event == event_name:
            payload = _one_event_payload(event_name, usable_rows=0)
        elif manifest_count_mismatch_event == event_name:
            payload = _one_event_payload(event_name, usable_rows=2)
        else:
            payload = _one_event_payload(event_name, usable_rows=1)

        (raw_dir / raw_file).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        usable = 0 if zero_usable_photometry_event == event_name else 1
        if manifest_count_mismatch_event == event_name:
            usable = 1
        points = len(payload[event_name]["photometry"])
        artifacts.append(
            _artifact_entry(
                event_name,
                raw_file,
                photometry_points=points,
                usable_photometry_points=usable,
            )
        )

    if artifacts_override is not None:
        artifacts = artifacts_override
    elif max_artifacts_in_manifest is not None:
        artifacts = artifacts[:max_artifacts_in_manifest]
    manifest: dict[str, Any] = {
        "download_date_utc": "2026-03-15T00:00:00+00:00",
        "sources_used": [
            {
                "name": "Open Supernova Catalog",
                "url": "https://sne.space/",
                "bulk_file_url": (
                    "https://raw.githubusercontent.com/astrocatalogs/supernovae/"
                    "master/output/catalog.json"
                ),
                "raw_file": "osc_catalog.json",
            },
            {
                "name": "Open Astronomy Catalog API",
                "url": "https://api.astrocats.space/",
                "dataset_identifier": "SN2014J,SN2011fe,SN1987A",
                "event_count": len(artifacts),
            },
        ],
        "sources_skipped": [
            {
                "name": "ASAS-SN",
                "url": "https://asas-sn.osu.edu/",
                "reason": "Not implemented in this script.",
            }
        ],
        "note": "Raw files only; data/ and plots/ from other scripts.",
    }
    if not omit_artifacts_key:
        manifest["artifacts"] = artifacts
    (raw_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


class RawDownloadVerificationTests(unittest.TestCase):
    """Validate the dedicated raw-download verification script."""

    def test_check_atomic_downloads_accepts_complete_valid_fixture(self) -> None:
        """Atomic verification must accept a complete manifest and valid payloads."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_atomic_fixture(root)
            ok, messages = check_atomic_downloads(root)
            self.assertTrue(ok)
            self.assertTrue(
                any("atomic raw payloads:" in message for message in messages)
            )

    def test_check_atomic_downloads_rejects_missing_expected_spectrum(self) -> None:
        """Atomic verification must fail when one expected spectrum is missing."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_atomic_fixture(root, omit_last_spectrum=True)
            ok, messages = check_atomic_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any(
                    "Missing spectra in atomic manifest" in message
                    for message in messages
                )
            )

    def test_check_supernova_downloads_accepts_valid_catalog(self) -> None:
        """Supernova verification must accept a readable non-empty OSC catalog."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root)
            ok, messages = check_supernova_downloads(root)
            self.assertTrue(ok)
            self.assertTrue(
                any("osc catalog records:" in message for message in messages)
            )

    def test_check_supernova_downloads_rejects_invalid_catalog_json(self) -> None:
        """Supernova verification must fail when osc_catalog.json is malformed."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, bad_catalog_json=True)
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any("Unreadable OSC catalog JSON" in message for message in messages)
            )

    def test_check_supernova_downloads_rejects_missing_sn2014j_event(self) -> None:
        """Supernova verification must fail when sn2014j_event.json is missing."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, missing_raw_file="SN2014J")
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any(
                    "sn2014j_event.json" in message and "Missing" in message
                    for message in messages
                )
                or any(
                    "Missing required supernova raw file" in message
                    and "sn2014j_event.json" in message
                    for message in messages
                )
            )

    def test_check_supernova_downloads_rejects_missing_sn2011fe_event(self) -> None:
        """Supernova verification must fail when sn2011fe_event.json is missing."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, missing_raw_file="SN2011fe")
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any(
                    "sn2011fe_event.json" in message and "Missing" in message
                    for message in messages
                )
                or any(
                    "Missing required supernova raw file" in message
                    and "sn2011fe_event.json" in message
                    for message in messages
                )
            )

    def test_check_supernova_downloads_rejects_missing_sn1987a_event(self) -> None:
        """Supernova verification must fail when sn1987a_event.json is missing."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, missing_raw_file="SN1987A")
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any(
                    "sn1987a_event.json" in message and "Missing" in message
                    for message in messages
                )
                or any(
                    "Missing required supernova raw file" in message
                    and "sn1987a_event.json" in message
                    for message in messages
                )
            )

    def test_check_supernova_downloads_rejects_zero_usable_photometry(self) -> None:
        """Fail when a curated artifact has no usable photometry."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, zero_usable_photometry_event="SN2014J")
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any(
                    "usable_photometry_points" in message
                    and ("<= 0" in message or "required" in message)
                    for message in messages
                )
            )

    def test_check_supernova_downloads_rejects_manifest_raw_count_mismatch(
        self,
    ) -> None:
        """Fail when manifest usable_photometry_points does not match raw file."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, manifest_count_mismatch_event="SN2011fe")
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any("does not match raw file" in message for message in messages)
            )

    def test_check_supernova_downloads_rejects_manifest_omits_artifacts(
        self,
    ) -> None:
        """Supernova verification must fail when manifest omits 'artifacts' list."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, omit_artifacts_key=True)
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any(
                    "artifacts" in message and "must be a list" in message
                    for message in messages
                )
            )

    def test_check_supernova_downloads_rejects_manifest_fewer_than_three_artifacts(
        self,
    ) -> None:
        """Fail when manifest has fewer than 3 curated artifacts."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_supernova_fixture(root, max_artifacts_in_manifest=2)
            ok, messages = check_supernova_downloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any(
                    "at least 3 curated artifacts" in message and "got 2" in message
                    for message in messages
                )
            )


if __name__ == "__main__":
    unittest.main()

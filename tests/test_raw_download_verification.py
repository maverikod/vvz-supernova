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


def _write_supernova_fixture(root: Path, *, bad_catalog_json: bool = False) -> None:
    """Minimal supernova raw fixture: OSC catalog, 3 OAC event files, manifest."""
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

    # OAC event payload: one event key, photometry with time+signal.
    curated = [
        ("SN2014J", "sn2014j_event.json"),
        ("SN2011fe", "sn2011fe_event.json"),
        ("SN1987A", "sn1987a_event.json"),
    ]
    artifacts: list[dict[str, object]] = []
    for event_name, raw_file in curated:
        payload = {
            event_name: {
                "name": event_name,
                "photometry": [
                    {"time": "57000.0", "magnitude": "12.5", "e_magnitude": "0.1"}
                ],
            }
        }
        (raw_dir / raw_file).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        artifacts.append(
            {
                "event_name": event_name,
                "metadata_url": f"https://api.astrocats.space/{event_name}",
                "photometry_url": (
                    f"https://api.astrocats.space/{event_name}/photometry"
                ),
                "raw_file": raw_file,
                "download_date_utc": "2026-03-15T00:00:00+00:00",
                "photometry_points": 1,
                "usable_photometry_points": 1,
                "sha256": "0" * 64,
            }
        )

    manifest = {
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
                "event_count": 3,
            },
        ],
        "sources_skipped": [
            {
                "name": "ASAS-SN",
                "url": "https://asas-sn.osu.edu/",
                "reason": "Not implemented in this script.",
            }
        ],
        "artifacts": artifacts,
        "note": "Raw files only; data/ and plots/ from other scripts.",
    }
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


if __name__ == "__main__":
    unittest.main()

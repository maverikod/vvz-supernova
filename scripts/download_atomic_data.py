"""
Download atomic spectral lines from NIST ASD into raw/atomic_lines_raw/.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Fetches data per spectrum (element + ion stage) via NIST CGI interface.
Saves raw response files and a manifest with source, date, and URL.
Run: python scripts/download_atomic_data.py
Output: raw/atomic_lines_raw/*.html, raw/atomic_lines_raw/manifest.json
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Required elements per task_supernova_atomic_pipeline.txt (Part A)
REQUIRED_ELEMENTS = [
    "H",
    "He",
    "C",
    "N",
    "O",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Fe",
    "Ni",
]

# Ion stages: neutral (I) and low ionization (II, III) when available
ION_STAGES = ["I", "II", "III"]

NIST_ASD_BASE = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"
REQUEST_DELAY_SEC = 1.0
TIMEOUT_SEC = 30


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def spectrum_to_param(spectrum: str) -> str:
    """Convert 'H I' to 'H+I' for NIST CGI parameter."""
    return spectrum.replace(" ", "+")


def safe_filename(spectrum: str) -> str:
    """Convert 'H I' to 'H_I' for file name."""
    return re.sub(r"\s+", "_", spectrum.strip())


def build_spectra_list() -> list[str]:
    """Build list of spectra to request: each element with I, II, III."""
    out: list[str] = []
    for el in REQUIRED_ELEMENTS:
        for stage in ION_STAGES:
            out.append(f"{el} {stage}")
    return out


def fetch_nist_spectrum(spectrum: str) -> tuple[bool, str]:
    """
    Request one spectrum from NIST ASD.
    Return (success, body or error message).
    """
    params = {
        "spectra": spectrum_to_param(spectrum),
        "format": "1",
        "output": "0",
        "level_out": "on",
        "line_out": "on",
    }
    url = f"{NIST_ASD_BASE}?{urlencode(params)}"
    try:
        headers = {"User-Agent": "supernova-atomic-pipeline/1.0"}
        req = Request(url, headers=headers)
        with urlopen(req, timeout=TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, body
    except Exception as e:
        return False, str(e)


def main() -> None:
    """
    Ensure raw/atomic_lines_raw/ exists, fetch NIST ASD data per spectrum,
    save raw files and manifest (source, date, URL).
    """
    root = project_root()
    raw_dir = root / "raw" / "atomic_lines_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    spectra = build_spectra_list()
    manifest_entries: list[dict[str, str]] = []
    download_date = datetime.now(timezone.utc).isoformat()
    source_url = "https://physics.nist.gov/PhysRefData/ASD/lines_form.html"

    for i, spectrum in enumerate(spectra):
        if i > 0:
            time.sleep(REQUEST_DELAY_SEC)
        ok, content = fetch_nist_spectrum(spectrum)
        fname = safe_filename(spectrum) + ".html"
        out_path = raw_dir / fname
        if ok:
            out_path.write_text(content, encoding="utf-8")
            query = f"{NIST_ASD_BASE}?spectra={spectrum_to_param(spectrum)}"
            manifest_entries.append(
                {
                    "spectrum": spectrum,
                    "file": fname,
                    "source_url": query,
                }
            )
        else:
            manifest_entries.append(
                {
                    "spectrum": spectrum,
                    "file": fname,
                    "error": content,
                }
            )

    manifest = {
        "source_catalog": "NIST ASD",
        "source_url": source_url,
        "download_date_utc": download_date,
        "elements_requested": REQUIRED_ELEMENTS,
        "ion_stages_requested": ION_STAGES,
        "files": manifest_entries,
    }
    manifest_path = raw_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()

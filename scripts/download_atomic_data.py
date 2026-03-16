"""
Download atomic spectral lines from NIST ASD into raw/atomic_lines_raw/.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Fetches data per spectrum (element + ion stage) via NIST CGI interface.
Saves raw response files and a manifest with source, date, and URL.
Run: python scripts/download_atomic_data.py
Output: raw/atomic_lines_raw/*.txt, raw/atomic_lines_raw/manifest.json
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from supernova_atomic.nist_parser import is_nist_error_text

# Required elements per current TZ
# (docs/TECH_SPEC.md)
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
ION_STAGE_INDEX = {"I": 1, "II": 2, "III": 3}
MAX_SUPPORTED_STAGE_INDEX_BY_ELEMENT = {
    "H": 1,
    "He": 2,
}

NIST_ASD_BASE = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"
REQUEST_DELAY_SEC = 1.0
TIMEOUT_SEC = 30
TEXT_EXPORT_PARAMS = {
    "limits_type": "0",
    "low_w": "",
    "upp_w": "",
    "unit": "1",
    "de": "0",
    "format": "3",
    "line_out": "0",
    "en_unit": "0",
    "output": "0",
    "page_size": "2000",
    "show_obs_wl": "1",
    "show_calc_wl": "1",
    "show_wn": "1",
    "unc_out": "1",
    "order_out": "0",
    "max_low_enrg": "",
    "show_av": "2",
    "max_upp_enrg": "",
    "tsb_value": "0",
    "min_str": "",
    "A_out": "0",
    "f_out": "on",
    "S_out": "on",
    "loggf_out": "on",
    "intens_out": "on",
    "max_str": "",
    "allowed_out": "1",
    "forbid_out": "1",
    "min_accur": "",
    "min_intens": "",
    "conf_out": "on",
    "term_out": "on",
    "enrg_out": "on",
    "J_out": "on",
    "g_out": "on",
}


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def safe_filename(spectrum: str) -> str:
    """Convert 'H I' to 'H_I' for file name."""
    return re.sub(r"\s+", "_", spectrum.strip())


def build_spectra_list() -> list[str]:
    """Build list of spectra to request, skipping unsupported fully ionized states."""
    out: list[str] = []
    for el in REQUIRED_ELEMENTS:
        max_stage_index = MAX_SUPPORTED_STAGE_INDEX_BY_ELEMENT.get(el, 3)
        for stage in ION_STAGES:
            if ION_STAGE_INDEX[stage] > max_stage_index:
                continue
            out.append(f"{el} {stage}")
    return out


def build_query_url(spectrum: str) -> str:
    """Build a valid NIST ASD text-export URL for one spectrum."""
    params = {"spectra": spectrum, **TEXT_EXPORT_PARAMS}
    return f"{NIST_ASD_BASE}?{urlencode(params)}"


def response_has_atomic_payload(body: str) -> bool:
    """Return True when a response looks like real NIST line data."""
    if is_nist_error_text(body):
        return False
    first_line = next((line for line in body.splitlines() if line.strip()), "")
    return "\t" in first_line and "Aki" in first_line


def _remove_stale_raw_files(raw_dir: Path, spectrum: str) -> None:
    """Delete legacy raw files for the same spectrum before rewriting it."""
    stem = safe_filename(spectrum)
    for suffix in (".html", ".txt", ".tsv"):
        stale_path = raw_dir / f"{stem}{suffix}"
        if stale_path.exists():
            stale_path.unlink()


def _purge_atomic_payload_files(raw_dir: Path) -> None:
    """Remove previously downloaded atomic payload files before a fresh rebuild."""
    for path in raw_dir.iterdir():
        if path.name in {".gitkeep", "manifest.json"}:
            continue
        if path.suffix.lower() in {".html", ".txt", ".tsv"}:
            path.unlink()


def fetch_nist_spectrum(spectrum: str) -> tuple[bool, str, str]:
    """Request one spectrum from NIST ASD and return (valid, body, source_url)."""
    url = build_query_url(spectrum)
    try:
        headers = {"User-Agent": "supernova-atomic-pipeline/1.0"}
        req = Request(url, headers=headers)
        with urlopen(req, timeout=TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return response_has_atomic_payload(body), body, url
    except Exception as e:
        return False, str(e), url


def main() -> None:
    """
    Ensure raw/atomic_lines_raw/ exists, fetch NIST ASD data per spectrum,
    save raw files and manifest (source, date, URL).
    """
    root = project_root()
    raw_dir = root / "raw" / "atomic_lines_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    _purge_atomic_payload_files(raw_dir)

    spectra = build_spectra_list()
    manifest_entries: list[dict[str, object]] = []
    download_date = datetime.now(timezone.utc).isoformat()
    source_url = "https://physics.nist.gov/PhysRefData/ASD/lines_form.html"

    for i, spectrum in enumerate(spectra):
        if i > 0:
            time.sleep(REQUEST_DELAY_SEC)
        ok, content, query = fetch_nist_spectrum(spectrum)
        fname = safe_filename(spectrum) + ".txt"
        out_path = raw_dir / fname
        _remove_stale_raw_files(raw_dir, spectrum)
        out_path.write_text(content, encoding="utf-8")
        entry = {
            "spectrum": spectrum,
            "file": fname,
            "source_url": query,
            "valid_payload": ok,
        }
        if not ok:
            entry["error"] = "Invalid NIST response payload"
        manifest_entries.append(entry)

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

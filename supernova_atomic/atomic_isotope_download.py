"""
Atomic isotope download helpers for open spectroscopy sources.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from supernova_atomic.nist_parser import parse_nist_payload

NIST_ASD_BASE: Final[str] = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"
NIST_SOURCE_URL: Final[str] = (
    "https://physics.nist.gov/PhysRefData/ASD/Html/lineshelp.html"
)
KURUCZ_SOURCE_URL: Final[str] = "http://kurucz.harvard.edu/linelists.html"
TIMEOUT_SEC: Final[int] = 30
TEXT_EXPORT_PARAMS: Final[dict[str, str]] = {
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


@dataclass(frozen=True)
class NistIsotopeQuery:
    """One openly accessible isotope-specific NIST spectrum query."""

    spectra: str
    element: str
    ion_stage: str
    isotope_mass: int


@dataclass(frozen=True)
class KuruczArtifact:
    """One openly downloadable Kurucz isotope artifact."""

    artifact_id: str
    url: str
    element: str
    ion_stage: str


NIST_ISOTOPE_QUERIES: Final[tuple[NistIsotopeQuery, ...]] = (
    NistIsotopeQuery("1H I", "H", "I", 1),
    NistIsotopeQuery("2H I", "H", "I", 2),
    NistIsotopeQuery("3He I", "He", "I", 3),
    NistIsotopeQuery("12C I", "C", "I", 12),
    NistIsotopeQuery("13C I", "C", "I", 13),
)

KURUCZ_ISOTOPE_ARTIFACTS: Final[tuple[KuruczArtifact, ...]] = (
    KuruczArtifact(
        artifact_id="gf2601iso_all",
        url="http://kurucz.harvard.edu/atoms/2601/gf2601iso.all",
        element="Fe",
        ion_stage="I",
    ),
    KuruczArtifact(
        artifact_id="gf2801iso_pos",
        url="http://kurucz.harvard.edu/atoms/2801/gf2801iso.pos",
        element="Ni",
        ion_stage="II",
    ),
    KuruczArtifact(
        artifact_id="isoshifts2001_dat",
        url="http://kurucz.harvard.edu/atoms/2001/isoshifts2001.dat",
        element="Ca",
        ion_stage="II",
    ),
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def isotope_raw_dir(root: Path) -> Path:
    """Return the raw directory used for isotope downloads."""
    return root / "raw" / "atomic_isotope_raw"


def build_nist_query_url(spectra: str) -> str:
    """Build the NIST ASD text-export URL for one isotope-specific spectrum."""
    params = {"spectra": spectra, **TEXT_EXPORT_PARAMS}
    return f"{NIST_ASD_BASE}?{urlencode(params)}"


def _safe_name(value: str) -> str:
    """Create a filesystem-safe, ASCII-only filename stem."""
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def _fetch_text(url: str) -> str:
    """Download UTF-8-ish text content from an open URL."""
    request = Request(url, headers={"User-Agent": "supernova-atomic-pipeline/1.0"})
    with urlopen(request, timeout=TIMEOUT_SEC) as response:
        payload = bytes(response.read())
    return payload.decode("utf-8", errors="replace")


def _nist_valid_payload(query: NistIsotopeQuery, body: str, source_url: str) -> bool:
    """Check that the downloaded NIST body parses into at least one line row."""
    rows = parse_nist_payload(
        payload=body,
        element=query.element,
        ion_state=query.ion_stage,
        source_catalog="NIST ASD isotope query",
        source_url=source_url,
    )
    return bool(rows)


def _write_text(path: Path, content: str) -> None:
    """Write text content ensuring parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _download_nist_queries(target_dir: Path) -> list[dict[str, object]]:
    """Download all configured isotope-specific NIST spectra into raw storage."""
    nist_dir = target_dir / "nist"
    nist_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    for query in NIST_ISOTOPE_QUERIES:
        url = build_nist_query_url(query.spectra)
        body = _fetch_text(url)
        filename = f"{_safe_name(query.spectra)}.txt"
        _write_text(nist_dir / filename, body)
        entries.append(
            {
                "source_catalog": "NIST ASD isotope query",
                "source_url": url,
                "file": f"nist/{filename}",
                "element": query.element,
                "ion_stage": query.ion_stage,
                "isotope_mass": query.isotope_mass,
                "query": query.spectra,
                "valid_payload": _nist_valid_payload(query, body, url),
            }
        )
    return entries


def _download_kurucz_artifacts(target_dir: Path) -> list[dict[str, object]]:
    """Download all configured Kurucz isotope artifacts into raw storage."""
    kurucz_dir = target_dir / "kurucz"
    kurucz_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    for artifact in KURUCZ_ISOTOPE_ARTIFACTS:
        body = _fetch_text(artifact.url)
        filename = f"{artifact.artifact_id}.txt"
        _write_text(kurucz_dir / filename, body)
        entries.append(
            {
                "source_catalog": "Kurucz isotope artifacts",
                "source_url": artifact.url,
                "file": f"kurucz/{filename}",
                "element": artifact.element,
                "ion_stage": artifact.ion_stage,
                "artifact_id": artifact.artifact_id,
                "valid_payload": bool(body.strip()),
            }
        )
    return entries


def write_isotope_manifest(
    raw_dir: Path,
    entries: list[dict[str, object]],
) -> None:
    """Write a manifest describing downloaded isotope artifacts."""
    manifest = {
        "source_catalog": "Open isotope spectroscopy bundle",
        "source_urls": [NIST_SOURCE_URL, KURUCZ_SOURCE_URL],
        "download_date_utc": datetime.now(timezone.utc).isoformat(),
        "files": entries,
    }
    _write_text(raw_dir / "manifest.json", json.dumps(manifest, indent=2))


def download_atomic_isotope_data(root: Path | None = None) -> Path:
    """Download all supported isotope artifacts and write the shared manifest."""
    project = root or project_root()
    raw_dir = isotope_raw_dir(project)
    raw_dir.mkdir(parents=True, exist_ok=True)
    entries = _download_nist_queries(raw_dir)
    entries.extend(_download_kurucz_artifacts(raw_dir))
    write_isotope_manifest(raw_dir, entries)
    return raw_dir

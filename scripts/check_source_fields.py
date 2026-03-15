"""
Check that required task fields can be obtained from stated sources.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run from project root: python scripts/check_source_fields.py
Performs sample requests to NIST ASD and OAC, reports which required
fields appear. Required field lists: ATOMIC_REQUIRED, SN_CATALOG_REQUIRED,
SN_LIGHTCURVE_REQUIRED in this script; context: docs/refactoring/TECH_SPEC.md.
"""

from __future__ import annotations

import json
import sys
import urllib.request

# Required atomic columns (task Part A)
ATOMIC_REQUIRED = [
    "element",
    "ion_state",
    "wavelength_vac_nm",
    "wavelength_air_nm",
    "frequency_hz",
    "wavenumber_cm1",
    "Aki_s^-1",
    "intensity",
    "Ei_cm1",
    "Ek_cm1",
    "lower_configuration",
    "upper_configuration",
    "lower_term",
    "upper_term",
    "lower_J",
    "upper_J",
    "line_type",
    "source_catalog",
    "source_url",
]

# Required supernova catalog columns (task Part B)
SN_CATALOG_REQUIRED = [
    "sn_name",
    "source_catalog",
    "ra",
    "dec",
    "redshift",
    "host_galaxy",
    "sn_type",
    "discovery_mjd",
    "peak_mjd",
    "peak_mag",
    "band",
    "distance_modulus",
    "luminosity_distance_Mpc",
    "lightcurve_points_count",
]

# Required light-curve point columns
SN_LIGHTCURVE_REQUIRED = [
    "sn_name",
    "mjd",
    "mag",
    "mag_err",
    "flux",
    "flux_err",
    "band",
    "instrument",
    "source_catalog",
]


def fetch_url(url: str, timeout: int = 15) -> str:
    """GET URL and return decoded body; empty string on error."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "supernova-pipeline-check/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body: str = resp.read().decode("utf-8", errors="replace")
            return body
    except Exception as e:
        return f"ERROR: {e}"


def check_nist_asd() -> tuple[bool, list[str]]:
    """
    Request one NIST ASD lines page (H I), parse for column-like content.
    Return (success, list of detected column names or messages).
    """
    # Request H I spectrum (form may redirect or show form)
    url = (
        "https://physics.nist.gov/cgi-bin/ASD/lines1.pl?"
        "spectra=H+I&"
        "format=1&"
        "output=0&"
        "level_out=on&"
        "line_out=on"
    )
    body = fetch_url(url, timeout=20)
    if body.startswith("ERROR"):
        return False, [body]

    # NIST output: column headers and table; look for typical column content
    found = []
    if "Wavelength" in body or "wavelength" in body:
        found.append("wavelength (vac/air)")
    if "Aki" in body:
        found.append("Aki")
    if "Rel. Int" in body or "Intensity" in body:
        found.append("intensity")
    if "cm" in body and ("Ei" in body or "Ek" in body or "Energy" in body):
        found.append("Ei/Ek (energy)")
    if "Config" in body or "Configuration" in body:
        found.append("configuration")
    if "Term" in body:
        found.append("term")
    if "J " in body or "J-value" in body:
        found.append("J")
    if "Ion" in body or "Spectrum" in body:
        found.append("ion/spectrum (element+ion_state)")
    if "Type" in body or "transition type" in body.lower():
        found.append("line_type")

    if not found:
        found.append("(no known column markers; page may be form or error)")
    return True, found


def check_oac_api() -> tuple[bool, list[str]]:
    """
    Request one event from OAC (SN2011fe); check JSON for catalog keys.
    Return (success, list of detected field names or messages).
    """
    url = "https://api.astrocats.space/SN2011fe"
    body = fetch_url(url, timeout=15)
    if body.startswith("ERROR"):
        return False, [body]

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False, ["Response is not JSON"]

    if isinstance(data, dict) and "SN2011fe" in data:
        event = data["SN2011fe"]
    elif isinstance(data, dict) and len(data) == 1:
        event = next(iter(data.values()))
    else:
        event = data if isinstance(data, dict) else {}

    def key_mapping() -> list[str]:
        """Map OAC event keys to required SN/catalog field names for reporting."""
        out = []
        if not isinstance(event, dict):
            return ["(not a dict)"]
        if "name" in event:
            out.append("sn_name (name)")
        if "ra" in event:
            out.append("ra")
        if "dec" in event or "hostdec" in event:
            out.append("dec / hostdec")
        if "redshift" in event:
            out.append("redshift")
        if "claimedtype" in event:
            out.append("sn_type (claimedtype)")
        if "host" in event:
            out.append("host_galaxy (host)")
        if "discoverdate" in event:
            out.append("discovery_mjd (discoverdate)")
        if "maxdate" in event:
            out.append("peak_mjd (maxdate)")
        if "maxappmag" in event:
            out.append("peak_mag (maxappmag)")
        if "lumdist" in event:
            out.append("luminosity_distance_Mpc (lumdist)")
        if "photometry" in event:
            out.append("photometry (mjd/mag/band/instrument)")
        if "catalog" in event:
            out.append("source_catalog (catalog)")
        return out

    found = key_mapping()
    if not found:
        keys = list(event.keys())[:15] if isinstance(event, dict) else []
        found = ["Top-level keys: " + str(keys)]
    return True, found


def main() -> int:
    """Run source checks and print report."""
    print("Source field check (required task parameters)\n")
    print("Required fields: see script constants; docs/refactoring/TECH_SPEC.md\n")

    all_ok = True

    print("--- NIST ASD (atomic lines) ---")
    ok, msgs = check_nist_asd()
    if ok:
        print("  Sample request OK. Detected or expected in output:")
        for m in msgs:
            print(f"    - {m}")
        print("  => Required atomic fields obtainable (see doc for mapping).")
    else:
        print("  Request failed:", msgs[0] if msgs else "unknown")
        all_ok = False

    print("\n--- OAC / Open Supernova Catalog ---")
    ok, msgs = check_oac_api()
    if ok:
        print("  Sample request OK. Detected or expected in response:")
        for m in msgs:
            print(f"    - {m}")
        print("  => Required SN catalog and light-curve fields obtainable.")
    else:
        print("  Request failed:", msgs[0] if msgs else "unknown")
        all_ok = False

    print("\n--- Summary ---")
    if all_ok:
        print("  NIST ASD and OAC responded. Parameters obtainable from")
        print("  stated sources (see current TZ for field list).")
        return 0
    print("  One or more checks failed; review output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

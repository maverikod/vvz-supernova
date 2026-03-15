"""
Deterministic regression tests for scripts/check_source_fields.py.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Covers:
- Parsing of representative OAC JSON into reported field markers.
- Negative path for malformed or non-JSON response handling.
- Local test for NIST/OAC response classification logic.

All tests use patched fetch_url; no live network access.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from scripts import check_source_fields


def _oac_sample_json() -> str:
    """Representative OAC API response for one event (SN2011fe-style)."""
    return """{
        "SN2011fe": {
            "name": "SN2011fe",
            "ra": 210.773,
            "dec": 54.348,
            "redshift": 0.0008,
            "claimedtype": "Ia",
            "host": "M101",
            "discoverdate": "55814.0",
            "maxdate": "55820.0",
            "maxappmag": "9.94",
            "lumdist": "6.4",
            "photometry": [],
            "catalog": "Open Supernova Catalog"
        }
    }"""


class TestOacJsonParsing(unittest.TestCase):
    """Tests for OAC API response parsing into reported field markers."""

    @patch.object(check_source_fields, "fetch_url")
    def test_oac_json_parsing_returns_expected_field_markers(
        self, mock_fetch_url: MagicMock
    ) -> None:
        """Parsing valid OAC JSON yields catalog/lightcurve field markers."""
        mock_fetch_url.return_value = _oac_sample_json()
        ok, msgs = check_source_fields.check_oac_api()
        self.assertTrue(ok, "check_oac_api should succeed on valid JSON")
        self.assertIsInstance(msgs, list)
        self.assertGreater(len(msgs), 0)
        # Required field markers that key_mapping() produces from OAC keys
        markers = set(msgs)
        self.assertIn("sn_name (name)", markers)
        self.assertIn("ra", markers)
        self.assertIn("dec / hostdec", markers)
        self.assertIn("redshift", markers)
        self.assertIn("sn_type (claimedtype)", markers)
        self.assertIn("host_galaxy (host)", markers)
        self.assertIn("discovery_mjd (discoverdate)", markers)
        self.assertIn("peak_mjd (maxdate)", markers)
        self.assertIn("peak_mag (maxappmag)", markers)
        self.assertIn("luminosity_distance_Mpc (lumdist)", markers)
        self.assertIn("photometry (mjd/mag/band/instrument)", markers)
        self.assertIn("source_catalog (catalog)", markers)


class TestOacMalformedResponse(unittest.TestCase):
    """Negative path: malformed or non-JSON OAC response handling."""

    @patch.object(check_source_fields, "fetch_url")
    def test_oac_non_json_response_returns_failure(
        self, mock_fetch_url: MagicMock
    ) -> None:
        """When response body is not JSON, check_oac_api returns failure and message."""
        mock_fetch_url.return_value = "not json at all"
        ok, msgs = check_source_fields.check_oac_api()
        self.assertFalse(ok)
        self.assertEqual(len(msgs), 1)
        self.assertIn("not JSON", msgs[0])

    @patch.object(check_source_fields, "fetch_url")
    def test_oac_invalid_json_returns_failure(self, mock_fetch_url: MagicMock) -> None:
        """When response body is invalid JSON, check_oac_api returns failure."""
        mock_fetch_url.return_value = '{"broken": '
        ok, msgs = check_source_fields.check_oac_api()
        self.assertFalse(ok)
        self.assertEqual(len(msgs), 1)
        self.assertIn("not JSON", msgs[0])


class TestNistResponseClassification(unittest.TestCase):
    """Local test for NIST response classification (column markers in HTML)."""

    @patch.object(check_source_fields, "fetch_url")
    def test_nist_html_detects_column_markers(self, mock_fetch_url: MagicMock) -> None:
        """NIST ASD HTML with typical column headers is classified with markers."""
        mock_fetch_url.return_value = """
        <html><body>
        <table>
        <tr><th>Wavelength</th><th>Aki</th><th>Rel. Int</th><th>Ei</th><th>Config</th>
        <th>Term</th><th>J </th><th>Ion</th><th>Type</th></tr>
        </table>
        </body></html>
        """
        ok, found = check_source_fields.check_nist_asd()
        self.assertTrue(ok)
        self.assertIsInstance(found, list)
        self.assertGreater(len(found), 0)
        markers = " ".join(found).lower()
        self.assertIn("wavelength", markers)
        self.assertIn("aki", markers)
        self.assertIn("intensity", markers)
        self.assertIn("configuration", markers)
        self.assertIn("term", markers)
        self.assertIn("j", markers)
        self.assertIn("line_type", markers)

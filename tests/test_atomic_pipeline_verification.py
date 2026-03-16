"""
Atomic pipeline verification tests.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_pipeline_data import check_atomic_raw_payloads, check_data_csv
from supernova_atomic.nist_parser import parse_nist_payload


class AtomicPipelineVerificationTests(unittest.TestCase):
    """Verify atomic payload parsing and completeness checks."""

    def test_parse_nist_payload_rejects_error_page(self) -> None:
        """Parser must drop NIST error pages instead of returning fake rows."""
        payload = """
        <html>
        <head><title>NIST ASD : Input Error</title></head>
        <body><h2>Error Message:</h2><font color=red>Unknown parameter</font></body>
        </html>
        """
        rows = parse_nist_payload(
            payload=payload,
            element="H",
            ion_state="I",
            source_catalog="NIST ASD",
            source_url="https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra=H+I",
        )
        self.assertEqual(rows, [])

    def test_parse_nist_payload_reads_tab_delimited_export(self) -> None:
        """Parser must extract one physical transition from NIST TSV text."""
        payload = (
            "obs_wl_vac(nm)\tunc_obs_wl\tritz_wl_vac(nm)\tunc_ritz_wl\twn(cm-1)\t"
            "intens\tAki(s^-1)\tfik\tS(a.u.)\tlog_gf\tAcc\tEi(cm-1)\tEk(cm-1)\t"
            "conf_i\tterm_i\tJ_i\tconf_k\tterm_k\tJ_k\tg_i\tg_k\tType\n"
            '""\t""\t"91.2323660"\t"0.0000008"\t"109610.2232"\t""\t'
            '"1.2258e+02"\t"2.4474e-05"\t"1.4701e-04"\t"-4.31027"\tAAA\t'
            '"0.0000000000"\t"[109610.2232]"\t"1s"\t"2S"\t"1/2"\t'
            '"40"\t""\t""\t2\t3200\t""\n'
        )
        rows = parse_nist_payload(
            payload=payload,
            element="H",
            ion_state="I",
            source_catalog="NIST ASD",
            source_url="https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra=H+I",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["element"], "H")
        self.assertEqual(rows[0]["ion_state"], "I")
        self.assertEqual(rows[0]["lower_configuration"], "1s")
        self.assertAlmostEqual(float(rows[0]["wavelength_vac_nm"]), 91.2323660)
        self.assertAlmostEqual(float(rows[0]["Aki_s^-1"]), 122.58)

    def test_check_atomic_raw_payloads_reports_invalid_raw_files(self) -> None:
        """Raw validation must fail if manifest marks a payload as invalid."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw" / "atomic_lines_raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "H_I.txt").write_text(
                "<html><title>NIST ASD : Input Error</title>Unknown parameter</html>",
                encoding="utf-8",
            )
            (raw_dir / "manifest.json").write_text(
                (
                    '{"files": [{"spectrum": "H I", "file": "H_I.txt", '
                    '"valid_payload": false}]}'
                ),
                encoding="utf-8",
            )
            ok, messages = check_atomic_raw_payloads(root)
            self.assertFalse(ok)
            self.assertTrue(
                any("Invalid atomic raw payload" in message for message in messages)
            )

    def test_check_data_csv_rejects_header_only_atomic_files(self) -> None:
        """Completeness checks must fail for atomic CSV files without data rows."""
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            data_dir = root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            (data_dir / "atomic_lines_clean.csv").write_text(
                "element,frequency_hz\n",
                encoding="utf-8",
            )
            (data_dir / "atomic_lines_by_element.csv").write_text(
                "element\n",
                encoding="utf-8",
            )
            (data_dir / "atomic_transition_summary.csv").write_text(
                "element,n_lines,freq_min_hz,freq_max_hz\n",
                encoding="utf-8",
            )
            (data_dir / "supernova_catalog_clean.csv").write_text(
                "sn_name,source_catalog\nSN2024abc,OSC\n",
                encoding="utf-8",
            )
            (data_dir / "supernova_lightcurves_long.csv").write_text(
                "sn_name,mjd,band\nSN2024abc,60000.0,g\n",
                encoding="utf-8",
            )
            (data_dir / "supernova_event_summary.csv").write_text(
                (
                    "sn_name,sn_type,source_catalog,peak_mjd,"
                    "rise_time_days,decay_time_days\n"
                    "SN2024abc,Ia,OSC,60001.0,10.0,20.0\n"
                ),
                encoding="utf-8",
            )
            ok, messages = check_data_csv(root)
            self.assertFalse(ok)
            self.assertTrue(
                any("header only or no rows" in message for message in messages)
            )


if __name__ == "__main__":
    unittest.main()

"""
End-to-end supernova time-domain pipeline tests (offline, fixture-driven).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Proves the repaired supernova path yields a usable time-domain dataset:
clean -> event summary -> verification -> transient events -> third-spec report.
"""

from __future__ import annotations

import csv
import json
import runpy
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


def _real_project_root() -> Path:
    """Project root (parent of tests/)."""
    return Path(__file__).resolve().parent.parent


def _valid_nist_tsv_payload() -> str:
    """Minimal valid NIST TSV so atomic raw payload check passes."""
    return (
        "obs_wl_vac(nm)\tunc_obs_wl\tritz_wl_vac(nm)\tunc_ritz_wl\twn(cm-1)\t"
        "intens\tAki(s^-1)\tfik\tS(a.u.)\tlog_gf\tAcc\tEi(cm-1)\tEk(cm-1)\t"
        "conf_i\tterm_i\tJ_i\tconf_k\tterm_k\tJ_k\tg_i\tg_k\tType\n"
        '""\t""\t"91.2323660"\t"0.0000008"\t"109610.2232"\t""\t'
        '"1.2258e+02"\t"2.4474e-05"\t"1.4701e-04"\t"-4.31027"\tAAA\t'
        '"0.0000000000"\t"[109610.2232]"\t"1s"\t"2S"\t"1/2"\t'
        '"40"\t""\t""\t2\t3200\t""\n'
    )


def _osc_value(val: str) -> list[dict]:
    """OSC-style list of dict with 'value'."""
    return [{"value": val}]


def _event_block(
    ra: str = "14:03:05.17",
    dec: str = "+54:16:25.4",
    redshift: str = "0.001",
    host: str = "M82",
    claimed: str = "Ia",
    discoverdate: str = "2014/01/21",
    maxdate: str = "2014/02/01",
    lumdist: float = 3.5,
    photometry: list[dict] | None = None,
) -> dict:
    """Build one OAC event block for curated artifact."""
    block: dict = {
        "ra": _osc_value(ra),
        "dec": _osc_value(dec),
        "redshift": _osc_value(redshift),
        "host": _osc_value(host),
        "claimedtype": _osc_value(claimed),
        "discoverdate": _osc_value(discoverdate),
        "maxdate": _osc_value(maxdate),
        "lumdist": _osc_value(str(lumdist)),
        "photometry": photometry or [],
    }
    return block


def _photometry_point(mjd: float, mag: float, band: str = "B") -> dict:
    """One photometry sample."""
    return {"time": mjd, "magnitude": mag, "band": band, "e_magnitude": 0.05}


def build_supernova_fixture(root: Path) -> None:
    """Create raw/supernova_raw with osc_catalog.json, manifest, three artifacts."""
    raw_sn = root / "raw" / "supernova_raw"
    raw_sn.mkdir(parents=True, exist_ok=True)

    (raw_sn / "osc_catalog.json").write_text("{}", encoding="utf-8")

    # SN2014J: >= 20 points in one band for has_lightcurve=1 and number_of_points >= 20.
    base_mjd = 56680.0
    peak_mjd = 56690.0
    peak_mag = 12.0
    points_2014j = []
    for i in range(25):
        mjd = base_mjd + i * 2.0
        mag = peak_mag + 0.5 * abs((mjd - peak_mjd) / 5.0)
        points_2014j.append(_photometry_point(mjd, mag, "B"))

    sn2014j = {
        "SN2014J": _event_block(
            lumdist=3.5,
            photometry=points_2014j,
        ),
    }
    (raw_sn / "SN2014J.json").write_text(
        json.dumps(sn2014j, indent=0), encoding="utf-8"
    )

    # SN2011fe: few points.
    points_11fe = [
        _photometry_point(55750.0 + i, 11.0 + i * 0.1, "B") for i in range(5)
    ]
    sn2011fe = {
        "SN2011fe": _event_block(
            discoverdate="2011/08/24",
            maxdate="2011/09/10",
            lumdist=6.4,
            photometry=points_11fe,
        ),
    }
    (raw_sn / "SN2011fe.json").write_text(
        json.dumps(sn2011fe, indent=0), encoding="utf-8"
    )

    # SN1987A: few points.
    points_87a = [_photometry_point(46850.0 + i, 5.0 + i * 0.2, "V") for i in range(5)]
    sn1987a = {
        "SN1987A": _event_block(
            discoverdate="1987/02/23",
            maxdate="1987/03/01",
            lumdist=0.05,
            photometry=points_87a,
        ),
    }
    (raw_sn / "SN1987A.json").write_text(
        json.dumps(sn1987a, indent=0), encoding="utf-8"
    )

    manifest = {
        "download_date_utc": "2020-01-01T00:00:00Z",
        "artifacts": [
            {
                "event_name": "SN2014J",
                "raw_file": "SN2014J.json",
                "usable_photometry_points": 25,
            },
            {
                "event_name": "SN2011fe",
                "raw_file": "SN2011fe.json",
                "usable_photometry_points": 5,
            },
            {
                "event_name": "SN1987A",
                "raw_file": "SN1987A.json",
                "usable_photometry_points": 5,
            },
        ],
    }
    (raw_sn / "manifest.json").write_text(
        json.dumps(manifest, indent=0), encoding="utf-8"
    )


def build_atomic_fixture(root: Path) -> None:
    """Create raw/atomic_lines_raw so verify_pipeline_data passes atomic checks."""
    raw_atomic = root / "raw" / "atomic_lines_raw"
    raw_atomic.mkdir(parents=True, exist_ok=True)
    (raw_atomic / "H_I.txt").write_text(_valid_nist_tsv_payload(), encoding="utf-8")
    manifest = {
        "files": [
            {"spectrum": "H I", "file": "H_I.txt", "valid_payload": True},
        ],
    }
    (raw_atomic / "manifest.json").write_text(
        json.dumps(manifest, indent=0), encoding="utf-8"
    )


def build_atomic_data_stubs(root: Path) -> None:
    """Create minimal data/ atomic CSVs so check_data_csv passes."""
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "atomic_lines_clean.csv").write_text(
        "element,frequency_hz\nH,3.29e15\n", encoding="utf-8"
    )
    (data_dir / "atomic_lines_by_element.csv").write_text(
        "element\nH\n", encoding="utf-8"
    )
    (data_dir / "atomic_transition_summary.csv").write_text(
        "element,n_lines,freq_min_hz,freq_max_hz\nH,1,3.0e15,3.5e15\n",
        encoding="utf-8",
    )


def build_plot_stubs(root: Path) -> None:
    """Create plot placeholders so check_plots passes."""
    plots_dir = root / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "atomic_frequency_histogram.png",
        "atomic_Aki_histogram.png",
        "supernova_peak_mag_histogram.png",
        "supernova_rise_time_histogram.png",
        "supernova_decay_time_histogram.png",
        "example_lightcurves.png",
    ]:
        (plots_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n")


def copy_scripts(real_root: Path, tmp_root: Path) -> None:
    """Copy the five supernova chain scripts into tmp/scripts/."""
    scripts_src = real_root / "scripts"
    scripts_dst = tmp_root / "scripts"
    scripts_dst.mkdir(parents=True, exist_ok=True)
    for name in [
        "clean_supernova_data.py",
        "build_event_summaries.py",
        "verify_pipeline_data.py",
        "build_supernova_transient_events.py",
        "build_third_spec_report.py",
    ]:
        (scripts_dst / name).write_text(
            (scripts_src / name).read_text(encoding="utf-8"), encoding="utf-8"
        )


def run_script(tmp_root: Path, script_name: str, real_root: Path) -> None:
    """Run one script from tmp/scripts/ with real project on path; handle SystemExit."""
    path = tmp_root / "scripts" / script_name
    if not path.is_file():
        raise FileNotFoundError(path)
    old_path = list(sys.path)
    sys.path.insert(0, str(real_root))
    try:
        try:
            runpy.run_path(str(path), run_name="__main__")
        except SystemExit as e:
            if e.code not in (0, None):
                raise AssertionError(f"{script_name} exited with code {e.code}") from e
    finally:
        sys.path[:] = old_path


class SupernovaTimeDomainPipelineTests(unittest.TestCase):
    """End-to-end offline tests for the repaired supernova chain."""

    def test_supernova_chain_produces_usable_time_domain_dataset(self) -> None:
        """Run full chain on isolated fixture; assert non-empty outputs and timing."""
        real_root = _real_project_root()
        with TemporaryDirectory() as td:
            tmp = Path(td)
            build_supernova_fixture(tmp)
            build_atomic_fixture(tmp)
            build_atomic_data_stubs(tmp)
            build_plot_stubs(tmp)
            copy_scripts(real_root, tmp)

            run_script(tmp, "clean_supernova_data.py", real_root)
            run_script(tmp, "build_event_summaries.py", real_root)
            run_script(tmp, "verify_pipeline_data.py", real_root)
            run_script(tmp, "build_supernova_transient_events.py", real_root)
            run_script(tmp, "build_third_spec_report.py", real_root)

            data_dir = tmp / "data"
            lc_path = data_dir / "supernova_lightcurves_long.csv"
            self.assertTrue(
                lc_path.is_file(), "supernova_lightcurves_long.csv must exist"
            )
            with lc_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertGreater(
                len(rows), 0, "supernova_lightcurves_long.csv must be non-empty"
            )

            summary_path = data_dir / "supernova_event_summary.csv"
            self.assertTrue(summary_path.is_file())
            with summary_path.open(newline="", encoding="utf-8") as f:
                sum_reader = csv.DictReader(f)
                summary_rows = list(sum_reader)
            timing_ok = any(
                (
                    (row.get("rise_time_days") or "").strip()
                    and (row.get("rise_time_days") or "").strip() not in ("nan", "NaN")
                )
                or (
                    (row.get("decay_time_days") or "").strip()
                    and (row.get("decay_time_days") or "").strip() not in ("nan", "NaN")
                )
                or (
                    (row.get("peak_width_days") or "").strip()
                    and (row.get("peak_width_days") or "").strip() not in ("nan", "NaN")
                )
                for row in summary_rows
            )
            self.assertTrue(
                timing_ok,
                "At least one event_summary row must have non-empty timing",
            )

            transient_path = data_dir / "supernova_transient_events.csv"
            self.assertTrue(transient_path.is_file())
            with transient_path.open(newline="", encoding="utf-8") as f:
                trans_reader = csv.DictReader(f)
                trans_rows = list(trans_reader)
            has_lc_count = sum(
                1 for r in trans_rows if (r.get("has_lightcurve") or "").strip() == "1"
            )
            self.assertGreater(
                has_lc_count,
                0,
                "At least one row must have has_lightcurve=1",
            )
            points_ok = any(
                int((r.get("number_of_points") or "0")) >= 20 for r in trans_rows
            )
            self.assertTrue(
                points_ok,
                "At least one row must have number_of_points >= 20",
            )

            report_dir = tmp / "report"
            report_md = report_dir / "data_report.md"
            self.assertTrue(report_md.is_file())
            text = report_md.read_text(encoding="utf-8")
            self.assertIn("Supernova timing coverage", text)
            self.assertIn("rise_time_days", text)
            self.assertIn("has_lightcurve", text)


if __name__ == "__main__":
    unittest.main()

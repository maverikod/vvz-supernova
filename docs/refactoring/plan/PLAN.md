# Data-First Refactoring Plan

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This plan is written against `docs/refactoring/TECH_SPEC.md`.

## Goal

Produce a supernova dataset that is sufficient for time-domain analysis, not only structurally valid:

- `raw/supernova_raw/` contains the OSC bulk catalog and photometry-bearing event artifacts.
- `data/supernova_lightcurves_long.csv` is non-empty and built from real source photometry.
- `data/supernova_event_summary.csv` has non-zero timing coverage in `rise_time_days`, `decay_time_days`, and/or `peak_width_days`.
- `report/` makes source coverage and timing coverage explicit.

## Authoritative execution rule

`docs/refactoring/plan/step_*.md` are the authoritative execution documents. `PLAN.md`, `PARALLEL_CHAINS.md`, and `COVERAGE_MATRIX.md` are coordination documents only. If any coordination note conflicts with a step file, the step file wins.

## Why this plan exists

Current code proves only catalog-level success for the supernova path:

- `scripts/download_supernova_data.py` downloads only `osc_catalog.json`.
- `scripts/clean_supernova_data.py` hardcodes empty light curves.
- `scripts/verify_pipeline_data.py` does not fail on header-only supernova light-curve output.
- current tests do not prove that the main `supernova_*` chain yields a usable time-domain dataset.

## Sufficiency gate for this branch

This branch is considered sufficient only if all of the following are true at the end:

1. `scripts/download_supernova_data.py` downloads OSC bulk metadata and a curated OAC photometry subset for `SN2014J`, `SN2011fe`, and `SN1987A`.
2. every photometry-bearing raw artifact in `raw/supernova_raw/manifest.json` produces at least one cleaned light-curve row;
3. `data/supernova_lightcurves_long.csv` is non-empty;
4. `data/supernova_event_summary.csv` has non-zero populated timing fields for at least one real object from the curated subset;
5. `data/supernova_transient_events.csv` contains at least one row with `has_lightcurve=1` and `number_of_points >= 20`;
6. `report/source_manifest.csv`, `report/missingness_report.csv`, and `report/data_report.md` expose supernova source and timing coverage;
7. `python scripts/verify_raw_downloads.py`, `python scripts/verify_pipeline_data.py`, and the full test suite pass.

## Execution rules

- One step targets exactly one code file.
- One step file describes exactly one implementation step.
- The critical supernova data path goes first; cleanup exists only where it is required to keep files below the project size limit or to keep the path handoff-ready.
- After every implementation step: run `source .venv/bin/activate`, then run `black`, `flake8`, `mypy`, `pytest`, and `code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400`.
- If a step cannot stay within one target code file, stop and report a blackstop instead of spilling into a second production file.

## Environment prerequisite

At plan authoring time, `.venv` activates correctly, but `python -m pytest --version` fails with `No module named pytest`. Therefore each executable step must treat `pytest` availability in `.venv` as a blocking prerequisite and must stop under blackstop rules if the environment has not been repaired yet.

## Planned order

1. `step_01_create_oac_event_artifacts_helper.md`
2. `step_02_refactor_download_supernova_data_entrypoint.md`
3. `step_03_create_supernova_raw_ingest_helper.md`
4. `step_04_refactor_clean_supernova_data_entrypoint.md`
5. `step_05_refactor_build_event_summaries.md`
6. `step_06_refactor_verify_raw_downloads.md`
7. `step_07_refactor_verify_pipeline_data.md`
8. `step_08_refactor_build_supernova_transient_events.md`
9. `step_09_refactor_build_third_spec_report.md`
10. `step_10_expand_raw_download_verification_tests.md`
11. `step_11_add_supernova_time_domain_pipeline_tests.md`

## Commands required after every step

- `source .venv/bin/activate`
- `python -m black scripts supernova_atomic tests docs/search/engine`
- `python -m flake8 scripts supernova_atomic tests docs/search/engine`
- `python -m mypy scripts supernova_atomic tests docs/search/engine`
- `python -m pytest`
- `code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400`

## References

- `docs/refactoring/TECH_SPEC.md`
- `docs/TECH_SPEC.md`
- `docs/DATA_SOURCES_AND_ALGORITHMS.md`
- `docs/PROJECT_STRUCTURE.md`
- `supernova_atomic/third_spec_schema.py`

# Step 07: Refactor `verify_pipeline_data.py`

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for final pipeline verification. Your job is to encode the supernova sufficiency gate directly into the existing verification script.

## Execution directive

Edit exactly one production file: `scripts/verify_pipeline_data.py`. Do not convert it into a report generator and do not edit any other file in this step.

## Target file

`scripts/verify_pipeline_data.py`

## Step scope

This step updates final verification only. It strengthens failure conditions and console summary output for the supernova path while preserving atomic checks and plot checks.

## Dependency contract

- Steps 04, 05, and 06 must already be complete.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- `raw/supernova_raw/manifest.json` must follow the contract established in step 02.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `scripts/verify_pipeline_data.py`
- `scripts/verify_raw_downloads.py`
- `scripts/clean_supernova_data.py`
- `scripts/build_event_summaries.py`

You must edit these symbols inside the target file:

- `check_data_csv()`
- `print_summary_from_data()`
- `main()`

## Forbidden scope

- Do not edit `scripts/verify_raw_downloads.py`.
- Do not weaken atomic row-count checks.
- Do not remove plot verification.
- Do not accept header-only supernova outputs when curated photometry-bearing raw inputs exist.

## Atomic operations

1. Keep all existing atomic checks intact.
2. Read `raw/supernova_raw/manifest.json` inside the target file and detect whether curated artifacts with `usable_photometry_points > 0` exist.
3. In `check_data_csv()`, fail if curated photometry-bearing raw artifacts exist and `data/supernova_lightcurves_long.csv` has zero data rows.
4. In `check_data_csv()`, fail if `data/supernova_event_summary.csv` has zero non-empty values across all three timing columns:
   - `rise_time_days`
   - `decay_time_days`
   - `peak_width_days`
5. In `print_summary_from_data()`, print these exact supernova counters:
   - total supernova catalog rows;
   - number of unique supernovae with light-curve rows;
   - total long-table row count;
   - count with non-empty `rise_time_days`;
   - count with non-empty `decay_time_days`;
   - count with non-empty `peak_width_days`.
6. Keep output as console text only; do not write files.

## Expected file change

Only `scripts/verify_pipeline_data.py` changes in this step.

That file must change in these exact areas:

- `check_data_csv()` must enforce supernova sufficiency, not just schema presence;
- `print_summary_from_data()` must print explicit supernova timing-coverage counts;
- `main()` must continue to orchestrate verification without becoming a report writer.

## Expected deliverables

- Updated `scripts/verify_pipeline_data.py`
- Final verification that fails on metadata-only supernova success
- Console summary that exposes timing coverage explicitly

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python scripts/verify_pipeline_data.py
python -m black scripts/verify_pipeline_data.py
python -m flake8 scripts/verify_pipeline_data.py
python -m mypy scripts/verify_pipeline_data.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `python scripts/verify_pipeline_data.py` must fail on header-only `supernova_lightcurves_long.csv` when curated photometry-bearing raw inputs exist;
- `python scripts/verify_pipeline_data.py` must fail when all timing coverage counts are zero;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- If curated photometry-bearing raw artifacts exist, header-only `supernova_lightcurves_long.csv` is a hard failure.
- If timing coverage across all three timing columns is zero, the verification fails even if the summary file exists and has rows.
- Schema presence alone is never sufficient for the supernova path after this step.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Steps 04, 05, or 06 are incomplete.
- The manifest contract needed for the sufficiency gate is absent.
- The target file would exceed the project file-size limit.
- A second production file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.

## Handoff package

When the step is complete, the handoff must include:

- the exact supernova failure conditions added to `check_data_csv()`;
- the exact timing coverage counters printed by `print_summary_from_data()`;
- verification output showing pass/fail behavior on the repaired dataset;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

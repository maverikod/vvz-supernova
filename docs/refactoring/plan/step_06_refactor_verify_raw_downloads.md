# Step 06: Refactor `verify_raw_downloads.py`

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for raw-download verification. Your job is to make raw verification reject metadata-only supernova success states and enforce the curated OAC artifact contract.

## Execution directive

Edit exactly one production file: `scripts/verify_raw_downloads.py`. Reuse the helper from step 01; do not duplicate artifact verification logic.

## Target file

`scripts/verify_raw_downloads.py`

## Step scope

This step updates raw verification only. It does not change final pipeline verification, tests, cleaners, or downloader behavior.

## Dependency contract

- Step 02 raw layout must already exist.
- Step 01 helper must already be importable.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `scripts/verify_raw_downloads.py`
- `scripts/download_supernova_data.py`
- `supernova_atomic/oac_event_artifacts.py`
- `tests/test_raw_download_verification.py`

You must edit these symbols inside the target file:

- `check_supernova_downloads()`
- `main()`
- any new internal helper functions added inside this same file

## Forbidden scope

- Do not edit `scripts/verify_pipeline_data.py`.
- Do not relax atomic verification.
- Do not accept raw success when only `osc_catalog.json` is present.
- Do not edit tests in this step.

## Atomic operations

1. Keep `check_atomic_downloads()` behavior unchanged.
2. In `check_supernova_downloads()`, require these exact supernova raw files:
   - `osc_catalog.json`
   - `sn2014j_event.json`
   - `sn2011fe_event.json`
   - `sn1987a_event.json`
3. Require `manifest.json` to include:
   - top-level `artifacts` list;
   - exactly three curated artifact entries;
   - event names exactly `SN2014J`, `SN2011fe`, `SN1987A`.
4. For each artifact entry, call the helper-based verification path and fail if:
   - raw file is missing;
   - JSON is unreadable;
   - event key is missing from the raw payload;
   - photometry list is empty;
   - `usable_photometry_points <= 0`;
   - manifest counts do not match raw counts.
5. Keep the existing OSC bulk readability check for `osc_catalog.json`.
6. Print explicit summary counts for:
   - `sources_used`
   - `sources_skipped`
   - verified curated artifacts

## Expected file change

Only `scripts/verify_raw_downloads.py` changes in this step.

That file must change in these exact areas:

- `check_supernova_downloads()` must enforce curated artifact presence and validity;
- `main()` must report curated artifact verification results explicitly;
- `check_atomic_downloads()` must remain behaviorally unchanged.

## Expected deliverables

- Updated `scripts/verify_raw_downloads.py`
- Raw verification that fails on any missing or unusable curated artifact
- Clear console summary that distinguishes OSC bulk metadata from curated photometry artifacts

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python scripts/verify_raw_downloads.py
python -m black scripts/verify_raw_downloads.py
python -m flake8 scripts/verify_raw_downloads.py
python -m mypy scripts/verify_raw_downloads.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `python scripts/verify_raw_downloads.py` must fail if any curated artifact is missing or unusable;
- `python scripts/verify_raw_downloads.py` must pass on the repaired raw layout;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- Missing any one curated event is a hard failure.
- A readable `osc_catalog.json` is necessary but never sufficient.
- Any curated artifact with zero usable photometry is a hard failure.
- Keep atomic and supernova result reporting separate inside `main()`.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Step 01 helper cannot verify artifacts as required.
- Step 02 raw manifest structure differs from the required contract.
- The target file would exceed the project file-size limit.
- A second production file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.

## Handoff package

When the step is complete, the handoff must include:

- the exact list of required curated raw files;
- the exact curated event names enforced by verification;
- one example failure condition now caught by `check_supernova_downloads()`;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

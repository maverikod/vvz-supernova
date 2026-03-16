# Step 11: Add Supernova Time-Domain Pipeline Tests

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for end-to-end supernova sufficiency coverage. Your job is to add one deterministic offline test file that proves the repaired `supernova_*` path yields a usable time-domain dataset.

## Execution directive

Create exactly one test file: `tests/test_supernova_time_domain_pipeline.py`. Do not split this coverage across multiple new test files.

## Target file

`tests/test_supernova_time_domain_pipeline.py`

## Step scope

This step adds end-to-end offline coverage for the repaired supernova chain. It does not change any production file.

## Dependency contract

- Steps 04, 05, 07, 08, 09, and 10 must already be complete.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- The test must remain fully offline and must not depend on user-local raw data.

## Required context

Read these files before creating the test:

- `scripts/clean_supernova_data.py`
- `scripts/build_event_summaries.py`
- `scripts/verify_pipeline_data.py`
- `scripts/build_supernova_transient_events.py`
- `scripts/build_third_spec_report.py`
- `tests/test_atomic_pipeline_verification.py`

## Forbidden scope

- Do not call the network.
- Do not read the user's current raw/data directories as test fixtures.
- Do not create additional new test files.
- Do not modify production code in this step.

## Atomic operations

1. Create one fixture-driven test module that assembles an isolated temporary project tree.
2. Build raw fixture data that includes:
   - `osc_catalog.json`
   - `manifest.json`
   - three curated event artifacts for `SN2014J`, `SN2011fe`, and `SN1987A`
3. Ensure at least one curated fixture event contains `>= 20` valid `(mjd, mag)` rows in one band.
4. Run the production chain against the isolated fixture state in this exact order:
   - cleaner path
   - event summary builder
   - final pipeline verification
   - downstream supernova transient event builder
   - third-spec report builder
5. Add assertions that prove all of the following:
   - `supernova_lightcurves_long.csv` is non-empty;
   - at least one row in `supernova_event_summary.csv` has non-empty timing fields;
   - at least one row in `supernova_transient_events.csv` has `has_lightcurve=1`;
   - at least one row in `supernova_transient_events.csv` has `number_of_points >= 20`;
   - final verification accepts the fixture state;
   - report outputs include supernova timing coverage.

## Expected file change

Only `tests/test_supernova_time_domain_pipeline.py` is created in this step.

That file must contain:

- isolated temporary-project fixtures for the repaired supernova raw layout;
- end-to-end execution of the repaired supernova chain;
- assertions for non-empty light curves, non-empty timing fields, downstream `has_lightcurve=1`, and durable report coverage.

## Expected deliverables

- New file `tests/test_supernova_time_domain_pipeline.py`
- Deterministic offline proof that the repaired supernova path is sufficient under fixture conditions

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python -m black tests/test_supernova_time_domain_pipeline.py
python -m flake8 tests/test_supernova_time_domain_pipeline.py
python -m mypy tests/test_supernova_time_domain_pipeline.py
python -m pytest tests/test_supernova_time_domain_pipeline.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `python -m pytest tests/test_supernova_time_domain_pipeline.py` must pass fully offline;
- the fixture must prove non-empty long-table output and non-empty timing coverage;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- The fixture must use the curated event names exactly.
- Timing assertions must check actual non-empty output fields, not only file existence.
- The test must fail if the long table becomes header-only or if timing coverage disappears.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Any prerequisite step is incomplete.
- The target test file would exceed the project file-size limit.
- A second new test file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- The production chain cannot be exercised offline through isolated temporary fixtures.

## Handoff package

When the step is complete, the handoff must include:

- the exact fixture components created;
- the exact sufficiency assertions added;
- confirmation that the test is fully offline and isolated;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

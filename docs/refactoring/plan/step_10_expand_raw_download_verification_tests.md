# Step 10: Expand Raw Download Verification Tests

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for raw-download regression coverage. Your job is to lock the repaired raw verification contract into deterministic offline tests.

## Execution directive

Edit exactly one test file: `tests/test_raw_download_verification.py`. Do not create a second test file in this step.

## Target file

`tests/test_raw_download_verification.py`

## Step scope

This step updates raw verification tests only. It does not modify production verification logic or add end-to-end pipeline coverage.

## Dependency contract

- Step 06 must already be complete.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- Tests must remain fully offline and deterministic.

## Required context

Read these files before editing:

- `scripts/verify_raw_downloads.py`
- `scripts/download_supernova_data.py`
- `supernova_atomic/oac_event_artifacts.py`
- `tests/test_raw_download_verification.py`

## Forbidden scope

- Do not call live network endpoints.
- Do not create `tests/test_raw_download_verification_extra.py`.
- Do not remove existing atomic fixture tests.
- Do not edit production files in this step.

## Atomic operations

1. Keep all existing atomic fixture tests.
2. Extend the supernova fixture so it can model:
   - presence of all three curated event artifacts;
   - missing one curated artifact;
   - artifact JSON with empty or unusable photometry;
   - mismatch between manifest counts and raw artifact contents.
3. Add deterministic tests for these exact failure cases:
   - missing `sn2014j_event.json`, `sn2011fe_event.json`, or `sn1987a_event.json`;
   - curated artifact exists but has zero usable photometry;
   - manifest claims one `usable_photometry_points` count and raw payload yields another;
   - manifest omits the `artifacts` list or provides fewer than three curated entries.
4. Keep one positive test that proves a fully valid curated manifest passes.

## Expected file change

Only `tests/test_raw_download_verification.py` changes in this step.

That file must gain:

- positive coverage for a fully valid curated manifest;
- negative coverage for each required curated raw artifact missing;
- negative coverage for unusable curated photometry;
- negative coverage for manifest/raw count mismatch.

## Expected deliverables

- Updated `tests/test_raw_download_verification.py`
- Offline regression coverage that rejects metadata-only raw success states

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python -m black tests/test_raw_download_verification.py
python -m flake8 tests/test_raw_download_verification.py
python -m mypy tests/test_raw_download_verification.py
python -m pytest tests/test_raw_download_verification.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `python -m pytest tests/test_raw_download_verification.py` must pass offline;
- at least one positive curated-manifest test and multiple failure-mode tests must exist;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- Every new test must use local fixture files only.
- One valid curated manifest test must remain.
- One failure test per required contract break must exist; do not collapse all failure modes into one generic test.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Step 06 is incomplete.
- The target file would exceed the project file-size limit.
- A second test file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- Offline fixtures cannot represent the required raw manifest contract.

## Handoff package

When the step is complete, the handoff must include:

- the list of newly added failure cases covered by tests;
- confirmation that tests remain fully offline;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

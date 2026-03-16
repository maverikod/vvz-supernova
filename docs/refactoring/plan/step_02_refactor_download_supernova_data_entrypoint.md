# Step 02: Refactor `download_supernova_data.py` Entrypoint

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for the supernova raw-download entrypoint. Your job is to make the existing downloader produce the exact raw artifact layout required by downstream cleaning and verification.

## Execution directive

Edit exactly one production file: `scripts/download_supernova_data.py`. Reuse the helper created in step 01. Do not move production logic into any file other than the already-created helper.

## Target file

`scripts/download_supernova_data.py`

## Step scope

This step updates the main raw download CLI entrypoint and its manifest-writing behavior only. It does not update cleaners, verifiers, tests, wrappers, or reports.

## Dependency contract

- Step 01 must already be complete and importable.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- The raw output directory must remain `raw/supernova_raw/`.
- Wrapper `scripts/download_supernova.py` must remain unchanged and continue to call this entrypoint.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `docs/TECH_SPEC.md`
- `docs/DATA_SOURCES_AND_ALGORITHMS.md`
- `supernova_atomic/oac_event_artifacts.py`
- `scripts/download_supernova_data.py`
- `scripts/download_supernova.py`

You must edit these symbols inside the target file:

- `write_manifest()`
- `main()`
- the raw download flow that currently downloads only `osc_catalog.json`

## Forbidden scope

- Do not edit `scripts/download_supernova.py`.
- Do not edit `scripts/verify_raw_downloads.py`.
- Do not add any source beyond OSC bulk metadata and the curated OAC subset.
- Do not change the OSC bulk filename.
- Do not change the manifest filename.

## Atomic operations

1. Keep the OSC bulk download behavior intact and continue writing:
   - `raw/supernova_raw/osc_catalog.json`
2. Download exactly three curated event artifacts using the helper from step 01:
   - `raw/supernova_raw/sn2014j_event.json`
   - `raw/supernova_raw/sn2011fe_event.json`
   - `raw/supernova_raw/sn1987a_event.json`
3. Update `write_manifest()` so `raw/supernova_raw/manifest.json` has these exact top-level keys:
   - `download_date_utc`
   - `sources_used`
   - `sources_skipped`
   - `artifacts`
   - `note`
4. Write `sources_used` as exactly two entries:
   - OSC entry with keys:
     - `name`
     - `url`
     - `bulk_file_url`
     - `raw_file`
   - OAC curated entry with keys:
     - `name`
     - `url`
     - `dataset_identifier`
     - `event_count`
5. Set the OAC `dataset_identifier` exactly to:
   - `SN2014J,SN2011fe,SN1987A`
6. Write `artifacts` as one entry per curated event with these exact keys:
   - `event_name`
   - `metadata_url`
   - `photometry_url`
   - `raw_file`
   - `download_date_utc`
   - `photometry_points`
   - `usable_photometry_points`
   - `sha256`
7. Keep `sources_skipped` entries for unimplemented external sources and leave their reason as explicit non-implementation, not as a runtime error.

## Expected file change

Only `scripts/download_supernova_data.py` changes in this step.

That file must change in these exact areas:

- `write_manifest()` must write the new top-level manifest keys and curated artifact entries;
- `main()` must download the three curated OAC event artifacts;
- the script must continue downloading `osc_catalog.json` and must continue writing `raw/supernova_raw/manifest.json`.

## Expected deliverables

- Updated `scripts/download_supernova_data.py`
- Raw files:
  - `osc_catalog.json`
  - `sn2014j_event.json`
  - `sn2011fe_event.json`
  - `sn1987a_event.json`
- One manifest that references all four raw artifacts through the exact structure above

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python scripts/download_supernova_data.py
python -m black scripts/download_supernova_data.py
python -m flake8 scripts/download_supernova_data.py
python -m mypy scripts/download_supernova_data.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `raw/supernova_raw/osc_catalog.json` must exist after the run;
- `raw/supernova_raw/sn2014j_event.json`, `sn2011fe_event.json`, and `sn1987a_event.json` must exist after the run;
- `raw/supernova_raw/manifest.json` must contain `artifacts` with exactly three curated entries;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- If a curated event download fails, the step is not complete; do not silently downgrade to metadata-only success.
- If any curated artifact has `usable_photometry_points == 0`, the step is not complete.
- Use the exact manifest structure and filenames defined in this step; do not invent alternative names or nesting.
- Preserve the existing OSC entry fields exactly as part of backward-compatible manifest structure.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Step 01 helper cannot be imported cleanly.
- The script would exceed the project file-size limit.
- A second production file beyond the target and the existing helper is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- The manifest cannot be written in the exact structure required above.

## Handoff package

When the step is complete, the handoff must include:

- the exact raw filenames created;
- the exact top-level manifest keys;
- one example artifact entry schema copied from the resulting manifest;
- confirmation that all three curated events were downloaded with `usable_photometry_points > 0`;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

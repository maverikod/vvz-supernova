# Step 04: Refactor `clean_supernova_data.py` Entrypoint

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for the main supernova cleaner entrypoint. Your job is to wire the new raw-ingest helper into the existing CLI and produce the actual cleaned CSV outputs.

## Execution directive

Edit exactly one production file: `scripts/clean_supernova_data.py`. Import and use the helper from step 03. Do not move production logic into any additional file.

## Target file

`scripts/clean_supernova_data.py`

## Step scope

This step updates the main cleaning CLI entrypoint and its internal file-writing flow only. It does not compute timing fields, update reports, or change wrappers.

## Dependency contract

- Step 03 must already be complete and importable.
- Step 02 raw outputs must exist in `raw/supernova_raw/`.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- Wrapper `scripts/clean_supernova.py` must remain unchanged.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `docs/TECH_SPEC.md`
- `supernova_atomic/supernova_raw_ingest.py`
- `scripts/clean_supernova_data.py`
- `scripts/clean_supernova.py`

You must edit these symbols inside the target file:

- `load_osc_catalog()`
- `load_osc_lightcurves()`
- `read_raw_supernova()`
- `main()`

## Forbidden scope

- Do not edit `scripts/clean_supernova.py`.
- Do not compute `rise_time_days`, `decay_time_days`, or `peak_width_days` here.
- Do not add source logic beyond OSC bulk plus curated OAC artifacts.
- Do not create a second helper file.

## Atomic operations

1. Replace the current inline OSC bulk loading path so it delegates to `supernova_atomic/supernova_raw_ingest.py`.
2. Replace the current hardcoded `load_osc_lightcurves()` empty-list behavior with helper-driven artifact ingestion.
3. Preserve the existing output filenames:
   - `data/supernova_catalog_clean.csv`
   - `data/supernova_lightcurves_long.csv`
4. Preserve the existing CSV column order for both files.
5. Ensure `main()` writes schema-only CSVs only when raw inputs are genuinely absent, not when manifest-declared photometry-bearing artifacts exist.
6. Ensure the cleaner fails instead of silently succeeding if helper ingestion reports a photometry-bearing artifact that produces zero cleaned rows.

## Expected file change

Only `scripts/clean_supernova_data.py` changes in this step.

That file must change in these exact areas:

- `load_osc_catalog()` must stop silently rejecting dict-root OSC bulk JSON;
- `load_osc_lightcurves()` must stop returning a hardcoded empty list;
- `read_raw_supernova()` must use the helper-driven raw ingestion path;
- `main()` must write non-empty cleaned light-curve output when curated photometry-bearing artifacts exist.

## Expected deliverables

- Updated `scripts/clean_supernova_data.py`
- Non-empty `data/supernova_lightcurves_long.csv` after running the cleaner on the repaired raw layout
- `lightcurve_points_count` values in `data/supernova_catalog_clean.csv` synchronized to cleaned row counts

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python scripts/clean_supernova_data.py
python -m black scripts/clean_supernova_data.py
python -m flake8 scripts/clean_supernova_data.py
python -m mypy scripts/clean_supernova_data.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `data/supernova_lightcurves_long.csv` must have at least one data row after the run;
- curated event names must appear in that CSV;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- If the raw manifest contains curated artifacts with `usable_photometry_points > 0`, a header-only light-curve CSV is a failure, not an acceptable output.
- Preserve catalog rows even when a given object has zero cleaned light-curve rows, but keep `lightcurve_points_count` exact.
- Do not recompute or infer any timing values in this step.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Step 03 helper cannot be imported or does not expose the required ingestion API.
- The target file would exceed the project file-size limit.
- A second production file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- The existing CSV schema must change to make the step work.

## Handoff package

When the step is complete, the handoff must include:

- confirmation that the target file remains the only edited production entrypoint in this step;
- row counts for `supernova_catalog_clean.csv` and `supernova_lightcurves_long.csv`;
- confirmation that curated event names appear in the long table;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

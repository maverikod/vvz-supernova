# Step 03: Create Supernova Raw Ingest Helper

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for the raw-to-clean supernova ingestion layer. Your job is to encode the exact normalization and deduplication policy that downstream cleaning will use.

## Execution directive

Edit exactly one production file: `supernova_atomic/supernova_raw_ingest.py`. Do not edit the cleaner entrypoint in this step.

## Target file

`supernova_atomic/supernova_raw_ingest.py`

## Step scope

This step creates the helper that reads `raw/supernova_raw/manifest.json`, `osc_catalog.json`, and curated event artifacts and converts them into cleaned catalog rows and long-table photometry rows.

## Dependency contract

- Step 02 must already be complete and its raw layout must exist.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- The manifest structure used by this step is exactly the one defined in step 02.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `docs/DATA_SOURCES_AND_ALGORITHMS.md`
- `scripts/clean_supernova_data.py`
- `scripts/clean_astrophysical_transient_data.py`
- `scripts/download_supernova_data.py`

The helper must provide importable functions for:

- loading OSC bulk catalog rows;
- loading curated OAC artifact rows;
- building catalog rows;
- building light-curve rows;
- deduplicating output rows.

## Forbidden scope

- Do not edit `scripts/clean_supernova_data.py`.
- Do not compute rise, decay, or width in this helper.
- Do not create report logic.
- Do not add a second helper file.
- Do not add merge logic for sources beyond OSC bulk plus curated OAC artifacts.

## Atomic operations

1. Implement OSC bulk loading with this exact root handling rule:
   - if root is a dict, iterate over `dict.values()`;
   - if root is a list, iterate over the list items;
   - otherwise return an empty catalog list.
2. Build catalog rows with the existing supernova catalog schema:
   - `sn_name`
   - `source_catalog`
   - `ra`
   - `dec`
   - `redshift`
   - `host_galaxy`
   - `sn_type`
   - `discovery_mjd`
   - `peak_mjd`
   - `peak_mag`
   - `band`
   - `distance_modulus`
   - `luminosity_distance_Mpc`
   - `lightcurve_points_count`
3. Load curated event artifacts only from the `artifacts` list in `raw/supernova_raw/manifest.json`.
4. Normalize one photometry row into the long-table schema only if:
   - `time` is present and parseable as finite float;
   - at least one of `magnitude` or `flux` is parseable as finite float.
5. Map photometry fields with these exact rules:
   - `sn_name = event_name`
   - `mjd = float(time)`
   - `mag = float(magnitude)` if parseable else empty
   - `mag_err = float(e_magnitude)` if parseable else empty
   - `flux = float(flux)` if parseable else empty
   - `flux_err = float(e_flux)` if parseable else empty
   - `band = str(band).strip()` or empty string
   - `instrument = str(instrument).strip()` else `str(telescope).strip()` else empty string
   - `source_catalog = "Open Astronomy Catalog API"`
6. Apply exact duplicate removal on light-curve rows using the full tuple:
   - `(sn_name, mjd, mag, mag_err, flux, flux_err, band, instrument, source_catalog)`
7. Apply exact duplicate removal on catalog rows using the full output schema tuple.
8. After deduplication, recompute `lightcurve_points_count` exactly as the number of cleaned long-table rows for each `sn_name`.
9. If a manifest artifact has `usable_photometry_points > 0` but yields zero cleaned long-table rows, raise a hard failure.

## Expected file change

Only `supernova_atomic/supernova_raw_ingest.py` changes in this step.

That file must gain:

- OSC bulk loader with dict-root and list-root handling;
- curated artifact loader driven by `manifest.json`;
- light-curve row normalization logic;
- exact duplicate removal for catalog and light-curve rows;
- recomputation of `lightcurve_points_count`;
- hard failure on photometry-bearing artifacts that clean to zero rows.

## Expected deliverables

- One new module: `supernova_atomic/supernova_raw_ingest.py`
- Importable helper functions for catalog ingestion, artifact ingestion, row normalization, and deduplication
- Deterministic behavior for empty or partially empty photometry rows

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python -m black supernova_atomic/supernova_raw_ingest.py
python -m flake8 supernova_atomic/supernova_raw_ingest.py
python -m mypy supernova_atomic/supernova_raw_ingest.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- the helper must import successfully from a Python REPL inside `.venv`;
- all four quality commands must succeed;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- Keep flux-only rows in the long table if they satisfy the normalization rule; they do not become timing rows later unless a later step explicitly uses `mag`.
- Do not discard a row only because `band` or `instrument` is empty.
- Do not merge or average conflicting duplicate-near rows; only exact duplicates are removed.
- If both `instrument` and `telescope` exist, prefer `instrument`.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Step 02 raw layout is absent or structurally incompatible.
- The helper would exceed the project file-size limit.
- A second production file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- The required normalization rules cannot be expressed without changing another production file.

## Handoff package

When the step is complete, the handoff must include:

- the final helper path and exported symbols;
- the exact duplicate key used for light curves;
- the exact rule for dict-root versus list-root OSC bulk JSON;
- the exact rule for partially empty photometry rows;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

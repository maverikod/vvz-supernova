# Step 05 — Clean supernova data

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/clean_supernova_data.py`  
**Plan file:** `docs/plan/step_05_clean_supernova_data.md`

---

## Executor role

Implement or verify the script that cleans raw supernova data and produces `data/supernova_catalog_clean.csv` and `data/supernova_lightcurves_long.csv`. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/clean_supernova_data.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/clean_supernova_data.py`
- **Type:** standalone runnable script
- **Purpose:** Read raw supernova data; normalize to schema; output catalog CSV and light-curves long CSV.

## Dependency contract

- **Prerequisites:** Step 04 done (`raw/supernova_raw/` populated).
- **Unlocks:** Step 06.
- **Forbidden:** Do not modify raw files; do not build event summary; do not change other scripts.

## Required context

Schema in IMPLEMENTATION_SPEC Sections 4.2–4.4; sn_type as in catalog; time MJD, distance Mpc; duplicate removal.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Part B: fields, processing)
- `docs/IMPLEMENTATION_SPEC.md` (Sections 4.2–4.4)
- `scripts/clean_supernova_data.py` (current implementation)

## Expected file change

- Reads from `raw/supernova_raw/`.
- Writes: `data/supernova_catalog_clean.csv`, `data/supernova_lightcurves_long.csv`.
- Catalog: one row per SN; required columns; NaN for missing; exact duplicate rows removed.
- Light-curves: long format; one row per point; columns per spec.

## Forbidden alternatives

- Do not rename sn_type manually; keep as in catalog.
- Do not drop rows only for one missing field; use NaN.

## Atomic operations

1. Load raw catalog and light-curve data.
2. Normalize to required columns; units (MJD, Mpc); remove exact duplicates.
3. Write both CSVs to `data/`.

## Expected deliverables

- `data/supernova_catalog_clean.csv` and `data/supernova_lightcurves_long.csv` with required columns.

## Mandatory validation

- black, flake8, mypy on `scripts/clean_supernova_data.py`
- `python scripts/clean_supernova_data.py` — exit 0; both CSVs exist; columns match spec
- If tests exist: **all tests pass**

## Decision rules

- Flux unit: add column if available from source; document in README.

## Blackstops

- Missing raw input; validation or schema mismatch.

## Handoff package

- Modified: `scripts/clean_supernova_data.py`
- Confirmations: two CSVs present and valid
- Validation evidence: lint and run success
- Blockers: none or list

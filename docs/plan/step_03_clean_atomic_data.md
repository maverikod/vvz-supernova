# Step 03 — Clean atomic data

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/clean_atomic_data.py`  
**Plan file:** `docs/plan/step_03_clean_atomic_data.md`

---

## Executor role

Implement or verify the script that cleans raw atomic data and produces `data/atomic_lines_clean.csv`, `data/atomic_lines_by_element.csv`, `data/atomic_transition_summary.csv`. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/clean_atomic_data.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/clean_atomic_data.py`
- **Type:** standalone runnable script
- **Purpose:** Read raw atomic data; clean; deduplicate; output three CSVs per IMPLEMENTATION_SPEC.

## Dependency contract

- **Prerequisites:** Step 02 done (`raw/atomic_lines_raw/` populated).
- **Unlocks:** Step 07 (QC/plots need atomic outputs).
- **Forbidden:** Do not modify raw files; do not download; do not change other scripts.

## Required context

Schema and processing rules in IMPLEMENTATION_SPEC Section 3; frequency = c / wavelength_vac_nm; NaN for missing; no row drop for single missing field.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Part A: fields, processing)
- `docs/IMPLEMENTATION_SPEC.md` (Sections 3.2–3.5)
- `scripts/clean_atomic_data.py` (current implementation)

## Expected file change

- Reads from `raw/atomic_lines_raw/` (and manifest if present).
- Writes: `data/atomic_lines_clean.csv`, `data/atomic_lines_by_element.csv`, `data/atomic_transition_summary.csv`.
- Cleaning: strip Excel artifacts, normalize decimals, exact duplicate removal; frequency_hz from wavelength; NaN for missing.

## Forbidden alternatives

- Do not drop entire rows only because one column is missing.
- Do not invent or synthesize values.

## Atomic operations

1. Load raw data.
2. Normalize columns to spec; compute frequency_hz; clean numerics; deduplicate.
3. Write clean and by-element CSVs.
4. Aggregate per element → atomic_transition_summary.csv.

## Expected deliverables

- Three CSVs in `data/` with required columns; no duplicate rows in clean table.

## Mandatory validation

- black, flake8, mypy on `scripts/clean_atomic_data.py`
- `python scripts/clean_atomic_data.py` — exit 0; three CSVs exist; column names match spec
- If tests exist: **all tests pass**

## Decision rules

- If only air wavelength: use documented conversion to vacuum or set flag; document in README.

## Blackstops

- Missing raw input; validation or schema mismatch.

## Handoff package

- Modified: `scripts/clean_atomic_data.py`
- Confirmations: three CSVs present and valid
- Validation evidence: lint and run success
- Blockers: none or list

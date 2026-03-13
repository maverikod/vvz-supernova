# Step 02 — Download atomic data

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/download_atomic_data.py`  
**Plan file:** `docs/plan/step_02_download_atomic_data.md`

---

## Executor role

Implement or verify the script that downloads NIST ASD data into `raw/atomic_lines_raw/`. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/download_atomic_data.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/download_atomic_data.py`
- **Type:** standalone runnable script
- **Purpose:** Download atomic spectral lines for required elements; save under `raw/atomic_lines_raw/` with provenance (source, date, URL).

## Dependency contract

- **Prerequisites:** Step 01 done (directories exist).
- **Unlocks:** Step 03.
- **Forbidden:** Do not write to `data/` or `plots/`; do not modify other scripts.

## Required context

NIST Atomic Spectra Database; elements: H, He, C, N, O, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca, Fe, Ni.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Part A)
- `docs/IMPLEMENTATION_SPEC.md` (Section 3)
- `scripts/download_atomic_data.py` (current implementation)

## Expected file change

- Script writes only under `raw/atomic_lines_raw/`.
- Output: files (and/or manifest) with source name, download date, source URL.
- Elements covered as per task; if only subset available, document in manifest.

## Forbidden alternatives

- Do not write cleaned data or summaries.
- No synthetic or invented data.

## Atomic operations

1. Ensure `raw/atomic_lines_raw/` exists (or depend on Step 01).
2. Fetch data from NIST ASD for required elements (and ion states if available).
3. Save raw files and provenance metadata.

## Expected deliverables

- `raw/atomic_lines_raw/` non-empty; provenance recorded.

## Mandatory validation

- black, flake8, mypy on `scripts/download_atomic_data.py`
- `python scripts/download_atomic_data.py` — exit 0; raw dir non-empty
- If tests exist: **all tests pass**

## Decision rules

- If API/URL differs from NIST ASD: document in script and README.
- If only air wavelength available: store as-is; cleaning step will handle conversion.

## Blackstops

- Network or API failure; validation failure.

## Handoff package

- Modified: `scripts/download_atomic_data.py`
- Confirmations: raw files and manifest present
- Validation evidence: lint and run success
- Blockers: none or list

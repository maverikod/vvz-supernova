# Step 04 — Download supernova data

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/download_supernova_data.py`  
**Plan file:** `docs/plan/step_04_download_supernova_data.md`

---

## Executor role

Implement or verify the script that downloads supernova catalog and light-curve data into `raw/supernova_raw/`. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/download_supernova_data.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/download_supernova_data.py`
- **Type:** standalone runnable script
- **Purpose:** Download from open SN catalogs (OSC, ASAS-SN, ZTF, Pan-STARRS, etc.); save under `raw/supernova_raw/` with provenance.

## Dependency contract

- **Prerequisites:** Step 01 done (directories exist).
- **Unlocks:** Step 05.
- **Forbidden:** Do not write to `data/` or `plots/`; do not modify other scripts.

## Required context

Priority: Open Supernova Catalog, ASAS-SN, ZTF, Pan-STARRS; need light-curves and peak/max date where possible.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Part B)
- `docs/IMPLEMENTATION_SPEC.md` (Section 4)
- `scripts/download_supernova_data.py` (current implementation)

## Expected file change

- Script writes only under `raw/supernova_raw/`.
- Output: files and provenance (source, date, URL).

## Forbidden alternatives

- Do not write cleaned catalog or light-curves to `data/`.
- No synthetic or invented data.

## Atomic operations

1. Ensure `raw/supernova_raw/` exists.
2. Fetch from chosen open catalogs; save raw responses/files.
3. Record provenance metadata.

## Expected deliverables

- `raw/supernova_raw/` non-empty; metadata records sources used.

## Mandatory validation

- black, flake8, mypy on `scripts/download_supernova_data.py`
- `python scripts/download_supernova_data.py` — exit 0; raw dir non-empty
- If tests exist: **all tests pass**

## Decision rules

- If a catalog is unavailable: skip and document; continue with others.

## Blackstops

- No data from any source; validation failure.

## Handoff package

- Modified: `scripts/download_supernova_data.py`
- Confirmations: raw files and provenance present
- Validation evidence: lint and run success
- Blockers: none or list

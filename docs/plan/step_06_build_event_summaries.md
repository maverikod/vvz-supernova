# Step 06 — Build supernova event summaries

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/build_event_summaries.py`  
**Plan file:** `docs/plan/step_06_build_event_summaries.md`

---

## Executor role

Implement or verify the script that builds `data/supernova_event_summary.csv` from catalog and light-curves. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/build_event_summaries.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/build_event_summaries.py`
- **Type:** standalone runnable script
- **Purpose:** Compute per-SN summary (rise_time_days, decay_time_days, peak_width_days, etc.); write supernova_event_summary.csv.

## Dependency contract

- **Prerequisites:** Step 05 done (catalog and light-curves CSVs in `data/`).
- **Unlocks:** Step 07 (QC/plots need event summary).
- **Forbidden:** Do not modify catalog or light-curve CSVs; do not change other scripts.

## Required context

Summary schema in IMPLEMENTATION_SPEC Section 4.5; rise/decay/width from light-curves where possible; NaN otherwise; do not invent values.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Part B: supernova_event_summary)
- `docs/IMPLEMENTATION_SPEC.md` (Section 4.5)
- `scripts/build_event_summaries.py` (current implementation)

## Expected file change

- Reads: `data/supernova_catalog_clean.csv`, `data/supernova_lightcurves_long.csv`.
- Writes: `data/supernova_event_summary.csv` with at least sn_name, sn_type, source_catalog, peak_mjd, peak_mag, rise_time_days, decay_time_days, peak_width_days, lightcurve_points_count, redshift, luminosity_distance_Mpc.
- Compute rise/decay/width from light-curves when possible; else NaN. Document definition in script or README.

## Forbidden alternatives

- Do not invent or synthesize rise_time_days, decay_time_days, or peak_width_days.

## Atomic operations

1. Load catalog and light-curves.
2. Per SN: compute derived quantities from light-curve or set NaN.
3. Write summary CSV.

## Expected deliverables

- `data/supernova_event_summary.csv` with required columns; NaN where computation not possible.

## Mandatory validation

- black, flake8, mypy on `scripts/build_event_summaries.py`
- `python scripts/build_event_summaries.py` — exit 0; summary CSV exists; columns match spec
- If tests exist: **all tests pass**

## Decision rules

- Definition of rise/decay/width: document in docstring (e.g. time from X% of peak to peak and peak to X% decline).

## Blackstops

- Missing input CSVs; validation or schema mismatch.

## Handoff package

- Modified: `scripts/build_event_summaries.py`
- Confirmations: summary CSV present and valid
- Validation evidence: lint and run success
- Blockers: none or list

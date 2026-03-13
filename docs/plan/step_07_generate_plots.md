# Step 07 — Quality control and generate plots

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/generate_plots.py`  
**Plan file:** `docs/plan/step_07_generate_plots.md`

---

## Executor role

Implement or verify the script that outputs QC metrics and produces the six required plots. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/generate_plots.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/generate_plots.py`
- **Type:** standalone runnable script
- **Purpose:** Read from `data/`; print/write QC metrics; save six PNGs under `plots/`.

## Dependency contract

- **Prerequisites:** Step 03 done (atomic CSVs); Step 06 done (supernova_event_summary.csv).
- **Unlocks:** Step 08 (README can reference metrics and plot list).
- **Forbidden:** Do not modify any CSV in `data/`; do not change other scripts.

## Required context

Part D of task: six metrics (elements count, lines count, SN count, SN with light-curve, SN with rise_time, sources list); six plots per IMPLEMENTATION_SPEC Section 6.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Part D)
- `docs/IMPLEMENTATION_SPEC.md` (Section 6)
- Existing `scripts/verify_pipeline_data.py` if it overlaps (avoid duplication; this step = one script for QC + plots)

## Expected file change

- Reads: `data/atomic_lines_clean.csv`, `data/atomic_transition_summary.csv`, `data/supernova_catalog_clean.csv`, `data/supernova_event_summary.csv`, `data/supernova_lightcurves_long.csv` as needed.
- Outputs: (1) QC metrics to stdout and/or small report file; (2) six files: `plots/atomic_frequency_histogram.png`, `plots/atomic_Aki_histogram.png`, `plots/supernova_peak_mag_histogram.png`, `plots/supernova_rise_time_histogram.png`, `plots/supernova_decay_time_histogram.png`, `plots/example_lightcurves.png`.

## Forbidden alternatives

- Do not overwrite or alter data CSVs.
- Do not add plots not in the required list without task change.

## Atomic operations

1. Load required CSVs.
2. Compute and output six QC metrics.
3. Generate each of the six plots and save to `plots/`.

## Expected deliverables

- All six PNGs in `plots/`; metrics consistent with CSV contents.

## Mandatory validation

- black, flake8, mypy on `scripts/generate_plots.py`
- `python scripts/generate_plots.py` — exit 0; six PNGs exist
- If tests exist: **all tests pass**

## Decision rules

- If `verify_pipeline_data.py` already does metrics: either merge plot generation into it and treat that as the "code file" for this step, or keep generate_plots.py and have it call/copy metrics logic so one script does QC+plots. Plan file points to single code file: `scripts/generate_plots.py` (or rename to `run_quality_control.py` and include plots).

## Blackstops

- Missing input CSVs; validation failure; missing PNGs.

## Handoff package

- Modified: `scripts/generate_plots.py`
- Confirmations: six PNGs and metrics output
- Validation evidence: lint and run success
- Blockers: none or list

# Step 08: Refactor `build_supernova_transient_events.py`

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for the downstream supernova event-table builder. Your job is to carry repaired timing coverage into `supernova_transient_events.csv` without weakening the third-spec validity threshold.

## Execution directive

Edit exactly one production file: `scripts/build_supernova_transient_events.py`. Do not edit the schema file or any upstream file in this step.

## Target file

`scripts/build_supernova_transient_events.py`

## Step scope

This step updates only the downstream event-table projection logic. It does not change upstream timing computation or reporting.

## Dependency contract

- Steps 05 and 07 must already be complete.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- `supernova_atomic/third_spec_schema.py` remains authoritative for `MIN_LIGHTCURVE_POINTS_VALID`.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `docs/TECH_SPEC.md`
- `supernova_atomic/third_spec_schema.py`
- `scripts/build_supernova_transient_events.py`
- `scripts/build_event_summaries.py`

You must edit these symbols inside the target file:

- `main()`
- `_peak_abs_mag()`
- the points-per-supernova counting path

## Forbidden scope

- Do not edit `supernova_atomic/third_spec_schema.py`.
- Do not create a new downstream CSV file.
- Do not weaken `MIN_LIGHTCURVE_POINTS_VALID`.
- Do not infer time-domain readiness from metadata-only rows.

## Atomic operations

1. Keep the output file path exactly `data/supernova_transient_events.csv`.
2. Keep the existing output column contract from `SUPERNOVA_TRANSIENT_EVENTS_COLUMNS`.
3. Continue to count points from `data/supernova_lightcurves_long.csv`.
4. Set `number_of_points` for each row from the long-table count if present; otherwise fall back to `lightcurve_points_count` from the summary row.
5. Set `has_lightcurve` exactly as:
   - `1` when `number_of_points >= MIN_LIGHTCURVE_POINTS_VALID`
   - `0` otherwise
6. Keep rows only when `peak_abs_mag` is computable from `peak_mag` and `luminosity_distance_Mpc`.
7. Preserve timing fields from `supernova_event_summary.csv` without recomputation.
8. Ensure at least one curated row with valid distance and enough points survives into the output when upstream data permits.

## Expected file change

Only `scripts/build_supernova_transient_events.py` changes in this step.

That file must change in these exact areas:

- `main()` must carry the repaired point counts into downstream rows;
- `has_lightcurve` must follow the exact `MIN_LIGHTCURVE_POINTS_VALID` rule;
- timing fields must remain a projection of upstream summary values, not be recomputed here.

## Expected deliverables

- Updated `scripts/build_supernova_transient_events.py`
- `data/supernova_transient_events.csv` with at least one row having:
  - `has_lightcurve=1`
  - `number_of_points >= 20`

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python scripts/build_supernova_transient_events.py
python -m black scripts/build_supernova_transient_events.py
python -m flake8 scripts/build_supernova_transient_events.py
python -m mypy scripts/build_supernova_transient_events.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `data/supernova_transient_events.csv` must contain at least one row with `has_lightcurve=1`;
- that output must contain at least one row with `number_of_points >= 20`;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- Never set `has_lightcurve=1` for `number_of_points < 20`.
- Never recompute rise, decay, or width here.
- If `peak_abs_mag` cannot be computed, the row is dropped exactly as in the current implementation.
- Use summary timing fields as-is; downstream logic is a projection, not a second timing engine.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Steps 05 or 07 are incomplete.
- The target file would exceed the project file-size limit.
- A second production file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- The threshold in `supernova_atomic/third_spec_schema.py` would need to change to make the step pass.

## Handoff package

When the step is complete, the handoff must include:

- the exact `has_lightcurve` rule implemented;
- count of output rows with `has_lightcurve=1`;
- count of output rows with `number_of_points >= 20`;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

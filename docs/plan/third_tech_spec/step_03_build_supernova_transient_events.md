# Step 03 — Build supernova_transient_events.csv

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 plan file.  
**Code file:** `scripts/build_supernova_transient_events.py`

---

## Executor role

Read catalog, event summary, lightcurves; map to spec columns; filter rows without peak_abs_mag; assign event_id; write `data/supernova_transient_events.csv`.

## Execution directive

Execute only this step. Create only `scripts/build_supernova_transient_events.py`. Stop on validation failure.

## Read first

- `docs/Third_tech_spec.md`
- `scripts/build_event_summaries.py` (output columns)
- `data/supernova_catalog_clean.csv`, `data/supernova_event_summary.csv`, `data/supernova_lightcurves_long.csv`

## Expected file change

- Read supernova_catalog_clean.csv, supernova_event_summary.csv, supernova_lightcurves_long.csv.
- Map: name, type, redshift, distance_Mpc, peak_abs_mag (derive from peak_mag + distance modulus when possible; else empty), peak_mag, L_proxy = 10^(-0.4 * peak_abs_mag), rise_time_days, decay_time_days, width_days (e.g. peak_width_days), t0_days, asymmetry, width_norm, event_strength, has_lightcurve, number_of_points.
- Filter out rows without peak_abs_mag (spec: drop events without peak_abs_mag).
- event_id = name; append index if duplicates.
- Light curve valid only if number_of_points ≥ 20 (has_lightcurve set accordingly).
- Output columns per spec: event_id, name, type, redshift, distance_Mpc, peak_abs_mag, L_proxy, rise_time_days, decay_time_days, width_days, t0_days, asymmetry, width_norm, event_strength, has_lightcurve, number_of_points.

## Mandatory validation

- black, flake8, mypy on `scripts/build_supernova_transient_events.py`
- Run script; supernova_transient_events.csv exists with correct columns.

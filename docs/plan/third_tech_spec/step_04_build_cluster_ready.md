# Step 04 — Build cluster_ready_events.csv

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 plan file.  
**Code file:** `scripts/build_cluster_ready.py`

---

## Executor role

Read atomic_transition_events.csv and supernova_transient_events.csv; build unified table with event_id, domain, logE, logt, logQ_or_width, shape_1, shape_2, class_hint; only rows with finite log-values; write `data/cluster_ready_events.csv`.

## Execution directive

Execute only this step. Create only `scripts/build_cluster_ready.py`. Stop on validation failure.

## Read first

- `docs/Third_tech_spec.md` (cluster_ready_events.csv columns and formulas)
- Outputs of steps 02 and 03

## Expected file change

- Read data/atomic_transition_events.csv and data/supernova_transient_events.csv.
- Atomic: logE = log10(deltaE_eV), logt = log10(tau_s), logQ_or_width = log10(Q_proxy), shape_1 = deltaJ, shape_2 = parity_change, class_hint = "atomic_transition". Skip rows where Q_proxy <= 0 or deltaE_eV/tau_s invalid (avoid -inf).
- Supernova: logE = log10(L_proxy), logt = log10(t0_days), logQ_or_width = log10(width_norm) or log10(width_days) if width_norm missing, shape_1 = asymmetry, shape_2 = number_of_points, class_hint = "stellar_transient". Skip rows where log would be -inf or nan.
- Output columns: event_id, domain (atomic/supernova), logE, logt, logQ_or_width, shape_1, shape_2, class_hint.

## Mandatory validation

- black, flake8, mypy on `scripts/build_cluster_ready.py`
- Run script; cluster_ready_events.csv exists with correct columns.

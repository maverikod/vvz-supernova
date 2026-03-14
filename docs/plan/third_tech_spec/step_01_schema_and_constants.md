# Step 01 — Schema and constants for Third spec

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 plan file.  
**Code/artifact:** New module under `supernova_atomic/` (e.g. `third_spec_schema.py`) or extend `atomic_schema.py`.

---

## Executor role

Implement shared schema and constants for Third tech spec: parity rule, energy conversion (cm-1 → eV), transition_id / event_id formats, class_hint mapping.

## Execution directive

Execute only this step. Add or extend package module so that scripts can import. Stop on validation failure.

## Read first

- `docs/Third_tech_spec.md` (including ADDITIONAL SPECIFICATIONS)
- `supernova_atomic/atomic_schema.py`

## Expected file change

- **Parity:** function or rule: parity = 1 if term contains (o, °, odd), else 0.
- **Energy:** constant CM1_TO_EV = 8065.54429; function E_cm1_to_eV(E_cm1) and deltaE_eV(Ei_cm1, Ek_cm1).
- **IDs:** document or helper for transition_id `{element}_{ion}_{lower}_{upper}_{row}`; event_id = name + index if duplicates.
- **class_hint:** CLASS_HINT_ATOMIC = "atomic_transition", CLASS_HINT_SUPERNOVA = "stellar_transient".
- Column name constants for atomic_transition_events, supernova_transient_events, cluster_ready_events if useful.

## Mandatory validation

- black, flake8, mypy on new/changed files.

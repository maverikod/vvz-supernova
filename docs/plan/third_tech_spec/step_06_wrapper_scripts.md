# Step 06 — Wrapper scripts (spec names)

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 plan file.  
**Code files:** `scripts/download_atomic.py`, `scripts/download_supernova.py`, `scripts/clean_atomic.py`, `scripts/clean_supernova.py`

---

## Executor role

Add four wrapper scripts that call existing and new scripts so that spec script names are available. Do not rename existing scripts.

## Execution directive

Execute only this step. Create only the four wrapper scripts. Stop on validation failure.

## Read first

- `docs/Third_tech_spec.md` (script names, "Do not rename existing scripts")
- Plan step 02–05 (which scripts are called)

## Expected file change

- **download_atomic.py:** Invoke `scripts/download_atomic_data.py` (e.g. subprocess or import main); exit with same code.
- **download_supernova.py:** Invoke `scripts/download_supernova_data.py`; exit with same code.
- **clean_atomic.py:** Run `scripts/clean_atomic_data.py` then `scripts/build_atomic_transition_events.py`; exit non-zero if either fails.
- **clean_supernova.py:** Run `scripts/clean_supernova_data.py` then `scripts/build_event_summaries.py` then `scripts/build_supernova_transient_events.py`; exit non-zero if any fails.

All run from project root; docstrings state they are wrappers per Third tech spec.

## Mandatory validation

- black, flake8, mypy on all four wrapper scripts.
- Each wrapper runs without error when dependencies are satisfied.

# Third Tech Spec — Plan index

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Reference:** [docs/Third_tech_spec.md](../../Third_tech_spec.md)

**Rule:** 1 step = 1 plan file; each step specifies the code/script(s) to add or change. Existing scripts are not renamed; spec names are satisfied by wrapper scripts.

---

## Steps and plan files

| Step | Plan file | Main artifact |
|------|-----------|---------------|
| 01 | [step_01_schema_and_constants.md](step_01_schema_and_constants.md) | Schema and constants (parity, energy conversion, IDs, class_hint) in package |
| 02 | [step_02_build_atomic_transition_events.md](step_02_build_atomic_transition_events.md) | `scripts/build_atomic_transition_events.py` → `data/atomic_transition_events.csv` |
| 03 | [step_03_build_supernova_transient_events.md](step_03_build_supernova_transient_events.md) | `scripts/build_supernova_transient_events.py` → `data/supernova_transient_events.csv` |
| 04 | [step_04_build_cluster_ready.md](step_04_build_cluster_ready.md) | `scripts/build_cluster_ready.py` → `data/cluster_ready_events.csv` |
| 05 | [step_05_reporting.md](step_05_reporting.md) | `scripts/build_third_spec_report.py` → `report/data_report.md`, missingness_report.csv, source_manifest.csv |
| 06 | [step_06_wrapper_scripts.md](step_06_wrapper_scripts.md) | `scripts/download_atomic.py`, download_supernova.py, clean_atomic.py, clean_supernova.py |
| 07 | [step_07_archive_and_readme.md](step_07_archive_and_readme.md) | Archive layout (data/, scripts/, report/), README |

---

## Completion criteria

- All three CSV outputs exist with spec columns; no synthetic data; empty where source missing.
- Wrapper scripts exist with spec names.
- Report contains load/drop/remain counts, drop reasons, missingness.
- Archive structure matches spec.
- black, flake8, mypy pass on all touched code.

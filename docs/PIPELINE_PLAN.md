# Pipeline plan — index

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This plan implements `docs/task_supernova_atomic_pipeline.txt`. Schema and rules: `docs/IMPLEMENTATION_SPEC.md`.

**Rule:** 1 step = 1 code file = 1 plan file. Each step has a dedicated plan file in `docs/plan/`.

---

## Structure

- **Step files:** `docs/plan/step_NN_<name>.md` — one file per step; executor follows that file only for the step.
- **Parallel execution:** `docs/plan/PARALLEL_EXECUTION.md` — waves, dependency graph, and commands for parallel run.

---

## Steps and code files

| Step | Code file | Plan file |
|------|-----------|-----------|
| 01 | `scripts/ensure_dirs.py` | [step_01_ensure_dirs.md](plan/step_01_ensure_dirs.md) |
| 02 | `scripts/download_atomic_data.py` | [step_02_download_atomic_data.md](plan/step_02_download_atomic_data.md) |
| 03 | `scripts/clean_atomic_data.py` | [step_03_clean_atomic_data.md](plan/step_03_clean_atomic_data.md) |
| 04 | `scripts/download_supernova_data.py` | [step_04_download_supernova_data.md](plan/step_04_download_supernova_data.md) |
| 05 | `scripts/clean_supernova_data.py` | [step_05_clean_supernova_data.md](plan/step_05_clean_supernova_data.md) |
| 06 | `scripts/build_event_summaries.py` | [step_06_build_event_summaries.md](plan/step_06_build_event_summaries.md) |
| 07 | `scripts/generate_plots.py` | [step_07_generate_plots.md](plan/step_07_generate_plots.md) |
| 08 | `README.md` | [step_08_readme.md](plan/step_08_readme.md) |
| 09 | `scripts/build_archive.py` | [step_09_build_archive.md](plan/step_09_build_archive.md) |

---

## Parallel execution (optimized)

Independent steps are grouped into **waves**. Steps in the same wave can run in parallel.

| Wave | Steps | Parallel? |
|------|-------|-----------|
| 0 | 01 ensure_dirs | — |
| 1 | 02 download_atomic, **04 download_supernova** | Yes |
| 2 | 03 clean_atomic, **05 clean_supernova** | Yes |
| 3 | 06 build_event_summaries | — |
| 4 | 07 generate_plots | — |
| 5 | 08 README | — |
| 6 | 09 build_archive (optional) | — |

Full dependency graph, exact commands for serial and parallel run, and completion criteria: **[docs/plan/PARALLEL_EXECUTION.md](plan/PARALLEL_EXECUTION.md)**.

---

## Prerequisites

- Python 3.x, venv (`.venv`) activated.
- Dependencies from `pyproject.toml`.
- Project root = working directory for all commands.

---

## Completion criteria

- All required steps executed; for each code file: black, flake8, mypy pass; script run success.
- If a test suite exists: **all tests pass**.

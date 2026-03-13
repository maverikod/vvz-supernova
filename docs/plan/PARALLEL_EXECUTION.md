# Parallel execution plan

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This document defines **execution waves** so that independent steps run in parallel. Rule: **1 step = 1 code file = 1 plan file**. Step files live in `docs/plan/step_NN_*.md`.

---

## Dependency graph

```
                    Step 01 (ensure_dirs)
                           |
            +--------------+--------------+
            |                             |
      Step 02 (download_atomic)    Step 04 (download_supernova)
            |                             |
      Step 03 (clean_atomic)        Step 05 (clean_supernova)
            |                             |
            |                       Step 06 (build_event_summaries)
            |                             |
            +--------------+--------------+
                           |
                    Step 07 (generate_plots)
                           |
                    Step 08 (README)
                           |
                    Step 09 (build_archive, optional)
```

---

## Execution waves

Steps in the **same wave** have no dependency on each other and **can run in parallel**. Run a wave only after all steps of the previous wave are complete.

| Wave | Steps | Code files | Can run in parallel |
|------|-------|------------|---------------------|
| **0** | Step 01 | `scripts/ensure_dirs.py` | — |
| **1** | Step 02, Step 04 | `download_atomic_data.py`, `download_supernova_data.py` | Yes (atomic and supernova downloads) |
| **2** | Step 03, Step 05 | `clean_atomic_data.py`, `clean_supernova_data.py` | Yes (clean atomic and clean supernova) |
| **3** | Step 06 | `build_event_summaries.py` | — (depends on Step 05 only) |
| **4** | Step 07 | `generate_plots.py` | — (depends on Step 03 and Step 06) |
| **5** | Step 08 | `README.md` | — |
| **6** | Step 09 | `scripts/build_archive.py` | — (optional) |

---

## Wave execution commands

**Serial (one after another):**
```bash
python scripts/ensure_dirs.py
python scripts/download_atomic_data.py && python scripts/download_supernova_data.py   # wave 1
python scripts/clean_atomic_data.py && python scripts/clean_supernova_data.py       # wave 2
python scripts/build_event_summaries.py
python scripts/generate_plots.py
# Then update README (Step 08), then optionally:
python scripts/build_archive.py
```

**Parallel (wave 1 and wave 2 in background):**
```bash
python scripts/ensure_dirs.py

# Wave 1: run both downloads in parallel
python scripts/download_atomic_data.py &   PID1=$!
python scripts/download_supernova_data.py &   PID2=$!
wait $PID1 $PID2

# Wave 2: run both clean scripts in parallel
python scripts/clean_atomic_data.py &   PID3=$!
python scripts/clean_supernova_data.py &   PID4=$!
wait $PID3 $PID4

# Rest is serial
python scripts/build_event_summaries.py
python scripts/generate_plots.py
# README, then optional build_archive.py
```

---

## Step ↔ code file ↔ plan file mapping

| Step | Code file | Plan file |
|------|-----------|-----------|
| 01 | `scripts/ensure_dirs.py` | `docs/plan/step_01_ensure_dirs.md` |
| 02 | `scripts/download_atomic_data.py` | `docs/plan/step_02_download_atomic_data.md` |
| 03 | `scripts/clean_atomic_data.py` | `docs/plan/step_03_clean_atomic_data.md` |
| 04 | `scripts/download_supernova_data.py` | `docs/plan/step_04_download_supernova_data.md` |
| 05 | `scripts/clean_supernova_data.py` | `docs/plan/step_05_clean_supernova_data.md` |
| 06 | `scripts/build_event_summaries.py` | `docs/plan/step_06_build_event_summaries.md` |
| 07 | `scripts/generate_plots.py` | `docs/plan/step_07_generate_plots.md` |
| 08 | `README.md` | `docs/plan/step_08_readme.md` |
| 09 | `scripts/build_archive.py` | `docs/plan/step_09_build_archive.md` |

---

## Completion criteria

- All steps of the last required wave (08, or 09 if archive is required) are done.
- For each step: black, flake8, mypy pass on the code file; script run succeeds; if tests exist, **all tests pass**.

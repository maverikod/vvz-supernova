# Step 01 — Ensure directories

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/ensure_dirs.py`  
**Plan file:** `docs/plan/step_01_ensure_dirs.md`

---

## Executor role

Implement or verify the script that creates pipeline directories. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/ensure_dirs.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/ensure_dirs.py`
- **Type:** standalone runnable script
- **Purpose:** Create `raw/atomic_lines_raw/`, `raw/supernova_raw/`, `data/`, `plots/` if missing; idempotent.

## Dependency contract

- **Prerequisites:** Project root exists; venv activated.
- **Unlocks:** Step 02, Step 04 (both may run after this).
- **Forbidden:** Do not create or modify any other scripts or data files.

## Required context

`docs/PROJECT_STRUCTURE.md` (directory layout).

## Read first

- `docs/PROJECT_STRUCTURE.md`
- `docs/task_supernova_atomic_pipeline.txt` (Parts A–B: raw/ and data/ paths)

## Expected file change

- Create `scripts/ensure_dirs.py` if missing.
- Script creates (with `pathlib` or `os.makedirs`) from project root: `raw/atomic_lines_raw/`, `raw/supernova_raw/`, `data/`, `plots/`.
- No overwrite of existing files; directories only. Module docstring and Author/email in header.

## Forbidden alternatives

- Do not create directories inside `supernova_atomic/` for this step.
- Do not download or write data; only create empty directories.

## Atomic operations

1. Resolve project root (e.g. script location → parent of `scripts/`).
2. Create each of the four paths if not present.

## Expected deliverables

- `scripts/ensure_dirs.py` present and runnable.
- After run: `raw/atomic_lines_raw/`, `raw/supernova_raw/`, `data/`, `plots/` exist.

## Mandatory validation

- `black scripts/ensure_dirs.py`
- `flake8 scripts/ensure_dirs.py`
- `mypy scripts/ensure_dirs.py`
- Run: `python scripts/ensure_dirs.py` — exit 0; directories exist.
- If tests exist: **all tests pass**.

## Decision rules

- If script already exists and behaviour matches: no change; validation still required.
- If project root detection differs from other scripts: align with existing convention in `scripts/`.

## Blackstops

- Directory creation fails (permissions, path error).
- Validation (black/flake8/mypy or tests) fails.

## Handoff package

- Modified/created: `scripts/ensure_dirs.py`
- Confirmations: directories exist after run
- Validation evidence: black/flake8/mypy clean; script run success
- Blockers: none or list

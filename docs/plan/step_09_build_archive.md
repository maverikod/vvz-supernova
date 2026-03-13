# Step 09 — Build final archive (optional)

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `scripts/build_archive.py`  
**Plan file:** `docs/plan/step_09_build_archive.md`

---

## Executor role

Implement or verify the script that creates `supernova_atomic_data_pipeline.zip` with README.md, scripts/, raw/, data/, plots/. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing code. Modify only `scripts/build_archive.py`. Stop on any blackstop.

## Step scope

- **Target file:** `scripts/build_archive.py`
- **Type:** standalone runnable script
- **Purpose:** Package project root contents into a zip per task (README.md, scripts/, raw/, data/, plots/).

## Dependency contract

- **Prerequisites:** Step 08 done (README final); pipeline run complete so data/ and plots/ are populated.
- **Unlocks:** None (final deliverable).
- **Forbidden:** Do not modify README, data, or plots; do not change other scripts.

## Required context

Task: archive name `supernova_atomic_data_pipeline.zip`; structure: README.md, scripts/, raw/, data/, plots/.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Final archive)
- `docs/PROJECT_STRUCTURE.md`
- Current `scripts/build_archive.py` if present

## Expected file change

- Script creates zip from project root (or current dir) including README.md, scripts/, raw/, data/, plots/.
- Output path: e.g. project root or `dist/`; archive name: `supernova_atomic_data_pipeline.zip`.

## Forbidden alternatives

- Do not include .venv, __pycache__, .git, or gitignored build artifacts unless task says so.
- Do not change contents of included directories.

## Atomic operations

1. Resolve project root and output path.
2. Build zip with required top-level entries; exclude per .gitignore where appropriate.
3. Write zip file.

## Expected deliverables

- `supernova_atomic_data_pipeline.zip` exists; unpacking yields README.md, scripts/, raw/, data/, plots/.

## Mandatory validation

- black, flake8, mypy on `scripts/build_archive.py`
- `python scripts/build_archive.py` — exit 0; zip exists; structure correct
- If tests exist: **all tests pass**

## Decision rules

- Optional step: if product owner skips archive, script may still be implemented for reproducibility.

## Blackstops

- Missing README or directories; validation failure.

## Handoff package

- Modified: `scripts/build_archive.py`
- Confirmations: zip created and structure verified
- Validation evidence: lint and run success
- Blockers: none or list

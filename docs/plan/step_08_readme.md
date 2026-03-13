# Step 08 — README

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 code file = 1 plan file.  
**Code file:** `README.md` (repository root; deliverable = this file)  
**Plan file:** `docs/plan/step_08_readme.md`

---

## Executor role

Create or update `README.md` so it contains sources, output files, table fields, run order, dependencies, and units. No alternative implementations.

## Execution directive

Execute only this step. Read "Read first" before changing content. Modify only `README.md` at repository root. Stop on any blackstop.

## Step scope

- **Target file:** `README.md`
- **Type:** documentation
- **Purpose:** Fulfil Part F of task: sources, files, fields, run instructions, dependencies, units.

## Dependency contract

- **Prerequisites:** Steps 01–07 done (so run order and file list are final).
- **Unlocks:** Step 09 (archive can include README).
- **Forbidden:** Do not change code or data; do not add unrequested sections.

## Required context

Part F of task; IMPLEMENTATION_SPEC Section 8; parallel run order from `docs/plan/PARALLEL_EXECUTION.md`.

## Read first

- `docs/task_supernova_atomic_pipeline.txt` (Part F)
- `docs/IMPLEMENTATION_SPEC.md` (Section 8)
- `docs/plan/PARALLEL_EXECUTION.md` (run order and waves)
- Current `README.md` if present

## Expected file change

- README.md contains: (1) sources used (atomic + supernova), (2) list of created files (data/, plots/, raw/ structure), (3) summary of fields in each final table or reference to IMPLEMENTATION_SPEC, (4) step-by-step commands to run all scripts (including parallel waves if applicable), (5) Python version and dependencies (pyproject.toml), (6) units reference (nm, Hz, MJD, days, Mpc, etc.).

## Forbidden alternatives

- Do not remove or contradict project structure in docs/PROJECT_STRUCTURE.md.
- Do not add theoretical or interpretative content beyond task.

## Atomic operations

1. Gather final list of scripts and output files from plan.
2. Write or update README sections per Part F and IMPLEMENTATION_SPEC.

## Expected deliverables

- `README.md` at project root; all six content items present and accurate.

## Mandatory validation

- README exists; sections 1–6 present; commands runnable as documented.
- No code linters for markdown; optional: markdownlint if project uses it.

## Decision rules

- If run order is parallel: document "run wave 1 (step 01), then wave 2 (steps 02 and 04 in parallel), ..." or equivalent.

## Blackstops

- Missing any of the six required content items.

## Handoff package

- Modified: `README.md`
- Confirmations: all six items present
- Validation evidence: manual check
- Blockers: none or list

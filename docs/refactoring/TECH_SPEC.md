# Data-First Refactoring Technical Specification (TZ)

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This document is the technical specification for a **data-first refactoring** of the supernova–atomic pipeline repository. The primary goal is **not** to improve code for its own sake, but to remove architectural and implementation blockers that currently prevent the repository from producing the **required dataset for physical analysis**, especially the supernova time-domain dataset.

This document defines objectives, scope, current-state evidence, target state, constraints, and completion conditions. It does **not** define the step-by-step execution plan; the plan is written later in a separate directory after discussion and must reference this TZ.

**Governing documents (read first by any executor or plan author):**
- **Project TZ:** `docs/TECH_SPEC.md`
- **Sources and algorithms:** `docs/DATA_SOURCES_AND_ALGORITHMS.md`
- **Project structure:** `docs/PROJECT_STRUCTURE.md`
- **Scale-law branch:** `docs/scale_law_validation/TECH_SPEC.md`
- **Project rules:** `.cursor/rules/` and user rules: file size 350–400 lines, one class = one file, no placeholder code, black/flake8/mypy, and **all tests pass**.

---

## 1. Primary objective

The objective of this refactoring branch is to make the repository capable of producing a **usable, verified, and analysis-ready dataset**, not merely a validation-clean codebase.

The required dataset must include:

- a complete and verified **atomic branch** from NIST ASD;
- a canonical **supernova catalog layer**;
- a non-empty **supernova photometry layer** with real time-series points from at least one timing-capable source beyond the current OSC bulk metadata file;
- a non-empty **event-summary layer** with actually computed time-domain fields, especially `peak_mjd`, `rise_time_days`, `decay_time_days`, and `peak_width_days` where source photometry permits;
- provenance and verification outputs sufficient to understand source coverage, merge conflicts, missingness, and physical usability.

Refactoring is in scope only insofar as it is required to make the above dataset obtainable, reproducible, and verifiable.

---

## 2. Problem statement

The repository currently produces:

- a strong atomic dataset from NIST ASD;
- a large supernova object catalog from OSC bulk JSON;
- verification scripts for raw downloads and final pipeline outputs;
- event and report layers for downstream analysis.

However, the current repository **does not yet produce the necessary time-domain supernova dataset** because:

- `download_supernova_data.py` downloads only the OSC bulk catalog, not photometry time series;
- `clean_supernova_data.py` therefore often produces an empty `supernova_lightcurves_long.csv`;
- `build_event_summaries.py` then has no usable light curves for rise/decay/width estimation;
- the current outputs can pass structural verification while still being physically incomplete for time-domain analysis.

Therefore, the main gap is **dataset completeness**, not just code cleanliness.

---

## 3. Current state (evidence)

### 3.1. Data state

Observed from the current pipeline state:

- atomic branch is populated and verified;
- OSC bulk catalog is downloaded and readable;
- `supernova_catalog_clean.csv` is populated;
- `supernova_lightcurves_long.csv` is empty or effectively empty in the current OSC-bulk-only flow;
- `supernova_event_summary.csv` exists, but time-domain fields derived from light curves remain empty when light curves are absent.

This means the current repository can produce a **catalog dataset**, but not yet the **required time-domain dataset** for analysis of outburst timing.

### 3.2. Source support gap

Per `docs/TECH_SPEC.md` and `docs/DATA_SOURCES_AND_ALGORITHMS.md`, the target source set for photometry and timing includes:

- OAC API / OSC per-object photometry;
- ASAS-SN;
- CfA Supernova Archive;
- Carnegie Supernova Project (CSP);
- optionally YSE or similar public releases.

Current implementation status:

- OSC bulk catalog: implemented;
- OAC API photometry: not implemented;
- ASAS-SN ingestion: not implemented;
- CfA ingestion: not implemented;
- CSP ingestion: not implemented.

### 3.3. Codebase state relevant to delivery of data

The following files are large enough to create execution and handoff risk and may need splitting during the plan, because they sit on or near the data path:

| File | Lines | Relevance |
|------|-------|-----------|
| `scripts/clean_astrophysical_transient_data.py` | 477 | Oversized script in transient data path. |
| `docs/search/engine/theory_index/sqlite_search.py` | 437 | Oversized but not on the main data-delivery path. |
| `scripts/download_astrophysical_transient_data.py` | 416 | Oversized download script in transient data path. |
| `scripts/build_fourth_spec_report.py` | 405 | Oversized reporting script. |
| `scripts/build_astrophysical_transient_events.py` | 396 | Near limit; derived-data path. |
| `scripts/clean_supernova_data.py` | 380 | Critical for current supernova pipeline. |
| `scripts/build_atomic_transition_passports.py` | 374 | Derived-data path. |
| `supernova_atomic/nist_parser.py` | 368 | Atomic ingestion path. |

These are not the goal by themselves. They matter only where their structure prevents reliable execution, testing, or extension toward the target dataset.

### 3.4. Validation state

The repository already has:

- `tests/test_atomic_pipeline_verification.py`
- `tests/test_theory_search_engine.py`
- `tests/test_source_field_checks.py`
- `tests/test_raw_download_verification.py`

This is a good baseline, but the current suite does **not** by itself prove that the required multi-source supernova timing dataset is obtainable.

---

## 4. Target state

At the end of this refactoring branch, the repository must be able to produce an analysis-ready dataset with the following properties.

### 4.1. Required deliverables

The final system must produce:

1. `raw/atomic_lines_raw/` with valid NIST payload coverage and manifest.
2. `raw/supernova_raw/` with:
   - canonical object source(s),
   - at least one implemented time-series source for supernova photometry,
   - manifests documenting used and skipped sources.
3. `data/supernova_catalog_clean.csv` as the canonical catalog layer.
4. `data/supernova_lightcurves_long.csv` as a **non-empty** merged photometry table.
5. `data/supernova_event_summary.csv` with **non-zero populated counts** for derived timing fields wherever photometry is available.
6. Verification outputs that make source coverage and data quality explicit.

### 4.2. Required data properties

The final dataset must satisfy all of the following:

- no synthetic rows or invented values;
- source provenance preserved at row level where applicable;
- time values normalized to MJD;
- catalog and photometry layers merged without silent overwrites;
- duplicate handling is documented and deterministic;
- event summaries are derived from real photometry, not guessed defaults;
- missing values remain empty where the source truly does not provide the information.

### 4.3. Required engineering properties

Any file modified or created by the plan must:

- follow project file-size and docstring rules;
- contain no placeholder logic;
- preserve public CLI and output contracts unless a step explicitly and narrowly changes the data path for the purpose of producing the required dataset;
- pass `black`, `flake8`, `mypy`, and the full test suite.

---

## 5. In scope

### 5.1. Data-delivery work

In scope:

- implementing or restructuring ingestion required to obtain real supernova light curves and time-domain data;
- implementing or restructuring merge logic required to combine catalog and photometry layers;
- implementing or restructuring event-summary computation so that real timing outputs are produced when light curves exist;
- implementing verification and reporting needed to prove the dataset is usable for analysis.

### 5.2. Refactoring work

In scope only when it supports the data objective:

- splitting oversized files on the data path;
- extracting helpers/modules to make ingestion, merge, verification, or event building reliable and handoff-ready;
- tightening tests to cover source ingestion, merge behavior, and timing derivation;
- removing structural ambiguity that blocks executor-style steps.

---

## 6. Out of scope

Out of scope for this branch:

- changing the theory content in `docs/scale_law_validation/`;
- changing the theory-search database contents in `docs/search/db/`;
- speculative new physical models or synthetic augmentation of missing observables;
- schema churn that is not required for obtaining the target dataset;
- unrelated code cleanup that does not improve the ability to produce or verify the required data.

---

## 7. Constraints (invariants)

- **Canonical rule:** code changes are justified only by the need to obtain, merge, verify, or summarize the required data.
- **One step = one code file = one step file.**
- **No architectural guesswork:** each later plan step must name exact files, exact expected change, exact checks, and exact blockers.
- **No alternative implementations:** the plan must prescribe one concrete implementation path per step.
- **No silent behavior drift:** a step must not change pipeline wave order, output names, or schema semantics unless that exact change is explicitly required by the data objective and documented in the step.
- **No fallback or placeholder logic** unless explicitly requested by the user.
- **All tests pass** after every step.

---

## 8. Completion condition

This refactoring branch is complete only when **all** of the following are true:

1. The repository can produce the required dataset, not just a structurally valid pipeline run.
2. `supernova_lightcurves_long.csv` is non-empty and comes from real source photometry.
3. `supernova_event_summary.csv` contains non-zero derived timing coverage (`rise_time_days`, `decay_time_days`, and/or `peak_width_days`) for real objects.
4. Raw and final verification pass, including any merge-specific verification introduced by the branch.
5. Source coverage, skipped sources, conflicts, and missingness are documented in output reports or manifests.
6. All modified or created code files comply with project rules.
7. `black --check scripts supernova_atomic tests docs/search/engine`, `flake8 scripts supernova_atomic tests docs/search/engine`, `mypy scripts supernova_atomic tests docs/search/engine`, and **pytest (all tests pass)** all succeed.

If the code is clean but the required dataset is still not produced, the branch is **not complete**.

---

## 9. Plan to be written after discussion

The later execution plan must live in a separate directory under `docs/refactoring/plan/` and must be written against this data-first TZ.

The plan must:

- prioritize steps on the critical data path first;
- separate data-delivery steps from purely structural cleanup;
- require all tests to pass after every step;
- define blackstops when a step cannot stay within one target code file;
- explicitly encode when a step is complete in terms of **data obtained**, not just code changed.

Each step file must remain 100% handoff-ready for another model.

---

## 10. References

- `docs/TECH_SPEC.md`
- `docs/DATA_SOURCES_AND_ALGORITHMS.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/scale_law_validation/TECH_SPEC.md`
- project rules in `.cursor/rules/` and the user rules applied to this repository.

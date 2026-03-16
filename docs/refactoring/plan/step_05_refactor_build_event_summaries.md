# Step 05: Refactor `build_event_summaries.py`

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for the timing-summary stage. Your job is to make the summary builder consume the repaired light-curve table deterministically and produce reproducible timing fields.

## Execution directive

Edit exactly one production file: `scripts/build_event_summaries.py`. Do not create or edit a second production helper file in this step.

## Target file

`scripts/build_event_summaries.py`

## Step scope

This step modifies the timing-selection and summary-building logic only. It does not alter raw ingestion, CSV schemas, wrappers, reports, or downstream event-table code.

## Dependency contract

- Step 04 must already be complete and produce a non-empty `data/supernova_lightcurves_long.csv`.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- The timing definition remains the existing 1-mag threshold contract already documented in the file.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `docs/TECH_SPEC.md`
- `scripts/build_event_summaries.py`
- `scripts/clean_supernova_data.py`
- `scripts/build_supernova_transient_events.py`

You must edit these symbols inside the target file:

- `compute_rise_decay_width()`
- `build_summary_rows()`
- any new internal helper functions added inside this same file

## Forbidden scope

- Do not change `SUMMARY_COLUMNS`.
- Do not invent synthetic peaks or timing values.
- Do not edit any other production file.
- Do not mix incompatible bands within one object's timing series.

## Atomic operations

1. Keep the current 1-mag threshold timing definition unchanged.
2. Filter candidate timing rows to those with finite `mjd`, finite `mag`, and non-empty `sn_name`.
3. Group candidate rows by `sn_name` and then by `band`.
4. Choose exactly one timing band per object using this deterministic rule:
   - prefer the band with the largest number of valid `(mjd, mag)` rows;
   - if tied, prefer the band that contains a finite catalog `peak_mag` match if available;
   - if still tied, choose the lexicographically smallest band string;
   - if all valid rows have empty band, use the empty-string band bucket.
5. Within the chosen band, sort points by `mjd`.
6. If catalog `peak_mjd` and `peak_mag` are both finite, use them.
7. Otherwise infer the peak from the chosen band as:
   - minimum magnitude value in the chosen band;
   - if multiple rows share the same minimum magnitude, choose the earliest `mjd`.
8. Compute rise and decay only from the chosen band.
9. Leave `rise_time_days`, `decay_time_days`, and `peak_width_days` empty when the chosen series cannot support the corresponding threshold crossing.
10. Set `lightcurve_points_count` in the output row to:
    - the integer from catalog if it is finite and positive;
    - otherwise the count of valid `(mjd, mag)` rows used for that object's chosen band.

## Expected file change

Only `scripts/build_event_summaries.py` changes in this step.

That file must change in these exact areas:

- `compute_rise_decay_width()` must keep the current timing definition but operate on deterministic single-band input;
- `build_summary_rows()` must group by object, group by band, choose one band by the fixed tie-break rule, and emit timing fields from that band only;
- no CSV schema changes are allowed.

## Expected deliverables

- Updated `scripts/build_event_summaries.py`
- Deterministic single-band timing selection per object
- Non-zero timing coverage for at least one curated object after running the script on repaired cleaned inputs

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python scripts/build_event_summaries.py
python -m black scripts/build_event_summaries.py
python -m flake8 scripts/build_event_summaries.py
python -m mypy scripts/build_event_summaries.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `data/supernova_event_summary.csv` must contain at least one non-empty timing field among `rise_time_days`, `decay_time_days`, `peak_width_days`;
- timing values must come from one chosen band per object;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- Never combine points from multiple bands for one object's timing computation.
- If the chosen band cannot provide pre-peak support, `rise_time_days` stays empty.
- If the chosen band cannot provide post-peak support, `decay_time_days` stays empty.
- `peak_width_days` is populated only when both rise and decay are populated.
- Flux-only rows never participate in timing selection in this step.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Step 04 outputs are absent or still header-only.
- The target file would exceed the project file-size limit.
- A second production file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- The existing timing contract would need to change to make the step work.

## Handoff package

When the step is complete, the handoff must include:

- the exact chosen-band decision rule implemented;
- counts of rows with non-empty `rise_time_days`, `decay_time_days`, and `peak_width_days`;
- the names of curated events that gained timing fields;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

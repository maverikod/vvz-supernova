# Step 09: Refactor `build_third_spec_report.py`

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for the durable report layer. Your job is to make `report/` explicitly prove or disprove supernova time-domain sufficiency for the repaired curated subset.

## Execution directive

Edit exactly one production file: `scripts/build_third_spec_report.py`. Do not replace it with another report script and do not edit any other production file in this step.

## Target file

`scripts/build_third_spec_report.py`

## Step scope

This step updates durable report generation only. It does not alter verification scripts, upstream data generation, or schema files.

## Dependency contract

- Steps 02, 05, 07, and 08 must already be complete.
- `.venv` must be active.
- `python -m pytest --version` must succeed before final validation.
- Raw manifest shape must remain the one defined in step 02.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `scripts/build_third_spec_report.py`
- `scripts/build_supernova_transient_events.py`
- `scripts/verify_pipeline_data.py`
- `raw/supernova_raw/manifest.json`

You must edit these symbols inside the target file:

- `main()`
- `_count_non_empty_column()`
- the source-manifest writer path
- the markdown report assembly path

## Forbidden scope

- Do not switch to `build_fourth_spec_report.py`.
- Do not remove atomic reporting.
- Do not write synthetic counts.
- Do not create a second report script.

## Atomic operations

1. Keep current output files:
   - `report/source_manifest.csv`
   - `report/missingness_report.csv`
   - `report/data_report.md`
2. Extend `report/source_manifest.csv` so the supernova branch contributes:
   - one OSC bulk source row;
   - one OAC curated source row;
   - note text that makes the curated subset explicit.
3. Extend `report/missingness_report.csv` so it includes supernova timing presence for:
   - `supernova_event_summary`
   - `supernova_transient_events`
4. Extend `report/data_report.md` so it prints these exact supernova metrics:
   - row count in `supernova_event_summary.csv`
   - row count in `supernova_transient_events.csv`
   - count with non-empty `rise_time_days`
   - count with non-empty `decay_time_days`
   - count with non-empty `peak_width_days`
   - count with `has_lightcurve=1`
5. Keep report output derived only from actual CSV and manifest contents.

## Expected file change

Only `scripts/build_third_spec_report.py` changes in this step.

That file must change in these exact areas:

- `main()` must add durable supernova coverage metrics to `data_report.md`;
- the source-manifest writer path must include repaired supernova provenance rows;
- the missingness writer path must include supernova timing datasets.

## Expected deliverables

- Updated `scripts/build_third_spec_report.py`
- Durable report artifacts that expose supernova source coverage and timing coverage explicitly

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python scripts/build_third_spec_report.py
python -m black scripts/build_third_spec_report.py
python -m flake8 scripts/build_third_spec_report.py
python -m mypy scripts/build_third_spec_report.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `report/data_report.md` must contain explicit supernova timing coverage metrics;
- `report/source_manifest.csv` must include repaired supernova provenance rows;
- `report/missingness_report.csv` must include supernova timing datasets;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- Use the repaired raw manifest as the source-of-truth for supernova provenance rows.
- Do not infer coverage from expectations; count only what exists in the actual generated CSVs.
- If a supernova timing field is empty in all rows, report zero; do not suppress the metric.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- Steps 02, 05, 07, or 08 are incomplete.
- The target file would exceed the project file-size limit.
- A second production file is required.
- `.venv` is inactive or `pytest` is unavailable in `.venv`.
- Required source coverage metrics cannot be derived from actual generated artifacts.

## Handoff package

When the step is complete, the handoff must include:

- the exact supernova metrics added to `data_report.md`;
- the exact supernova datasets added to `missingness_report.csv`;
- the exact provenance rows added to `source_manifest.csv`;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

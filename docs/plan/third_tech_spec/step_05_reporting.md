# Step 05 — Reporting (data_report, missingness, source_manifest)

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 plan file.  
**Code file:** `scripts/build_third_spec_report.py`

---

## Executor role

Produce report/data_report.md (counts: loaded, dropped, remaining; reasons; field presence), report/missingness_report.csv, report/source_manifest.csv using pipeline outputs and manifests.

## Execution directive

Execute only this step. Create only `scripts/build_third_spec_report.py`. Ensure `report/` directory exists. Stop on validation failure.

## Read first

- `docs/Third_tech_spec.md` (ДОПОЛНИТЕЛЬНО section)
- Existing manifests in raw/atomic_lines_raw, raw/supernova_raw
- Data CSVs produced by pipeline

## Expected file change

- Script builds report/ directory if missing.
- data_report.md: narrative or structured text with how many rows loaded, dropped, remaining; main reasons for dropping; which fields are present vs missing across datasets.
- missingness_report.csv: e.g. table of dataset, column, count_non_empty, count_empty (or similar).
- source_manifest.csv: aggregate of source URLs, download dates, file counts from raw manifests.
- Use existing manifest.json and pipeline outputs; no synthetic data.

## Mandatory validation

- black, flake8, mypy on `scripts/build_third_spec_report.py`
- Run script; report/data_report.md, report/missingness_report.csv, report/source_manifest.csv exist.

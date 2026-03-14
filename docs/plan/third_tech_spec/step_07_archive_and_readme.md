# Step 07 — Archive layout and README

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 plan file.  
**Code/artifact:** Extend `scripts/build_archive.py` or add spec-specific pack script; update README.

---

## Executor role

Ensure final deliverable layout matches spec: /data (atomic_transition_events.csv, supernova_transient_events.csv, cluster_ready_events.csv, supernova_lightcurves_long.csv if available); /scripts (download_atomic, download_supernova, clean_atomic, clean_supernova, build_cluster_ready); /report (data_report.md, missingness_report.csv, source_manifest.csv); README.

## Execution directive

Execute only this step. Modify build_archive or add script; update README. Stop on validation failure.

## Read first

- `docs/Third_tech_spec.md` (СОХРАНИТЬ В АРХИВ)
- Current `scripts/build_archive.py` and `README.md`

## Expected file change

- Archive (zip or directory layout) includes: data/ with the three event CSVs and supernova_lightcurves_long.csv when present; scripts/ with the five spec-named scripts (four wrappers + build_cluster_ready); report/ with the three report files; README.md.
- README updated to describe data sources, processing steps, units, and reproducibility per spec (no synthetic data, empty when missing).

## Mandatory validation

- black, flake8, mypy on any changed code.
- Archive can be produced and contains required structure.

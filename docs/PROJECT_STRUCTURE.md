# Supernova Atomic Pipeline — Project Structure

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

Repository layout, data locations, scripts, and documentation. Flat layout (no `src/`).  
Technical specification: **docs/TECH_SPEC.md**. Sources and algorithms: **docs/DATA_SOURCES_AND_ALGORITHMS.md**.

---

## 1. Directory layout

```
supernova/
├── .git/
├── .gitignore
├── .venv/                         # Local venv (not committed)
├── README.md
├── pyproject.toml                 # Build and PyPI metadata
├── LICENSE
│
├── supernova_atomic/              # Installable Python package (flat, at root)
│   ├── __init__.py
│   ├── atomic_schema.py
│   ├── nist_parser.py
│   ├── third_spec_schema.py
│   ├── passport_schema.py
│   └── fourth_spec_report.py
│
├── scripts/                       # Runnable pipeline and utility scripts
│   ├── __init__.py
│   ├── ensure_dirs.py
│   ├── download_atomic_data.py
│   ├── download_atomic_isotope_data.py
│   ├── download_supernova_data.py
│   ├── download_atomic.py
│   ├── download_supernova.py
│   ├── download_astrophysical_transient_data.py
│   ├── clean_atomic_data.py
│   ├── clean_supernova_data.py
│   ├── clean_atomic.py
│   ├── clean_supernova.py
│   ├── clean_astrophysical_transient_data.py
│   ├── build_event_summaries.py
│   ├── build_atomic_two_frequency_analysis.py
│   ├── build_atomic_transition_events.py
│   ├── build_supernova_transient_events.py
│   ├── build_astrophysical_transient_events.py
│   ├── build_atomic_transition_passports.py
│   ├── build_cluster_ready_transition_passports.py
│   ├── build_cluster_ready.py
│   ├── build_unified_transition_passports.py
│   ├── build_astrophysical_flash_passports.py
│   ├── build_third_spec_report.py
│   ├── build_fourth_spec_report.py
│   ├── build_archive.py
│   ├── generate_plots.py
│   ├── verify_pipeline_data.py
│   ├── verify_raw_downloads.py
│   └── check_source_fields.py
│
├── data/                          # Cleaned and derived data (not in git)
│   ├── atomic_lines_clean.csv
│   ├── atomic_lines_by_element.csv
│   ├── atomic_transition_summary.csv
│   ├── atomic_transition_events.csv
│   ├── atomic_transition_passports.csv
│   ├── atomic_isotope_lines_clean.csv
│   ├── atomic_isotope_envelope_summary.csv
│   ├── atomic_two_frequency_group_summary.csv
│   ├── atomic_two_frequency_similarity.csv
│   ├── supernova_catalog_clean.csv
│   ├── supernova_lightcurves_long.csv
│   ├── supernova_event_summary.csv
│   ├── supernova_transient_events.csv
│   ├── cluster_ready_events.csv
│   ├── cluster_ready_transition_passports.csv
│   ├── unified_transition_passports.csv
│   ├── astrophysical_transient_*.csv
│   └── ...
│
├── raw/                           # Raw downloads (not in git)
│   ├── atomic_lines_raw/          # NIST per-spectrum .txt + manifest.json
│   ├── atomic_isotope_raw/        # NIST/Kurucz isotope bundle + manifest.json
│   ├── supernova_raw/             # OSC catalog.json + manifest.json
│   └── astrophysical_transient_raw/
│
├── report/                        # Reports (not in git)
│   ├── data_report.md
│   ├── atomic_two_frequency_report.md
│   ├── missingness_report.csv
│   └── source_manifest.csv
│
├── plots/                         # Generated plots (not in git)
│   ├── atomic_frequency_histogram.png
│   ├── atomic_Aki_histogram.png
│   ├── supernova_peak_mag_histogram.png
│   ├── supernova_rise_time_histogram.png
│   ├── supernova_decay_time_histogram.png
│   └── example_lightcurves.png
│
├── docs/                          # Documentation
│   ├── README.md                  # Doc index; pointer to TZ
│   ├── PROJECT_STRUCTURE.md       # This file
│   ├── TECH_SPEC.md               # Current technical specification (TZ)
│   ├── DATA_SOURCES_AND_ALGORITHMS.md  # Sources, algorithms, outputs
│   ├── chapters/                  # Canonical long-form theory chapters
│   │   ├── README.md
│   │   └── THETA_LEVELS_AND_PHASE_SPEED.md
│   ├── scale_law_validation/      # Scale-law theory and verification
│   │   ├── TECH_SPEC.md
│   │   └── THEORY_SCALE_LAW.md
│   └── search/                    # Theory full-text search (SQLite)
│       ├── README.md
│       ├── db/
│       ├── doc/
│       └── engine/
│
├── code_analysis/                 # Optional: code_mapper indices (gitignored)
└── tests/
    ├── test_atomic_pipeline_verification.py
    ├── test_theory_search_engine.py
    ├── test_source_field_checks.py
    └── test_raw_download_verification.py
```

- **No `src/`**: the installable package is `supernova_atomic/` at the repository root.
- **Data**: pipeline outputs under `data/`, `report/`, `plots/`; created by scripts, not committed.
- **Raw**: original downloads under `raw/`; each subdir has a manifest for provenance.

---

## 2. Data locations (reference)

| Purpose | Path |
|--------|------|
| Cleaned atomic lines | `data/atomic_lines_clean.csv`, `data/atomic_lines_by_element.csv`, `data/atomic_transition_summary.csv` |
| Cleaned supernova catalog | `data/supernova_catalog_clean.csv` |
| Supernova light curves (long) | `data/supernova_lightcurves_long.csv` |
| Supernova event summary | `data/supernova_event_summary.csv` |
| Atomic/supernova event tables | `data/atomic_transition_events.csv`, `data/supernova_transient_events.csv` |
| Atomic isotope / two-frequency outputs | `data/atomic_isotope_lines_clean.csv`, `data/atomic_isotope_envelope_summary.csv`, `data/atomic_two_frequency_group_summary.csv`, `data/atomic_two_frequency_similarity.csv` |
| Cluster-ready / passports | `data/cluster_ready_events.csv`, `data/cluster_ready_transition_passports.csv`, `data/unified_transition_passports.csv` |
| Raw atomic | `raw/atomic_lines_raw/` |
| Raw atomic isotopes | `raw/atomic_isotope_raw/` |
| Raw supernova | `raw/supernova_raw/` |
| Reports | `report/data_report.md`, `report/atomic_two_frequency_report.md`, `report/missingness_report.csv`, `report/source_manifest.csv` |
| Plots | `plots/*.png` |

---

## 3. Pipeline waves (execution order)

| Wave | Scripts | Purpose |
|------|--------|--------|
| 0 | `ensure_dirs.py` | Create raw/, data/, plots/, report/ |
| 1 | `download_atomic_data.py`, `download_atomic_isotope_data.py`, `download_supernova_data.py` | Fetch NIST atomic, isotope-resolved atomic sources, and OSC bulk catalog |
| 1b | `verify_raw_downloads.py` | Verify raw manifests and payloads |
| 2 | `clean_atomic_data.py`, `clean_supernova_data.py` | Clean and normalize → data/ CSVs |
| 3 | `build_event_summaries.py` | Rise/decay/width from light curves → supernova_event_summary.csv |
| 4 | `generate_plots.py` | QC histograms and example light curves |
| 5 | `build_atomic_two_frequency_analysis.py`, `build_atomic_transition_events.py`, `build_supernova_transient_events.py`, etc. | Two-frequency atomic artefacts, event tables, and scale-law reports |
| — | `verify_pipeline_data.py` | Final check: columns, row counts, plots |

---

## 4. Git and PyPI

- **Ignore:** `.venv/`, `__pycache__/`, `raw/`, `data/`, `plots/`, `code_analysis/`, `*.egg-info/`, `dist/`, `build/`.
- **PyPI:** `python -m build` → `dist/`; `twine upload dist/*`. Package: `supernova_atomic` (flat); see `pyproject.toml`.

---

## 5. Relation to documentation

- **TZ (technical specification):** `docs/TECH_SPEC.md` — schemas, merge strategy, pipeline contract.
- **Sources and algorithms:** `docs/DATA_SOURCES_AND_ALGORITHMS.md` — provenance, download/clean/merge logic, outputs.
- **Canonical chapters:** `docs/chapters/` — long-form academic theory chapters intended for canon integration.
- **Scale-law validation:** `docs/scale_law_validation/` — theory and verification branch.
- **Theory search:** `docs/search/` — full-text search over theory blocks.

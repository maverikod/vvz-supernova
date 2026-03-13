# Supernova Atomic Pipeline — Project Structure

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This document describes the repository layout, Git usage, and PyPI publication setup.  
Flat layout (no `src/`); all data under `data/`.

---

## 1. Directory layout (flat, no `src/`)

```
supernova/
├── .git/
├── .gitignore
├── .venv/                    # Local venv (not committed)
├── README.md
├── pyproject.toml             # Build and PyPI metadata
├── LICENSE
│
├── supernova_atomic/          # Installable Python package (flat, at root)
│   ├── __init__.py
│   └── ...                   # Package modules
│
├── scripts/                   # Runnable pipeline scripts
│   ├── download_atomic_data.py
│   ├── clean_atomic_data.py
│   ├── download_supernova_data.py
│   ├── clean_supernova_data.py
│   └── build_event_summaries.py
│
├── data/                      # Cleaned output data (gitignored or committed by policy)
│   ├── atomic_lines_clean.csv
│   ├── atomic_lines_by_element.csv
│   ├── atomic_transition_summary.csv
│   ├── supernova_catalog_clean.csv
│   ├── supernova_lightcurves_long.csv
│   └── supernova_event_summary.csv
│
├── raw/                       # Raw downloaded data (gitignored by default)
│   ├── atomic_lines_raw/
│   └── supernova_raw/
│
├── plots/                     # Generated plots (gitignored or committed by policy)
│   ├── atomic_frequency_histogram.png
│   ├── atomic_Aki_histogram.png
│   ├── supernova_peak_mag_histogram.png
│   ├── supernova_rise_time_histogram.png
│   ├── supernova_decay_time_histogram.png
│   └── example_lightcurves.png
│
├── docs/                      # Documentation and task specs
│   ├── README.md
│   ├── PROJECT_STRUCTURE.md   # This file
│   └── task_supernova_atomic_pipeline.txt
│
├── code_analysis/             # Optional: code_mapper indices (gitignored)
└── tests/                     # Tests (optional)
```

- **No `src/`**: the installable package is `supernova_atomic/` at the repository root.
- **Data**: all pipeline outputs (cleaned CSVs, summaries) live under `data/`.
- **Raw**: original downloads under `raw/` (atomic_lines_raw, supernova_raw).
- **Scripts**: standalone scripts in `scripts/`; can be invoked as `python scripts/...` or via entry points from the package.

---

## 2. Git setup

- **Repository**: initialised in project root; no submodules required for this layout.
- **Ignore**: `.gitignore` excludes:
  - `.venv/`, `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.ruff_cache/`
  - Contents of `raw/`, `data/`, `plots/` (directories kept via `.gitkeep`; remove these rules to commit outputs)
  - `*.egg-info/`, `dist/`, `build/`, `code_analysis/`
- **Branches**: default branch `main`; feature branches as needed.
- **Commits**: one logical change per commit; no commits of generated data unless policy says so.

---

## 3. PyPI publication (flat layout)

- **Build system**: PEP 517/518 via `pyproject.toml` in the project root.
- **Package**: single top-level package `supernova_atomic` (flat, no `src`).
- **Config**:
  - `[build-system]`: `setuptools` (or `hatch`) with `pyproject.toml`.
  - `[project]`: name (e.g. `supernova-atomic-pipeline`), version, description, readme, license, classifiers, dependencies.
  - `[tool.setuptools.packages.find]`: `where = ["."]`, `include = ["supernova_atomic*"]` so only the root-level package is included (no `src/`).
- **Entry points** (optional): console scripts in `scripts/` can be exposed as `supernova-atomic-download`, `supernova-atomic-clean`, etc.
- **Publish**:
  - `python -m build` → `dist/`
  - `twine upload dist/*` to PyPI (or TestPyPI).

---

## 4. Data locations (reference)

| Purpose              | Path |
|----------------------|------|
| Cleaned atomic lines | `data/atomic_lines_clean.csv`, `data/atomic_lines_by_element.csv`, `data/atomic_transition_summary.csv` |
| Cleaned supernova    | `data/supernova_catalog_clean.csv`, `data/supernova_lightcurves_long.csv`, `data/supernova_event_summary.csv` |
| Raw atomic           | `raw/atomic_lines_raw/` |
| Raw supernova        | `raw/supernova_raw/` |
| Plots                | `plots/*.png` |

---

## 5. Publishing to PyPI (steps)

1. Install build tools: `pip install build twine`
2. From project root: `python -m build` → creates `dist/*.whl` and `dist/*.tar.gz`
3. Upload: `twine upload dist/*` (or `twine upload --repository testpypi dist/*` for TestPyPI)
4. Bump version in `pyproject.toml` and `supernova_atomic/__init__.py` for each release

---

## 6. Relation to task document

This structure implements the layout required in `docs/task_supernova_atomic_pipeline.txt`: scripts in `scripts/`, raw under `raw/`, cleaned and summary data in `data/`, plots in `plots/`, with a flat package layout and readiness for Git and PyPI.

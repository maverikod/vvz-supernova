# Implementation Specification: Supernova Atomic Data Pipeline

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This document is the technical specification (ТЗ) for implementing the code of the Supernova Atomic Data Pipeline. It is derived from `docs/task_supernova_atomic_pipeline.txt` and aligned with `docs/PROJECT_STRUCTURE.md` and project rules.

---

## 1. Purpose and scope

**Goal:** Implement reproducible Python scripts that:

1. Download and store raw atomic transition data (NIST) and supernova catalog/light-curve data (Open Supernova Catalog, ASAS-SN, ZTF, Pan-STARRS, etc.).
2. Clean and normalize the data into defined CSV schemas.
3. Build summary tables and produce quality-control metrics and plots.
4. Expose a clear run order and README for users.

**Out of scope:** Physical interpretation, hypotheses, synthetic data, or any logic that invents or alters values beyond cleaning/normalization.

---

## 2. General implementation rules

| Rule | Requirement |
|------|-------------|
| No invented data | Do not generate or guess values; use only what comes from sources. |
| No synthetic values | No placeholder or synthetic numbers (e.g. no fake light-curves). |
| Raw vs cleaned | Keep all raw downloads under `raw/`; write cleaned/summary outputs under `data/` and `plots/`. |
| Provenance | For each produced file (or dataset), record: source name, download date, and source URL (in metadata or in a manifest next to raw data). |
| Missing values | Use NaN for missing fields; do not drop entire rows only because one field is missing (unless the task explicitly requires filtering). |
| Units | Use the units defined in Section 6; document them in README and, if needed, in column headers or a schema file. |
| Reproducibility | Every step must be runnable from Python scripts; no manual-only steps that affect outputs. |

---

## 3. Part A — Atomic transitions: implementation

### 3.1 Source and scope

- **Source:** NIST Atomic Spectra Database (ASD).
- **Elements (required):** H, He, C, N, O, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca, Fe, Ni.
- **Ion states:** If the chosen API or export allows, include all available neutral and low ionization stages; otherwise document which states are included.

### 3.2 Output schema: atomic lines (cleaned)

**File:** `data/atomic_lines_clean.csv`

Each row = one spectral line. Columns (exact names, types as below):

| Column | Type | Unit / format | Notes |
|--------|------|----------------|-------|
| element | str | — | Element symbol. |
| ion_state | str | e.g. I, II, III | Ionization stage. |
| wavelength_vac_nm | float | nm | Vacuum wavelength; NaN if only air available. |
| wavelength_air_nm | float | nm | Air wavelength; NaN if only vacuum available. |
| frequency_hz | float | Hz | Derived: c / wavelength_vac_nm (or from air with conversion if only air given; document in README). |
| wavenumber_cm1 | float | cm⁻¹ | NaN if not available. |
| Aki_s^-1 | float | s⁻¹ | Einstein A coefficient. |
| intensity | float or str | as in source | Keep as-is or normalize; document in README. |
| Ei_cm1 | float | cm⁻¹ | Lower level energy. |
| Ek_cm1 | float | cm⁻¹ | Upper level energy. |
| lower_configuration | str | — | NaN if missing. |
| upper_configuration | str | — | NaN if missing. |
| lower_term | str | — | NaN if missing. |
| upper_term | str | — | NaN if missing. |
| lower_J | str or float | — | As in source. |
| upper_J | str or float | — | As in source. |
| line_type | str | — | e.g. observed, Ritz; NaN if missing. |
| source_catalog | str | — | e.g. NIST ASD. |
| source_url | str | — | URL or identifier of the dataset. |

If a column is not provided by the source, create the column and fill with NaN.

### 3.3 Processing requirements (atomic)

1. **Frequency:** `frequency_hz = c / wavelength_vac_nm` (use standard c in m/s, convert wavelength to m). If only air wavelength is available, convert air→vacuum via a standard formula (e.g. Edlén) and document; or set a flag column if needed.
2. **Cleaning:** Remove Excel-style prefixes, stray quotes, and non-numeric artifacts from numeric columns; normalize decimal separators.
3. **Deduplication:** Remove exact duplicate rows (all columns identical).
4. **Raw storage:** Save original downloads (or API responses) under `raw/atomic_lines_raw/` with a manifest or naming that includes source and date.
5. **By-element output:** Produce `data/atomic_lines_by_element.csv` with the same schema as `atomic_lines_clean.csv` (or a documented subset); the only difference is ordering/filtering (e.g. sorted by element); schema must be documented.

### 3.4 Atomic summary schema

**File:** `data/atomic_transition_summary.csv`

One row per element (or per element+ion_state if required). Minimum columns:

| Column | Type | Unit | Notes |
|--------|------|------|-------|
| element | str | — | Element symbol. |
| n_lines | int | — | Number of lines. |
| freq_min_hz | float | Hz | Minimum frequency. |
| freq_max_hz | float | Hz | Maximum frequency. |
| freq_median_hz | float | Hz | Median frequency. |
| Aki_median | float | s⁻¹ | Median Aki. |
| Aki_max | float | s⁻¹ | Max Aki. |
| wavelength_min_nm | float | nm | Min wavelength. |
| wavelength_max_nm | float | nm | Max wavelength. |

Additional columns (e.g. ion_state) are allowed if they do not conflict with the task.

### 3.5 Scripts (atomic)

- **`scripts/download_atomic_data.py`**  
  - Input: none (or config path).  
  - Output: files under `raw/atomic_lines_raw/`; metadata (source, date, URL) stored as specified (e.g. manifest JSON/CSV).  
  - Must create `raw/atomic_lines_raw/` if missing. Must not overwrite cleaned outputs.

- **`scripts/clean_atomic_data.py`**  
  - Input: `raw/atomic_lines_raw/` (and any manifest).  
  - Output: `data/atomic_lines_clean.csv`, `data/atomic_lines_by_element.csv`, `data/atomic_transition_summary.csv`.  
  - Must create `data/` if missing. Must implement cleaning and deduplication as above. Must compute summary from cleaned lines.

---

## 4. Part B — Supernovae: implementation

### 4.1 Sources (priority order)

1. Open Supernova Catalog  
2. ASAS-SN  
3. ZTF public supernova/transient tables  
4. Pan-STARRS public SN tables  
5. Other open catalogs that provide light-curves and peak/maximum date

Use only open, documented APIs or bulk data; document which sources were actually used in README and in output metadata.

### 4.2 Output schema: supernova catalog (cleaned)

**File:** `data/supernova_catalog_clean.csv`

One row per supernova. Columns:

| Column | Type | Unit / format | Notes |
|--------|------|----------------|-------|
| sn_name | str | — | Official or catalog name. |
| source_catalog | str | — | Catalog identifier. |
| ra | float | deg | NaN if missing. |
| dec | float | deg | NaN if missing. |
| redshift | float | — | NaN if missing. |
| host_galaxy | str | — | NaN if missing. |
| sn_type | str | — | As in catalog; do not rename. |
| discovery_mjd | float | MJD | NaN if missing. |
| peak_mjd | float | MJD | NaN if missing. |
| peak_mag | float | mag | NaN if missing. |
| band | str | — | Filter/band for peak_mag; NaN if N/A. |
| distance_modulus | float | mag | NaN if missing. |
| luminosity_distance_Mpc | float | Mpc | NaN if missing. |
| lightcurve_points_count | int | — | Count of light-curve points; 0 or NaN if none. |

### 4.3 Output schema: light-curves (long format)

**File:** `data/supernova_lightcurves_long.csv`

One row per light-curve point. Columns:

| Column | Type | Unit | Notes |
|--------|------|------|-------|
| sn_name | str | — | Match to catalog. |
| mjd | float | MJD | Time. |
| mag | float | mag | Magnitude; NaN if only flux. |
| mag_err | float | mag | Error; NaN if missing. |
| flux | float | — | As in catalog; unit in separate column if available. |
| flux_err | float | — | NaN if missing. |
| band | str | — | Filter/band. |
| instrument | str | — | NaN if missing. |
| source_catalog | str | — | Catalog identifier. |

If flux unit is available from the source, add a column (e.g. flux_unit) and document in README.

### 4.4 Processing requirements (supernova)

1. **Light-curves:** Stored in long format; one file `data/supernova_lightcurves_long.csv` as above.
2. **Derived quantities (per event):** Compute when possible; otherwise NaN:
   - rise_time_days  
   - decay_time_days  
   - peak_width_days  
   - peak_flux  
   Definition of rise/decay/width must be documented (e.g. time from some fraction of peak to peak, and peak to same fraction on decline).
3. **Types:** Keep `sn_type` exactly as in the catalog; no manual renaming.
4. **Deduplication:** Remove exact duplicate rows in catalog and in light-curve table.
5. **Raw:** Keep all raw downloads under `raw/supernova_raw/` with source and date.

### 4.5 Supernova event summary schema

**File:** `data/supernova_event_summary.csv`

One row per supernova. Minimum columns:

| Column | Type | Unit | Notes |
|--------|------|------|-------|
| sn_name | str | — | |
| sn_type | str | — | |
| source_catalog | str | — | |
| peak_mjd | float | MJD | NaN if missing. |
| peak_mag | float | mag | NaN if missing. |
| rise_time_days | float | days | NaN if not computed. |
| decay_time_days | float | days | NaN if not computed. |
| peak_width_days | float | days | NaN if not computed. |
| lightcurve_points_count | int | — | |
| redshift | float | — | NaN if missing. |
| luminosity_distance_Mpc | float | Mpc | NaN if missing. |

### 4.6 Scripts (supernova)

- **`scripts/download_supernova_data.py`**  
  - Input: none (or config path).  
  - Output: files under `raw/supernova_raw/`; metadata (source, date, URL).  
  - Must create `raw/supernova_raw/` if missing.

- **`scripts/clean_supernova_data.py`**  
  - Input: `raw/supernova_raw/` (and manifest if any).  
  - Output: `data/supernova_catalog_clean.csv`, `data/supernova_lightcurves_long.csv`.  
  - Must create `data/` if missing. Implements cleaning, deduplication, and unit normalization as above.

- **`scripts/build_event_summaries.py`**  
  - Input: `data/supernova_catalog_clean.csv`, `data/supernova_lightcurves_long.csv` (and optionally `data/atomic_*` if needed for future extensions).  
  - Output: `data/supernova_event_summary.csv`.  
  - Must compute rise_time_days, decay_time_days, peak_width_days where possible; otherwise NaN. Must not invent values.

---

## 5. Part C — Units and formats (reference)

- **Atomic:** wavelength [nm], frequency [Hz], wavenumber [cm⁻¹], Aki [s⁻¹].  
- **Supernova:** time [MJD], durations [days], luminosity distance [Mpc]. Flux: as in catalog, with unit in a separate column if available.  
- **CSV:** UTF-8; decimal point `.`; no thousands separator in numbers. Document any date/datetime format (e.g. MJD as float).

---

## 6. Part D — Quality control and plots

### 6.1 Metrics to produce (and document in README or a small report)

1. Number of elements for which at least one atomic line was collected.  
2. Total number of atomic lines (in `atomic_lines_clean.csv`).  
3. Number of supernovae in the cleaned catalog.  
4. Number of supernovae that have at least one light-curve point.  
5. Number of supernovae with non-NaN `rise_time_days`.  
6. List of sources actually used in the final datasets (atomic and supernova).

These may be printed to stdout by a script, written to a small report file under `data/` or `docs/`, or both; the exact location must be documented in README.

### 6.2 Plots (required files)

| File | Content |
|------|---------|
| `plots/atomic_frequency_histogram.png` | Histogram of line frequencies (from cleaned atomic data). |
| `plots/atomic_Aki_histogram.png` | Histogram of Aki (s⁻¹). |
| `plots/supernova_peak_mag_histogram.png` | Histogram of peak magnitudes. |
| `plots/supernova_rise_time_histogram.png` | Histogram of rise_time_days (omit or bin NaN as documented). |
| `plots/supernova_decay_time_histogram.png` | Histogram of decay_time_days. |
| `plots/example_lightcurves.png` | Example light-curves (e.g. a few SNe with time vs mag or flux). |

Scripts that generate these plots must create `plots/` if missing. Plot scripts can be separate or integrated into `clean_*` / `build_event_summaries`; the implementation spec does not mandate a single script, but the README must state how to generate each plot.

---

## 7. Part E — Scripts and run order

**Scripts to implement:**

- `scripts/download_atomic_data.py`  
- `scripts/clean_atomic_data.py`  
- `scripts/download_supernova_data.py`  
- `scripts/clean_supernova_data.py`  
- `scripts/build_event_summaries.py`  

Optional: one or more scripts under `scripts/` to generate the Part D plots (e.g. `scripts/generate_plots.py`), or the same logic inside the clean/summary scripts.

**Run order:**

1. `download_atomic_data.py`  
2. `clean_atomic_data.py`  
3. `download_supernova_data.py`  
4. `clean_supernova_data.py`  
5. `build_event_summaries.py`  
6. Plot generation (as implemented)

Each script must be runnable standalone (e.g. `python scripts/download_atomic_data.py`), have a short module docstring and comments, and not depend on interactive input unless documented.

---

## 8. Part F — README

**File:** `README.md` (repository root)

Must include:

1. **Sources:** Which sources were used for atomic data and for supernova data (and where applicable, links).  
2. **Output files:** List of files under `data/`, `plots/`, and structure of `raw/`.  
3. **Schemas:** Summary of columns in each final table (or reference to this spec / a schema file).  
4. **Run instructions:** Step-by-step command sequence to run all scripts (e.g. the run order in Section 7).  
5. **Dependencies:** Python version and required packages (e.g. in `pyproject.toml` or `requirements.txt`).  
6. **Units:** Short reference to units (wavelength, frequency, time, distance, etc.) as in Section 5.

---

## 9. Final deliverable (archive)

**Optional deliverable** (if required by product owner):

- **Archive name:** `supernova_atomic_data_pipeline.zip`  
- **Contents:**  
  - `README.md`  
  - `scripts/` (all pipeline scripts)  
  - `raw/` (or a note that raw is recreated by download scripts)  
  - `data/` (cleaned and summary CSVs)  
  - `plots/` (all required PNGs)  

Implementation may add a script that builds this archive from the project root after a full pipeline run.

---

## 10. Validation and code quality

- Code must comply with project rules: no hardcoded credentials, no placeholders (e.g. `TODO`, fake data), no `pass` except in exception bodies, no `NotImplemented` except in abstract methods.  
- After implementation: run **black**, **flake8**, **mypy** and fix all reported issues.  
- File size: no single code file over 350–400 lines; split by facade + modules or by domain (e.g. atomic vs supernova).  
- Docstrings: every module, class, and public function must have an English docstring; file header must include Author and email as in project rules.  
- Tests: if a test suite exists, the implementation is complete only when **all tests pass**.

---

## 11. Reference to source task

This implementation spec is derived from `docs/task_supernova_atomic_pipeline.txt` and must stay consistent with it. In case of conflict, the source task document takes precedence unless explicitly overridden by the product owner.

# Supernova Atomic Pipeline

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

Data pipeline: atomic spectral lines (NIST) and supernova catalogs (OSC, ASAS-SN, ZTF, etc.).  
Cleaned outputs go to `data/`; raw downloads to `raw/`. Flat layout (no `src/`).

- **Structure and PyPI**: [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
- **Task spec**: [docs/task_supernova_atomic_pipeline.txt](docs/task_supernova_atomic_pipeline.txt)
- **Implementation spec**: [docs/IMPLEMENTATION_SPEC.md](docs/IMPLEMENTATION_SPEC.md)

---

## 1. Sources

**Atomic data**

- **NIST Atomic Spectra Database (ASD)**  
  <https://www.nist.gov/pml/atomic-spectra-database>  
  Spectral lines for elements: H, He, C, N, O, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca, Fe, Ni (neutral and low ionization stages as available).

**Supernova data** (priority order)

1. **Open Supernova Catalog (OSC)** — <https://sne.space/>
2. **ASAS-SN** — <https://asas-sn.osu.edu/>
3. **ZTF** public supernova/transient tables
4. **Pan-STARRS** public SN tables
5. Other open catalogs that provide light-curves and peak/maximum date

Which sources were actually used in a run is recorded in output metadata and in the `source_catalog` / `source_url` fields of the produced files.

---

## 2. Output files

Scripts create the following directories and files. None of `raw/`, `data/`, or `plots/` are committed; they are created when you run the pipeline.

| Location | Files |
|----------|--------|
| **raw/** | Raw downloads only. Not modified by clean/summary scripts. |
| **raw/atomic_lines_raw/** | Files fetched by `download_atomic_data.py` (e.g. per-element exports from NIST). |
| **raw/supernova_raw/** | Files fetched by `download_supernova_data.py` (catalogs and light-curves from OSC, ASAS-SN, etc.). |
| **data/** | Cleaned and summary CSVs. |
| **data/atomic_lines_clean.csv** | All cleaned atomic lines (one row per line). |
| **data/atomic_lines_by_element.csv** | Same schema as clean; ordered/filtered by element. |
| **data/atomic_transition_summary.csv** | One row per element: counts and frequency/Aki/wavelength stats. |
| **data/supernova_catalog_clean.csv** | One row per supernova (catalog-level fields). |
| **data/supernova_lightcurves_long.csv** | One row per light-curve point (long format). |
| **data/supernova_event_summary.csv** | One row per supernova: peak, rise/decay/width, redshift, distance, etc. |
| **plots/** | Quality-control plots. |
| **plots/atomic_frequency_histogram.png** | Histogram of line frequencies. |
| **plots/atomic_Aki_histogram.png** | Histogram of Aki (s⁻¹). |
| **plots/supernova_peak_mag_histogram.png** | Histogram of peak magnitudes. |
| **plots/supernova_rise_time_histogram.png** | Histogram of rise_time_days. |
| **plots/supernova_decay_time_histogram.png** | Histogram of decay_time_days. |
| **plots/example_lightcurves.png** | Example light-curves (time vs mag/flux). |

---

## 3. Table fields (schemas)

Full column definitions, types, and units are in **docs/IMPLEMENTATION_SPEC.md** (Sections 3–5). Summary:

**data/atomic_lines_clean.csv** (and atomic_lines_by_element.csv)  
Per-line columns: `element`, `ion_state`, `wavelength_vac_nm`, `wavelength_air_nm`, `frequency_hz`, `wavenumber_cm1`, `Aki_s^-1`, `intensity`, `Ei_cm1`, `Ek_cm1`, `lower_configuration`, `upper_configuration`, `lower_term`, `upper_term`, `lower_J`, `upper_J`, `line_type`, `source_catalog`, `source_url`.

**data/atomic_transition_summary.csv**  
Per-element (or element+ion) summary: `element`, `n_lines`, `freq_min_hz`, `freq_max_hz`, `freq_median_hz`, `Aki_median`, `Aki_max`, `wavelength_min_nm`, `wavelength_max_nm`.

**data/supernova_catalog_clean.csv**  
Per-SN catalog: `sn_name`, `source_catalog`, `ra`, `dec`, `redshift`, `host_galaxy`, `sn_type`, `discovery_mjd`, `peak_mjd`, `peak_mag`, `band`, `distance_modulus`, `luminosity_distance_Mpc`, `lightcurve_points_count`.

**data/supernova_lightcurves_long.csv**  
Per light-curve point: `sn_name`, `mjd`, `mag`, `mag_err`, `flux`, `flux_err`, `band`, `instrument`, `source_catalog`.

**data/supernova_event_summary.csv**  
Per-SN summary: `sn_name`, `sn_type`, `source_catalog`, `peak_mjd`, `peak_mag`, `rise_time_days`, `decay_time_days`, `peak_width_days`, `lightcurve_points_count`, `redshift`, `luminosity_distance_Mpc`.

---

## 4. Run instructions

Use a virtual environment and install the project (from repo root):

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Execution is in **waves**. Run each wave only after the previous wave has finished. Within a wave, steps can be run in parallel.

- **Wave 0** — Prepare directories:  
  `python scripts/ensure_dirs.py`

- **Wave 1** — Download atomic and supernova data (can run in parallel):  
  `python scripts/download_atomic_data.py`  
  `python scripts/download_supernova_data.py`

- **Wave 2** — Clean atomic and supernova data (can run in parallel):  
  `python scripts/clean_atomic_data.py`  
  `python scripts/clean_supernova_data.py`

- **Wave 3** — Build event summaries:  
  `python scripts/build_event_summaries.py`

- **Wave 4** — Generate plots:  
  `python scripts/generate_plots.py`

**Serial (all in order):**

```bash
python scripts/ensure_dirs.py
python scripts/download_atomic_data.py
python scripts/download_supernova_data.py
python scripts/clean_atomic_data.py
python scripts/clean_supernova_data.py
python scripts/build_event_summaries.py
python scripts/generate_plots.py
```

**Parallel (wave 1 and wave 2):**

```bash
python scripts/ensure_dirs.py

# Wave 1
python scripts/download_atomic_data.py &   PID1=$!
python scripts/download_supernova_data.py &   PID2=$!
wait $PID1 $PID2

# Wave 2
python scripts/clean_atomic_data.py &   PID3=$!
python scripts/clean_supernova_data.py &   PID4=$!
wait $PID3 $PID4

# Rest serial
python scripts/build_event_summaries.py
python scripts/generate_plots.py
```

---

## 5. Dependencies

- **Python**: 3.10 or newer (see `requires-python` in `pyproject.toml`).
- **Packages**: Declared in `pyproject.toml`; install with `pip install -e .` from the project root.  
  Core runtime: `matplotlib>=3.5`.  
  Optional dev: `black`, `flake8`, `mypy` (e.g. `pip install -e ".[dev]"`).

---

## 6. Units reference

| Quantity | Unit | Notes |
|----------|------|--------|
| Wavelength | nm | Vacuum and/or air; column names indicate which. |
| Frequency | Hz | Derived as c / wavelength_vac. |
| Wavenumber | cm⁻¹ | |
| Einstein A (Aki) | s⁻¹ | |
| Time (dates) | MJD | Modified Julian Date (float). |
| Durations (rise, decay, width) | days | |
| Luminosity distance | Mpc | |
| Magnitude | mag | As in source catalog. |
| Flux | — | As in catalog; unit in separate column if available. |
| Angles (ra, dec) | deg | |

CSV format: UTF-8, decimal point `.`, no thousands separator in numbers.

---

## PyPI (optional)

```bash
pip install build twine
python -m build
twine upload dist/*
```

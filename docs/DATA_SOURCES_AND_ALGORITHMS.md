# Data Sources, Algorithms, and Outputs

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This document describes all external data sources, ingestion and merge algorithms, and output artefacts of the pipeline. It is the single reference for provenance and reproducibility.

---

## 1. Atomic data

### 1.1. Source

| Attribute | Value |
|-----------|--------|
| **Name** | NIST Atomic Spectra Database (ASD) |
| **URL** | https://www.nist.gov/pml/atomic-spectra-database |
| **Export URL** | https://physics.nist.gov/cgi-bin/ASD/lines1.pl |
| **Format** | Tab-delimited text export (per spectrum) |

**Elements requested (per TZ):** H, He, C, N, O, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca, Fe, Ni.  
**Ion stages:** I (neutral), II, III (skipping unsupported fully ionized states, e.g. He III).

### 1.2. Download algorithm

- **Script:** `scripts/download_atomic_data.py`
- Build list of spectra (element + ion), one NIST CGI request per spectrum.
- For each response: detect NIST error page vs real line data (header with `Aki` and tab separator).
- Save raw response as `raw/atomic_lines_raw/<Element>_<Roman>.txt`.
- Write `raw/atomic_lines_raw/manifest.json`: `source_catalog`, `download_date_utc`, `elements_requested`, `ion_stages_requested`, `files[]` with `spectrum`, `file`, `source_url`, `valid_payload`.
- Rate limit: 1 s delay between requests; no retries in current implementation.

### 1.3. Cleaning algorithm

- **Script:** `scripts/clean_atomic_data.py`
- **Input:** All `*.txt` in `raw/atomic_lines_raw/` listed in manifest (skip non-manifest files).
- Parse NIST TSV: extract wavelength (vac/air), wavenumber, Aki, intensity, Ei/Ek, configurations, terms, J, type.
- Normalize element/ion from filename and header; convert to SI-friendly column names.
- Output: `data/atomic_lines_clean.csv`, `data/atomic_lines_by_element.csv`, `data/atomic_transition_summary.csv` (per-element counts and freq/wl/Aki stats).
- **Provenance:** Each row keeps `source_catalog` (NIST ASD) and `source_url` (query URL).

### 1.4. Isotope-resolved atomic sources for two-frequency analysis

| Source | Access | Suitability | Current validated scope |
|--------|--------|-------------|-------------------------|
| **NIST ASD isotope-specific spectra** | Open HTTP text export via `lines1.pl` | **Suitable** for targeted automated downloads when an isotope-specific spectrum is accepted by ASD. Not universal across all isotopes/elements. | `1H I`, `2H I`, `3He I`, `12C I`, `13C I` |
| **Kurucz isotope artifacts** | Open HTTP directory listings and raw text files | **Suitable** for automated downloads of isotope/hyperfine-resolved artefacts; requires source-specific parsing because formats differ (`gf*iso*`, shift tables). | `gf2601iso.all` (Fe I), `gf2801iso.pos` (Ni II), `isoshifts2001.dat` (Ca II) |
| **VALD3** | Registration required | **Not suitable** for unattended pipeline ingestion in the current project because automated access requires prior registration and user credentials. | Documented as manual/deferred source only |

### 1.5. Isotope download algorithm

- **Script:** `scripts/download_atomic_isotope_data.py`
- Downloads an openly accessible isotope bundle into `raw/atomic_isotope_raw/`.
- **NIST branch:** targeted isotope-specific spectra are saved as `raw/atomic_isotope_raw/nist/*.txt`.
- **Kurucz branch:** validated isotope artefacts are saved as `raw/atomic_isotope_raw/kurucz/*.txt`.
- Writes `raw/atomic_isotope_raw/manifest.json` with `source_catalog`, `source_urls`, `download_date_utc`, and `files[]` entries carrying per-artifact provenance and `valid_payload`.

### 1.6. Two-frequency analysis algorithm

- **Script:** `scripts/build_atomic_two_frequency_analysis.py`
- **Inputs:** `data/atomic_transition_passports.csv` and `raw/atomic_isotope_raw/`.
- Operationalizes the two-frequency picture as:
  - carrier-envelope frequency `omega_theta_env` for one `(element, ion_stage)` carrier group,
  - observable ensemble spectrum `Omega_L0` represented by linewise `omega_mode` and their ratios to `omega_theta_env`.
- Builds:
  - `data/atomic_two_frequency_group_summary.csv`
  - `data/atomic_isotope_lines_clean.csv`
  - `data/atomic_isotope_envelope_summary.csv`
  - `data/atomic_two_frequency_similarity.csv`
  - `report/atomic_two_frequency_report.md`
- Current numerical audit confirms six strong homologous neutral-pair matches in the two-frequency feature space: `C-Si`, `N-P`, `O-S`, `Ne-Ar`, `Na-K`, `Mg-Ca`, all with cosine similarity above `0.99`.

### 1.7. Atomic outputs (reference)

| File | Description |
|------|-------------|
| `data/atomic_lines_clean.csv` | One row per spectral line; columns include element, ion_state, wavelength_vac_nm, frequency_hz, Aki_s^-1, lower/upper config/term/J, source_catalog, source_url. |
| `data/atomic_lines_by_element.csv` | Same schema; ordered/filtered by element. |
| `data/atomic_transition_summary.csv` | One row per element (or element+ion): n_lines, freq_min/max/median_hz, Aki_median/max, wavelength_min/max_nm. |
| `data/atomic_two_frequency_group_summary.csv` | One row per carrier group `(element, ion_stage)`: `omega_theta_env`, `kappa_theta_env_m_inv`, and quantiles of the `L0` spectrum relative to the carrier envelope. |
| `data/atomic_isotope_lines_clean.csv` | One row per isotope-resolved line from the validated `NIST ASD` and `Kurucz` sources. |
| `data/atomic_isotope_envelope_summary.csv` | One row per isotope family with the reconstructed carrier-envelope frequency `omega_theta_env`. |
| `data/atomic_two_frequency_similarity.csv` | Pairwise cosine similarities for homologous neutral-element pairs in the two-frequency feature space. |

---

## 2. Supernova / transient data

### 2.1. Primary catalog source: Open Supernova Catalog (OSC)

| Attribute | Value |
|-----------|--------|
| **Name** | Open Supernova Catalog |
| **URL** | https://sne.space/ |
| **Bulk catalog** | https://raw.githubusercontent.com/astrocatalogs/supernovae/master/output/catalog.json |
| **Format** | Single JSON object: keys = object names (e.g. SN names), values = metadata (name, alias, discoverer, discoverdate, maxdate, maxappmag, host, ra, dec, redshift, claimedtype, photolink, etc.). |

**Role:** Master list of objects and metadata. Does **not** contain embedded light-curve points in the bulk file; photometry is available per object via OAC API.

### 2.2. Photometry and time-series sources (for light curves and times of outburst)

| Source | URL | Data provided | Use in pipeline |
|--------|-----|----------------|-----------------|
| **OAC API** | api.astrocats.space, astroquery.oac | Per-object photometry: time, magnitude, e_magnitude, band, instrument | Intended: fetch light curves for OSC objects to compute rise/decay/peak. |
| **ASAS-SN** | https://asas-sn.osu.edu/photometry | JD, flux, magnitude, errors; bulk or by coordinates | Light curves for cross-match with OSC. |
| **CfA Supernova Archive** | https://lweb.cfa.harvard.edu/supernova/SNarchive.html | ASCII light curves (UBVRI, etc.), bulk tarballs | Curated multi-band light curves; merge by object name/alias. |
| **Carnegie Supernova Project (CSP)** | https://csp.obs.carnegiescience.edu/data | Photometry DR2/DR3, bolometric light curves | High-quality light curves; merge by object id. |
| **Young Supernova Experiment (YSE)** | Zenodo / data releases | Light curves + classifications | Optional additional source. |

### 2.3. Download algorithm (current)

- **Script:** `scripts/download_supernova_data.py`
- Downloads OSC bulk `catalog.json` → `raw/supernova_raw/osc_catalog.json`.
- Writes `raw/supernova_raw/manifest.json`: `download_date_utc`, `sources_used[]`, `sources_skipped[]` (ASAS-SN, ZTF, Pan-STARRS documented as not implemented).
- **Not yet implemented:** OAC API photometry per object, ASAS-SN/CfA/CSP bulk or per-object light-curve fetch.

### 2.4. Merge strategy (target design)

- **Catalog layer:** One row per object. Primary key: canonical `sn_name` (from OSC or chosen primary source). Fields: sn_name, source_catalog, ra, dec, redshift, sn_type, discovery_mjd, peak_mjd, peak_mag, band, distance_modulus, luminosity_distance_Mpc, lightcurve_points_count, and alias list for cross-matching.
- **Photometry layer:** Many rows per object. Columns: sn_name, mjd, mag, mag_err, flux, flux_err, band, instrument, source_catalog, source_url. No overwriting of points; append-only from each source. Duplicate detection by (object_id, time, band, magnitude or flux, source).
- **Name/alias resolution:** Use OSC `alias` and normalisation (e.g. SN2020abc vs AT2020abc) to match objects across catalogs. Conflicts (e.g. different coordinates) resolved by keeping primary source and marking alternate in metadata.
- **Time:** All times in MJD. Rise time, decay time, peak width derived from light curves in a separate step (e.g. `build_event_summaries.py`).

### 2.5. Cleaning algorithm (current)

- **Script:** `scripts/clean_supernova_data.py`
- **Input:** `raw/supernova_raw/osc_catalog.json`.
- Parse JSON; map OSC fields to schema (sn_name, source_catalog, ra, dec, redshift, host_galaxy, sn_type, discovery_mjd, peak_mjd, peak_mag, band, distance_modulus, luminosity_distance_Mpc).
- Output: `data/supernova_catalog_clean.csv`. Optionally `data/supernova_lightcurves_long.csv` if photometry is ingested (currently often empty when only bulk OSC is used).

### 2.6. Event summary algorithm

- **Script:** `scripts/build_event_summaries.py`
- **Input:** `data/supernova_catalog_clean.csv`, `data/supernova_lightcurves_long.csv`.
- For each object: if light-curve points exist, compute rise_time_days, decay_time_days, peak_width_days (e.g. from magnitude threshold crossing and peak finding). Else leave empty.
- Output: `data/supernova_event_summary.csv` (sn_name, sn_type, source_catalog, peak_mjd, peak_mag, rise_time_days, decay_time_days, peak_width_days, lightcurve_points_count, redshift, luminosity_distance_Mpc).

### 2.7. Supernova outputs (reference)

| File | Description |
|------|-------------|
| `data/supernova_catalog_clean.csv` | One row per supernova; catalog-level fields from OSC (and future merged catalog). |
| `data/supernova_lightcurves_long.csv` | One row per photometry point: sn_name, mjd, mag, mag_err, flux, flux_err, band, instrument, source_catalog. |
| `data/supernova_event_summary.csv` | One row per supernova: summary plus rise/decay/width when computable from light curves. |

---

## 3. Verification and quality

### 3.1. Raw download verification

- **Script:** `scripts/verify_raw_downloads.py`
- Checks: atomic manifest structure and full spectrum coverage; atomic payload files present, non-empty, and not NIST error pages; supernova manifest structure; presence and readability of `osc_catalog.json` (root object or array, non-empty).
- Exit 0 if all checks pass, 1 otherwise.

### 3.2. Pipeline data verification

- **Script:** `scripts/verify_pipeline_data.py`
- Checks: raw dirs present; atomic raw payloads valid per manifest; data CSVs exist with required columns and row-count constraints; plot files present.
- Prints quality summary (element count, line count, SN count, light-curve coverage, rise_time coverage).

---

## 4. Event tables and reports (third-spec / scale-law branch)

- **Scripts:** `build_atomic_transition_events.py`, `build_supernova_transient_events.py`, `build_cluster_ready_transition_passports.py`, `build_event_summaries.py`, `build_third_spec_report.py` (or `build_fourth_spec_report.py`).
- **Outputs:** `data/atomic_transition_events.csv`, `data/supernova_transient_events.csv`, `data/cluster_ready_events.csv`, `report/data_report.md`, `report/missingness_report.csv`, `report/source_manifest.csv`.
- See `docs/scale_law_validation/TECH_SPEC.md` and `docs/TECH_SPEC.md` for schemas and usage.

---

## 5. Plots

- **Script:** `scripts/generate_plots.py`
- **Input:** data CSVs.
- **Outputs:** `plots/atomic_frequency_histogram.png`, `plots/atomic_Aki_histogram.png`, `plots/supernova_peak_mag_histogram.png`, `plots/supernova_rise_time_histogram.png`, `plots/supernova_decay_time_histogram.png`, `plots/example_lightcurves.png`.

---

## 6. Units and conventions

| Quantity | Unit | Notes |
|----------|------|--------|
| Wavelength | nm | Vacuum and/or air as in column name. |
| Frequency | Hz | c / wavelength_vac. |
| Wavenumber | cm⁻¹ | |
| Aki | s⁻¹ | Einstein A coefficient. |
| Time (dates) | MJD | Modified Julian Date. |
| Durations | days | Rise, decay, width. |
| Luminosity distance | Mpc | |
| Magnitude | mag | As in source. |
| Energy (event tables) | eV | Conversion from cm⁻¹: 8065.54429. |

CSV: UTF-8, decimal point `.`, no synthetic data; empty cell when source is missing.

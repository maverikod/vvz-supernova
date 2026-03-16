# Technical Specification (TZ) — Data Pipeline and Multi-Source Merge

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This document is the current technical specification for the supernova–atomic data pipeline: data model, sources, merge strategy, pipeline waves, and output schemas.  
Companion: **docs/DATA_SOURCES_AND_ALGORITHMS.md** (sources, algorithms, provenance).

---

## 1. Purpose and scope

- Ingest **atomic spectral lines** (NIST ASD) and **supernova/transient** data from multiple open catalogs.
- Produce **cleaned catalog** and **light-curve** tables; derive **event summaries** (peak, rise/decay times) where photometry exists.
- Support **multi-source merge**: one canonical catalog layer plus photometry from OSC (OAC API), ASAS-SN, CfA, CSP, and others, with full provenance.
- Output **event tables** (atomic and supernova) and **cluster-ready** representations for downstream analysis (e.g. scale-law validation).
- No synthetic data; empty cells when source data are missing.

---

## 2. Data model (high level)

### 2.1. Atomic branch

- **Raw:** Per-spectrum NIST TSV in `raw/atomic_lines_raw/`; manifest with `source_catalog`, `download_date_utc`, `files[]` (spectrum, file, valid_payload).
- **Cleaned:** One row per line → `atomic_lines_clean.csv`, `atomic_lines_by_element.csv`; per-element summary → `atomic_transition_summary.csv`.
- **Derived:** Event table `atomic_transition_events.csv` (deltaE_eV, tau_s, etc.) and passport/cluster tables as per scale-law branch.
- **Isotope / two-frequency extension:** raw isotope bundle in `raw/atomic_isotope_raw/`; derived outputs `atomic_isotope_lines_clean.csv`, `atomic_isotope_envelope_summary.csv`, `atomic_two_frequency_group_summary.csv`, `atomic_two_frequency_similarity.csv`, and `report/atomic_two_frequency_report.md`.

### 2.2. Supernova / transient branch

- **Catalog layer (one row per object):** Canonical identifier `sn_name`; fields: source_catalog, ra, dec, redshift, host_galaxy, sn_type, discovery_mjd, peak_mjd, peak_mag, band, distance_modulus, luminosity_distance_Mpc, lightcurve_points_count. Alias list used for cross-matching only.
- **Photometry layer (many rows per object):** sn_name, mjd, mag, mag_err, flux, flux_err, band, instrument, source_catalog, source_url. Append-only from each source; no overwrite. Duplicates identified by (object, time, band, mag/flux, source).
- **Event summary (one row per object):** sn_name, sn_type, source_catalog, peak_mjd, peak_mag, rise_time_days, decay_time_days, peak_width_days, lightcurve_points_count, redshift, luminosity_distance_Mpc. Rise/decay/width computed from light curves when available.

### 2.3. Time and units

- All times: **MJD** (float).
- Durations: **days**.
- Wavelength: **nm**; frequency: **Hz**; Aki: **s⁻¹**; energy in event tables: **eV** (cm⁻¹ → eV: 8065.54429).
- CSV: UTF-8, decimal `.`, no synthetic values.

---

## 3. Data sources (summary)

| Domain | Primary source | Additional sources (for merge) |
|--------|----------------|---------------------------------|
| Atomic | NIST ASD (per-spectrum CGI export) | — |
| Atomic isotopes / two-frequency | NIST ASD isotope-specific spectra | Kurucz isotope artefacts (`gf2601iso.all`, `gf2801iso.pos`, `isoshifts2001.dat`); VALD3 deferred because registration is required |
| SN catalog | Open Supernova Catalog (OSC bulk JSON) | — |
| SN photometry / times | OAC API (per-object photometry) | ASAS-SN, CfA SN Archive, Carnegie CSP, YSE |

Details, URLs, and ingestion algorithms: **docs/DATA_SOURCES_AND_ALGORITHMS.md**.

---

## 4. Multi-source merge strategy

- **Canonical object list:** From OSC bulk catalog; `sn_name` = primary name; aliases stored for matching.
- **Photometry:** Fetched from OAC API, ASAS-SN, CfA, CSP (scripts to be extended). Each point keeps `source_catalog` and `source_url`. Same object matched by alias/coordinates where needed.
- **Conflict rules:** Catalog fields (ra, dec, type, redshift) from primary catalog; do not overwrite with alternate source. Conflicting photometry: keep both rows with different source_catalog.
- **Deduplication:** (sn_name, mjd, band, magnitude or flux, source_catalog) — treat as duplicate and keep one row per such key.
- **Rise/decay/width:** Computed in `build_event_summaries.py` from merged light-curve table; one set of summary fields per object (e.g. from preferred band or combined).

---

## 5. Pipeline waves and scripts

| Wave | Script | Input | Output |
|------|--------|-------|--------|
| 0 | ensure_dirs.py | — | raw/, data/, plots/, report/ |
| 1 | download_atomic_data.py | — | raw/atomic_lines_raw/*.txt, manifest.json |
| 1 | download_atomic_isotope_data.py | — | raw/atomic_isotope_raw/{nist,kurucz}/*.txt, manifest.json |
| 1 | download_supernova_data.py | — | raw/supernova_raw/osc_catalog.json, manifest.json |
| 1b | verify_raw_downloads.py | raw/ | Exit 0/1; console report |
| 2 | clean_atomic_data.py | raw/atomic_lines_raw/ | data/atomic_lines_*.csv, atomic_transition_summary.csv |
| 2 | clean_supernova_data.py | raw/supernova_raw/ | data/supernova_catalog_clean.csv, supernova_lightcurves_long.csv (if any) |
| 3 | build_event_summaries.py | catalog + lightcurves | data/supernova_event_summary.csv |
| 4 | generate_plots.py | data/ | plots/*.png |
| 5 | build_atomic_two_frequency_analysis.py | atomic passports + isotope raw bundle | data/atomic_*two_frequency*.csv, data/atomic_isotope_*.csv, report/atomic_two_frequency_report.md |
| 5 | build_*_transition_events, build_*_report, etc. | data/ | data/*_events.csv, report/* |
| — | verify_pipeline_data.py | raw/, data/, plots/ | Exit 0/1; quality summary |

---

## 6. Output schemas (core)

### 6.1. atomic_lines_clean.csv (and atomic_lines_by_element.csv)

Columns: element, ion_state, wavelength_vac_nm, wavelength_air_nm, frequency_hz, wavenumber_cm1, Aki_s^-1, intensity, Ei_cm1, Ek_cm1, lower_configuration, upper_configuration, lower_term, upper_term, lower_J, upper_J, line_type, source_catalog, source_url.

### 6.2. atomic_transition_summary.csv

Columns: element, n_lines, freq_min_hz, freq_max_hz, freq_median_hz, Aki_median, Aki_max, wavelength_min_nm, wavelength_max_nm.

### 6.3. atomic isotope / two-frequency outputs

- `atomic_isotope_lines_clean.csv`: source_catalog, element, ion_stage, isotope_mass, wavelength_vac_nm, frequency_hz, isotope_shift_mA, source_file.
- `atomic_isotope_envelope_summary.csv`: source_catalog, element, ion_stage, isotope_mass, line_count, omega_theta_env.
- `atomic_two_frequency_group_summary.csv`: element, ion_stage, line_count, omega_theta_env, kappa_theta_env_m_inv, omega_l0 quantiles, ratio quantiles.
- `atomic_two_frequency_similarity.csv`: left_element, right_element, cosine_similarity.

### 6.4. supernova_catalog_clean.csv

Columns: sn_name, source_catalog, ra, dec, redshift, host_galaxy, sn_type, discovery_mjd, peak_mjd, peak_mag, band, distance_modulus, luminosity_distance_Mpc, lightcurve_points_count.

### 6.5. supernova_lightcurves_long.csv

Columns: sn_name, mjd, mag, mag_err, flux, flux_err, band, instrument, source_catalog.

### 6.6. supernova_event_summary.csv

Columns: sn_name, sn_type, source_catalog, peak_mjd, peak_mag, rise_time_days, decay_time_days, peak_width_days, lightcurve_points_count, redshift, luminosity_distance_Mpc.

---

## 7. Verification contracts

- **verify_raw_downloads.py:** Atomic manifest complete; all expected spectra present; payloads valid (no NIST error pages); supernova manifest valid; osc_catalog.json readable and non-empty.
- **verify_pipeline_data.py:** Raw dirs present; atomic payloads valid; data CSVs exist with required columns; atomic data rows > 0; plot files present.

---

## 8. Future work (in scope of this TZ)

- Implement photometry ingestion: OAC API (per-object), ASAS-SN, CfA bulk, CSP.
- Implement merge step: alias resolution, append-only photometry table, duplicate key (object, time, band, mag/flux, source).
- Optional: configurable primary catalog (OSC vs other) and source priority for catalog fields.

---

## 9. References

- **Project structure:** docs/PROJECT_STRUCTURE.md  
- **Sources and algorithms:** docs/DATA_SOURCES_AND_ALGORITHMS.md  
- **Scale-law validation:** docs/scale_law_validation/TECH_SPEC.md, THEORY_SCALE_LAW.md  
- **Theory search:** docs/search/README.md  

# Source field verification: can required parameters be obtained?

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

This document checks whether each required field from `docs/task_supernova_atomic_pipeline.txt` can be obtained from the stated sources. Run `python scripts/check_source_fields.py` to re-check availability (sample requests).

---

## Part A — Atomic transitions (NIST ASD)

**Source:** NIST Atomic Spectra Database  
**Access:** Web form (Lines Form), output as ASCII / CSV / tab-delimited.  
**URL:** https://physics.nist.gov/PhysRefData/ASD/lines_form.html  
**Retrieval:** User selects spectrum (e.g. H I, Fe I), output format, then "Retrieve Data". No official REST API; bulk export via form submission (CGI).

### Required fields vs NIST output

| Task field | NIST ASD | Notes |
|------------|----------|--------|
| element | Yes | From "Ion" column (e.g. "H I" → H). |
| ion_state | Yes | From "Ion" (Roman numeral I, II, …). |
| wavelength_vac_nm | Yes | User chooses "Vacuum (all wavelengths)"; units nm available. |
| wavelength_air_nm | Yes | User chooses air; or both columns. |
| frequency_hz | Derived | Compute from wavelength: c / λ_vac (or convert from GHz if chosen). |
| wavenumber_cm1 | Yes | Optional column; or derive from wavelength. |
| Aki_s^-1 | Yes | Column "Aki" (default s⁻¹). |
| intensity | Yes | "Rel. Int" (relative intensity). |
| Ei_cm1 | Yes | Lower level energy (default cm⁻¹). |
| Ek_cm1 | Yes | Upper level energy. |
| lower_configuration | Yes | "Configurations" (lower). |
| upper_configuration | Yes | "Configurations" (upper). |
| lower_term | Yes | "Terms" (lower). |
| upper_term | Yes | "Terms" (upper). |
| lower_J | Yes | "J-values" (lower). |
| upper_J | Yes | "J-values" (upper). |
| line_type | Yes | "Type" (e.g. E1, M1). |
| source_catalog | Set by pipeline | e.g. "NIST ASD". |
| source_url | Set by pipeline | e.g. lines_form.html or specific query URL. |

**Conclusion (atomic):** All required atomic parameters can be obtained from NIST ASD (some derived, some from columns). Export is per-spectrum via web form; automation would require form submission (e.g. POST) and parsing ASCII/CSV.

---

## Part B — Supernovae

### 1. Open Supernova Catalog (OAC / OSC)

**Source:** Open Astronomy Catalog API (supernovae).  
**Access:** REST API (e.g. astroquery.oac, or direct to api.astrocats.space).  
**Docs:** https://astroquery.readthedocs.io/en/stable/oac/oac.html, https://github.com/astrocatalogs/OACAPI

| Task field | OAC/OSC | Notes |
|------------|---------|--------|
| sn_name | Yes | Event name (query key). |
| source_catalog | Set by pipeline | e.g. "OSC". |
| ra | Yes | In event metadata. |
| dec | Yes | In event metadata. |
| redshift | Yes | In event metadata. |
| host_galaxy | Yes | In metadata (schema-dependent). |
| sn_type | Yes | In metadata (type/claimedtype). |
| discovery_mjd | Yes | In metadata (discoverdate → convert if needed). |
| peak_mjd | Partial | From photometry or derived; not always explicit. |
| peak_mag | Partial | From photometry or metadata if available. |
| band | Yes | Photometry attribute. |
| distance_modulus | Partial | If in metadata. |
| luminosity_distance_Mpc | Partial | If in metadata or from redshift. |
| lightcurve_points_count | Derived | Count of photometry points. |

**Light-curve points:**

| Task field | OAC/OSC | Notes |
|------------|---------|--------|
| sn_name | Yes | Event name. |
| mjd | Yes | Photometry "time" (MJD). |
| mag | Yes | "magnitude". |
| mag_err | Yes | "e_magnitude". |
| flux | Partial | If provided. |
| flux_err | Partial | If provided. |
| band | Yes | "band". |
| instrument | Yes | "instrument". |
| source_catalog | Set by pipeline | "OSC". |

**Conclusion (OSC):** Catalog and light-curve fields required by the task can be obtained from OAC; peak_mjd/peak_mag and distance may need to be derived from light-curves or metadata when not explicit.

---

### 2. ASAS-SN

**Source:** ASAS-SN Sky Patrol (pyasassn, skypatrol).  
**Access:** Python API; light curves in CSV.  
**Docs:** http://asas-sn.ifa.hawaii.edu/documentation/

| Task field | ASAS-SN | Notes |
|------------|---------|--------|
| sn_name / source_catalog | Yes | Catalog/ID from API. |
| ra, dec | Yes | From catalog/target metadata. |
| Light-curve | Yes | JD, magnitude, magnitude error, flux; CSV download. |
| peak_mjd, peak_mag | Derived | From light-curve. |
| redshift, host_galaxy, sn_type | External | Often from cross-match (e.g. OSC); not always in ASAS-SN. |

**Conclusion (ASAS-SN):** Positions and light-curves (mjd, mag, mag_err, band-equivalent) obtainable; peak and type/redshift may require derivation or other catalogs.

---

### 3. ZTF

**Source:** ZTF (IRSA) light-curve API.  
**Access:** IRSA ZTF Lightcurve API (e.g. by object ID or position).  
**Docs:** https://irsa.ipac.caltech.edu/docs/program_interface/ztf_lightcurve_api.html

| Task field | ZTF | Notes |
|------------|-----|--------|
| sn_name / source_catalog | Yes | Object ID / catalog. |
| mjd, mag (and err) | Yes | In light-curve table. |
| band | Yes | BANDNAME. |
| ra, dec | Yes | From metadata/query. |
| peak_mjd, peak_mag | Derived | From light-curve. |
| redshift, sn_type | External | From other catalogs. |

**Conclusion (ZTF):** Light-curves and coordinates obtainable; peak and type/redshift from derivation or cross-match.

---

### 4. Pan-STARRS

**Source:** Pan-STARRS via MAST (catalog/detection tables).  
**Access:** MAST Catalog API, CasJobs, VO TAP.  
**Docs:** https://catalogs.mast.stsci.edu/docs/panstarrs.html

| Task field | Pan-STARRS | Notes |
|------------|------------|--------|
| ra, dec | Yes | In catalog. |
| Light-curve / photometry | Yes | From detection/forced tables. |
| sn_name / sn_type | Partial | No dedicated SN catalog; need SN lists/cross-match. |

**Conclusion (Pan-STARRS):** Astrometry and photometry obtainable; supernova identification and type require external SN lists or cross-matching.

---

## Summary

| Source | Catalog fields | Light-curve fields | Peak / rise/decay |
|--------|----------------|--------------------|-------------------|
| NIST ASD | All required atomic fields | — | — |
| OSC (OAC) | Yes (ra, dec, redshift, type, etc.) | Yes (mjd, mag, mag_err, band, instrument) | Partial / derived |
| ASAS-SN | Positions + IDs | Yes (JD, mag, err) | Derived |
| ZTF | Positions + IDs | Yes (MJD, mag, band) | Derived |
| Pan-STARRS | Positions + photometry | Yes (from tables) | Derived; SN id from cross-match |

**Overall:** The required parameters from the task can be obtained from the stated sources. Some quantities (peak_mjd, peak_mag, rise_time_days, decay_time_days, redshift, sn_type for some catalogs) must be derived from light-curves or taken from metadata/cross-match where available; the task allows NaN when not computable.

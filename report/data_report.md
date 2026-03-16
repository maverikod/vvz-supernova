# Fourth tech spec — data report

Run mode: **physical-enabled**.

## 1. Observable completeness

Row counts for observable-domain artifacts (§10.1).

| Artifact | Rows |
|----------|------|
| atomic_lines_clean.csv | 69505 |
| atomic_lines_by_element.csv | 69505 |
| atomic_transition_summary.csv | 18 |
| atomic_transition_events.csv | 38948 |
| astrophysical_transient_catalog_clean.csv | 3 |
| astrophysical_transient_lightcurves_long.csv | 8388 |
| astrophysical_transient_events.csv | 3 |

## 2. Transition-passport completeness

Row counts and c_theta_pending counts for passport outputs (§10.2, §10.3).

| Artifact | Rows | c_theta_pending |
|----------|------|----------------|
| atomic_transition_passports.csv | 38948 | 0 |
| astrophysical_flash_transition_passports.csv | 3 | 0 |
| unified_transition_passports.csv | 38951 | 0 |
| cluster_ready_transition_passports.csv | 35359 | 0 |

## 3. Rows invalidated during transition-passport translation

- **Atomic:** 0 rows (atomic_transition_events -> atomic_transition_passports).
- **Astrophysical:** 0 rows (astrophysical_transient_events -> astrophysical_flash_transition_passports).

## 4. Rows left in c_theta_pending

Total passport rows with passport_status = c_theta_pending (unified scope): 0.

Per-file counts are in the transition-passport completeness table above.

## 5. Cluster-ready note

cluster_ready_transition_passports.csv contains physical-layer rows.

---

**§13.11:** This report states what is observed (observable tables), what is inferred (passport tables), and what remains unavailable (c_theta_pending, invalidated rows).

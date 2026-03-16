# Coverage Matrix

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

| Gap proven by code analysis | Evidence in current code | Planned step(s) |
|---|---|---|
| No supernova photometry is downloaded | `scripts/download_supernova_data.py` downloads only `osc_catalog.json` and marks other sources as skipped | 01, 02 |
| No cleaned supernova light curves are produced | `scripts/clean_supernova_data.py` returns `[]` from `load_osc_lightcurves()` | 03, 04 |
| Timing summary has no reliable light-curve input | `scripts/build_event_summaries.py` works only if `mjd` and `mag` rows exist | 05 |
| Raw verification does not require photometry-bearing artifacts | `scripts/verify_raw_downloads.py` checks only manifest structure and readable OSC JSON | 06, 10 |
| Final verification allows header-only supernova light-curve output | `scripts/verify_pipeline_data.py` rejects empty atomic CSVs only | 07, 11 |
| Downstream event table does not explicitly prove timing-rich rows | `scripts/build_supernova_transient_events.py` needs real counts and timing fields to become analysis-meaningful | 08, 11 |
| Durable report does not expose supernova timing coverage clearly enough | `scripts/build_third_spec_report.py` counts rows but not timing coverage by field/source | 09, 11 |
| Existing tests do not prove end-to-end supernova sufficiency | current tests cover atomic validation and minimal raw supernova readability only | 10, 11 |

## Notes

- The curated OAC subset is not a convenience feature; it is the minimum concrete source addition already evidenced by donor code in `scripts/download_astrophysical_transient_data.py`.
- The plan intentionally does not touch unrelated oversized files outside the supernova data path.

# Parallel Chains

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Rule

The critical supernova data path is mostly sequential because each later step depends on real photometry artifacts created earlier.

This file is informational only. Dependency contracts, blackstops, and handoff obligations that control execution live inside each `step_*.md` file and must not be inferred from this file alone.

## Chain A: Critical path

1. `step_01_create_oac_event_artifacts_helper.md`
2. `step_02_refactor_download_supernova_data_entrypoint.md`
3. `step_03_create_supernova_raw_ingest_helper.md`
4. `step_04_refactor_clean_supernova_data_entrypoint.md`
5. `step_05_refactor_build_event_summaries.md`
6. `step_06_refactor_verify_raw_downloads.md`
7. `step_07_refactor_verify_pipeline_data.md`
8. `step_08_refactor_build_supernova_transient_events.md`
9. `step_09_refactor_build_third_spec_report.md`

Reason: each step consumes artifacts or contracts introduced by the previous one.

## Chain B: Test coverage

1. `step_10_expand_raw_download_verification_tests.md`
2. `step_11_add_supernova_time_domain_pipeline_tests.md`

## Allowed parallelism

- `step_10_expand_raw_download_verification_tests.md` may run only after `step_06_refactor_verify_raw_downloads.md`.
- `step_11_add_supernova_time_domain_pipeline_tests.md` may run only after steps 04, 05, 07, 08, and 09 are complete.
- once `step_06_refactor_verify_raw_downloads.md` is complete, `step_10_expand_raw_download_verification_tests.md` may run in parallel with steps 08 and 09;
- no earlier step may be parallelized without breaking the single-file, data-first contract.

## Blackstops

- If step 02 cannot keep download logic under the file-size limit, stop and report instead of moving logic into another production file outside the declared helper.
- If step 04 cannot keep cleaning logic under the file-size limit, stop and report instead of editing a second production file.
- If step 05 requires a second production file for timing logic, stop and reopen the plan before implementation.

# Fourth spec — remaining work by step

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

Checklist of code and behaviour changes required per step after TECH_SPEC and plan updates (source sufficiency, run modes, cluster-ready).

---

## Step 01 — Passport schema

**Status:** Done. No changes.

---

## Step 02 — Build atomic transition passports

**Status:** Done for normalized-only.

**If physical-enabled run is required later:**

| # | What to do |
|---|------------|
| 1 | Add a single source of `c_theta` (e.g. config file, env var, CLI arg). |
| 2 | When `c_theta` is set and finite: compute `L_eff_m = c_theta * t_char_s`, `kappa_eff_m^-1 = omega_mode / c_theta` and write them; set `passport_status = complete` where applicable. |
| 3 | When `c_theta` is not set: keep current behaviour (empty physical fields, `c_theta_pending`). |

---

## Step 03 — Download astrophysical transient data

**Contract:** Raw artifact must contain photometric samples or a reproducible path to them. Metadata-only catalog is not valid completion.

| # | What to do | Notes |
|---|------------|--------|
| 1 | Ensure the script downloads (or records reproducible access to) **per-event photometry**, not only a bulk object catalog. | Current script may already use Open Astronomy Catalog API and event-level photometry; confirm it writes raw files that step 04 can turn into non-empty `lightcurves_long`. |
| 2 | Completeness verification must assert that at least one raw artifact has **usable photometry** (e.g. non-empty photometry list with time + magnitude or flux). | Fail with clear message if only metadata was downloaded. |
| 3 | If using OSC bulk `catalog.json` only: add a second stage (or separate scripted path) that fetches photometry for selected events and saves it under `raw/`; document in manifest. | Do not treat bulk catalog alone as sufficient. |

**Deliverable:** After run, step 04 must be able to produce a non-empty `astrophysical_transient_lightcurves_long.csv`.

---

## Step 04 — Clean astrophysical transient data

**Contract:** Assumes step 03 provided photometry-bearing raw. A header-only `astrophysical_transient_lightcurves_long.csv` caused by metadata-only source is an upstream blocker.

| # | What to do | Notes |
|---|------------|--------|
| 1 | Parse raw so that **light-curve samples** (mjd, mag or flux, band, event_id) are extracted and written to `astrophysical_transient_lightcurves_long.csv`. | Schema and column names per §8.1 / §10.1. |
| 2 | Completeness verification: if raw is declared photometry-bearing (e.g. manifest or artifact list indicates photometry), require **at least one data row** in `astrophysical_transient_lightcurves_long.csv`; otherwise fail. | Distinguish “no raw” vs “raw has no photometry” and treat the latter as blocker. |
| 3 | When raw is missing or not photometry-bearing: write minimal CSVs (headers only) and exit with non-zero or report blocker; do not treat as successful branch completion. | Per decision rules in step file. |

**Deliverable:** Non-empty `astrophysical_transient_lightcurves_long.csv` when step 03 produced photometry-bearing raw.

---

## Step 05 — Build astrophysical transient events

**Contract:** Assumes step 04 produced a non-empty light-curve table. Empty output must be explained by real filtering (§8.5), not by header-only upstream.

| # | What to do | Notes |
|---|------------|--------|
| 1 | **Before** building events: if `astrophysical_transient_lightcurves_long.csv` exists but has **zero data rows** (only header), **stop and report** “upstream source insufficiency” (e.g. print to stderr and exit with non-zero). Do not silently write header-only `astrophysical_transient_events.csv`. | Per step 05 decision rules and blackstops. |
| 2 | Keep existing logic: aggregate `number_of_points` per event from long table; exclude events with `number_of_points < 20`; require `peak_abs_mag` (or derivable from peak_mag + distance). | No change to formulas. |
| 3 | Completeness verification: if output has zero rows, verification may still pass only when upstream lightcurves had data and all rows were excluded by §8.5 / peak_abs_mag rules; otherwise treat as failure or document reason. | Optional: add a simple check “if lightcurves_long has 0 rows then we must have exited earlier with blocker”. |

**Deliverable:** Non-empty `astrophysical_transient_events.csv` when upstream provided non-empty lightcurves and at least one event passes §8.5 and has peak_abs_mag.

---

## Step 06 — Build astrophysical flash passports

**Status:** No contract change. Depends on step 05 output.

| # | What to do | Notes |
|---|------------|--------|
| 1 | No code change required for “photometry-bearing” or “run mode”. | Just re-run after step 05 is fixed. |
| 2 | If physical-enabled run is required: same as step 02 — need `c_theta` input and fill `L_eff_m`, `kappa_eff_m^-1` when available. | Only if you add physical mode later. |

**Deliverable:** Non-empty `astrophysical_flash_transition_passports.csv` when step 05 produced non-empty events.

---

## Step 07 — Build unified transition passports

**Status:** No contract change. Depends on steps 02 and 06.

| # | What to do | Notes |
|---|------------|--------|
| 1 | No code change required. | Re-run after 02 and 06; unified table will contain both atomic and astrophysical rows when both branches are non-empty. |

**Deliverable:** `unified_transition_passports.csv` with rows from both domains when both branches produced data.

---

## Step 08 — Build cluster-ready transition passports

**Contract:** Physical-layer step. Header-only output is valid only in normalized-only run when the reason (no `c_theta`, so no L_eff/kappa) is reported explicitly.

| # | What to do | Notes |
|---|------------|--------|
| 1 | Keep current behaviour: exclude rows without finite `L_eff_m` and `kappa_eff_m^-1`; write header-only when no row passes; **print exclusion reason** to stderr (e.g. “Excluded N row(s): L_eff_m missing (c_theta unavailable)”). | Already implemented; verify message is explicit. |
| 2 | Do **not** add synthetic `c_theta` or fake logs. | Per §9 and step forbidden alternatives. |
| 3 | If physical-enabled run is added: when `c_theta` is configured and step 02/06 fill physical fields, this step will automatically emit rows for those passports. | No change needed in step 08 for that; only 02/06 need to emit physical fields. |

**Deliverable:** Either non-empty cluster-ready (when `c_theta` is set and passports have physical fields) or header-only with explicit stderr report in normalized-only run.

---

## Step 09 — Build fourth-spec report

**Contract:** Report must reflect actual pipeline state and run mode.

| # | What to do | Notes |
|---|------------|--------|
| 1 | Ensure report states **observable completeness** and **transition-passport completeness** with real row counts (including zeros when a branch produced no data). | Already in scope. |
| 2 | Add or clarify in `data_report.md`: **run mode** (normalized-only vs physical-enabled) and, if normalized-only, that **cluster_ready** is empty because `c_theta` was not provided. | So readers know header-only cluster-ready is expected when c_theta is absent. |
| 3 | No code change required for “blocker” reporting; step 09 only reports what the pipeline produced. | Steps 03–05 are responsible for failing on metadata-only / empty lightcurves. |

**Deliverable:** Report that explicitly separates the four topics and explains empty cluster-ready when applicable.

---

## Summary table

| Step | Main code/behaviour change |
|------|----------------------------|
| 01   | None. |
| 02   | Optional: add `c_theta` input and fill physical fields when set. |
| 03   | Ensure photometry-bearing raw (event-level photometry); completeness must assert usable photometry. |
| 04   | Parse raw into lightcurves_long; completeness must require non-empty lightcurves when raw is photometry-bearing. |
| 05   | **Block** when lightcurves_long has 0 data rows; exit with “upstream source insufficiency”. |
| 06   | None (re-run after 05). Optional: physical fields if c_theta added. |
| 07   | None (re-run after 06). |
| 08   | Verify stderr message is explicit for excluded rows; no fake logs. |
| 09   | Report run mode and reason for empty cluster-ready when normalized-only. |

---

## Execution order to get non-empty astrophysical branch

1. **03** — Download photometry-bearing raw (e.g. current OAC API script).
2. **04** — Clean → non-empty `astrophysical_transient_catalog_clean.csv` and `astrophysical_transient_lightcurves_long.csv`.
3. **05** — Build events (will pass once 04 has data; step 05 must block if 04 produced header-only lightcurves).
4. **06** → **07** → **09** — Re-run; unified and report will show both branches.

To get non-empty **cluster_ready**: add `c_theta` to config/calibration and implement physical-field output in steps **02** and **06**, then re-run **07** → **08** → **09**.

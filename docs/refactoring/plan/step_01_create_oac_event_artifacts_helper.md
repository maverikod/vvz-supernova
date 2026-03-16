# Step 01: Create OAC Event Artifacts Helper

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

## Executor role

You are the implementation executor for the first supernova data-path step. Your job is to create one helper module that encapsulates the exact OAC event-artifact workflow required by later downloader and verifier steps.

## Execution directive

Edit exactly one production file: `supernova_atomic/oac_event_artifacts.py`. Do not edit any other production file in this step. If the target behavior cannot fit into this one file while staying within project rules, stop under the blackstop rules below.

## Target file

`supernova_atomic/oac_event_artifacts.py`

## Step scope

This step creates the reusable helper layer for curated OAC event artifacts only. It does not change any CLI entrypoint, any wrapper script, any report script, or any final pipeline verification logic.

## Dependency contract

- This is the first executable implementation step in the plan; no previous code step is required.
- Before changing code, activate `.venv` and confirm the interpreter path is the project environment.
- Before final validation, `python -m pytest --version` must succeed inside `.venv`.
- If `pytest` is missing in `.venv`, stop and report the environment prerequisite failure instead of continuing.

## Required context

Read these files before editing:

- `docs/refactoring/TECH_SPEC.md`
- `docs/TECH_SPEC.md`
- `docs/DATA_SOURCES_AND_ALGORITHMS.md`
- `scripts/download_supernova_data.py`
- `scripts/download_astrophysical_transient_data.py`
- `scripts/verify_raw_downloads.py`

The helper must be shaped so later steps can import it from:

- `scripts/download_supernova_data.py`
- `scripts/verify_raw_downloads.py`

## Forbidden scope

- Do not edit `scripts/download_supernova_data.py`.
- Do not edit `scripts/verify_raw_downloads.py`.
- Do not create a second helper file.
- Do not add ASAS-SN, CfA, CSP, YSE, ZTF, or Pan-STARRS logic.
- Do not add synthetic data or mock fallbacks.

## Atomic operations

1. Create module constants with the exact curated dataset definition:
   - `CURATED_OAC_EVENTS = ("SN2014J", "SN2011fe", "SN1987A")`
   - `OAC_SOURCE_NAME = "Open Astronomy Catalog API"`
   - `OAC_SOURCE_URL = "https://api.astrocats.space/"`
   - `OAC_API_BASE_URL = "https://api.astrocats.space"`
2. Implement deterministic filename generation:
   - `SN2014J -> sn2014j_event.json`
   - `SN2011fe -> sn2011fe_event.json`
   - `SN1987A -> sn1987a_event.json`
3. Implement exact URL builders for:
   - metadata endpoint: `https://api.astrocats.space/<event>`
   - photometry endpoint: `https://api.astrocats.space/<event>/photometry`
4. Implement retry-based JSON fetch using the same request style as the donor downloader.
5. Implement payload merge logic that produces one JSON object with exactly one top-level key equal to the event name and with the `photometry` list attached to the metadata block.
6. Implement usable photometry counting with this exact rule:
   - count a row only if it has non-empty `time` and at least one non-empty signal field among `magnitude`, `flux`, `fluxdensity`, `counts`.
7. Implement artifact verification helpers that validate:
   - raw file exists;
   - JSON root is an object;
   - requested event exists in the payload;
   - payload contains a non-empty `photometry` list;
   - manifest `photometry_points` and `usable_photometry_points` match the raw artifact.

## Expected file change

Only `supernova_atomic/oac_event_artifacts.py` changes in this step.

That file must gain:

- curated OAC event constants;
- deterministic raw artifact filename logic;
- metadata and photometry URL builders;
- JSON fetch helper with retry;
- merged-payload builder for one event;
- usable photometry counter;
- artifact verification helper.

## Expected deliverables

- One new module: `supernova_atomic/oac_event_artifacts.py`
- Importable symbols for later steps, including:
  - curated event constants;
  - filename sanitization for event artifacts;
  - OAC URL builders;
  - JSON fetch helper;
  - payload merge helper;
  - usable photometry counter;
  - artifact verification helper.

## Mandatory validation

Run these commands exactly:

```bash
source .venv/bin/activate
python -m pytest --version
python -m black supernova_atomic/oac_event_artifacts.py
python -m flake8 supernova_atomic/oac_event_artifacts.py
python -m mypy supernova_atomic/oac_event_artifacts.py
python -m pytest
code_mapper -r "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova" -o "/home/vasilyvz/Desktop/Инерция/7d/progs/supernova/code_analysis" -m 400
```

Step-specific gate:

- `python -m pytest --version` must succeed inside `.venv`;
- all four quality commands must succeed;
- the full `python -m pytest` run must succeed;
- `code_mapper` must finish successfully and refresh `code_analysis/`.

## Decision rules

- Use the curated event set exactly as listed above; do not add or remove events.
- Use lowercase artifact filenames exactly as listed above.
- Use the donor implementation path from `scripts/download_astrophysical_transient_data.py`; do not invent a second alternative API workflow.
- If the donor code exposes optional fields not needed for later supernova steps, omit them rather than expanding scope.

## Blackstops

Stop immediately and report instead of continuing if any of the following occurs:

- The helper would exceed the project file-size limit.
- A second production file is required.
- The target API cannot be expressed deterministically from the donor implementation.
- `.venv` is inactive or not the interpreter in use.
- `pytest` is unavailable in `.venv`.

## Handoff package

When the step is complete, the handoff must include:

- the final path `supernova_atomic/oac_event_artifacts.py`;
- the list of exported symbols created in the module;
- confirmation that artifact filenames and curated event names match this step exactly;
- results of `black`, `flake8`, `mypy`, `pytest`, and the code-mapper update.

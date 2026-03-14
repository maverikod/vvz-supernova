# Step 02 — Build atomic_transition_events.csv

Author: Vasiliy Zdanovskiy  
email: vasilyvz@gmail.com

**Rule:** 1 step = 1 plan file.  
**Code file:** `scripts/build_atomic_transition_events.py`

---

## Executor role

Read `data/atomic_lines_clean.csv`; drop rows without wavelength or Aki; compute parity, deltaE_eV, tau_s, nu_Hz, Q_proxy, deltaJ, parity_change; assign transition_id; write `data/atomic_transition_events.csv` with spec columns.

## Execution directive

Execute only this step. Create only `scripts/build_atomic_transition_events.py`. Stop on validation failure.

## Read first

- `docs/Third_tech_spec.md`
- `supernova_atomic/atomic_schema.py` (and third_spec_schema if added in Step 01)
- Current `data/atomic_lines_clean.csv` column names

## Expected file change

- Script reads atomic_lines_clean.csv.
- Drop rows missing wavelength (wavelength_vac_nm or wavelength_air_nm) or Aki (Aki_s^-1).
- Parity from lower_term/upper_term: 1 if term contains (o, °, odd), else 0.
- deltaE_eV = (Ek_cm1 - Ei_cm1) / 8065.54429; tau_s = 1/Aki; nu_Hz from frequency_hz or c/wavelength; Q_proxy = nu_Hz * tau_s; deltaJ from J (parse fraction e.g. "1/2" to float; else leave empty); parity_change = 1 if parity_upper != parity_lower else 0.
- transition_id = `{element}_{ion}_{lower}_{upper}_{row}` (lower/upper can be row index or level label for uniqueness).
- Output columns: transition_id, element, ion_stage, deltaE_eV, tau_s, nu_Hz, Q_proxy, deltaJ, parity_change, wavelength_nm, Aki.

## Mandatory validation

- black, flake8, mypy on `scripts/build_atomic_transition_events.py`
- Run script; atomic_transition_events.csv exists with correct columns.

"""
Transition-passport schema: P4 core, P_obs derived layer, column lists, status.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Defines canonical field names, minimum columns for atomic/astrophysical/unified/
cluster-ready passport CSVs, passport_status values, and validity rules per
docs/TECH_SPEC.md §§5, 6, 9, 11. No I/O; constants and pure functions only.
"""

from __future__ import annotations

import math
from typing import Any

# --- §5.1 P4 canonical core ---
P4_OMEGA_MODE = "omega_mode"
P4_C_THETA = "c_theta"
P4_KAPPA_EFF = "kappa_eff"
P4_L_EFF = "L_eff"

P4_CORE_FIELDS = (P4_OMEGA_MODE, P4_C_THETA, P4_KAPPA_EFF, P4_L_EFF)

# --- §5.2 P_obs derived layer ---
P_OBS_OMEGA_MODE = "omega_mode"
P_OBS_T_CHAR_S = "t_char_s"
P_OBS_Q_EFF = "Q_eff"
P_OBS_CHI_LOSS = "chi_loss"
P_OBS_TAIL_STRENGTH = "tail_strength"
P_OBS_TAIL_ENERGY_PROXY = "tail_energy_proxy"
P_OBS_SHAPE_1 = "shape_1"
P_OBS_SHAPE_2 = "shape_2"
P_OBS_PASSPORT_STATUS = "passport_status"
P_OBS_DOMAIN = "domain"

P_OBS_FIELDS = (
    P_OBS_OMEGA_MODE,
    P_OBS_T_CHAR_S,
    P_OBS_Q_EFF,
    P_OBS_CHI_LOSS,
    P_OBS_TAIL_STRENGTH,
    P_OBS_TAIL_ENERGY_PROXY,
    P_OBS_SHAPE_1,
    P_OBS_SHAPE_2,
    P_OBS_PASSPORT_STATUS,
    P_OBS_DOMAIN,
)

# --- §9.2 Physical fields (only when c_theta available) ---
# CSV header string: invalid as Python identifier
KAPPA_EFF_M_INV = "kappa_eff_m^-1"
L_EFF_M = "L_eff_m"

PHYSICAL_FIELDS = (P4_C_THETA, L_EFF_M, KAPPA_EFF_M_INV)

# --- §6 Passport completeness states ---
COMPLETE = "complete"
C_THETA_PENDING = "c_theta_pending"
PARTIALLY_OBSERVED = "partially_observed"
INVALID = "invalid"

PASSPORT_STATUS_VALUES = (COMPLETE, C_THETA_PENDING, PARTIALLY_OBSERVED, INVALID)

# --- §11.1 Atomic transition passports minimum columns ---
ATOMIC_TRANSITION_PASSPORTS_COLUMNS = (
    "object_id",
    "domain",
    "element",
    "ion_stage",
    "omega_mode",
    "t_char_s",
    "Q_eff",
    "chi_loss",
    "c_theta",
    L_EFF_M,
    KAPPA_EFF_M_INV,
    "tail_strength",
    "tail_energy_proxy",
    "shape_1",
    "shape_2",
    "passport_status",
    "source_catalog",
)

# --- §11.2 Astrophysical flash-transition passports minimum columns ---
ASTROPHYSICAL_FLASH_TRANSITION_PASSPORTS_COLUMNS = (
    "object_id",
    "domain",
    "name",
    "transient_class",
    "omega_mode",
    "t_char_s",
    "Q_eff",
    "chi_loss",
    "c_theta",
    L_EFF_M,
    KAPPA_EFF_M_INV,
    "tail_strength",
    "tail_energy_proxy",
    "shape_1",
    "shape_2",
    "passport_status",
    "source_catalog",
)

# --- §11.3 Unified transition passports minimum columns ---
UNIFIED_TRANSITION_PASSPORTS_COLUMNS = (
    "object_id",
    "domain",
    "omega_mode",
    "t_char_s",
    "Q_eff",
    "chi_loss",
    "c_theta",
    L_EFF_M,
    KAPPA_EFF_M_INV,
    "tail_strength",
    "tail_energy_proxy",
    "shape_1",
    "shape_2",
    "passport_status",
    "class_hint",
    "source_catalog",
)

# --- §11.4 Clustering-ready transition passports minimum columns ---
CLUSTER_READY_TRANSITION_PASSPORTS_COLUMNS = (
    "object_id",
    "domain",
    "log_omega",
    "log_t",
    "log_Q",
    "log_L_eff",
    "log_kappa",
    "log_tail_strength",
    "shape_1",
    "shape_2",
    "passport_status",
    "class_hint",
)


def _finite_float(value: Any) -> float:
    """Return float value if finite and positive; else NaN. Handles str/float."""
    if value is None:
        return float("nan")
    try:
        x = float(value)
        return x if math.isfinite(x) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def classify_passport_status(row: dict[str, Any]) -> str:
    """
    Classify passport_status from a row dict per §6 and §7.4/§8.4.

    Rules:
    - invalid: omega_mode or t_char_s missing, <= 0, or non-finite.
    - c_theta_pending: normalized layer valid but c_theta absent or non-finite.
    - complete: all required normalized and physical fields present and finite.
    - partially_observed: otherwise (partial normalized passport).

    No I/O; pure function. Missing values in row are treated as absent.
    """
    omega = _finite_float(row.get("omega_mode"))
    t_char = _finite_float(row.get("t_char_s"))
    if omega <= 0 or t_char <= 0:
        return INVALID
    q_eff = _finite_float(row.get("Q_eff"))
    chi = _finite_float(row.get("chi_loss"))
    tail_s = _finite_float(row.get("tail_strength"))
    tail_e = _finite_float(row.get("tail_energy_proxy"))
    s1 = row.get("shape_1")
    s2 = row.get("shape_2")
    has_shape1 = s1 is not None and (
        isinstance(s1, (int, float)) or (isinstance(s1, str) and s1.strip() != "")
    )
    has_shape2 = s2 is not None and (
        isinstance(s2, (int, float)) or (isinstance(s2, str) and s2.strip() != "")
    )
    normalized_ok = (
        q_eff > 0
        and chi > 0
        and not math.isnan(tail_s)
        and not math.isnan(tail_e)
        and has_shape1
        and has_shape2
    )
    if not normalized_ok:
        return PARTIALLY_OBSERVED
    c_theta = _finite_float(row.get("c_theta"))
    l_eff = _finite_float(row.get(L_EFF_M))
    kappa = _finite_float(row.get(KAPPA_EFF_M_INV))
    if c_theta <= 0 or l_eff <= 0 or kappa <= 0:
        return C_THETA_PENDING
    return COMPLETE

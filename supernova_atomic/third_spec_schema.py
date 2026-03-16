"""
Third tech spec: schema and constants for event tables and cluster-ready output.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Parity rule, energy conversion (cm-1 to eV), ID formats, class_hint mapping.
See docs/TECH_SPEC.md.
"""

from __future__ import annotations

import re

# Energy: E_eV = E_cm-1 / 8065.54429 (current TZ)
CM1_TO_EV = 8065.54429

# class_hint per spec: atomic -> atomic_transition, supernova -> stellar_transient
CLASS_HINT_ATOMIC = "atomic_transition"
CLASS_HINT_SUPERNOVA = "stellar_transient"

# Light curve valid only if number_of_points >= 20 (current TZ)
MIN_LIGHTCURVE_POINTS_VALID = 20

# Output column names for Third spec tables
ATOMIC_TRANSITION_EVENTS_COLUMNS = [
    "transition_id",
    "element",
    "ion_stage",
    "deltaE_eV",
    "tau_s",
    "nu_Hz",
    "Q_proxy",
    "deltaJ",
    "parity_change",
    "wavelength_nm",
    "Aki",
]

SUPERNOVA_TRANSIENT_EVENTS_COLUMNS = [
    "event_id",
    "name",
    "type",
    "redshift",
    "distance_Mpc",
    "peak_abs_mag",
    "L_proxy",
    "rise_time_days",
    "decay_time_days",
    "width_days",
    "t0_days",
    "asymmetry",
    "width_norm",
    "event_strength",
    "has_lightcurve",
    "number_of_points",
]

CLUSTER_READY_EVENTS_COLUMNS = [
    "event_id",
    "domain",
    "logE",
    "logt",
    "logQ_or_width",
    "shape_1",
    "shape_2",
    "class_hint",
]

# Parity: 1 if term contains (o, °, odd), else 0 (spec: parity from term)
_PARITY_ODD_PATTERN = re.compile(r"o|°|odd", re.IGNORECASE)


def parity_from_term(term: str) -> int:
    """
    Return parity 1 if term indicates odd (contains o, °, odd), else 0.
    Used when source does not provide parity_lower/parity_upper.
    """
    if not term or not isinstance(term, str):
        return 0
    return 1 if _PARITY_ODD_PATTERN.search(term.strip()) else 0


def cm1_to_eV(E_cm1: float) -> float:
    """Convert energy in cm-1 to eV. Returns float; use math.isnan for invalid."""
    try:
        return float(E_cm1) / CM1_TO_EV
    except (TypeError, ValueError, ZeroDivisionError):
        return float("nan")


def deltaE_eV(Ei_cm1: float, Ek_cm1: float) -> float:
    """
    Transition energy in eV: (Ek - Ei) / 8065.54429.
    Returns nan if inputs are invalid or missing.
    """
    try:
        ei = float(Ei_cm1)
        ek = float(Ek_cm1)
        if ei != ei or ek != ek:  # NaN
            return float("nan")
        return (ek - ei) / CM1_TO_EV
    except (TypeError, ValueError):
        return float("nan")

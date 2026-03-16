"""
Astrophysical passport row builders for transition-passport scripts.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from supernova_atomic.passport_schema import (
    C_THETA_PENDING,
    COMPLETE,
    INVALID,
    KAPPA_EFF_M_INV,
    L_EFF_M,
)

DOMAIN_ASTROPHYSICAL = "astrophysical"
SECONDS_PER_DAY = 86400.0
TWO_PI = 2.0 * math.pi


def parse_float_or_nan(value: str | float | None) -> float:
    """Parse a numeric value or return NaN for missing or invalid input."""
    if value is None or (
        isinstance(value, str) and value.strip() in ("", "nan", "NaN")
    ):
        return float("nan")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def to_csv_value(value: float | str | int | None) -> str:
    """Serialize a scalar for CSV; NaN or None become empty strings."""
    if value is None:
        return ""
    if isinstance(value, float):
        return "" if math.isnan(value) else str(value)
    text = str(value).strip()
    return "" if text.lower() in ("nan", "") else text


def astrophysical_passport_status(
    t_char_s: float,
    q_eff: float,
    has_tail_strength: bool,
    has_tail_energy: bool,
    has_shape1: bool,
    has_shape2: bool,
    c_theta: float | None,
) -> str:
    """Return passport status for an astrophysical/supernova transition row."""
    if t_char_s <= 0 or q_eff <= 0 or math.isnan(t_char_s) or math.isnan(q_eff):
        return INVALID
    if not (has_tail_strength and has_tail_energy and has_shape1 and has_shape2):
        return INVALID
    if c_theta is None:
        return C_THETA_PENDING
    return COMPLETE


def _build_row(
    *,
    event_id: str,
    name: str,
    transient_class: str,
    source_catalog: str,
    t_char_s: float,
    omega_mode: float,
    q_eff: float,
    chi_loss: float,
    tail_strength: float,
    tail_energy_proxy: float,
    shape_1: float,
    shape_2: float,
    c_theta: float | None,
) -> dict[str, str]:
    """Build one output passport row after status and physical-layer computation."""
    status = astrophysical_passport_status(
        t_char_s,
        q_eff,
        has_tail_strength=not math.isnan(tail_strength),
        has_tail_energy=not math.isnan(tail_energy_proxy),
        has_shape1=not math.isnan(shape_1),
        has_shape2=not math.isnan(shape_2),
        c_theta=c_theta,
    )
    if status == INVALID:
        t_char_s = float("nan")
        omega_mode = float("nan")
        q_eff = float("nan")
        chi_loss = float("nan")
        tail_strength = float("nan")
        tail_energy_proxy = float("nan")
        shape_1 = float("nan")
        shape_2 = float("nan")

    l_eff_m = float("nan")
    kappa_eff_m_inv = float("nan")
    if status == COMPLETE and c_theta is not None:
        l_eff_m = c_theta * t_char_s
        kappa_eff_m_inv = omega_mode / c_theta

    return {
        "object_id": event_id,
        "domain": DOMAIN_ASTROPHYSICAL,
        "name": name,
        "transient_class": transient_class,
        "omega_mode": to_csv_value(omega_mode),
        "t_char_s": to_csv_value(t_char_s),
        "Q_eff": to_csv_value(q_eff),
        "chi_loss": to_csv_value(chi_loss),
        "c_theta": to_csv_value(c_theta),
        L_EFF_M: to_csv_value(l_eff_m),
        KAPPA_EFF_M_INV: to_csv_value(kappa_eff_m_inv),
        "tail_strength": to_csv_value(tail_strength),
        "tail_energy_proxy": to_csv_value(tail_energy_proxy),
        "shape_1": to_csv_value(shape_1),
        "shape_2": to_csv_value(shape_2),
        "passport_status": status,
        "source_catalog": source_catalog,
    }


def _append_astrophysical_event_rows(
    rows_out: list[dict[str, str]],
    events_path: Path,
    c_theta: float | None,
) -> None:
    """Append passport rows derived from astrophysical_transient_events.csv."""
    if not events_path.exists():
        return
    with events_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            event_id = (row.get("event_id") or "").strip() or "unknown"
            name = (row.get("name") or "").strip()
            transient_class = (
                row.get("transient_class") or row.get("type") or ""
            ).strip()
            source_catalog = (row.get("source_catalog") or "").strip()

            t0_days = parse_float_or_nan(row.get("t0_days"))
            width_days = parse_float_or_nan(row.get("width_days"))
            width_norm = parse_float_or_nan(row.get("width_norm"))
            l_proxy = parse_float_or_nan(row.get("L_proxy"))
            event_strength = parse_float_or_nan(row.get("event_strength"))
            asymmetry = parse_float_or_nan(row.get("asymmetry"))
            points_raw = row.get("number_of_points")
            try:
                n_pts = int(float(points_raw)) if points_raw else None
            except (ValueError, TypeError):
                n_pts = None

            t_char_s = parse_float_or_nan(row.get("t_char_s"))
            if math.isnan(t_char_s) and not math.isnan(t0_days) and t0_days > 0:
                t_char_s = t0_days * SECONDS_PER_DAY

            omega_mode = parse_float_or_nan(row.get("omega_mode"))
            if math.isnan(omega_mode) and not math.isnan(t_char_s) and t_char_s > 0:
                omega_mode = TWO_PI / t_char_s

            q_eff = parse_float_or_nan(row.get("Q_eff"))
            if math.isnan(q_eff):
                if width_norm > 0:
                    q_eff = 1.0 / width_norm
                elif width_days > 0 and not math.isnan(t0_days) and t0_days > 0:
                    q_eff = t0_days / width_days

            chi_loss = (
                1.0 / (2.0 * q_eff)
                if not math.isnan(q_eff) and q_eff > 0
                else float("nan")
            )
            tail_strength = parse_float_or_nan(row.get("tail_strength"))
            if math.isnan(tail_strength):
                tail_strength = l_proxy
            tail_energy_proxy = parse_float_or_nan(row.get("tail_energy_proxy"))
            if math.isnan(tail_energy_proxy):
                tail_energy_proxy = event_strength
            shape_1 = parse_float_or_nan(row.get("shape_1"))
            if math.isnan(shape_1):
                shape_1 = asymmetry
            shape_2 = parse_float_or_nan(row.get("shape_2"))
            if math.isnan(shape_2) and n_pts is not None:
                shape_2 = float(n_pts)

            rows_out.append(
                _build_row(
                    event_id=event_id,
                    name=name,
                    transient_class=transient_class,
                    source_catalog=source_catalog,
                    t_char_s=t_char_s,
                    omega_mode=omega_mode,
                    q_eff=q_eff,
                    chi_loss=chi_loss,
                    tail_strength=tail_strength,
                    tail_energy_proxy=tail_energy_proxy,
                    shape_1=shape_1,
                    shape_2=shape_2,
                    c_theta=c_theta,
                )
            )


def _append_supernova_event_rows(
    rows_out: list[dict[str, str]],
    events_path: Path,
    c_theta: float | None,
) -> None:
    """Append passport rows derived from supernova_transient_events.csv."""
    if not events_path.exists():
        return
    with events_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            event_id = (row.get("event_id") or "").strip() or "unknown"
            name = (row.get("name") or "").strip()
            transient_class = (row.get("type") or "").strip()

            t0_days = parse_float_or_nan(row.get("t0_days"))
            width_days = parse_float_or_nan(row.get("width_days"))
            width_norm = parse_float_or_nan(row.get("width_norm"))
            l_proxy = parse_float_or_nan(row.get("L_proxy"))
            event_strength = parse_float_or_nan(row.get("event_strength"))
            asymmetry = parse_float_or_nan(row.get("asymmetry"))
            points_raw = row.get("number_of_points")
            try:
                n_pts = int(float(points_raw)) if points_raw else None
            except (ValueError, TypeError):
                n_pts = None

            t_char_s = (
                t0_days * SECONDS_PER_DAY
                if not math.isnan(t0_days) and t0_days > 0
                else float("nan")
            )
            omega_mode = (
                TWO_PI / t_char_s
                if not math.isnan(t_char_s) and t_char_s > 0
                else float("nan")
            )

            q_eff = parse_float_or_nan(row.get("Q_eff"))
            if math.isnan(q_eff):
                if width_norm > 0:
                    q_eff = 1.0 / width_norm
                elif width_days > 0 and not math.isnan(t0_days) and t0_days > 0:
                    q_eff = t0_days / width_days

            chi_loss = (
                1.0 / (2.0 * q_eff)
                if not math.isnan(q_eff) and q_eff > 0
                else float("nan")
            )
            tail_strength = parse_float_or_nan(row.get("tail_strength"))
            if math.isnan(tail_strength):
                tail_strength = l_proxy
            tail_energy_proxy = parse_float_or_nan(row.get("tail_energy_proxy"))
            if math.isnan(tail_energy_proxy):
                tail_energy_proxy = event_strength
            shape_1 = parse_float_or_nan(row.get("shape_1"))
            if math.isnan(shape_1):
                shape_1 = asymmetry
            shape_2 = parse_float_or_nan(row.get("shape_2"))
            if math.isnan(shape_2) and n_pts is not None:
                shape_2 = float(n_pts)

            rows_out.append(
                _build_row(
                    event_id=event_id,
                    name=name,
                    transient_class=transient_class,
                    source_catalog="",
                    t_char_s=t_char_s,
                    omega_mode=omega_mode,
                    q_eff=q_eff,
                    chi_loss=chi_loss,
                    tail_strength=tail_strength,
                    tail_energy_proxy=tail_energy_proxy,
                    shape_1=shape_1,
                    shape_2=shape_2,
                    c_theta=c_theta,
                )
            )


def build_astrophysical_passport_rows(
    supernova_events_path: Path,
    astrophysical_events_path: Path,
    c_theta: float | None,
) -> list[dict[str, str]]:
    """Build astrophysical-domain passport rows from available event tables."""
    rows_out: list[dict[str, str]] = []
    _append_supernova_event_rows(rows_out, supernova_events_path, c_theta)
    _append_astrophysical_event_rows(rows_out, astrophysical_events_path, c_theta)
    return rows_out

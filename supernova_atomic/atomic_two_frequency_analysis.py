"""
Two-frequency atomic analysis and isotope validation helpers.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Final

from supernova_atomic.atomic_schema import parse_float_or_nan, write_csv

GROUP_COLUMNS: Final[list[str]] = [
    "element",
    "ion_stage",
    "line_count",
    "omega_theta_env",
    "kappa_theta_env_m_inv",
    "omega_l0_p10",
    "omega_l0_p50",
    "omega_l0_p90",
    "ratio_p10",
    "ratio_p50",
    "ratio_p90",
]
ISOTOPE_LINE_COLUMNS: Final[list[str]] = [
    "source_catalog",
    "element",
    "ion_stage",
    "isotope_mass",
    "wavelength_vac_nm",
    "frequency_hz",
    "isotope_shift_mA",
    "source_file",
]
ISOTOPE_ENV_COLUMNS: Final[list[str]] = [
    "source_catalog",
    "element",
    "ion_stage",
    "isotope_mass",
    "line_count",
    "omega_theta_env",
]
SIMILARITY_COLUMNS: Final[list[str]] = [
    "left_element",
    "right_element",
    "cosine_similarity",
]
HOMOLOGOUS_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("C", "Si"),
    ("N", "P"),
    ("O", "S"),
    ("Ne", "Ar"),
    ("Na", "K"),
    ("Mg", "Ca"),
)


def _serialize_float(value: float) -> str:
    """Serialize finite floats for CSV output."""
    return "" if not math.isfinite(value) else str(value)


def _percentile(values: list[float], fraction: float) -> float:
    """Return a simple linear-interpolated percentile for sorted positive values."""
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _geometric_median_scale(values: list[float]) -> float:
    """Return a robust positive carrier-scale proxy in omega-space."""
    positives = [value for value in values if value > 0.0 and math.isfinite(value)]
    if not positives:
        return float("nan")
    ordered_logs = sorted(math.log10(value) for value in positives)
    middle = len(ordered_logs) // 2
    if len(ordered_logs) % 2:
        median_log = float(ordered_logs[middle])
    else:
        median_log = float((ordered_logs[middle - 1] + ordered_logs[middle]) / 2.0)
    return float(10.0**median_log)


def _carrier_vector(row: dict[str, str]) -> list[float]:
    """Build a compact feature vector for two-frequency clustering/similarity."""
    features: list[float] = []
    for key in ("kappa_theta_env_m_inv", "ratio_p10", "ratio_p50", "ratio_p90"):
        value = parse_float_or_nan(row.get(key))
        if not math.isfinite(value) or value <= 0.0:
            return []
        features.append(math.log10(value))
    return features


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity for equal-length feature vectors."""
    if not left or not right or len(left) != len(right):
        return float("nan")
    numerator = sum(lv * rv for lv, rv in zip(left, right))
    left_norm = math.sqrt(sum(lv * lv for lv in left))
    right_norm = math.sqrt(sum(rv * rv for rv in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return float("nan")
    return numerator / (left_norm * right_norm)


def build_two_frequency_group_rows(passports_path: Path) -> list[dict[str, str]]:
    """Build one row per atomic carrier group from full passport data."""
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    c_theta_values: dict[tuple[str, str], float] = {}
    with passports_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("domain") or "").strip() != "atomic":
                continue
            if (row.get("passport_status") or "").strip() != "complete":
                continue
            element = (row.get("element") or "").strip()
            ion_stage = (row.get("ion_stage") or "").strip()
            omega_mode = parse_float_or_nan(row.get("omega_mode"))
            c_theta = parse_float_or_nan(row.get("c_theta"))
            if not element or not ion_stage or omega_mode <= 0.0:
                continue
            key = (element, ion_stage)
            grouped[key].append(omega_mode)
            if c_theta > 0.0 and key not in c_theta_values:
                c_theta_values[key] = c_theta

    rows: list[dict[str, str]] = []
    for key in sorted(grouped):
        omega_values = grouped[key]
        omega_env = _geometric_median_scale(omega_values)
        ratios = [
            omega / omega_env
            for omega in omega_values
            if omega > 0.0 and omega_env > 0.0 and math.isfinite(omega_env)
        ]
        c_theta = c_theta_values.get(key, float("nan"))
        kappa_env = omega_env / c_theta if c_theta > 0.0 else float("nan")
        rows.append(
            {
                "element": key[0],
                "ion_stage": key[1],
                "line_count": str(len(omega_values)),
                "omega_theta_env": _serialize_float(omega_env),
                "kappa_theta_env_m_inv": _serialize_float(kappa_env),
                "omega_l0_p10": _serialize_float(_percentile(omega_values, 0.10)),
                "omega_l0_p50": _serialize_float(_percentile(omega_values, 0.50)),
                "omega_l0_p90": _serialize_float(_percentile(omega_values, 0.90)),
                "ratio_p10": _serialize_float(_percentile(ratios, 0.10)),
                "ratio_p50": _serialize_float(_percentile(ratios, 0.50)),
                "ratio_p90": _serialize_float(_percentile(ratios, 0.90)),
            }
        )
    return rows


def build_similarity_rows(group_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Compare homologous neutral groups in the new two-frequency feature space."""
    lookup = {
        row["element"]: row
        for row in group_rows
        if row.get("ion_stage") == "I" and _carrier_vector(row)
    }
    rows: list[dict[str, str]] = []
    for left, right in HOMOLOGOUS_PAIRS:
        if left not in lookup or right not in lookup:
            continue
        similarity = _cosine_similarity(
            _carrier_vector(lookup[left]),
            _carrier_vector(lookup[right]),
        )
        rows.append(
            {
                "left_element": left,
                "right_element": right,
                "cosine_similarity": _serialize_float(similarity),
            }
        )
    return rows


def write_two_frequency_outputs(
    root: Path,
    group_rows: list[dict[str, str]],
    isotope_line_rows: list[dict[str, str]],
    isotope_env_rows: list[dict[str, str]],
    similarity_rows: list[dict[str, str]],
) -> None:
    """Write all derived two-frequency data artifacts."""
    data_dir = root / "data"
    report_dir = root / "report"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        data_dir / "atomic_two_frequency_group_summary.csv", GROUP_COLUMNS, group_rows
    )
    write_csv(
        data_dir / "atomic_isotope_lines_clean.csv",
        ISOTOPE_LINE_COLUMNS,
        isotope_line_rows,
    )
    write_csv(
        data_dir / "atomic_isotope_envelope_summary.csv",
        ISOTOPE_ENV_COLUMNS,
        isotope_env_rows,
    )
    write_csv(
        data_dir / "atomic_two_frequency_similarity.csv",
        SIMILARITY_COLUMNS,
        similarity_rows,
    )
    _write_report(
        report_dir / "atomic_two_frequency_report.md",
        group_rows,
        isotope_env_rows,
        similarity_rows,
    )


def _write_report(
    path: Path,
    group_rows: list[dict[str, str]],
    isotope_env_rows: list[dict[str, str]],
    similarity_rows: list[dict[str, str]],
) -> None:
    """Write a concise markdown report with numerical outputs."""
    neutral_groups = [row for row in group_rows if row.get("ion_stage") == "I"]
    best_similarity = max(
        (parse_float_or_nan(row["cosine_similarity"]) for row in similarity_rows),
        default=float("nan"),
    )
    isotope_families = defaultdict(list)
    for row in isotope_env_rows:
        isotope_families[(row["element"], row["ion_stage"])].append(row)
    lines = [
        "# Atomic Two-Frequency Report",
        "",
        "Author: Vasiliy Zdanovskiy  ",
        "email: vasilyvz@gmail.com",
        "",
        "## Summary",
        "",
        f"- Carrier groups analysed: {len(group_rows)}.",
        f"- Neutral carrier groups analysed: {len(neutral_groups)}.",
        f"- Isotope-resolved envelope rows: {len(isotope_env_rows)}.",
        f"- Homologous neutral pair comparisons: {len(similarity_rows)}.",
        f"- Best homologous cosine similarity: {_serialize_float(best_similarity)}.",
        "",
        "## Isotope families",
        "",
    ]
    for family in sorted(isotope_families):
        isotopes = sorted(
            isotope_families[family],
            key=lambda row: int(row["isotope_mass"]),
        )
        masses = ", ".join(row["isotope_mass"] for row in isotopes)
        lines.append(f"- {family[0]} {family[1]}: isotopes {masses}.")
    lines.append("")
    lines.append(
        "Two-frequency mode is operationalized as carrier envelope "
        "`omega_theta_env` plus the observable `L0` transition spectrum."
    )
    path.write_text("\n".join(lines), encoding="utf-8")

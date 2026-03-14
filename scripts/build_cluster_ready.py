"""
Build cluster_ready_events.csv from atomic and supernova event tables.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Third tech spec: reads atomic_transition_events.csv and supernova_transient_events.csv;
builds unified table with event_id, domain, logE, logt, logQ_or_width, shape_1, shape_2,
class_hint; only rows with finite log-values. Run: python scripts/build_cluster_ready.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from supernova_atomic.third_spec_schema import (
    CLASS_HINT_ATOMIC,
    CLASS_HINT_SUPERNOVA,
    CLUSTER_READY_EVENTS_COLUMNS,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def _float(s: str | None) -> float | None:
    """Parse string to float; return None for empty or non-numeric."""
    if s is None or str(s).strip() in ("", "nan", "NaN"):
        return None
    try:
        v = float(str(s).strip())
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def _safe_log(x: float | None) -> float | None:
    """log10(x) if x is finite and > 0; else None."""
    if x is None or not math.isfinite(x) or x <= 0:
        return None
    try:
        return math.log10(x)
    except (ValueError, ZeroDivisionError):
        return None


def main() -> None:
    """Build cluster_ready_events.csv from both event CSVs."""
    root = project_root()
    data_dir = root / "data"
    atomic_path = data_dir / "atomic_transition_events.csv"
    supernova_path = data_dir / "supernova_transient_events.csv"
    output_path = data_dir / "cluster_ready_events.csv"

    rows_out: list[dict[str, str]] = []

    if atomic_path.exists():
        with atomic_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                transition_id = (row.get("transition_id") or "").strip()
                deltaE = _float(row.get("deltaE_eV"))
                tau_s = _float(row.get("tau_s"))
                Q = _float(row.get("Q_proxy"))
                deltaJ = row.get("deltaJ", "").strip()
                parity_change = row.get("parity_change", "").strip()
                logE = _safe_log(deltaE)
                logt = _safe_log(tau_s)
                logQ = _safe_log(Q)
                if logE is None or logt is None or logQ is None:
                    continue
                try:
                    shape_1 = (
                        str(float(deltaJ))
                        if deltaJ and deltaJ not in ("", "nan")
                        else ""
                    )
                except (ValueError, TypeError):
                    shape_1 = ""
                rows_out.append(
                    {
                        "event_id": transition_id,
                        "domain": "atomic",
                        "logE": str(logE),
                        "logt": str(logt),
                        "logQ_or_width": str(logQ),
                        "shape_1": shape_1,
                        "shape_2": parity_change if parity_change else "",
                        "class_hint": CLASS_HINT_ATOMIC,
                    }
                )

    if supernova_path.exists():
        with supernova_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                event_id = (row.get("event_id") or row.get("name") or "").strip()
                L_proxy = _float(row.get("L_proxy"))
                t0_days = _float(row.get("t0_days"))
                width_norm = _float(row.get("width_norm"))
                width_days = _float(row.get("width_days"))
                asymmetry = row.get("asymmetry", "").strip()
                n_pts = row.get("number_of_points", "").strip()
                logE = _safe_log(L_proxy)
                logt = _safe_log(t0_days)
                logQ_or_w = (
                    _safe_log(width_norm)
                    if width_norm is not None
                    else _safe_log(width_days)
                )
                if logE is None or logt is None:
                    continue
                rows_out.append(
                    {
                        "event_id": event_id,
                        "domain": "supernova",
                        "logE": str(logE),
                        "logt": str(logt),
                        "logQ_or_width": (
                            str(logQ_or_w) if logQ_or_w is not None else ""
                        ),
                        "shape_1": asymmetry if asymmetry else "",
                        "shape_2": n_pts if n_pts else "",
                        "class_hint": CLASS_HINT_SUPERNOVA,
                    }
                )

    data_dir.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CLUSTER_READY_EVENTS_COLUMNS)
        w.writeheader()
        w.writerows(rows_out)


if __name__ == "__main__":
    main()

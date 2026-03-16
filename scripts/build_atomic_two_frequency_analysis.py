"""
Build the atomic two-frequency analysis outputs and report.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import sys
from pathlib import Path

from supernova_atomic.atomic_isotope_parsing import (
    build_isotope_envelope_rows,
    build_isotope_line_rows,
)
from supernova_atomic.atomic_two_frequency_analysis import (
    build_similarity_rows,
    build_two_frequency_group_rows,
    write_two_frequency_outputs,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def main() -> int:
    """Build two-frequency atomic outputs from passport and isotope raw data."""
    root = project_root()
    passports_path = root / "data" / "atomic_transition_passports.csv"
    if not passports_path.exists():
        print("Missing data/atomic_transition_passports.csv", file=sys.stderr)
        return 1
    group_rows = build_two_frequency_group_rows(passports_path)
    isotope_line_rows = build_isotope_line_rows(root)
    isotope_env_rows = build_isotope_envelope_rows(isotope_line_rows)
    similarity_rows = build_similarity_rows(group_rows)
    write_two_frequency_outputs(
        root=root,
        group_rows=group_rows,
        isotope_line_rows=isotope_line_rows,
        isotope_env_rows=isotope_env_rows,
        similarity_rows=similarity_rows,
    )
    print("Built atomic two-frequency outputs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

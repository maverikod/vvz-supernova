"""
Ensure pipeline directories exist (raw, data, plots). Idempotent.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Run: python scripts/ensure_dirs.py
Creates from project root: raw/atomic_lines_raw/, raw/supernova_raw/,
data/, plots/.
"""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def main() -> None:
    """Create pipeline dirs if missing; no overwrite of existing files."""
    root = project_root()
    dirs = [
        root / "raw" / "atomic_lines_raw",
        root / "raw" / "supernova_raw",
        root / "data",
        root / "plots",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()

"""
Download open isotope-resolved atomic spectroscopy artifacts.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import sys
from pathlib import Path

from supernova_atomic.atomic_isotope_download import (
    download_atomic_isotope_data,
    isotope_raw_dir,
)


def project_root() -> Path:
    """Return project root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def main() -> int:
    """Download isotope artifacts and print their raw directory."""
    root = project_root()
    raw_dir = download_atomic_isotope_data(root)
    manifest_path = isotope_raw_dir(root) / "manifest.json"
    print(f"Downloaded isotope artifacts into: {raw_dir}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

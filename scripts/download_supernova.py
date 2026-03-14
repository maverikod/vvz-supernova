"""
Wrapper: run download_supernova_data.py (Third tech spec script name).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Do not rename existing scripts; this wrapper satisfies spec name download_supernova.py.
Run: python scripts/download_supernova.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Invoke scripts/download_supernova_data.py; return its exit code."""
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts" / "download_supernova_data.py"
    result = subprocess.run([sys.executable, str(script)], cwd=str(root))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

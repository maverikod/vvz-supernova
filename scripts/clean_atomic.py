"""
Wrapper: run clean_atomic_data.py then build_atomic_transition_events.py.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Third tech spec: clean_atomic.py. Do not rename existing scripts.
Run: python scripts/clean_atomic.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run clean_atomic_data then build_atomic_transition_events; return exit code."""
    root = Path(__file__).resolve().parent.parent
    scripts_dir = root / "scripts"
    r1 = subprocess.run(
        [sys.executable, str(scripts_dir / "clean_atomic_data.py")], cwd=str(root)
    )
    if r1.returncode != 0:
        return r1.returncode
    build_script = scripts_dir / "build_atomic_transition_events.py"
    r2 = subprocess.run([sys.executable, str(build_script)], cwd=str(root))
    return r2.returncode


if __name__ == "__main__":
    sys.exit(main())

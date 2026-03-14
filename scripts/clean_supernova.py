"""
Wrapper: clean_supernova_data, build_event_summaries, build_supernova_transient_events.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Third tech spec: clean_supernova.py. Run: python scripts/clean_supernova.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run clean_supernova_data, build_event_summaries build_supernova_transient_evts"""
    root = Path(__file__).resolve().parent.parent
    scripts_dir = root / "scripts"
    for name in (
        "clean_supernova_data.py",
        "build_event_summaries.py",
        "build_supernova_transient_events.py",
    ):
        r = subprocess.run([sys.executable, str(scripts_dir / name)], cwd=str(root))
        if r.returncode != 0:
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())

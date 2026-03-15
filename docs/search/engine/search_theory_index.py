#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Theory index/search tool (stable CLI entrypoint).

Lives under project docs/search/engine/. Implementation in engine/theory_index/.
All paths are relative to docs/search (search root). Default DB directory: db/.

Usage (from project root):
    python docs/search/engine/search_theory_index.py --mode sqlite_search --phrase "..."
    python docs/search/engine/search_theory_index.py --help
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_import_path() -> None:
    """Ensure engine/ is on sys.path so theory_index package can be imported."""
    base = Path(__file__).resolve().parent
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))


def main() -> int:
    """
    Stable CLI entrypoint for the theory index/search tool.

    Sets THEORY_SEARCH_ROOT to the search engine root (parent of engine/),
    ensures engine/ is on sys.path so theory_index can be imported,
    then delegates to theory_index.cli.main() for argument parsing and execution.

    Returns:
        Exit code from the underlying CLI (0 on success, non-zero on error).

    Public invocation (unchanged):
        python docs/search/engine/search_theory_index.py --mode ...
    """
    search_root = Path(__file__).resolve().parent.parent
    os.environ["THEORY_SEARCH_ROOT"] = str(search_root)
    _bootstrap_import_path()
    from theory_index.cli import main as impl_main

    return impl_main()


if __name__ == "__main__":
    raise SystemExit(main())

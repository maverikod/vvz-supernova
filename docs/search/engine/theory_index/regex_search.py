"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Regex search functionality for SQLite database.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


def regex_search_one(
    db_path: Path,
    pattern: str,
    scope: str,
    category: Optional[str],
    tag: Optional[str],
) -> List[Dict[str, str]]:
    """
    Search using regular expression.

    Args:
        db_path: Path to SQLite database
        pattern: Regular expression pattern
        scope: Search scope (segments or formulas)
        category: Optional category filter
        tag: Optional tag filter

    Returns:
        List of matching results with source_db and part_id fields
    """
    try:
        regex = re.compile(pattern, re.IGNORECASE | re.UNICODE)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e

    # Extract part_id from chain.partXXX.sqlite pattern
    part_id: Optional[str] = None
    chain_match = re.search(r"chain\.part(\d+)\.sqlite$", db_path.name, re.IGNORECASE)
    if chain_match:
        part_id = chain_match.group(1)

    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
    except Exception:
        # Fail-soft: return empty results
        return []

    results: List[Dict[str, str]] = []

    if scope == "formulas":
        # Get all formulas and filter by regex
        rows = cur.execute("SELECT segment_id, text FROM formulas LIMIT 500").fetchall()
        for seg_id, text in rows:
            if regex.search(text or ""):
                result = {
                    "id": str(seg_id),
                    "formula": str(text),
                    "db": db_path.name,
                    "source_db": str(db_path),
                }
                if part_id:
                    result["part_id"] = part_id
                results.append(result)
            if len(results) >= 200:  # Limit results per DB
                break
    else:
        # Get all segments and filter by regex
        rows = cur.execute(
            "SELECT id, category, summary, text FROM segments LIMIT 500"
        ).fetchall()
        for seg_id, cat, summary, text in rows:
            sid = str(seg_id)
            if tag and tag.lower() not in sid.lower():
                continue
            if category and category.lower() not in (str(cat) or "").lower():
                continue
            # Check if regex matches text or summary
            full_text = f"{summary or ''} {text or ''}"
            if regex.search(full_text):
                result = {
                    "id": sid,
                    "category": str(cat or ""),
                    "summary": str(summary or ""),
                    "snippet": str(text or "")[:2000],
                    "db": db_path.name,
                    "source_db": str(db_path),
                }
                if part_id:
                    result["part_id"] = part_id
                results.append(result)
            if len(results) >= 200:  # Limit results per DB
                break

    conn.close()
    return results

"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

SQLite schema and low-level insert helpers for the theory block database.

This module is shared by both single-file and sharded SQLite builds.
"""

from __future__ import annotations

import sqlite3
import sys
from typing import List, Sequence, Tuple


def create_schema(cur: sqlite3.Cursor) -> Tuple[bool, bool]:
    """
    Create the database schema.

    Returns:
        (has_fts_segments, has_fts_formulas)
    """

    cur.executescript("""
        CREATE TABLE meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE segments (
            id         TEXT PRIMARY KEY,
            category   TEXT,
            summary    TEXT,
            start_line INTEGER,
            end_line   INTEGER,
            text       TEXT
        );
        CREATE TABLE keywords (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_id TEXT,
            keyword    TEXT
        );
        CREATE TABLE formulas (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_id TEXT,
            line       INTEGER,
            text       TEXT
        );

        CREATE INDEX idx_segments_category ON segments(category);
        CREATE INDEX idx_keywords_keyword  ON keywords(keyword);
        CREATE INDEX idx_keywords_segment  ON keywords(segment_id);
        CREATE INDEX idx_formulas_segment  ON formulas(segment_id);
        """)

    has_fts_segments = False
    has_fts_formulas = False
    try:
        cur.execute(
            "CREATE VIRTUAL TABLE segments_fts USING fts5(id, category, summary, text)"
        )
        has_fts_segments = True
    except Exception:
        print(
            "WARNING: FTS5 not available for segments_fts – "
            "fulltext will fallback to LIKE.",
            file=sys.stderr,
        )
    try:
        cur.execute("CREATE VIRTUAL TABLE formulas_fts USING fts5(segment_id, text)")
        has_fts_formulas = True
    except Exception:
        print(
            "WARNING: FTS5 not available for formulas_fts – "
            "fulltext on formulas will fallback to LIKE.",
            file=sys.stderr,
        )
    return has_fts_segments, has_fts_formulas


def compute_block_text(
    seg_ranges: Sequence[Tuple[int, int]],
    lines: Sequence[str],
) -> str:
    n_lines = len(lines)
    text_parts: List[str] = []
    for s, e in seg_ranges:
        s1 = max(1, int(s))
        e1 = min(n_lines, int(e))
        for ln in range(s1, e1 + 1):
            text_parts.append(lines[ln - 1])
    return "".join(text_parts)


def insert_segment(
    cur: sqlite3.Cursor,
    seg_id: str,
    category: str,
    summary: str,
    start_line: int,
    end_line: int,
    block_text: str,
    keywords: Sequence[str],
    seg_ranges: Sequence[Tuple[int, int]],
    lines: Sequence[str],
    has_fts_segments: bool,
    has_fts_formulas: bool,
) -> None:
    cur.execute(
        "INSERT OR REPLACE INTO segments("
        "id, category, summary, start_line, end_line, text"
        ") VALUES (?, ?, ?, ?, ?, ?)",
        (seg_id, category, summary, start_line, end_line, block_text),
    )

    for kw in keywords or []:
        cur.execute(
            "INSERT INTO keywords(segment_id, keyword) VALUES (?, ?)",
            (seg_id, str(kw)),
        )

    n_lines = len(lines)
    for s, e in seg_ranges:
        s1 = max(1, int(s))
        e1 = min(n_lines, int(e))
        for ln in range(s1, e1 + 1):
            text_line = lines[ln - 1]
            if not any(tok in text_line for tok in ("$", "\\(", "\\[")):
                continue
            text_clean = text_line.rstrip("\n")
            cur.execute(
                "INSERT INTO formulas(segment_id, line, text) VALUES (?, ?, ?)",
                (seg_id, ln, text_clean),
            )
            if has_fts_formulas:
                cur.execute(
                    "INSERT INTO formulas_fts(segment_id, text) VALUES (?, ?)",
                    (seg_id, text_clean),
                )

    if has_fts_segments:
        cur.execute(
            "INSERT INTO segments_fts(id, category, summary, text) VALUES (?, ?, ?, ?)",
            (seg_id, category, summary, block_text),
        )


def estimate_segment_bytes(block_text: str, keywords: Sequence[str]) -> int:
    """
    Rough estimate for sharding decisions.

    This is intentionally conservative and used only for initial grouping;
    final size is checked using the actual SQLite file size on disk.
    """

    base = len(block_text.encode("utf-8"))
    kw = sum(len(str(k).encode("utf-8")) for k in keywords or [])
    return int((base + kw) * 1.20) + 4096

"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

SQLite chain validation and export helpers.

Goals:
- Validate that the SQLite chain contains all segment ids from ALL_index.yaml.
- Export a segment block from the SQLite chain into a markdown file, allowing
  recovery of a `7d-XXX*.md`-style block from the DB alone.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .index_data import IndexData
from .index_io import resolve_db_paths


def _list_segment_ids(db_path: Path) -> Set[str]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    try:
        rows = cur.execute("SELECT id FROM segments").fetchall()
    finally:
        conn.close()
    return {str(r[0]) for r in rows}


def mode_sqlite_validate_chain(
    idx: IndexData,
    db_path: str,
    fmt: str,
) -> int:
    if not db_path:
        print("ERROR: --db-path is required for sqlite_validate mode.", file=sys.stderr)
        return 1

    dbs = resolve_db_paths(db_path, None)
    if not dbs:
        print(f"ERROR: no sqlite db files resolved from: {db_path}", file=sys.stderr)
        return 1

    index_ids = {seg.id for seg in idx.segments if seg.id}
    db_ids: Set[str] = set()
    per_db_counts: List[Tuple[str, int]] = []
    for db in dbs:
        ids = _list_segment_ids(db)
        db_ids |= ids
        per_db_counts.append((db.name, len(ids)))

    missing = sorted(index_ids - db_ids)
    extra = sorted(db_ids - index_ids)

    payload: Dict[str, object] = {
        "db_files": [p.name for p in dbs],
        "db_segment_counts": [{"db": n, "segments": c} for n, c in per_db_counts],
        "index_segments": len(index_ids),
        "db_segments_union": len(db_ids),
        "missing_ids": missing,
        "extra_ids": extra,
    }

    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"DB files: {len(dbs)}")
        for n, c in per_db_counts:
            print(f"  - {n}: {c} segments")
        print(f"Index segments: {len(index_ids)}")
        print(f"DB segments (union): {len(db_ids)}")
        print(f"Missing ids: {len(missing)}")
        for m in missing[:100]:
            print("  -", m)
        if len(missing) > 100:
            print("  ... (truncated)")
        print(f"Extra ids: {len(extra)}")
        for e in extra[:100]:
            print("  -", e)
        if len(extra) > 100:
            print("  ... (truncated)")

    # Non-zero exit if missing exist
    return 2 if missing else 0


def _fetch_segment_text(db_path: Path, seg_id: str) -> Optional[str]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    try:
        row = cur.execute("SELECT text FROM segments WHERE id=?", (seg_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return str(row[0] or "")


def mode_sqlite_export_segment(
    db_path: str,
    seg_id: str,
    out_path: str,
) -> int:
    if not db_path:
        print(
            "ERROR: --db-path is required for sqlite_export_segment mode.",
            file=sys.stderr,
        )
        return 1
    if not seg_id:
        print(
            "ERROR: --segment-id is required for sqlite_export_segment mode.",
            file=sys.stderr,
        )
        return 1
    if not out_path:
        print(
            "ERROR: --output-path is required for sqlite_export_segment mode.",
            file=sys.stderr,
        )
        return 1

    dbs = resolve_db_paths(db_path, None)
    if not dbs:
        print(f"ERROR: no sqlite db files resolved from: {db_path}", file=sys.stderr)
        return 1

    text: Optional[str] = None
    src_db: Optional[str] = None
    for db in dbs:
        text = _fetch_segment_text(db, seg_id)
        if text is not None:
            src_db = db.name
            break

    if text is None:
        print(f"ERROR: segment not found in db chain: {seg_id}", file=sys.stderr)
        return 2

    out = Path(out_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    out.write_text(text, encoding="utf-8")
    print(f"[OK] Exported {seg_id} from {src_db} → {out}")
    return 0

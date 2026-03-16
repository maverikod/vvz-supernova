"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

SQLite build modes for the theory blocks index.

Supports:
- sqlite_build: build a single database.
- sqlite_build_chain: build a chain (shards) with max size limit per db file.

Important:
    Sharding is performed at segment granularity: a segment is never split.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .index_data import IndexData
from .sqlite_schema import (
    compute_block_text,
    create_schema,
    estimate_segment_bytes,
    insert_segment,
)


def mode_build_sqlite(idx: IndexData, lines: Optional[List[str]], db_path: str) -> int:
    if lines is None:
        print("ERROR: --theory is required for sqlite_build mode.", file=sys.stderr)
        return 1
    if not db_path:
        print("ERROR: --db-path is required for sqlite_build mode.", file=sys.stderr)
        return 1

    p = Path(db_path).resolve()
    if p.exists():
        p.unlink()

    conn = sqlite3.connect(str(p))
    cur = conn.cursor()
    has_fts_segments, has_fts_formulas = create_schema(cur)

    for seg in idx.segments:
        block_text = compute_block_text(seg.ranges, lines)
        insert_segment(
            cur=cur,
            seg_id=seg.id,
            category=seg.category,
            summary=seg.summary,
            start_line=seg.start_line,
            end_line=seg.end_line,
            block_text=block_text,
            keywords=seg.keywords or [],
            seg_ranges=seg.ranges,
            lines=lines,
            has_fts_segments=has_fts_segments,
            has_fts_formulas=has_fts_formulas,
        )

    cur.execute("INSERT INTO meta(key, value) VALUES (?, ?)", ("shard_index", "1"))
    cur.execute("INSERT INTO meta(key, value) VALUES (?, ?)", ("shard_count", "1"))
    conn.commit()
    conn.close()

    print(f"SQLite index written to {p}")
    return 0


def _build_shard(
    idx: IndexData,
    lines: Sequence[str],
    seg_indices: List[int],
    out_path: Path,
    shard_index: int,
    shard_count: Optional[int],
) -> None:
    if out_path.exists():
        out_path.unlink()
    conn = sqlite3.connect(str(out_path))
    cur = conn.cursor()
    has_fts_segments, has_fts_formulas = create_schema(cur)

    segs = idx.segments
    for i in seg_indices:
        seg = segs[i]
        block_text = compute_block_text(seg.ranges, lines)
        insert_segment(
            cur=cur,
            seg_id=seg.id,
            category=seg.category,
            summary=seg.summary,
            start_line=seg.start_line,
            end_line=seg.end_line,
            block_text=block_text,
            keywords=seg.keywords or [],
            seg_ranges=seg.ranges,
            lines=lines,
            has_fts_segments=has_fts_segments,
            has_fts_formulas=has_fts_formulas,
        )

    cur.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?)",
        ("shard_index", str(shard_index)),
    )
    if shard_count is not None:
        cur.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("shard_count", str(shard_count)),
        )

    conn.commit()
    conn.close()


def _fit_shard_by_size(
    idx: IndexData,
    lines: Sequence[str],
    seg_indices: List[int],
    out_path: Path,
    shard_index: int,
    max_db_bytes: int,
) -> Tuple[Path, List[int], List[int]]:
    """
    Build shard and ensure it fits into max_db_bytes by moving tail segments out.

    Returns:
        (db_path, accepted_indices, moved_to_next_indices)
    """

    accepted = list(seg_indices)
    moved: List[int] = []
    tmp_path = out_path.with_suffix(".tmp.sqlite")

    while True:
        _build_shard(idx, lines, accepted, tmp_path, shard_index, shard_count=None)
        size = tmp_path.stat().st_size
        if size <= max_db_bytes:
            if out_path.exists():
                out_path.unlink()
            tmp_path.rename(out_path)
            return out_path, accepted, moved
        if len(accepted) <= 1:
            print(
                f"[WARN] SQLite shard exceeds limit but contains a single segment. "
                f"Keeping it: {out_path.name} size={size} limit={max_db_bytes}",
                file=sys.stderr,
            )
            if out_path.exists():
                out_path.unlink()
            tmp_path.rename(out_path)
            return out_path, accepted, moved

        # Move one segment from the tail into the next shard.
        tail = accepted.pop()
        moved.insert(0, tail)
        try:
            tmp_path.unlink()
        except Exception:
            pass


def mode_build_sqlite_chain(
    idx: IndexData,
    lines: Optional[List[str]],
    manifest_path: str,
    max_db_bytes: int,
) -> int:
    if lines is None:
        print(
            "ERROR: --theory is required for sqlite_build_chain mode.", file=sys.stderr
        )
        return 1
    if not manifest_path:
        print(
            "ERROR: --db-path is required for sqlite_build_chain mode.", file=sys.stderr
        )
        return 1
    if max_db_bytes <= 0:
        print("ERROR: --max-db-bytes must be > 0", file=sys.stderr)
        return 1

    manifest = Path(manifest_path).resolve()
    base_dir = manifest.parent
    base_stem = manifest.stem

    # Initial greedy grouping by rough estimates
    segs = idx.segments
    estimates: List[int] = []
    for seg in segs:
        block_text = compute_block_text(seg.ranges, lines)
        estimates.append(estimate_segment_bytes(block_text, seg.keywords or []))

    safety = 0.85
    groups: List[List[int]] = []
    cur_group: List[int] = []
    cur_est = 0
    for i, est in enumerate(estimates):
        if cur_group and (cur_est + est) > int(max_db_bytes * safety):
            groups.append(cur_group)
            cur_group = []
            cur_est = 0
        cur_group.append(i)
        cur_est += est
    if cur_group:
        groups.append(cur_group)

    db_files: List[Path] = []
    carry: List[int] = []
    shard_index = 1

    for g in groups:
        seg_indices = carry + g
        carry = []
        db_name = f"{base_stem}.part{shard_index:03d}.sqlite"
        db_path = base_dir / db_name
        built, accepted, moved = _fit_shard_by_size(
            idx=idx,
            lines=lines,
            seg_indices=seg_indices,
            out_path=db_path,
            shard_index=shard_index,
            max_db_bytes=max_db_bytes,
        )
        db_files.append(built)
        carry = moved
        shard_index += 1

    # If leftover segments were pushed out of the last shard, keep building
    # until all segments are placed (never drop `moved`).
    while carry:
        db_name = f"{base_stem}.part{shard_index:03d}.sqlite"
        db_path = base_dir / db_name
        built, _, moved = _fit_shard_by_size(
            idx=idx,
            lines=lines,
            seg_indices=carry,
            out_path=db_path,
            shard_index=shard_index,
            max_db_bytes=max_db_bytes,
        )
        db_files.append(built)
        carry = moved
        shard_index += 1

    shard_count = len(db_files)
    # Update shard_count meta for each db
    for i, db in enumerate(db_files, start=1):
        conn = sqlite3.connect(str(db))
        cur2 = conn.cursor()
        cur2.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("shard_count", str(shard_count)),
        )
        conn.commit()
        conn.close()

    manifest.write_text("\n".join([p.name for p in db_files]) + "\n", encoding="utf-8")
    print(f"[OK] SQLite chain written: {shard_count} file(s)")
    print(f"[OK] Manifest → {manifest}")
    return 0

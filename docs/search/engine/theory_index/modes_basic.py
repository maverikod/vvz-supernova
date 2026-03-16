"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Basic modes: search/stats/tree/help.
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import Dict, List, Optional, Sequence

from .index_data import IndexData
from .index_io import segment_to_dict
from .segment import Segment


def mode_help() -> int:
    print(
        "Index manager help\n"
        "  --mode search|assemble|stats|validate|tree|sqlite_build|"
        "sqlite_build_chain|sqlite_search|help\n"
        "  --index ALL_index.yaml (required)\n"
        "  --theory All.md OR manifest.txt "
        "(for search/assemble/validate/sqlite_build)\n"
        "  --tag / --category / --phrase – filters\n"
        "  --preset earth|sun|particles – quick presets\n"
        "  --output-path path.md – for assemble\n"
        "  --db-path path.sqlite OR manifest.txt OR dir/ – for sqlite_* modes\n"
        "  --max-db-bytes N – for sqlite_build_chain\n"
        "  --format text|json – output format"
    )
    return 0


def _matches_phrase(
    seg: Segment,
    phrase: Optional[str],
    lines: Optional[Sequence[str]],
    cache: Dict[str, str],
) -> bool:
    if not phrase:
        return True
    if seg.id not in cache:
        text_parts = [str(kw) for kw in (seg.keywords or [])] + [str(seg.summary)]
        if lines is not None:
            for s, e in seg.ranges:
                s0 = max(0, s - 1)
                e0 = min(len(lines), e)
                text_parts.append("".join(lines[s0:e0]))
        cache[seg.id] = " ".join(text_parts).lower()
    return phrase.lower() in cache[seg.id]


def mode_search(
    idx: IndexData,
    lines: Optional[List[str]],
    tag: Optional[str],
    category: Optional[str],
    phrase: Optional[str],
    fmt: str,
) -> int:
    cache: Dict[str, str] = {}
    matched: List[Segment] = []

    for seg in idx.segments:
        if tag and tag.lower() not in seg.id.lower():
            continue
        if category and category.lower() not in seg.category.lower():
            continue
        if not _matches_phrase(seg, phrase, lines, cache):
            continue
        matched.append(seg)

    if fmt == "json":
        import json

        out = [segment_to_dict(s) for s in matched]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if not matched:
            print("No segments matched filters.", file=sys.stderr)
        for s in matched:
            print(s.id, s.category, s.start_line, s.end_line)
    return 0


def mode_stats(idx: IndexData, fmt: str) -> int:
    n = len(idx.segments)
    cats = Counter([s.category for s in idx.segments])
    if fmt == "json":
        import json

        payload = {
            "segments": n,
            "categories": dict(cats),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Segments:", n)
        print("Top categories:")
        for cat, cnt in cats.most_common(30):
            print(f"  {cnt:5d}  {cat}")
    return 0


def mode_tree(idx: IndexData, fmt: str) -> int:
    by_cat: Dict[str, List[Segment]] = {}
    for seg in idx.segments:
        by_cat.setdefault(seg.category or "<none>", []).append(seg)

    if fmt == "json":
        import json

        payload = {
            cat: [segment_to_dict(s) for s in sorted(segs, key=lambda s: s.start_line)]
            for cat, segs in by_cat.items()
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for cat in sorted(by_cat.keys()):
            segs = sorted(by_cat[cat], key=lambda s: s.start_line)
            print(f"[{cat}] ({len(segs)} segments)")
            for s in segs:
                print(f"  - {s.id} [{s.start_line}-{s.end_line}]")
            print()
    return 0

"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Segment model for the 7D theory index.

Segments are addressed by their canonical id (e.g., `7d-113`, `7d-14-12`) and
point to one or more line ranges inside the aggregated theory text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class Segment:
    """
    A single indexed segment of the theory corpus.

    Notes:
        A segment may consist of multiple ranges if it appears multiple times
        in the aggregated document (e.g., duplicate ids).
    """

    id: str
    category: str
    keywords: List[str]
    summary: str
    start_line: int
    end_line: int
    ranges: List[Tuple[int, int]]
    raw: Dict[str, Any]

    @property
    def length(self) -> int:
        return max(0, self.end_line - self.start_line + 1)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Segment":
        seg_id = str(d.get("id", ""))
        category = str(d.get("category", ""))
        keywords = list(d.get("keywords") or [])
        summary = str(d.get("summary", ""))

        ranges: List[Tuple[int, int]] = []
        if isinstance(d.get("ranges"), list):
            for r in d["ranges"]:
                try:
                    if isinstance(r, dict):
                        ranges.append((int(r["start_line"]), int(r["end_line"])))
                    else:
                        ranges.append((int(r[0]), int(r[1])))
                except Exception:
                    continue

        if not ranges:
            try:
                ranges.append((int(d["start_line"]), int(d["end_line"])))
            except Exception:
                ranges.append((0, 0))

        start = min(a for a, _ in ranges)
        end = max(b for _, b in ranges)
        return cls(seg_id, category, keywords, summary, start, end, ranges, d)

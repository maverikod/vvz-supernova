"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Result grouping functionality for search results.
"""

from __future__ import annotations

from typing import Dict, List


def group_results(
    results: List[Dict[str, str]],
    group_by: str,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Group results by specified field.

    Args:
        results: List of result dictionaries
        group_by: Field to group by (category, id, db)

    Returns:
        Dictionary mapping group keys to lists of results
    """
    grouped: Dict[str, List[Dict[str, str]]] = {}

    for r in results:
        key = ""
        if group_by == "category":
            key = str(r.get("category", "uncategorized"))
        elif group_by == "db":
            key = str(r.get("db", "unknown"))
        elif group_by == "id":
            # Group by segment ID prefix (e.g., "7d-10" from "7d-105")
            seg_id = str(r.get("id", ""))
            if "-" in seg_id:
                key = seg_id.split("-")[0] + "-" + seg_id.split("-")[1][:2]
            else:
                key = seg_id[:5] if len(seg_id) > 5 else seg_id
        else:
            key = "all"

        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)

    return grouped


def format_grouped_results(
    grouped: Dict[str, List[Dict[str, str]]],
    phrases: List[str],
    scope: str,
    summary_only: bool = False,
    highlight: bool = False,
) -> None:
    """
    Format and print grouped results.

    Args:
        grouped: Dictionary of grouped results
        phrases: Phrases for highlighting
        scope: Search scope
        summary_only: If True, show only summaries
        highlight: If True, highlight phrases
    """
    from .result_formatter import format_search_result

    for group_key in sorted(grouped.keys()):
        group_results = grouped[group_key]
        print(f"\n=== {group_key} ({len(group_results)} results) ===")
        for r in group_results:
            if scope == "segments":
                output = format_search_result(r, phrases, summary_only, highlight, 0)
                print(output)
            else:
                seg_id = r.get("id", "")
                db = r.get("db", "")
                formula = r.get("formula", "")
                print(f"[{seg_id}] ({db}) :: {formula}")

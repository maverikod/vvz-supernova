"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Query executor for logical operators in search results.
"""

from __future__ import annotations

from typing import Dict, List, Set, cast

from .query_parser import QueryNode


def execute_query(
    query_node: QueryNode,
    term_results: Dict[str, List[Dict[str, str]]],
) -> List[Dict[str, str]]:
    """
    Execute query tree on term results.

    AND and OR behave as set intersection and union over result IDs.
    NOT is intentionally fail-soft and context-limited: with no document set
    to subtract from, NOT returns no results; "A NOT B" would require
    AND(NOT(B), A) or dedicated semantics—not implemented here.

    Args:
        query_node: Root of query parse tree
        term_results: Dictionary mapping terms to their search results

    Returns:
        List of matching results
    """
    if query_node.op == "TERM":
        term = str(query_node.left)
        return term_results.get(term, [])

    if query_node.op == "NOT":
        if not query_node.left:
            return []
        # Standalone NOT: no document set to subtract from → return [].
        # AND/OR behavior is unchanged.
        return []

    if query_node.op == "AND":
        if not query_node.left or not query_node.right:
            return []
        left_results = execute_query(cast(QueryNode, query_node.left), term_results)
        right_results = execute_query(cast(QueryNode, query_node.right), term_results)
        left_ids = {_get_result_id(r) for r in left_results}
        right_ids = {_get_result_id(r) for r in right_results}
        # Intersection
        common_ids = left_ids & right_ids
        # Return results in intersection
        result_map: Dict[str, Dict[str, str]] = {}
        for r in left_results + right_results:
            rid = _get_result_id(r)
            if rid in common_ids:
                result_map[rid] = r
        return list(result_map.values())

    if query_node.op == "OR":
        if not query_node.left and not query_node.right:
            return []
        left_results = (
            execute_query(cast(QueryNode, query_node.left), term_results)
            if query_node.left
            else []
        )
        right_results = (
            execute_query(cast(QueryNode, query_node.right), term_results)
            if query_node.right
            else []
        )
        # Union
        seen_ids: Set[str] = set()
        results: List[Dict[str, str]] = []
        for r in left_results + right_results:
            rid = _get_result_id(r)
            if rid not in seen_ids:
                results.append(r)
                seen_ids.add(rid)
        return results

    return []


def _get_result_id(result: Dict[str, str]) -> str:
    """Get unique ID for result (segment_id + db)."""
    seg_id = result.get("id", "")
    db = result.get("db", "")
    return f"{seg_id}::{db}"

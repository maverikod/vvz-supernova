"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Result ranking by relevance for search results.
"""

from __future__ import annotations

from typing import Dict, List


def rank_results(
    results: List[Dict[str, str]],
    phrases: List[str],
    scope: str = "segments",
) -> List[Dict[str, str]]:
    """
    Rank results by relevance.

    Relevance is calculated based on:
    - Number of phrase matches
    - Position of matches (title/summary > snippet)
    - Frequency of matches

    Args:
        results: List of result dictionaries
        phrases: Search phrases
        scope: Search scope (segments or formulas)

    Returns:
        Sorted list of results by relevance (highest first)
    """
    if not results or not phrases:
        return results

    # Calculate relevance score for each result
    scored_results: List[tuple[float, Dict[str, str]]] = []
    for r in results:
        score = _calculate_relevance(r, phrases, scope)
        scored_results.append((score, r))

    # Sort by score (descending)
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # Return results without scores
    return [r for _, r in scored_results]


def _calculate_relevance(
    result: Dict[str, str],
    phrases: List[str],
    scope: str,
) -> float:
    """
    Calculate relevance score for a result.

    Args:
        result: Result dictionary
        phrases: Search phrases
        scope: Search scope

    Returns:
        Relevance score (higher is better)
    """
    score = 0.0
    text_lower = ""

    if scope == "segments":
        # Check summary (higher weight)
        summary = (result.get("summary") or "").lower()
        text_lower = summary
        for phrase in phrases:
            phrase_lower = phrase.lower()
            count = summary.count(phrase_lower)
            score += count * 10.0  # Summary matches worth more

        # Check snippet
        snippet = (result.get("snippet") or "").lower()
        text_lower += " " + snippet
        for phrase in phrases:
            phrase_lower = phrase.lower()
            count = snippet.count(phrase_lower)
            score += count * 1.0  # Snippet matches worth less

        # Check ID (exact match)
        seg_id = (result.get("id") or "").lower()
        for phrase in phrases:
            phrase_lower = phrase.lower()
            if phrase_lower in seg_id:
                score += 5.0
    else:
        # Formulas
        formula = (result.get("formula") or "").lower()
        text_lower = formula
        for phrase in phrases:
            phrase_lower = phrase.lower()
            count = formula.count(phrase_lower)
            score += count * 2.0

    # Bonus for multiple phrase matches
    if len(phrases) > 1:
        matches = sum(1 for p in phrases if p.lower() in text_lower)
        if matches == len(phrases):
            score += 5.0  # All phrases found

    return score

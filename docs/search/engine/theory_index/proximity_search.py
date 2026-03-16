"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Proximity search: find phrases within N words of each other.
"""

from __future__ import annotations

import re
from typing import Dict, List


def filter_by_proximity(
    results: List[Dict[str, str]],
    phrases: List[str],
    max_distance: int,
    scope: str = "segments",
) -> List[Dict[str, str]]:
    """
    Filter results where all phrases appear within max_distance words.

    Args:
        results: List of result dictionaries
        phrases: List of phrases to find
        max_distance: Maximum distance in words between phrases
        scope: Search scope (segments or formulas)

    Returns:
        Filtered list of results
    """
    if not results or not phrases or len(phrases) < 2:
        return results

    filtered: List[Dict[str, str]] = []
    for r in results:
        text = ""
        if scope == "segments":
            text = f"{r.get('summary', '')} {r.get('snippet', '')}"
        else:
            text = r.get("formula", "")

        if _phrases_within_distance(text, phrases, max_distance):
            filtered.append(r)

    return filtered


def _phrases_within_distance(text: str, phrases: List[str], max_distance: int) -> bool:
    """
    Check if all phrases appear within max_distance words.

    Args:
        text: Text to search
        phrases: Phrases to find
        max_distance: Maximum distance in words

    Returns:
        True if all phrases found within distance
    """
    if not text or not phrases:
        return False

    # Find positions of all phrases
    phrase_positions: List[List[int]] = []
    words = _split_words(text)

    for phrase in phrases:
        phrase_lower = phrase.lower()
        positions: List[int] = []
        # Find all occurrences of phrase
        for i, word in enumerate(words):
            if phrase_lower in word.lower():
                positions.append(i)
        if not positions:
            return False  # Phrase not found
        phrase_positions.append(positions)

    # Check if there's a combination where all phrases are within distance
    return _check_proximity(phrase_positions, max_distance)


def _split_words(text: str) -> List[str]:
    """Split text into words."""
    # Split on whitespace and punctuation, keep words
    words = re.findall(r"\b\w+\b", text, re.UNICODE)
    return words


def _check_proximity(phrase_positions: List[List[int]], max_distance: int) -> bool:
    """
    Check if there's a combination of positions where all phrases
    are within max_distance words.

    Args:
        phrase_positions: List of position lists for each phrase
        max_distance: Maximum distance

    Returns:
        True if valid combination exists
    """
    if not phrase_positions:
        return False

    # Use recursive search to find valid combination
    def _search_combination(
        current_phrases: List[int], remaining_phrases: List[List[int]]
    ) -> bool:
        if not remaining_phrases:
            # Check if all current positions are within distance
            if len(current_phrases) < 2:
                return True
            min_pos = min(current_phrases)
            max_pos = max(current_phrases)
            return (max_pos - min_pos) <= max_distance

        # Try each position in next phrase
        for pos in remaining_phrases[0]:
            if _search_combination(current_phrases + [pos], remaining_phrases[1:]):
                return True
        return False

    return _search_combination([], phrase_positions)

"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Result formatting with highlighting for search results.
"""

from __future__ import annotations

import re
from typing import Dict, List


def highlight_phrases(
    text: str,
    phrases: List[str],
    highlight_start: str = "**",
    highlight_end: str = "**",
) -> str:
    """
    Highlight phrases in text.

    Args:
        text: Text to highlight
        phrases: List of phrases to highlight
        highlight_start: Start marker for highlighting
        highlight_end: End marker for highlighting

    Returns:
        Text with highlighted phrases
    """
    if not text or not phrases:
        return text

    def escape_regex(s: str) -> str:
        """Escape special regex characters so the phrase is matched literally."""
        return re.escape(s)

    # Build pattern
    patterns = [escape_regex(p) for p in phrases if p]
    if not patterns:
        return text

    # Combine patterns
    pattern = "|".join(patterns)
    # Case-insensitive match
    regex = re.compile(f"({pattern})", re.IGNORECASE)

    # Find all matches and their positions
    matches = list(regex.finditer(text))
    if not matches:
        return text

    # Build highlighted text
    result = []
    last_end = 0
    for match in matches:
        # Add text before match
        result.append(text[last_end : match.start()])
        # Add highlighted match
        result.append(highlight_start)
        result.append(match.group(0))
        result.append(highlight_end)
        last_end = match.end()

    # Add remaining text
    result.append(text[last_end:])
    return "".join(result)


def format_search_result(
    result: Dict[str, str],
    phrases: List[str],
    summary_only: bool = False,
    highlight: bool = True,
    context_lines: int = 0,
) -> str:
    """
    Format search result with optional highlighting.

    Args:
        result: Result dictionary
        phrases: Phrases to highlight
        summary_only: If True, show only summary
        highlight: If True, highlight phrases

    Returns:
        Formatted result string
    """
    seg_id = result.get("id", "")
    db = result.get("db", "")
    category = result.get("category", "")
    summary = result.get("summary", "")
    snippet = result.get("snippet", "")

    # Header
    header = f"[{seg_id}] ({db}) {category} :: {summary}"

    if summary_only:
        return header

    # Body
    body = snippet
    if highlight and phrases:
        body = highlight_phrases(body, phrases)

    # Add context if requested
    if context_lines > 0:
        lines = body.split("\n")
        # For now, just show more lines from snippet
        # Full context requires access to source file
        if len(lines) > context_lines * 2:
            body = "\n".join(lines[: context_lines * 2 + 1])
            body += f"\n[... {len(lines) - context_lines * 2 - 1} more lines ...]"

    return f"{header}\n{body}\n----"


def format_results(
    results: List[Dict[str, str]],
    phrases: List[str],
    scope: str,
    summary_only: bool = False,
    highlight: bool = True,
    context_lines: int = 0,
) -> None:
    """
    Format and print search results.

    Args:
        results: List of result dictionaries
        phrases: Phrases to highlight
        scope: Search scope (segments or formulas)
        summary_only: If True, show only summaries
        highlight: If True, highlight phrases
    """
    try:
        for r in results:
            if scope == "segments":
                output = format_search_result(
                    r, phrases, summary_only, highlight, context_lines
                )
                print(output)
            else:
                seg_id = r.get("id", "")
                db = r.get("db", "")
                formula = r.get("formula", "")
                if highlight and phrases:
                    formula = highlight_phrases(formula, phrases)
                print(f"[{seg_id}] ({db}) :: {formula}")
    except BrokenPipeError:
        pass

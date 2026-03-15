"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

HTML export functionality for search results.
"""

from __future__ import annotations

import html
import re
from typing import Dict, List


def export_to_html(
    results: List[Dict[str, str]],
    phrases: List[str],
    scope: str,
    output_path: str,
    title: str = "Search Results",
) -> None:
    """
    Export search results to HTML file.

    Args:
        results: List of result dictionaries
        phrases: Search phrases for highlighting
        scope: Search scope (segments or formulas)
        output_path: Path to output HTML file
        title: HTML page title
    """
    html_content = _generate_html(results, phrases, scope, title)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def _generate_html(
    results: List[Dict[str, str]],
    phrases: List[str],
    scope: str,
    title: str,
) -> str:
    """Generate HTML content."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        f"<title>{html.escape(title)}</title>",
        "<meta charset='utf-8'>",
        "<style>",
        _get_css(),
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{html.escape(title)}</h1>",
        f"<p>Found {len(results)} results</p>",
        "<div class='results'>",
    ]

    for r in results:
        html_parts.append(_format_result_html(r, phrases, scope))

    html_parts.extend(["</div>", "</body>", "</html>"])
    return "\n".join(html_parts)


def _get_css() -> str:
    """Get CSS styles."""
    return """
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        .result {
            background: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .result-header {
            font-weight: bold;
            color: #0066cc;
            margin-bottom: 10px;
        }
        .result-category {
            color: #666;
            font-size: 0.9em;
        }
        .result-summary {
            margin: 10px 0;
            font-style: italic;
            color: #555;
        }
        .result-snippet {
            margin: 10px 0;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .highlight {
            background: #ffeb3b;
            font-weight: bold;
        }
        .separator {
            border-top: 1px solid #ddd;
            margin: 20px 0;
        }
    """


def _format_result_html(
    result: Dict[str, str],
    phrases: List[str],
    scope: str,
) -> str:
    """Format single result as HTML."""
    seg_id = html.escape(result.get("id", ""))
    db = html.escape(result.get("db", ""))
    category = html.escape(result.get("category", ""))
    summary = html.escape(result.get("summary", ""))
    snippet = html.escape(result.get("snippet", "") or result.get("formula", ""))

    # Highlight phrases
    for phrase in phrases:
        if phrase:
            snippet = _highlight_phrase(snippet, phrase)

    html_parts = [
        "<div class='result'>",
        f"<div class='result-header'>[{seg_id}] ({db})</div>",
    ]

    if category:
        html_parts.append(f"<div class='result-category'>{category}</div>")

    if summary:
        html_parts.append(f"<div class='result-summary'>{summary}</div>")

    if snippet:
        html_parts.append(f"<div class='result-snippet'>{snippet}</div>")

    html_parts.append("</div>")
    return "\n".join(html_parts)


def _highlight_phrase(text: str, phrase: str) -> str:
    """Highlight phrase in text."""
    if not phrase:
        return text

    # Case-insensitive replacement
    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
    return pattern.sub(lambda m: f"<span class='highlight'>{m.group(0)}</span>", text)

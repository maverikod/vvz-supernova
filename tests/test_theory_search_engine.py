"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Regression tests for the theory search engine (query parser, executor, formatter).

Deterministic unit/near-unit tests only; no network or live DB required.
Path to docs/search/engine is set below so theory_index is importable from project root.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add docs/search/engine to path so theory_index is importable from project root.
_engine_dir = Path(__file__).resolve().parent.parent / "docs" / "search" / "engine"
if str(_engine_dir) not in sys.path:
    sys.path.insert(0, str(_engine_dir))

import pytest  # type: ignore[import-not-found]  # noqa: E402

from theory_index.query_parser import (  # noqa: E402
    QueryNode,
    extract_terms,
    parse_query,
)
from theory_index.query_executor import execute_query  # noqa: E402
from theory_index.result_formatter import (  # noqa: E402
    format_search_result,
    highlight_phrases,
)

# --- Query parsing ---


class TestQueryParserBasics:
    """Logical query parsing: single term, AND, OR, NOT, parentheses, empty."""

    def test_parse_single_term(self) -> None:
        """Single unquoted term parses to TERM node."""
        node = parse_query("word")
        assert node.op == "TERM"
        assert node.left == "word"

    def test_parse_quoted_term(self) -> None:
        """Single-word quoted term is preserved as TERM."""
        node = parse_query('"word"')
        assert node.op == "TERM"
        assert node.left == "word"

    def test_parse_and(self) -> None:
        """A AND B parses to AND(TERM(A), TERM(B))."""
        node = parse_query("A AND B")
        assert node.op == "AND"
        assert isinstance(node.left, QueryNode) and node.left.op == "TERM"
        assert isinstance(node.right, QueryNode) and node.right.op == "TERM"

    def test_parse_or(self) -> None:
        """A OR B parses to OR with two TERM children."""
        node = parse_query("A OR B")
        assert node.op == "OR"
        assert isinstance(node.left, QueryNode) and node.left.op == "TERM"
        assert isinstance(node.right, QueryNode) and node.right.op == "TERM"

    def test_parse_not(self) -> None:
        """NOT A parses to NOT(TERM(A))."""
        node = parse_query("NOT A")
        assert node.op == "NOT"
        assert isinstance(node.left, QueryNode) and node.left.op == "TERM"

    def test_parse_implicit_and(self) -> None:
        """Adjacent terms get implicit AND (e.g. 'level 0')."""
        node = parse_query("level 0")
        assert node.op == "AND"
        assert isinstance(node.left, QueryNode) and node.left.op == "TERM"
        assert isinstance(node.right, QueryNode) and node.right.op == "TERM"

    def test_parse_empty_raises(self) -> None:
        """Empty query raises ValueError (fail-soft boundary: must not crash)."""
        with pytest.raises(ValueError, match="Empty query"):
            parse_query("")
        with pytest.raises(ValueError, match="Empty query"):
            parse_query("   ")

    def test_extract_terms_single(self) -> None:
        """extract_terms returns list of term strings from parse tree."""
        node = parse_query("foo")
        assert extract_terms(node) == ["foo"]

    def test_extract_terms_and(self) -> None:
        """extract_terms from AND collects both terms."""
        node = parse_query("A AND B")
        assert set(extract_terms(node)) == {"A", "B"}

    def test_extract_terms_or(self) -> None:
        """extract_terms from OR collects both terms."""
        node = parse_query("X OR Y")
        assert set(extract_terms(node)) == {"X", "Y"}


# --- Query execution ---


class TestQueryExecutorBasics:
    """Execute query tree on mock term_results: TERM, AND, OR, NOT, missing term."""

    def test_execute_term_returns_matching_results(self) -> None:
        """TERM node returns term_results[term] or []."""
        node = parse_query("x")
        term_results = {
            "x": [{"id": "1", "db": "a"}, {"id": "2", "db": "a"}],
        }
        out = execute_query(node, term_results)
        assert len(out) == 2
        assert out[0]["id"] == "1" and out[1]["id"] == "2"

    def test_execute_term_missing_returns_empty(self) -> None:
        """Missing term in term_results returns [] (fail-soft, no crash)."""
        node = parse_query("nonexistent")
        out = execute_query(node, {})
        assert out == []

    def test_execute_and_intersection(self) -> None:
        """AND returns intersection of result IDs."""
        node = parse_query("A AND B")
        term_results = {
            "A": [{"id": "1", "db": "d"}, {"id": "2", "db": "d"}],
            "B": [{"id": "1", "db": "d"}, {"id": "3", "db": "d"}],
        }
        out = execute_query(node, term_results)
        assert len(out) == 1
        assert out[0]["id"] == "1"

    def test_execute_or_union(self) -> None:
        """OR returns union of results, deduplicated by id::db."""
        node = parse_query("A OR B")
        term_results = {
            "A": [{"id": "1", "db": "d"}],
            "B": [{"id": "2", "db": "d"}, {"id": "1", "db": "d"}],
        }
        out = execute_query(node, term_results)
        assert len(out) == 2
        ids = {r["id"] for r in out}
        assert ids == {"1", "2"}

    def test_execute_not_returns_empty(self) -> None:
        """Standalone NOT has no document set; returns [] (documented behavior)."""
        node = parse_query("NOT something")
        term_results = {"something": [{"id": "1", "db": "d"}]}
        out = execute_query(node, term_results)
        assert out == []


# --- Result formatting ---


class TestResultFormatterStability:
    """Format and highlight: deterministic output for given inputs."""

    def test_highlight_phrases_stable(self) -> None:
        """highlight_phrases wraps matches with markers; output is deterministic."""
        text = "The quick brown fox and the lazy fox."
        out = highlight_phrases(text, ["fox"], highlight_start="**", highlight_end="**")
        assert "**fox**" in out
        assert out.count("**fox**") == 2
        assert "quick" in out and "lazy" in out

    def test_highlight_phrases_empty_phrases_returns_text_unchanged(self) -> None:
        """Empty phrases list returns text unchanged (no crash)."""
        text = "some text"
        assert highlight_phrases(text, []) == text
        assert highlight_phrases("", ["x"]) == ""

    def test_format_search_result_stable(self) -> None:
        """format_search_result produces stable header and body for one result."""
        result = {
            "id": "seg_001",
            "db": "part1.sqlite",
            "category": "theory",
            "summary": "A short summary",
            "snippet": "Snippet with keyword here.",
        }
        out = format_search_result(result, ["keyword"], summary_only=False)
        assert "[seg_001]" in out
        assert "part1.sqlite" in out
        assert "theory" in out
        assert "A short summary" in out
        assert "keyword" in out or "**keyword**" in out
        assert "----" in out and out.strip().endswith("----")

    def test_format_search_result_summary_only(self) -> None:
        """summary_only=True returns only header line."""
        result = {
            "id": "x",
            "db": "d",
            "category": "c",
            "summary": "s",
            "snippet": "body",
        }
        out = format_search_result(result, [], summary_only=True)
        assert "body" not in out
        assert "s" in out and "x" in out


# --- Fail-soft / empty paths ---


class TestFailSoftPaths:
    """Paths that must not crash: empty results, missing keys, empty inputs."""

    def test_execute_and_empty_side_returns_empty(self) -> None:
        """AND with one side empty returns []."""
        node = parse_query("A AND B")
        term_results = {"A": [], "B": [{"id": "1", "db": "d"}]}
        out = execute_query(node, term_results)
        assert out == []

    def test_format_search_result_missing_keys_does_not_crash(self) -> None:
        """format_search_result with minimal dict uses .get(); no KeyError."""
        result = {"id": "1"}
        out = format_search_result(result, [])
        assert "[1]" in out
        assert "----" in out

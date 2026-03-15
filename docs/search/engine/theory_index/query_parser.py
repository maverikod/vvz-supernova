"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Query parser for logical operators (AND, OR, NOT) using pyparsing.
"""

from __future__ import annotations

from typing import List, Optional, Union, cast

try:
    import re
    from pyparsing import (
        CaselessKeyword,
        ParserElement,
        QuotedString,
        Regex,
        infixNotation,
        opAssoc,
    )

    ParserElement.enablePackrat()
except ImportError:
    raise ImportError(
        "pyparsing is required for query parsing. "
        "Install it with: pip install pyparsing"
    )


class QueryNode:
    """Node in query parse tree."""

    def __init__(
        self,
        op: str,
        left: Optional[Union["QueryNode", str]] = None,
        right: Optional[Union["QueryNode", str]] = None,
    ) -> None:
        """Build a parse-tree node.

        Args:
            op: Operator name: "AND", "OR", "NOT", or "TERM".
            left: Left child (term string for TERM/NOT, or child node).
            right: Right child for AND/OR; unused for TERM/NOT.
        """
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        """Return a readable representation of this node for debugging."""
        if self.op == "TERM":
            return f'"{self.left}"'
        if self.op == "NOT":
            return f"NOT({self.left})"
        return f"{self.op}({self.left}, {self.right})"


def _insert_implicit_and(query: str) -> str:
    """Insert AND between adjacent non-operator words.

    Ensures e.g. 'уровень 0' and 'L0 OR ...' parse correctly.
    """
    ops = {"AND", "OR", "NOT"}
    tokens = query.split()
    if len(tokens) <= 1:
        return query
    out = [tokens[0]]
    for i in range(1, len(tokens)):
        if out[-1].upper() not in ops and tokens[i].upper() not in ops:
            out.append("AND")
        out.append(tokens[i])
    return " ".join(out)


def _build_parser() -> ParserElement:
    """Build pyparsing grammar for query language."""
    # Term: quoted string or unquoted word (supports Unicode, digits, L0, etc.)
    quoted_term = QuotedString('"', escChar="\\") | QuotedString("'", escChar="\\")
    # Unquoted: letters, digits, hyphen, dot, colon, slash
    unquoted_term = Regex(r"[\w\-\.:/]+", flags=re.UNICODE)
    term = (quoted_term | unquoted_term).setParseAction(
        lambda t: QueryNode("TERM", t[0])
    )

    # Operators
    AND = CaselessKeyword("AND")
    OR = CaselessKeyword("OR")
    NOT = CaselessKeyword("NOT")

    # Expression with operator precedence: NOT > AND > OR
    expr = infixNotation(
        term,
        [
            (NOT, 1, opAssoc.RIGHT, lambda t: QueryNode("NOT", t[0][1])),
            (AND, 2, opAssoc.LEFT, lambda t: _build_and_node(t)),
            (OR, 2, opAssoc.LEFT, lambda t: _build_or_node(t)),
        ],
    )

    return expr


def _build_and_node(tokens: list) -> QueryNode:
    """Build AND node from parsed tokens."""
    if len(tokens[0]) < 2:
        return cast(QueryNode, tokens[0][0])
    result = cast(QueryNode, tokens[0][0])
    for i in range(1, len(tokens[0]), 2):
        if i + 1 < len(tokens[0]):
            result = QueryNode("AND", result, tokens[0][i + 1])
    return result


def _build_or_node(tokens: list) -> QueryNode:
    """Build OR node from parsed tokens."""
    if len(tokens[0]) < 2:
        return cast(QueryNode, tokens[0][0])
    result = cast(QueryNode, tokens[0][0])
    for i in range(1, len(tokens[0]), 2):
        if i + 1 < len(tokens[0]):
            result = QueryNode("OR", result, tokens[0][i + 1])
    return result


# Global parser instance
_parser = None


def _get_parser() -> ParserElement:
    """Get or create parser instance."""
    global _parser
    if _parser is None:
        _parser = _build_parser()
    return _parser


def parse_query(query: str) -> QueryNode:
    """
    Parse query string into parse tree using pyparsing.

    Supports:
    - Terms: "word", 'word', word
    - AND: A AND B
    - OR: A OR B
    - NOT: NOT A
    - Parentheses: (A OR B) AND C

    Args:
        query: Query string

    Returns:
        QueryNode: Root of parse tree

    Raises:
        ValueError: If query cannot be parsed
    """
    query = query.strip()
    if not query:
        raise ValueError("Empty query")

    query = _insert_implicit_and(query)

    try:
        parser = _get_parser()
        result = parser.parseString(query, parseAll=True)
        if not result:
            raise ValueError("No parse result")
        return cast(QueryNode, result[0])
    except Exception as e:
        raise ValueError(f"Query parsing failed: {e}") from e


def extract_terms(node: QueryNode) -> List[str]:
    """
    Extract all terms from query tree (excluding operators).

    Args:
        node: Query node

    Returns:
        List of term strings
    """
    terms: List[str] = []
    if node.op == "TERM":
        term_str = str(node.left)
        # Filter out operators
        if term_str.upper() not in ("AND", "OR", "NOT"):
            terms.append(term_str)
    else:
        if node.left:
            if isinstance(node.left, QueryNode):
                terms.extend(extract_terms(node.left))
            else:
                term_str = str(node.left)
                if term_str.upper() not in ("AND", "OR", "NOT"):
                    terms.append(term_str)
        if node.right:
            if isinstance(node.right, QueryNode):
                terms.extend(extract_terms(node.right))
            else:
                term_str = str(node.right)
                if term_str.upper() not in ("AND", "OR", "NOT"):
                    terms.append(term_str)
    return terms

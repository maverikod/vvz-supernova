"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Index container type for `ALL_index.yaml`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .segment import Segment


@dataclass(frozen=True)
class IndexData:
    """Parsed index data."""

    segments: List[Segment]
    raw: Dict[str, Any]

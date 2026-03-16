"""
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

CLI presets and helpers.
"""

from __future__ import annotations

from typing import Optional, Tuple


def apply_preset(
    preset: Optional[str],
    tag: Optional[str],
    category: Optional[str],
    phrase: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not preset:
        return tag, category, phrase

    if preset == "earth" and not (tag or category or phrase):
        phrase = "Земл"
    elif preset == "sun" and not (tag or category or phrase):
        phrase = "Солнц"
    elif preset == "particles" and not (tag or category or phrase):
        phrase = "частиц"
    return tag, category, phrase

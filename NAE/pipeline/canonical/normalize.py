"""Stage 2.1b - Unicode normalization, dehyphenation, whitespace cleanup."""
from __future__ import annotations

import re
import unicodedata

_HYPHEN_WRAP = re.compile(r"(\w)-\n(\w)")
_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+\n")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")


def unicode_normalize(text: str) -> str:
    """NFC keeps composed diacritics/Greek/Hebrew combining marks intact for theology texts."""
    return unicodedata.normalize("NFC", text)


def dehyphenate(text: str) -> str:
    """Merge line-wrap hyphenation: 'right-\\neous' -> 'righteous'.

    Only fires on lowercase-to-lowercase joins to avoid merging genuine
    hyphenated compounds or proper-noun line breaks.
    """
    def _merge(match: re.Match[str]) -> str:
        left, right = match.group(1), match.group(2)
        if left.islower() and right.islower():
            return left + right
        return match.group(0)

    return _HYPHEN_WRAP.sub(_merge, text)


def normalize_whitespace(text: str) -> str:
    text = _TRAILING_WS.sub("\n", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip("\n")


def normalize_page(text: str) -> str:
    text = unicode_normalize(text)
    text = dehyphenate(text)
    text = normalize_whitespace(text)
    return text

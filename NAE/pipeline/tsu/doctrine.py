"""Doctrine category validation against a closed, reviewable vocabulary.

The LLM is instructed (in claim.py's prompt) to choose from config.DOCTRINE_CATEGORIES.
This module is the enforcement point: any value the model returns that is not
in the closed set is coerced to "Other" rather than trusted verbatim, so an
LLM-invented label can never silently enter the corpus as if it were a known
doctrine category.
"""
from __future__ import annotations

from . import config

_NORMALIZED = {d.lower(): d for d in config.DOCTRINE_CATEGORIES}


def normalize_doctrine(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    if key in ("none", "n/a", "null", ""):
        return None
    return _NORMALIZED.get(key, "Other")

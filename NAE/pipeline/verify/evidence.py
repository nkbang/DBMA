"""Scripture evidence check.

IMPORTANT SCOPE LIMITATION: this module verifies that a scripture reference
is *syntactically well-formed* (a real book name shape + plausible chapter:verse
numbers) - it does NOT verify that the referenced Bible passage actually
supports the claim's content. That would require cross-checking against an
actual Bible text corpus, which does not exist anywhere in NAE (NAE collects
theological commentary/secondary literature, not primary scripture text).

Building a fake "yes this verse supports this claim" check without that
corpus would produce exactly the kind of unvalidated-looking-precise output
this project has been careful to avoid elsewhere (see claim.py's confidence
handling). Every result from this module is tagged textual_verification =
"not_available" for that reason - only format_valid is a real, checked signal.

If/when a Bible text source is added to NAE, this module is the place to
add real cross-checking (fetch the passage, compare against the claim via
the same LLM-judge pattern used in claim.py).
"""
from __future__ import annotations

import re

_REF_PATTERN = re.compile(r"^[1-3]?\s?[A-Z][a-zA-Z.]*\s+\d{1,3}:\d{1,3}(?:[-–]\d{1,3})?$")

# Loose sanity bounds - not a real canon lookup, just catches obviously
# malformed chapter/verse numbers (e.g. "John 300:9999").
_MAX_PLAUSIBLE_CHAPTER = 150
_MAX_PLAUSIBLE_VERSE = 180


def check_reference(ref: str) -> dict:
    """Return a syntactic-validity result for one canonical scripture reference string."""
    if not _REF_PATTERN.match(ref.strip()):
        return {"reference": ref, "format_valid": False, "textual_verification": "not_available"}

    match = re.search(r"(\d{1,3}):(\d{1,3})", ref)
    if not match:
        return {"reference": ref, "format_valid": False, "textual_verification": "not_available"}

    chapter, verse = int(match.group(1)), int(match.group(2))
    plausible = 1 <= chapter <= _MAX_PLAUSIBLE_CHAPTER and 1 <= verse <= _MAX_PLAUSIBLE_VERSE

    return {"reference": ref, "format_valid": plausible, "textual_verification": "not_available"}


def check_record_evidence(record: dict) -> list[dict]:
    return [check_reference(ref) for ref in record.get("scriptures", [])]

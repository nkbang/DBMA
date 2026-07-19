"""
core/heading_constants.py — Shared heading detection constants (SPRINT31-A).

Single source of truth for the ATX Markdown heading pattern, shared by the
Provider layer (core/heading_provider.py) without either the Provider or the
Extractor owning the other (ADR-006 / SPRINT31-A decision #1: they are peer
layers). core/heading_extractor.py currently keeps its own private copy of
this pattern; unifying it here is deferred to a later phase that is allowed to
modify heading_extractor.py (SPRINT31-A boundary forbids touching it). A
drift-guard test asserts the two patterns stay identical until then.
"""

from __future__ import annotations

import re

# ATX Markdown heading: 1-6 '#', at least one space, then the title; a trailing
# run of '#' (closed ATX form) is stripped. Requiring the space avoids matching
# "#hashtag" / "#1". re.MULTILINE so it matches on any line.
ATX_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)

MAX_HEADING_DEPTH = 6

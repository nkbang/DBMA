"""
core/heading_extractor.py — Metadata-aware heading foundation (SPRINT29-C).

Boundary-preserving, additive, deterministic. This module does NOT change how
text is chunked — it only *reads* already-produced chunk text and derives a
hierarchical heading path for each chunk, so that heading structure can be
carried as additive TSU metadata (see core/tsu_builder.py, mirroring the
SPRINT28-B content_quality pattern).

Scope constraints (SPRINT29-C, explicitly approved):
  - Metadata-aware heading foundation only.
  - NO chunk boundary redesign — chunk text is consumed as-is.
  - NO PDF font/layout heuristic — headings are detected only from explicit,
    unambiguous ATX Markdown markers ("# ", "## ", ...) that survive in the
    extracted/normalized text (e.g. .md sources). PDF-derived text has no such
    markers, so its heading_path is simply empty — an honest no-op rather than
    a guess.
  - NO semantic chunking.

Because detection is limited to explicit ATX markers, this is a foundation:
correct and reversible where structure exists, inert where it does not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

# ATX Markdown heading at the start of a line: 1-6 '#', at least one space, then
# the title. A trailing run of '#' (closed ATX form) is stripped. Requiring the
# space after the hashes avoids matching "#hashtag" or "#1". re.MULTILINE so it
# matches on any line of a multi-line chunk.
_ATX_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)

MAX_HEADING_DEPTH = 6


@dataclass
class HeadingStack:
    """Running hierarchical heading context for one document, updated chunk by
    chunk in document order. Not thread-safe; use one instance per document.
    """

    # list of (level, title), monotonically nested (levels strictly increasing)
    _stack: List[Tuple[int, str]] = field(default_factory=list)

    def _push(self, level: int, title: str) -> None:
        # Pop any headings at the same or deeper level, then push. This keeps
        # the stack a valid ancestor path (e.g. a new H2 replaces the previous
        # H2 and drops any H3+ beneath it).
        while self._stack and self._stack[-1][0] >= level:
            self._stack.pop()
        self._stack.append((level, title))

    def apply_chunk(self, content: str) -> "ChunkHeading":
        """Apply every ATX heading found in `content` (in order) to the running
        stack and return the resulting heading path for this chunk.

        A chunk that introduces "## Section 1.1" is considered to sit under that
        section, so the path returned is the stack *after* applying the chunk's
        own headings. A chunk with no heading inherits the current stack
        unchanged.
        """
        for m in _ATX_HEADING_RE.finditer(content or ""):
            level = len(m.group(1))
            title = m.group(2).strip()
            if title:
                self._push(level, title)
        return ChunkHeading(
            heading_path=[t for _, t in self._stack],
            heading_depth=len(self._stack),
        )


@dataclass(frozen=True)
class ChunkHeading:
    heading_path: List[str]
    heading_depth: int


def extract_headings(text: str) -> List[Tuple[int, str]]:
    """Return all ATX headings in `text` as (level, title), in document order.
    Pure/read-only. Empty list when no explicit ATX heading marker is present
    (e.g. PDF-derived text)."""
    out: List[Tuple[int, str]] = []
    for m in _ATX_HEADING_RE.finditer(text or ""):
        title = m.group(2).strip()
        if title:
            out.append((len(m.group(1)), title))
    return out


def annotate_chunks(chunks: List[str]) -> List[ChunkHeading]:
    """Given ordered chunk texts for a single document, return the heading path
    for each, carrying heading context forward across chunks. Boundary-
    preserving: `chunks` is never modified, only read. The i-th result
    corresponds to chunks[i].
    """
    stack = HeadingStack()
    return [stack.apply_chunk(c) for c in chunks]

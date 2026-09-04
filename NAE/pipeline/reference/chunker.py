"""Chunker for reference corpora (dictionaries, encyclopedias, etc.).

Reads `canonical.json` paragraphs and produces text chunks suitable for
embedding.  Unlike the TSU chunker, this is a simple linear pass that:

1. Groups consecutive prose paragraphs into chunks up to CHUNK_SIZE.
2. Prepends the most recent heading as context when a new chunk starts.
3. Preserves page_start/page_end metadata for each chunk.

Does NOT depend on core/chunking_optimizer.py — it is a standalone,
lightweight chunker designed specifically for reference corpus structure.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("nae.reference.chunker")


@dataclass
class ReferenceChunk:
    """A single chunk from a reference corpus."""
    chunk_index: int
    text: str
    page_start: int | None
    page_end: int | None
    heading_context: str  # most recent heading, or "" if none


def load_canonical(canonical_path: Path) -> dict[str, Any]:
    """Load a canonical.json file and return its parsed content."""
    with open(canonical_path, encoding="utf-8") as fh:
        return __import__("json").load(fh)


def chunk_canonical(
    canonical: dict[str, Any],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[ReferenceChunk]:
    """Chunk a canonical.json's paragraphs into reference chunks.

    Strategy:
    - Walk paragraphs in order.
    - When type=="heading", remember it as the current heading context.
    - When type=="prose", accumulate text into a buffer.
    - When the buffer exceeds chunk_size, emit it as a chunk (with the
      most recent heading prepended), then start a new buffer with the
      tail of the last paragraph (for overlap).
    - page_start/page_end track the span of paragraphs in each chunk.

    Returns chunks sorted by chunk_index (0-based).
    """
    paragraphs: list[dict[str, Any]] = canonical.get("paragraphs", [])
    if not paragraphs:
        return []

    chunks: list[ReferenceChunk] = []
    current_heading: str = ""
    buf_text: list[str] = []
    buf_len: int = 0
    chunk_idx: int = 0
    first_page: int | None = None
    last_page: int | None = None

    def _flush(carry_overlap: bool = False) -> None:
        """Emit the current buffer as a chunk."""
        nonlocal buf_text, buf_len, first_page, last_page, current_heading, chunk_idx

        if not buf_text:
            return

        text = "\n\n".join(buf_text).strip()
        if not text:
            buf_text = []
            buf_len = 0
            return

        # Prepend heading context
        if current_heading:
            display_text = f"[{current_heading}]\n\n{text}"
        else:
            display_text = text

        chunks.append(ReferenceChunk(
            chunk_index=chunk_idx,
            text=display_text,
            page_start=first_page,
            page_end=last_page,
            heading_context=current_heading,
        ))
        chunk_idx += 1

        if carry_overlap and len(buf_text) >= 2:
            # Keep the last paragraph as overlap seed
            overlap_text = buf_text[-1]
            if len(overlap_text) > chunk_overlap:
                overlap_text = overlap_text[:chunk_overlap]
            buf_text = [overlap_text]
            buf_len = len(overlap_text)
        else:
            buf_text = []
            buf_len = 0
            first_page = None
            last_page = None

    for para in paragraphs:
        ptype = para.get("type", "prose")
        text = para.get("text", "")
        if not text or not text.strip():
            continue

        pg = para.get("page_start")

        if ptype == "heading":
            # Flush current buffer before starting a new heading context
            _flush(carry_overlap=False)
            current_heading = text.strip()
            continue

        # prose (or anything else treated as prose)
        para_len = len(text)
        if first_page is None:
            first_page = pg
        last_page = pg

        next_len = buf_len + (2 if buf_text else 0) + para_len
        if buf_text and next_len > chunk_size:
            _flush(carry_overlap=True)

        buf_text.append(text)
        buf_len = len("\n\n".join(buf_text))

    # Flush remaining buffer
    _flush(carry_overlap=False)

    logger.info(
        "Chunked %d paragraphs → %d chunks (size=%d, overlap=%d)",
        len(paragraphs), len(chunks), chunk_size, chunk_overlap,
    )
    return chunks

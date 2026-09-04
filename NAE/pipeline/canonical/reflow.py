"""Stage 2.3 - paragraph reconstruction, sentence-boundary repair, verse/poetry preservation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config

_TERMINAL_PUNCT = re.compile(r"[.!?;:]\s*$")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")


@dataclass
class Paragraph:
    index: int
    type: str  # "prose" | "verse"
    text: str
    page_start: int
    page_end: int


def _flatten(pages: list[list[str]]) -> list[tuple[str, int]]:
    flat: list[tuple[str, int]] = []
    for page_num, lines in enumerate(pages, start=1):
        for line in lines:
            flat.append((line, page_num))
    return flat


def _split_blocks(flat: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    blocks: list[list[tuple[str, int]]] = []
    current: list[tuple[str, int]] = []
    for line, page_num in flat:
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        current.append((line, page_num))
    if current:
        blocks.append(current)
    return blocks


def _is_verse_block(block: list[tuple[str, int]]) -> bool:
    """Poetry/hymn lines are consistently short and rarely end mid-sentence.

    Prose that happens to wrap into short lines still trends toward the
    column width and terminal punctuation on most lines, so both ratios
    are held high to keep false positives out of ordinary paragraphs.
    """
    non_blank = [line for line, _ in block if line.strip()]
    if len(non_blank) < 3:
        return False
    short_count = sum(1 for line in non_blank if len(line.strip()) <= config.VERSE_MAX_CHARS)
    non_terminal_count = sum(1 for line in non_blank if not _TERMINAL_PUNCT.search(line.strip()))
    return (short_count / len(non_blank)) >= 0.9 and (non_terminal_count / len(non_blank)) >= 0.75


def _render_prose(block: list[tuple[str, int]]) -> str:
    text = " ".join(line.strip() for line, _ in block if line.strip())
    return _MULTI_SPACE.sub(" ", text).strip()


def _render_verse(block: list[tuple[str, int]]) -> str:
    return "\n".join(line.strip() for line, _ in block if line.strip())


def reconstruct_paragraphs(pages: list[list[str]]) -> list[Paragraph]:
    flat = _flatten(pages)
    blocks = _split_blocks(flat)

    paragraphs: list[Paragraph] = []
    for idx, block in enumerate(blocks):
        page_start = block[0][1]
        page_end = block[-1][1]
        if _is_verse_block(block):
            paragraphs.append(Paragraph(idx, "verse", _render_verse(block), page_start, page_end))
        else:
            paragraphs.append(Paragraph(idx, "prose", _render_prose(block), page_start, page_end))
    return paragraphs


def find_scripture_references(text: str) -> list[str]:
    return re.findall(config.SCRIPTURE_REF_PATTERN, text)

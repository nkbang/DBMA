"""Stage 2.5 - structural/semantic annotation on top of reflowed paragraphs.

Adds, per paragraph: sentence segmentation, heading/quote classification,
canonical scripture-reference forms, and script-based language tags
(Greek/Hebrew are detected reliably via Unicode block; Latin is not
attempted here since it shares script with English and a heuristic
would be unreliable - see module docstring in scripture.py).
"""
from __future__ import annotations

import re

from . import config
from .reflow import Paragraph

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"‘“])")
_ABBREVIATIONS = {
    "mr.", "mrs.", "dr.", "rev.", "elder", "st.", "vs.", "etc.", "i.e.", "e.g.",
    "rom.", "cor.", "gal.", "eph.", "phil.", "col.", "thess.", "tim.", "tit.",
    "heb.", "jas.", "pet.", "jn.", "rev.", "gen.", "exod.", "lev.", "num.",
    "deut.", "josh.", "judg.", "ps.", "prov.", "eccl.", "isa.", "jer.", "ezek.",
    "matt.", "mk.", "lk.", "no.", "vol.", "p.", "pp.", "ch.", "art.",
}

_HEADING_TOP_LEVEL = re.compile(
    r"^(CHAPTER|PART|BOOK|SECTION)\b|^[IVXLCDM]+\.?\s*$", re.IGNORECASE
)
_ALL_CAPS_LINE = re.compile(r"^[A-Z0-9][A-Z0-9 .,;:'\"\-]{2,80}$")

_QUOTE_WRAP = re.compile(r'^[\"“‘].*[\"”’]$', re.DOTALL)

_GREEK_RANGE = re.compile(r"[Ͱ-Ͽἀ-῿]")
_HEBREW_RANGE = re.compile(r"[֐-׿]")

# Roman-numeral chapter/verse ("John iii.16") -> canonical arabic ("John 3:16").
# Also normalizes the common "Book ch.verse" dotted form to "Book ch:verse".
_ROMAN_MAP = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
    "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15,
    "xvi": 16, "xvii": 17, "xviii": 18, "xix": 19, "xx": 20, "xxi": 21,
    "xxii": 22, "xxiii": 23, "xxiv": 24, "xxv": 25, "xxvi": 26, "xxvii": 27,
    "xxviii": 28,
}
_LEGACY_REF = re.compile(
    r"\b(?P<book>(?:[1-3]\s)?[A-Z][a-z]+)\.?\s+(?P<chapter>[ivxlcdm]+)\.(?P<verse>\d{1,3})\b",
    re.IGNORECASE,
)
_ARABIC_REF = re.compile(
    r"\b(?P<book>(?:[1-3]\s)?[A-Z][a-z]+)\.?\s+(?P<chapter>\d{1,3}):(?P<verse>\d{1,3}(?:[-–]\d{1,3})?)\b"
)


def split_sentences(text: str) -> list[str]:
    """Best-effort sentence splitter; guards against common theological/biblical abbreviations."""
    if not text.strip():
        return []
    raw_parts = _SENTENCE_SPLIT.split(text)
    sentences: list[str] = []
    buffer = ""
    for part in raw_parts:
        buffer = f"{buffer} {part}".strip() if buffer else part
        tail = buffer.rstrip().split(" ")[-1].lower() if buffer.strip() else ""
        if tail in _ABBREVIATIONS:
            continue
        sentences.append(buffer)
        buffer = ""
    if buffer:
        sentences.append(buffer)
    return [s.strip() for s in sentences if s.strip()]


def classify_paragraph(paragraph: Paragraph) -> tuple[str, int | None]:
    """Return (type, heading_level). type in {heading, quote, verse, prose}; existing verse type wins."""
    if paragraph.type == "verse":
        return "verse", None

    text = paragraph.text.strip()
    is_single_line = "\n" not in text and len(text) <= 80

    if is_single_line and _HEADING_TOP_LEVEL.match(text):
        return "heading", 1
    if is_single_line and _ALL_CAPS_LINE.match(text) and text.upper() == text:
        return "heading", 2
    if _QUOTE_WRAP.match(text):
        return "quote", None
    return "prose", None


def canonicalize_scripture_ref(ref: str) -> str | None:
    """Convert legacy 'Book ivx.verse' notation to canonical 'Book chapter:verse'."""
    match = _LEGACY_REF.match(ref)
    if not match:
        match = _ARABIC_REF.match(ref)
        if match:
            book = re.sub(r"\s+", " ", match.group("book")).strip()
            return f"{book} {match.group('chapter')}:{match.group('verse')}"
        return None
    book = re.sub(r"\s+", " ", match.group("book")).strip()
    chapter_roman = match.group("chapter").lower()
    chapter = _ROMAN_MAP.get(chapter_roman)
    if chapter is None:
        return None
    return f"{book} {chapter}:{match.group('verse')}"


def find_scripture_references_extended(text: str) -> list[dict[str, str]]:
    """Find both canonical (John 3:16) and legacy (John iii.16) forms, paired with canonical output."""
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern in (_ARABIC_REF, _LEGACY_REF):
        for match in pattern.finditer(text):
            original = match.group(0)
            if original in seen:
                continue
            canonical = canonicalize_scripture_ref(original)
            if canonical is None:
                continue
            seen.add(original)
            results.append({"original": original, "canonical": canonical})
    return results


def detect_script_language(text: str) -> str | None:
    """Reliable script-based detection only (Greek/Hebrew Unicode blocks). Latin is not attempted."""
    greek_chars = len(_GREEK_RANGE.findall(text))
    hebrew_chars = len(_HEBREW_RANGE.findall(text))
    total = max(len(text.strip()), 1)
    if greek_chars / total > 0.15:
        return "greek"
    if hebrew_chars / total > 0.15:
        return "hebrew"
    return None


def annotate_paragraph(paragraph: Paragraph, index: int) -> dict:
    ptype, heading_level = classify_paragraph(paragraph)
    sentences = split_sentences(paragraph.text) if ptype in ("prose", "quote") else []
    scripture = find_scripture_references_extended(paragraph.text)
    language = detect_script_language(paragraph.text)

    entry = {
        "index": index,
        "type": ptype,
        "text": paragraph.text,
        "page_start": paragraph.page_start,
        "page_end": paragraph.page_end,
        "sentences": [{"sentence_index": i, "text": s} for i, s in enumerate(sentences)],
        "scripture_references": scripture,
    }
    if heading_level is not None:
        entry["heading_level"] = heading_level
    if language is not None:
        entry["language"] = language
    return entry

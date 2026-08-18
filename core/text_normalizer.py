from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


_RE_MULTISPACE = re.compile(r"[ \t]+")
_RE_MULTIBLANK = re.compile(r"\n{3,}")
_RE_HYPHEN_BREAK = re.compile(r"([A-Za-z가-힣0-9])-[ \t]*\n[ \t]*([A-Za-z가-힣0-9])")
_RE_SENTENCE_END = re.compile(r"[.!?。！？]|다\.|니다\.|요\.|이다\.|였다\.|합니다\.|입니다\.")
_RE_KOREAN_CHARS = re.compile(r"[가-힣]")
_RE_KOREAN_FUNCTION_END = re.compile(r"(?:다|니다|요|이다|했다|하였다|됩니다|입니다|같다|라고|하며|하면|하지만|그래서|그러나)$")
_RE_HANGUL = re.compile(r"[가-힣]")
_RE_LATIN = re.compile(r"[A-Za-z]")
_RE_HEBREW = re.compile(r"[\u0590-\u05FF]")
_RE_GREEK = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
_RE_BULLET_LINE = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+")
_RE_KO_SENT_END = re.compile(r"(?:다|니다|요|이다|였다|합니다|입니다|했다|하였다|됩니다|같다|라고|하며|하면|하지만|그래서|그러나)$")
_RE_EN_SENT_END = re.compile(r"[.!?]$")
_RE_WEAK_SENT_END = re.compile(r"[.!?。！？]|다\.|니다\.|요\.|이다\.|였다\.|합니다\.|입니다\.$")


LanguageLabel = Literal["ko", "en", "mixed", "other"]


@dataclass(frozen=True)
class ParagraphLanguage:
    label: LanguageLabel
    ko_ratio: float
    en_ratio: float
    hangul_count: int
    latin_count: int
    text_length: int
    hebrew_count: int = 0
    greek_count: int = 0
    has_original_language: bool = False


def normalize_extracted_text(text: str) -> str:
    """Normalize raw extracted text while preserving paragraph structure."""
    text = text or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _RE_HYPHEN_BREAK.sub(r"\1\2", text)
    text = _RE_MULTISPACE.sub(" ", text)
    text = _RE_MULTIBLANK.sub("\n\n", text)
    return text.strip()


def _looks_like_korean_prose(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    return bool(_RE_KOREAN_CHARS.search(line))


def _ends_like_sentence(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    if _RE_SENTENCE_END.search(line):
        return True
    return bool(_RE_KOREAN_FUNCTION_END.search(line))


def collapse_soft_linebreaks(text: str) -> str:
    """Join likely soft line breaks inside Korean paragraphs."""
    text = normalize_extracted_text(text)
    if not text:
        return ""

    lines = [line.strip() for line in text.split("\n")]
    paragraphs: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if buf:
            joined = " ".join(buf).strip()
            joined = _RE_MULTISPACE.sub(" ", joined)
            if joined:
                paragraphs.append(joined)
            buf = []

    for line in lines:
        if not line:
            flush()
            continue

        if not buf:
            buf.append(line)
            continue

        prev = buf[-1]
        prev_korean = _looks_like_korean_prose(prev)
        line_korean = _looks_like_korean_prose(line)

        if prev_korean and line_korean:
            if not _ends_like_sentence(prev):
                buf.append(line)
            else:
                if len(line) < 20 and not _ends_like_sentence(line):
                    buf.append(line)
                else:
                    flush()
                    buf.append(line)
            continue

        if len(line) < 20 and not _ends_like_sentence(line):
            buf.append(line)
            continue

        buf.append(line)

    flush()
    return "\n\n".join(p for p in paragraphs if p)


def normalize_pipeline_text(text: str) -> str:
    """Normalize extracted text for downstream chunking."""
    text = collapse_soft_linebreaks(text)
    text = _RE_MULTISPACE.sub(" ", text)
    text = _RE_MULTIBLANK.sub("\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    text = normalize_pipeline_text(text)
    if not text:
        return []
    return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]


def split_sentences(text: str) -> list[str]:
    text = normalize_pipeline_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _count_hangul(text: str) -> int:
    return len(_RE_HANGUL.findall(text))


def _count_latin(text: str) -> int:
    return len(_RE_LATIN.findall(text))


def _count_hebrew(text: str) -> int:
    return len(_RE_HEBREW.findall(text))


def _count_greek(text: str) -> int:
    return len(_RE_GREEK.findall(text))


# Minimum original-language character count before a paragraph is flagged
# as containing protected Hebrew/Greek content. Low on purpose: even a short
# insertion like "בָּמָה" or "λόγος" inside Korean/English prose should be
# protected from mid-word splitting.
ORIGINAL_LANGUAGE_MIN_CHARS = 3


def _clean_line(line: str) -> str:
    return _RE_MULTISPACE.sub(" ", line.strip())


def detect_paragraph_language(
    text: str,
    mixed_threshold: float = 0.20,
    min_significant_chars: int = 40,
) -> ParagraphLanguage:
    text = normalize_pipeline_text(text)
    if not text:
        return ParagraphLanguage("other", 0.0, 0.0, 0, 0, 0)

    hangul_count = _count_hangul(text)
    latin_count = _count_latin(text)
    hebrew_count = _count_hebrew(text)
    greek_count = _count_greek(text)
    text_length = len(text)
    denom = max(hangul_count + latin_count, 1)
    ko_ratio = hangul_count / denom
    en_ratio = latin_count / denom
    has_original_language = (hebrew_count + greek_count) >= ORIGINAL_LANGUAGE_MIN_CHARS

    def _lang(
        label: LanguageLabel,
        ko_ratio: float = ko_ratio,
        en_ratio: float = en_ratio,
    ) -> ParagraphLanguage:
        return ParagraphLanguage(
            label, ko_ratio, en_ratio, hangul_count, latin_count, text_length,
            hebrew_count, greek_count, has_original_language,
        )

    if text_length < min_significant_chars:
        if hangul_count and not latin_count:
            return _lang("ko")
        if latin_count and not hangul_count:
            return _lang("en")
        if hangul_count and latin_count:
            return _lang("mixed")
        if has_original_language:
            # Short paragraph that is purely/mostly Hebrew or Greek (e.g. a
            # standalone lemma or footnote gloss) — no Korean/English present
            # to dominate, but it is meaningful original-language content,
            # not noise. Route it through "mixed" so downstream chunking
            # treats it with the same care as bilingual prose instead of
            # discarding it under the generic "other" bucket.
            return ParagraphLanguage("mixed", 0.0, 0.0, hangul_count, latin_count,
                                      text_length, hebrew_count, greek_count, True)
        return ParagraphLanguage("other", 0.0, 0.0, 0, 0, text_length,
                                  hebrew_count, greek_count, has_original_language)

    if hangul_count == 0 and latin_count == 0:
        if has_original_language:
            return ParagraphLanguage("mixed", 0.0, 0.0, hangul_count, latin_count,
                                      text_length, hebrew_count, greek_count, True)
        return ParagraphLanguage("other", 0.0, 0.0, 0, 0, text_length,
                                  hebrew_count, greek_count, has_original_language)

    if hangul_count > 0 and latin_count == 0:
        return _lang("ko")

    if latin_count > 0 and hangul_count == 0:
        return _lang("en")

    if ko_ratio >= 1.0 - mixed_threshold:
        return _lang("ko")

    if en_ratio >= 1.0 - mixed_threshold:
        return _lang("en")

    return _lang("mixed")


def _looks_like_korean_sentence_end(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    return bool(_RE_KO_SENT_END.search(line) or line.endswith(("다.", "니다.", "요.", "이다.", "였다.", "합니다.", "입니다.")))


def _looks_like_english_sentence_end(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    return bool(_RE_EN_SENT_END.search(line))


def _is_bullet(line: str) -> bool:
    return bool(_RE_BULLET_LINE.match(line))


def split_sentences_mixed(
    text: str,
    mixed_threshold: float = 0.20,
    min_significant_chars: int = 40,
) -> list[str]:
    text = normalize_pipeline_text(text)
    if not text:
        return []

    lines = [_clean_line(x) for x in text.split("\n")]
    lines = [x for x in lines if x]
    if not lines:
        return []

    sentences: list[str] = []
    buf: list[str] = []

    def flush_buffer() -> None:
        nonlocal buf
        if buf:
            joined = _RE_MULTISPACE.sub(" ", " ".join(buf)).strip()
            if joined:
                sentences.append(joined)
            buf = []

    for line in lines:
        if _is_bullet(line):
            flush_buffer()
            sentences.append(line)
            continue

        if not buf:
            buf.append(line)
            continue

        prev = buf[-1]
        lang_prev = detect_paragraph_language(prev, mixed_threshold, min_significant_chars).label
        lang_line = detect_paragraph_language(line, mixed_threshold, min_significant_chars).label
        prev_end_ko = _looks_like_korean_sentence_end(prev)
        prev_end_en = _looks_like_english_sentence_end(prev)
        line_short = len(line) < 24
        line_end_ko = _looks_like_korean_sentence_end(line)
        line_end_en = _looks_like_english_sentence_end(line)

        if lang_prev == "ko" and lang_line == "ko":
            if not prev_end_ko:
                buf.append(line)
            else:
                if line_short and not line_end_ko:
                    buf.append(line)
                else:
                    flush_buffer()
                    buf.append(line)
            continue

        if lang_prev == "en" and lang_line == "en":
            if not prev_end_en:
                buf.append(line)
            else:
                if line_short and not line_end_en:
                    buf.append(line)
                else:
                    flush_buffer()
                    buf.append(line)
            continue

        if lang_prev == "mixed" or lang_line == "mixed":
            if prev_end_ko or prev_end_en:
                if line_short:
                    buf.append(line)
                else:
                    flush_buffer()
                    buf.append(line)
            else:
                buf.append(line)
            continue

        if line_short and not _RE_WEAK_SENT_END.search(line):
            buf.append(line)
            continue

        if prev_end_ko or prev_end_en:
            flush_buffer()
            buf.append(line)
        else:
            buf.append(line)

    flush_buffer()
    return [s for s in sentences if s]


def _sentence_overlap_tail(units: list[str], overlap_chars: int) -> list[str]:
    """[SPRINT29-B-Overlap] Smallest suffix of already-emitted sentences whose
    joined length >= overlap_chars, used to seed the next chunk. Never returns
    the whole list (units[0] is always excluded) so forward progress is
    guaranteed. Boundary-preserving: whole sentences only, never a mid-sentence
    cut. Empty when overlap is disabled or there is only one sentence to keep.
    """
    if overlap_chars <= 0 or len(units) <= 1:
        return []
    tail: list[str] = []
    total = 0
    for u in reversed(units[1:]):
        tail.insert(0, u)
        total += len(u) + 1
        if total >= overlap_chars:
            break
    # Bound overshoot from a single long trailing sentence (same rationale as
    # chunking_optimizer._paragraph_overlap_tail): if the seed exceeds ~2x the
    # target, trim its oldest sentence to a word-safe tail — never a mid-word cut.
    cap = overlap_chars * 2
    joined_len = sum(len(u) + 1 for u in tail)
    if joined_len > cap and tail:
        first = tail[0]
        if len(first) > overlap_chars:
            window = first[-overlap_chars:]
            m = re.search(r"[\s׃]", window)
            trimmed = window[m.start():].strip() if m else ""
            tail = ([trimmed] + tail[1:]) if trimmed else tail[1:]
    return tail


def _word_safe_hard_slice(s: str, max_chars: int) -> list[str]:
    """Split a single oversized unit into <= max_chars pieces without cutting
    inside a word. Mirrors core.chunking_optimizer._slice_preserving_words
    (kept as a separate copy to avoid a text_normalizer -> chunking_optimizer
    import cycle, since chunking_optimizer already imports from this module).

    Falls back to a hard slice only if one token (no spaces at all) itself
    exceeds max_chars.
    """
    tokens = re.split(r"(\s+|׃)", s)
    pieces: list[str] = []
    buf = ""
    for tok in tokens:
        if len(buf) + len(tok) <= max_chars:
            buf += tok
        else:
            if buf.strip():
                pieces.append(buf.strip())
            if len(tok) > max_chars:
                for i in range(0, len(tok), max_chars):
                    pieces.append(tok[i:i + max_chars].strip())
                buf = ""
            else:
                buf = tok
    if buf.strip():
        pieces.append(buf.strip())
    return [p for p in pieces if p]


def _merge_sentence_fragments(sentences: list[str], max_chars: int, overlap_chars: int = 0) -> list[str]:
    if not sentences:
        return []

    chunks: list[str] = []
    buf: list[str] = []
    total = 0

    def flush(carry_overlap: bool = False) -> None:
        nonlocal buf, total
        if buf:
            chunks.append(" ".join(buf).strip())
            if carry_overlap:
                seed = _sentence_overlap_tail(buf, overlap_chars)
                if seed:
                    buf = list(seed)
                    total = sum(len(s) + 1 for s in buf)
                    return
        buf = []
        total = 0

    for sent in sentences:
        sent = _clean_line(sent)
        if not sent:
            continue
        if len(sent) > max_chars:
            flush(carry_overlap=False)
            chunks.extend(_word_safe_hard_slice(sent, max_chars))
            continue
        if total + len(sent) + 1 <= max_chars:
            buf.append(sent)
            total += len(sent) + 1
        else:
            flush(carry_overlap=True)
            buf.append(sent)
            total += len(sent) + 1

    flush(carry_overlap=False)
    return [c for c in chunks if c]


def reflow_wrapped_lines(text: str) -> str:
    """Rejoin PDF-style mid-sentence line wraps into complete sentences.

    PDF text extraction wraps lines at the page width, so a raw extracted
    document typically has one sentence spread across several physical
    lines. Saved as-is, the .md body reads as visually "cut off" sentence
    fragments even though no content is missing. This reflows each
    paragraph (blank-line-separated block) through split_sentences_mixed()
    so the saved .md shows one complete sentence per line.

    Display/readability only — deliberately NOT used by the chunking
    pipeline (core/chunking_optimizer.py), which has its own independent
    sentence-merging logic already tuned for chunk-size packing.
    """
    if not text or not text.strip():
        return text

    paragraphs = re.split(r"\n[ \t]*\n", text)
    out_paragraphs: list[str] = []
    for para in paragraphs:
        if not para.strip():
            continue
        sentences = split_sentences_mixed(para)
        out_paragraphs.append("\n".join(sentences) if sentences else para.strip())

    return "\n\n".join(out_paragraphs)

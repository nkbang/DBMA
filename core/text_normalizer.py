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
    text_length = len(text)
    denom = max(hangul_count + latin_count, 1)
    ko_ratio = hangul_count / denom
    en_ratio = latin_count / denom

    if text_length < min_significant_chars:
        if hangul_count and not latin_count:
            return ParagraphLanguage("ko", ko_ratio, en_ratio, hangul_count, latin_count, text_length)
        if latin_count and not hangul_count:
            return ParagraphLanguage("en", ko_ratio, en_ratio, hangul_count, latin_count, text_length)
        if hangul_count and latin_count:
            return ParagraphLanguage("mixed", ko_ratio, en_ratio, hangul_count, latin_count, text_length)
        return ParagraphLanguage("other", 0.0, 0.0, 0, 0, text_length)

    if hangul_count == 0 and latin_count == 0:
        return ParagraphLanguage("other", 0.0, 0.0, 0, 0, text_length)

    if hangul_count > 0 and latin_count == 0:
        return ParagraphLanguage("ko", ko_ratio, en_ratio, hangul_count, latin_count, text_length)

    if latin_count > 0 and hangul_count == 0:
        return ParagraphLanguage("en", ko_ratio, en_ratio, hangul_count, latin_count, text_length)

    if ko_ratio >= 1.0 - mixed_threshold:
        return ParagraphLanguage("ko", ko_ratio, en_ratio, hangul_count, latin_count, text_length)

    if en_ratio >= 1.0 - mixed_threshold:
        return ParagraphLanguage("en", ko_ratio, en_ratio, hangul_count, latin_count, text_length)

    return ParagraphLanguage("mixed", ko_ratio, en_ratio, hangul_count, latin_count, text_length)


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


def _merge_sentence_fragments(sentences: list[str], max_chars: int) -> list[str]:
    if not sentences:
        return []

    chunks: list[str] = []
    buf: list[str] = []
    total = 0

    def flush() -> None:
        nonlocal buf, total
        if buf:
            chunks.append(" ".join(buf).strip())
            buf = []
            total = 0

    for sent in sentences:
        sent = _clean_line(sent)
        if not sent:
            continue
        if len(sent) > max_chars:
            flush()
            chunks.append(sent)
            continue
        if total + len(sent) + 1 <= max_chars:
            buf.append(sent)
            total += len(sent) + 1
        else:
            flush()
            buf.append(sent)
            total = len(sent)

    flush()
    return [c for c in chunks if c]

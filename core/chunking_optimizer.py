from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.utils import calculate_noise_score
from core.config import DEFAULT_MIN_CHUNK_SIZE

try:
    from core.text_normalizer import (
        normalize_pipeline_text,
        split_paragraphs,
        split_sentences,
        detect_paragraph_language,
        split_sentences_mixed,
        _merge_sentence_fragments,
    )
except ImportError:
    normalize_pipeline_text = None
    split_paragraphs = None
    split_sentences = None
    detect_paragraph_language = None
    split_sentences_mixed = None
    _merge_sentence_fragments = None


# ── SPRINT 1: Config-driven chunking (config.yaml is single source of truth) ──
# PRESETS and GRID_SIZES/OVERLAPS are isolated for Sprint 2.
# For Sprint 1, optimize_chunks() uses config.yaml defaults exclusively.
# To re-enable dynamic presets/grid-search for Sprint 2, set SPRINT1_USE_CONFIG_DEFAULTS = False.

SPRINT1_USE_CONFIG_DEFAULTS = True

# Sprint 2 fallback presets (isolated — not used in Sprint 1)
PRESETS: dict[str, dict] = {
    "pdf":     {"chunk_size": 900,  "chunk_overlap": 120},
    "txt":     {"chunk_size": 1000, "chunk_overlap": 120},
    "md":      {"chunk_size": 1200, "chunk_overlap": 150},
    "docx":    {"chunk_size": 1000, "chunk_overlap": 120},
    "epub":    {"chunk_size": 1000, "chunk_overlap": 120},
    "html":    {"chunk_size": 1000, "chunk_overlap": 120},
    "htm":     {"chunk_size": 1000, "chunk_overlap": 120},
    "rtf":     {"chunk_size": 1000, "chunk_overlap": 100},
    "default": {"chunk_size": 1200, "chunk_overlap": 200},
}

# Sprint 2 fallback grid search (isolated — not used in Sprint 1)
GRID_SIZES = [600, 800, 900, 1000, 1200, 1500]
GRID_OVERLAPS = [50, 80, 100, 120, 150, 200]

NOISE_THRESHOLD = 18.0
MAX_DUP_RATIO = 0.30
# [SPRINT29-B] Single source of truth via core/config.py (config.yaml
# chunking.min_chunk_size, default 80). Value unchanged from the previous
# hardcoded 80 — this only removes the duplicate literal shared with
# core/processing.py.
MIN_CHUNK_CHARS = DEFAULT_MIN_CHUNK_SIZE
SHORT_CHUNK_RATIO_LIMIT = 0.20

_RE_MULTISPACE = re.compile(r"[ \t]+")
_RE_BULLET_LINE = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+")
_RE_WEAK_SENT_END = re.compile(r"[.!?。！？]|다\.|니다\.|요\.|이다\.|였다\.|합니다\.|입니다\.$")


@dataclass
class ChunkQuality:
    noise_scores: list[float] = field(default_factory=list)
    dup_ratios: list[float] = field(default_factory=list)
    short_ratio: float = 0.0

    @property
    def avg_noise(self) -> float:
        return sum(self.noise_scores) / len(self.noise_scores) if self.noise_scores else 0.0

    @property
    def max_noise(self) -> float:
        return max(self.noise_scores) if self.noise_scores else 0.0

    @property
    def avg_dup(self) -> float:
        return sum(self.dup_ratios) / len(self.dup_ratios) if self.dup_ratios else 0.0

    @property
    def passed(self) -> bool:
        return (
            self.max_noise <= NOISE_THRESHOLD
            and self.avg_dup <= MAX_DUP_RATIO
            and self.short_ratio <= SHORT_CHUNK_RATIO_LIMIT
        )


@dataclass
class ChunkResult:
    chunks: list[str]
    params: dict
    quality: ChunkQuality
    strategy: str = "unknown"
    raw_len: int = 0
    clean_len: int = 0

    @property
    def passed(self) -> bool:
        return self.quality.passed

    @property
    def params_hash(self) -> str:
        return hashlib.md5(json.dumps(self.params, sort_keys=True).encode()).hexdigest()[:8]

    def to_markdown(self, source_name: str) -> str:
        lines = [
            "---",
            f"source: {source_name}",
            f"strategy: {self.strategy}",
            f"chunk_size: {self.params['chunk_size']}",
            f"chunk_overlap: {self.params['chunk_overlap']}",
            f"num_chunks: {len(self.chunks)}",
            f"raw_len: {self.raw_len}",
            f"clean_len: {self.clean_len}",
            f"avg_noise: {self.quality.avg_noise:.1f}",
            f"avg_dup: {self.quality.avg_dup:.2f}",
            f"short_ratio: {self.quality.short_ratio:.2f}",
            f"passed: {self.passed}",
            "---",
            "",
        ]
        for i, ch in enumerate(self.chunks, 1):
            ns = self.quality.noise_scores[i - 1] if i - 1 < len(self.quality.noise_scores) else None
            dr = self.quality.dup_ratios[i - 1] if i - 1 < len(self.quality.dup_ratios) else None
            noise_text = f"{ns:.1f}" if ns is not None else "N/A"
            dup_text = f"{dr:.2f}" if dr is not None else "N/A"
            lines.append(f"## Chunk {i}  _(noise={noise_text}, dup={dup_text})_")
            lines.append(ch)
            lines.append("")
        return "\n".join(lines)


def _slice_preserving_words(s: str, chunk_size: int) -> list[str]:
    """Split a long run of text into <= chunk_size pieces without cutting
    inside a word. Falls back to hard slicing only if a single "word" (e.g.
    one token with no spaces at all) itself exceeds chunk_size.

    Used for text that reached the "no sentence boundary found" fallback —
    most commonly long Hebrew/Greek quotations, which rarely contain ASCII
    sentence punctuation, so naive s[i:i+chunk_size] slicing risks cutting
    mid-word (and, for Hebrew, mid-niqud).
    """
    # Prefer clause boundaries (Hebrew sof pasuq) if present, else whitespace.
    tokens = re.split(r"(\s+|\u05C3)", s)
    pieces: list[str] = []
    buf = ""
    for tok in tokens:
        if len(buf) + len(tok) <= chunk_size:
            buf += tok
        else:
            if buf.strip():
                pieces.append(buf.strip())
            if len(tok) > chunk_size:
                # Single token longer than chunk_size (no spaces to break on)
                # — only remaining safe option is a hard slice of that token.
                for i in range(0, len(tok), chunk_size):
                    pieces.append(tok[i:i + chunk_size].strip())
                buf = ""
            else:
                buf = tok
    if buf.strip():
        pieces.append(buf.strip())
    return [p for p in pieces if p]


def _paragraph_overlap_tail(units: list[str], overlap_chars: int, joiner: str = "\n\n") -> list[str]:
    """[SPRINT29-B-Overlap] Smallest suffix of already-buffered paragraphs whose
    joined length >= overlap_chars, used to seed the next chunk. units[0] is
    always excluded so the buffer never carries its entire content forward
    (guarantees forward progress). Whole paragraphs only — never a mid-paragraph
    cut. Empty when overlap is disabled or only one paragraph is buffered.
    """
    if overlap_chars <= 0 or len(units) <= 1:
        return []
    tail: list[str] = []
    total = 0
    for u in reversed(units[1:]):
        tail.insert(0, u)
        total += len(u) + len(joiner)
        if total >= overlap_chars:
            break
    # A single large trailing paragraph can overshoot the target overlap
    # badly (an English commentary paragraph is often 400-600 chars vs a
    # 120-char target). Bound it: if the seed exceeds ~2x the target, trim
    # only its oldest paragraph to a word-safe tail — still never a mid-word
    # cut (per SPRINT29-B-Overlap constraint), just a shorter carry.
    cap = overlap_chars * 2
    joined_len = sum(len(u) + len(joiner) for u in tail)
    if joined_len > cap and tail:
        trimmed = _word_safe_tail(tail[0], overlap_chars)
        tail = ([trimmed] + tail[1:]) if trimmed else tail[1:]
    return tail


def _word_safe_tail(text: str, max_chars: int) -> str:
    """[SPRINT29-B-Overlap] Longest suffix of `text` up to max_chars that begins
    at a whitespace or Hebrew sof-pasuq boundary — never cuts mid-word or
    mid-original-language. Returns "" when no safe boundary exists within the
    window (overlap is skipped rather than risk a mid-word cut). Used to prepend
    preceding context to per-sentence chunks in the mixed/original-language
    path, where sentences are emitted individually (no accumulation buffer).
    """
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text.strip()
    window = text[-max_chars:]
    m = re.search(r"[\s׃]", window)
    if m:
        return window[m.start():].strip()
    return ""


def _separators() -> list[str]:
    # "\u05C3" = Hebrew sof pasuq (verse-end punctuation) — biblical Hebrew
    # rarely uses ASCII periods, so without this a long Hebrew quotation
    # falls through every separator above it and gets cut mid-clause by the
    # final "" (character-level) fallback.
    return ["\n\n", "\n", "다. ", "요. ", ". ", "! ", "? ", "\u05C3 ", "\u05C3", " ", ""]


def _simple_noise(chunk: str) -> float:
    if not chunk:
        return 100.0
    return calculate_noise_score(chunk, file_type="txt")["score"]


def _dup_ratio(prev: str, curr: str) -> float:
    if not prev:
        return 0.0
    a, b = set(prev.split()), set(curr.split())
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _evaluate(chunks: list[str]) -> ChunkQuality:
    noise = [_simple_noise(c) for c in chunks]
    dups = [0.0] + [_dup_ratio(chunks[i - 1], chunks[i]) for i in range(1, len(chunks))]
    short_ratio = sum(1 for c in chunks if len(c.strip()) < MIN_CHUNK_CHARS) / max(len(chunks), 1)
    return ChunkQuality(noise_scores=noise, dup_ratios=dups, short_ratio=short_ratio)


def _split_recursive(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_separators(),
        length_function=len,
    )
    return [c.strip() for c in splitter.split_text(text) if len(c.strip()) >= MIN_CHUNK_CHARS]


def _split_by_paragraphs(text: str, chunk_size: int, chunk_overlap: int) -> tuple[list[str], str]:
    if split_paragraphs is None:
        return _split_recursive(text, chunk_size, chunk_overlap), "recursive-fallback"

    paras = split_paragraphs(text)
    if not paras:
        return _split_recursive(text, chunk_size, chunk_overlap), "recursive-empty"

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    # [SPRINT29-B-Overlap] flush() carries a boundary-preserving paragraph
    # overlap into the next buffer, but only on a size-triggered flush
    # (carry_overlap=True). Structural flushes — before switching to the
    # sentence/original-language path, and the final end-of-document flush —
    # pass carry_overlap=False so a page/section transition is not blurred and
    # so the last chunk is not duplicated.
    def flush(carry_overlap: bool = False) -> None:
        nonlocal buf, buf_len
        if buf:
            chunk = "\n\n".join(buf).strip()
            if len(chunk) >= MIN_CHUNK_CHARS:
                chunks.append(chunk)
            if carry_overlap:
                seed = _paragraph_overlap_tail(buf, chunk_overlap)
                if seed:
                    buf = list(seed)
                    buf_len = len("\n\n".join(buf))
                    return
        buf = []
        buf_len = 0

    for p in paras:
        p = p.strip()
        if not p:
            continue

        para_lang = detect_paragraph_language(p) if detect_paragraph_language is not None else None
        lang = para_lang.label if para_lang is not None else "other"
        has_original_language = bool(para_lang and para_lang.has_original_language)

        if len(p) > int(chunk_size * 1.5) or lang == "mixed" or has_original_language:
            flush(carry_overlap=False)
            sents = split_sentences_mixed(p) if split_sentences_mixed is not None else (split_sentences(p) if split_sentences is not None else [])
            if sents:
                if lang == "mixed" or has_original_language:
                    # [SPRINT29-B-Overlap] Per-sentence chunks (no accumulation
                    # buffer) get a word-safe preceding-context prefix. The
                    # current sentence is never cut — only the *previous*,
                    # already-emitted sentence's tail is borrowed, at a
                    # whitespace/sof-pasuq boundary — so original-language
                    # protection on the current unit is preserved.
                    prev = ""
                    for s in sents:
                        prefix = _word_safe_tail(prev, chunk_overlap) if prev else ""
                        if len(s) <= chunk_size:
                            piece = f"{prefix} {s}".strip() if prefix else s
                            chunks.append(piece if len(piece) <= chunk_size else s)
                        else:
                            chunks.extend(_slice_preserving_words(s, chunk_size))
                        prev = s
                    continue

                para_chunks = _merge_sentence_fragments(sents, max_chars=chunk_size, overlap_chars=chunk_overlap)
                if para_chunks and len(para_chunks[-1]) < MIN_CHUNK_CHARS and len(para_chunks) > 1:
                    tail = para_chunks.pop()
                    para_chunks[-1] = f"{para_chunks[-1]} {tail}".strip()
                chunks.extend(para_chunks)
                continue

            chunks.extend(_split_recursive(p, chunk_size, chunk_overlap))
            continue

        next_len = len(p) if not buf else buf_len + 2 + len(p)
        if buf and next_len > chunk_size:
            flush(carry_overlap=True)   # sets buf to overlap seed (or empties it)
        buf.append(p)
        buf_len = len("\n\n".join(buf))

    flush(carry_overlap=False)
    return chunks if chunks else _split_recursive(text, chunk_size, chunk_overlap), "paragraph-first"


def chunk_once(text: str, chunk_size: int, chunk_overlap: int) -> ChunkResult:
    params = {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}

    if normalize_pipeline_text is None:
        raise RuntimeError("normalize_pipeline_text import failed. core/text_normalizer.py를 확인하세요.")

    raw_text = text or ""
    clean_text = normalize_pipeline_text(raw_text)

    chunks, strategy = _split_by_paragraphs(clean_text, chunk_size, chunk_overlap)
    quality = _evaluate(chunks)

    return ChunkResult(
        chunks=chunks,
        params=params,
        quality=quality,
        strategy=strategy,
        raw_len=len(raw_text),
        clean_len=len(clean_text),
    )


def _candidate_score(r: ChunkResult) -> tuple[bool, float, float, float, int]:
    return (
        not r.passed,
        r.quality.avg_noise,
        r.quality.avg_dup,
        r.quality.short_ratio,
        len(r.chunks),
    )


def optimize_chunks(text: str, doc_type: str) -> ChunkResult:
    """Sprint 1: Use config.yaml defaults exclusively (single source of truth).
    
    Sprint 2: Dynamic presets/grid-search will be re-enabled by setting
    SPRINT1_USE_CONFIG_DEFAULTS = False.
    """
    # Sprint 1: bypass PRESETS and GRID search; use config.yaml only
    if SPRINT1_USE_CONFIG_DEFAULTS:
        from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
        chunk_size = DEFAULT_CHUNK_SIZE
        chunk_overlap = DEFAULT_CHUNK_OVERLAP
    else:
        # Sprint 2: restore dynamic presets and grid search
        ext = doc_type.lower().lstrip(".")
        preset = PRESETS.get(ext, PRESETS["default"])
        chunk_size = preset["chunk_size"]
        chunk_overlap = preset["chunk_overlap"]

    if SPRINT1_USE_CONFIG_DEFAULTS:
        # Sprint 1: single-pass with config defaults (no grid search)
        return chunk_once(text, chunk_size, chunk_overlap)

    # Sprint 2: restore grid search
    candidates: list[ChunkResult] = [chunk_once(text, chunk_size, chunk_overlap)]

    for cs in GRID_SIZES:
        for co in GRID_OVERLAPS:
            if co >= cs:
                continue
            candidates.append(chunk_once(text, cs, co))

    return min(candidates, key=_candidate_score)


def save_optimized_md(result: ChunkResult, source_name: str, output_dir: Path, stem: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{stem}_chunks_{result.params_hash}.md"
    md_path.write_text(result.to_markdown(source_name), encoding="utf-8")
    return md_path

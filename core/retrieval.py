"""
DBMA Phase II — Production Retrieval Core (v1.0)
===================================================

TASK 1: Production Query Pipeline
TASK 2: Production Retrieval API (QueryProcessor, RetrievalEngine, RankingEngine, ContextAssembler, CitationBuilder, ResponseFormatter)
TASK 3: Metadata-first Filtering
TASK 4: Embedding Cache (SHA256 + incremental + batch)
TASK 5: Hybrid Retrieval Optimization (metadata → BM25 → vector → theological → ranking → dedup → top-K)
TASK 6: Performance Profiling hooks
TASK 7: Integration with TSU Engine, Gold Standard, Benchmark, Regression

All modules are production-grade with type hints, docstrings, and deterministic behavior.

Usage:
    from core.retrieval import QueryProcessor, RetrievalEngine, RankingEngine

    engine = RetrieityEngine()
    processor = QueryProcessor(engine)

    result = processor.process("Romans 5:3 — what does Paul say about suffering?")
    print(result.response_package)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import time
import tracemalloc
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.config import DEFAULT_TSU_DATASET_PATH, RETRIEVAL_DOCUMENT_CAP

# [SPRINT17-RG-3] Runtime usage verification — additive logging only, no logic change.
logger = logging.getLogger(__name__)


# ============================================================
# SECTION 1: DATA MODELS
# ============================================================

@dataclass
class ScriptureReference:
    """Parsed Bible scripture reference."""
    book_id: str
    chapter: int
    verse_start: int
    verse_end: Optional[int] = None

    def to_string(self) -> str:
        if self.verse_end and self.verse_end != self.verse_start:
            return f"{self.book_id} {self.chapter}:{self.verse_start}-{self.verse_end}"
        return f"{self.book_id} {self.chapter}:{self.verse_start}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "chapter": self.chapter,
            "verse_start": self.verse_start,
            "verse_end": self.verse_end,
        }


@dataclass
class ParsedQuery:
    """Result of query parsing — contains all detected metadata."""
    original_query: str
    intent: str  # "exegesis", "comparison", "devotional", "theological", "cross-reference", "unknown"
    scripture_refs: list[ScriptureReference] = field(default_factory=list)
    detected_books: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    language: str = "en"
    author: str = ""
    source_book: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "intent": self.intent,
            "scripture_refs": [r.to_string() for r in self.scripture_refs],
            "detected_books": self.detected_books,
            "themes": self.themes,
            "keywords": self.keywords,
            "language": self.language,
            "author": self.author,
            "source_book": self.source_book,
        }


@dataclass
class RankedCandidate:
    """A single candidate TSU after ranking with scores."""
    tsu_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    vector_score: float = 0.0
    bm25_score: float = 0.0
    theological_score: float = 0.0
    final_score: float = 0.0
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tsu_id": self.tsu_id,
            "content": self.content[:500],
            "metadata": self.metadata,
            "vector_score": round(self.vector_score, 4),
            "bm25_score": round(self.bm25_score, 4),
            "theological_score": round(self.theological_score, 4),
            "final_score": round(self.final_score, 4),
            "explanation": self.explanation,
        }


@dataclass
class PerformanceMetrics:
    """Profiling metrics for a single retrieval call."""
    total_ms: float = 0.0
    intent_detection_ms: float = 0.0
    scripture_detection_ms: float = 0.0
    metadata_extraction_ms: float = 0.0
    embedding_ms: float = 0.0
    cache_hit_rate: float = 0.0
    vector_search_ms: float = 0.0
    ranking_ms: float = 0.0
    theological_scoring_ms: float = 0.0
    deduplication_ms: float = 0.0
    context_assembly_ms: float = 0.0
    citation_builder_ms: float = 0.0
    embedding_cache_hits: int = 0
    embedding_cache_misses: int = 0
    bm25_scoring_ms: float = 0.0
    memory_peak_mb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ms": round(self.total_ms, 2),
            "intent_detection_ms": round(self.intent_detection_ms, 2),
            "scripture_detection_ms": round(self.scripture_detection_ms, 2),
            "metadata_extraction_ms": round(self.metadata_extraction_ms, 2),
            "embedding_ms": round(self.embedding_ms, 2),
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "vector_search_ms": round(self.vector_search_ms, 2),
            "ranking_ms": round(self.ranking_ms, 2),
            "theological_scoring_ms": round(self.theological_scoring_ms, 2),
            "deduplication_ms": round(self.deduplication_ms, 2),
            "context_assembly_ms": round(self.context_assembly_ms, 2),
            "citation_builder_ms": round(self.citation_builder_ms, 2),
            "embedding_cache_hits": self.embedding_cache_hits,
            "embedding_cache_misses": self.embedding_cache_misses,
            "memory_peak_mb": round(self.memory_peak_mb, 2),
        }


@dataclass
class ResponsePackage:
    """Final response package for a query."""
    query_id: str
    question: str
    candidates: list[RankedCandidate]
    top_k_results: list[RankedCandidate]
    performance_metrics: PerformanceMetrics
    parsed_query: ParsedQuery
    scripture_context: list[str] = field(default_factory=list)
    theological_summary: str = ""
    llm_context_block: str = ""
    citations: "list[Citation]" = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "question": self.question,
            "parsed_query": self.parsed_query.to_dict(),
            "top_k_results": [r.to_dict() for r in self.top_k_results],
            "total_candidates": len(self.candidates),
            "performance_metrics": self.performance_metrics.to_dict(),
            "scripture_context": self.scripture_context[:5],
            "theological_summary": self.theological_summary,
            "llm_context_block": self.llm_context_block[:2000],
            "citations": [citation.__dict__ for citation in self.citations],
        }


# ============================================================
# SECTION 2: BOOK ID REGISTRY (from theological_scorer.py)
# ============================================================

BOOK_ID_TO_NAMES: dict[str, list[str]] = {
    # Old Testament — Pentateuch
    "GEN": ["genesis", "gen", "창세기", "창세"],
    "EXO": ["exodus", "exo", "출애굽기", "출애", "출"],
    "LEV": ["leviticus", "lev", "레위기", "레"],
    "NUM": ["numbers", "num", "민수기", "민수", "민"],
    "DEU": ["deuteronomy", "deu", "신명기", "신명", "신"],
    # Historical books
    "JOS": ["joshua", "jos", "여호수아", "여호수"],
    "JDG": ["judges", "jdge", "사사기", "사사"],
    "RUT": ["ruth", "rut", "루트", "룻"],
    "1SA": ["1 samuel", "1 sa", "1sa", "사무엘상"],
    "2SA": ["2 samuel", "2 sa", "2sa", "사무엘하"],
    "1KI": ["1 kings", "1 ki", "1ki", "열왕기상"],
    "2KI": ["2 kings", "2 ki", "2ki", "열왕기하"],
    "1CH": ["1 chronicles", "1 ch", "1ch", "역대상"],
    "2CH": ["2 chronicles", "2 ch", "2ch", "역대하"],
    "EZR": ["ezra", "ezr", "에스라", "에스"],
    "NEH": ["nehemiah", "neh", "느헤미야", "느헤"],
    "EST": ["esther", "est", "에스더", "에스"],
    # Wisdom books
    "JOB": ["job", "욥기", "욥"],
    "PSA": ["psalms", "psalm", "psa", "시편", "시", "찬미"],
    "PRO": ["proverbs", "prov", "pro", "잠언", "잠", "지혜"],
    "ECC": ["ecclesiastes", "ecc", "전도서", "전도"],
    "SOL": ["song of solomon", "sol", "아래의 노래", "찬가"],
    # Prophetic books — Major
    "ISA": ["isaiah", "isa", "이사야", "이사"],
    "JER": ["jeremiah", "jer", "예레미야", "예레"],
    "LAM": ["lamentations", "lam", "애가", "애", "통곡"],
    "EZE": ["ezekiel", "eze", "에제키엘", "에스겔"],
    "DAN": ["daniel", "dan", "다니엘", "다니"],
    # Prophetic books — Minor
    "HOS": ["hosea", "hos", "호세아", "호"],
    "JOEL": ["joel", "요엘", "요"],
    "AMOS": ["amos", "아모스", "아"],
    "OBA": ["obadiah", "oba", "오바댜", "오바디아", "오"],
    "JON": ["jonah", "jon", "요나", "욘"],
    "MIC": ["micah", "mic", "미가", "미"],
    "NAM": ["nahum", "nam", "나훔", "나"],
    "HAB": ["habakkuk", "hab", "하박국", "하바"],
    "ZEP": ["zephaniah", "zep", "스바냐"],
    "HAG": ["haggai", "hag", "학개"],
    "ZEC": ["zechariah", "zec", "스가랴"],
    "MAL": ["malachi", "mal", "말라기", "말라"],
    # New Testament — Gospels
    "MAT": ["matthew", "matt", "mt", "mat", "마태복음", "마태", "마타", "마"],
    "MRK": ["mark", "mk", "mrk", "mar", "마르코복음", "마르코", "마가복음", "마가", "막", "막달"],
    "LUK": ["luke", "lk", "luk", "루카복음", "루카", "눋", "누가"],
    "JHN": ["john", "jn", "jhn", "요한복음", "요한", "요복", "요"],
    # New Testament — History
    "ACT": ["acts", "act", "사도행전", "사도", "사행"],
    # New Testament — Pauline Epistles
    "ROM": ["romans", "rom", "ro", "로마서", "로마", "롬"],
    "1CO": ["1 corinthians", "1 cor", "1 co", "1co", "고린도전서", "고린도전", "고전"],
    "2CO": ["2 corinthians", "2 cor", "2 co", "2co", "고린도후서", "고린도후", "고후"],
    "GAL": ["galatians", "gal", "갈라티아", "갈", "갈서"],
    "EPH": ["ephesians", "eph", "에베소서", "에베", "엡"],
    "PHP": ["philippians", "phil", "php", "phl", "빌립보서", "빌립", "빌립보", "빌"],
    "COL": ["colossians", "col", "골로새서", "골라", "골"],
    "1TH": ["1 thessalonians", "1 thess", "1 th", "1the", "1th", "살례전서", "살례전", "살전"],
    "2TH": ["2 thessalonians", "2 thess", "2 th", "2the", "2th", "살례후서", "살례후", "살후"],
    "1TI": ["1 timothy", "1 tim", "1 ti", "1ti", "디모데전서", "디모데전", "전"],
    "2TI": ["2 timothy", "2 tim", "2 ti", "2ti", "디모데후서", "디모데후", "후"],
    "TIT": ["titus", "tit", "디도서", "디도"],
    "PHM": ["philemon", "phm", "빌레몬서", "빌레몬"],
    # New Testament — General Epistles
    "HEB": ["hebrews", "heb", "히브리서", "히브", "히브리"],
    "JAS": ["james", "jas", "야고보서", "야고", "雅", "약"],
    "1PE": ["1 peter", "1 pe", "1pe", "베드로전서", "베드로전", "전서"],
    "2PE": ["2 peter", "2 pe", "2pe", "베드로후서", "베드로후", "후서"],
    "1JN": ["1 john", "1 jn", "1jn", "요한일서", "요한일", "일서"],
    "2JN": ["2 john", "2 jn", "2jn", "요한이서", "요한이"],
    "3JN": ["3 john", "3 jn", "3jn", "요한삼서", "요한삼"],
    "JUD": ["jude", "jud", "유다서", "유다"],
    # New Testament — Prophecy
    "REV": ["revelation", "rev", "요한의 묵시록", "묵시록", "계", "계시록"],
}

# Reverse mapping
NAME_TO_BOOK_ID: dict[str, str] = {}
for book_id, names in BOOK_ID_TO_NAMES.items():
    for name in names:
        NAME_TO_BOOK_ID[name] = book_id

# Thematic keywords (from theological_scorer.py)
THEME_KEYWORDS: dict[str, list[str]] = {
    "creation": ["create", "creation", "created", "beginning", "form", "make", "maker"],
    "covenant": ["covenant", "promise", "oath", "sign", "everlasting", "perpetual"],
    "redemption": ["redeem", "deliver", "save", "salvation", "ransom", "rescue"],
    "judgment": ["judge", "judgment", "condemn", "punish", "wrath", "justice"],
    "mercy": ["mercy", "grace", "compassion", "forgive", "forgiveness", "pity"],
    "faith": ["faith", "believe", "trust", "belief", "faithful", "faithfulness"],
    "worship": ["worship", "praise", "adoration", "holy", "glory", "worshipped"],
    "law": ["law", "commandment", "statute", "ordinance", "torah", "decree"],
    "kingdom": ["kingdom", "king", "reign", "sovereign", "throne", "rule"],
    "spirit": ["spirit", "soul", "breath", "heart", "inner", "spiritual"],
    "love": ["love", "loved", "charity", "dear", "beloved"],
    "wisdom": ["wisdom", "wise", "understanding", "knowledge", "discern"],
    "prophecy": ["prophesy", "prophecy", "vision", "reveal", "revelation", "seer"],
    "resurrection": ["rise", "raised", "resurrect", "life", "death", "alive", "living"],
}


# ============================================================
# SECTION 3: QUERY PARSER — TASK 1 + TASK 3 (Metadata-first)
# ============================================================

class QueryParser:
    """
    Parses raw user queries into structured metadata.

    Pipeline:
        Query → Intent Detection → Scripture Reference Detection → Metadata Extraction → Keyword Extraction

    Returns: ParsedQuery object.
    """

    # Intent detection patterns
    INTENT_PATTERNS: dict[str, str] = {
        "exegesis": r"(?:explain|what does|meaning of|interpret|study|analysis|deep dive)",
        "comparison": r"(?:compare|versus|vs\.?|difference between|similarities|unlike|while\s+\w+|but\s+\w+)",
        "devotional": r"(?:how|why|what can we|personal|application|practical|spiritual growth|encourage)",
        "theological": r"(?:doctrine|theology|belief|doctrinal|systematic|nature of|attribute of|God's nature)",
        "cross-reference": r"(?:cross.?ref|other place|where else|parallel|same theme|similar passage|related)",
    }

    def __init__(self) -> None:
        self._intent_patterns = {k: re.compile(v, re.IGNORECASE) for k, v in self.INTENT_PATTERNS.items()}

    def parse(self, query: str) -> ParsedQuery:
        """Parse a raw query into structured metadata."""
        parsed = ParsedQuery(original_query=query, intent="unknown")

        # 1. Intent detection (existing)
        parsed.intent = self._detect_intent(query)

        # 2. Standalone book detection (NEW — P0 fix for PT-RESEARCH-004)
        standalone_books = self._detect_books_standalone(query)

        # 3. Scripture reference detection (existing, unmodified)
        parsed.scripture_refs = self._extract_scripture_refs(query)

        # 4. Merge: detected_books = scripture refs + standalone books (UNIQUE by BOOK_ID)
        detected: list[str] = [r.book_id for r in parsed.scripture_refs]
        for b in standalone_books:
            if b not in detected:
                detected.append(b)
        parsed.detected_books = detected
        if parsed.detected_books:
            parsed.source_book = parsed.detected_books[0]

        # 5. Theme extraction (existing, unmodified)
        parsed.themes = self._extract_themes(query)

        # 6. Keyword extraction (existing, unmodified)
        parsed.keywords = self._extract_keywords(query)

        return parsed

    def _detect_intent(self, query: str) -> str:
        """Detect the intent of a query."""
        for intent, pattern in self._intent_patterns.items():
            if pattern.search(query):
                return intent
        # Default to theological if it contains biblical terms
        if re.search(r'(?:God|Jesus|Christ|Holy Spirit|law|grace|faith|covenant|kingdom|sin)', query, re.IGNORECASE):
            return "theological"
        return "unknown"

    def _extract_scripture_refs(self, query: str) -> list[ScriptureReference]:
        """Extract Bible scripture references from query text."""
        refs: list[ScriptureReference] = []

        # Pattern 1: Full book name + chapter:verse (e.g., "Romans 5:3")
        full_pattern = re.compile(
            r'(Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|'
             '1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|'
             'Ezra|Nehemiah|Esther|Job|Psalms|Psalm|Proverbs|Prov|Ecclesiastes|'
             'Song of Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|'
             'Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|'
             'Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|'
             'Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|'
             'Philippians|Colossians|1 Thessalonians|2 Thessalonians|'
             '1 Timothy|2 Timothy|Titus|Philemon|Hebrews|James|'
             '1 Peter|2 Peter|1 John|2 John|3 John|Jude|Revelation)'
             r'\s+(\d+):(\d+)(?:-(\d+))?',
            re.IGNORECASE
        )

        for match in full_pattern.finditer(query):
            book_name = match.group(1).lower()
            chapter = int(match.group(2))
            verse_start = int(match.group(3))
            verse_end = int(match.group(4)) if match.group(4) else None

            # Resolve book name to book_id
            book_id = self._resolve_book_name(book_name)
            if book_id:
                refs.append(ScriptureReference(
                    book_id=book_id,
                    chapter=chapter,
                    verse_start=verse_start,
                    verse_end=verse_end,
                ))

        # Pattern 2: Abbreviated book name + chapter:verse (e.g., "Rom 5:3", "Gen 1:1")
        #
        # [SPRINT18-A] Whitespace made optional (\s+ -> \s*) so no-space
        # short-form references like "요3:16" (vs. "요 3:16") also match.
        # The trailing \b was dropped rather than kept: Hangul syllables
        # and digits are both \w in Python's Unicode-aware regex, so
        # "요" immediately followed by "3" never had a \b between them in
        # the first place — \b\s+ never actually required a space for
        # Korean aliases, it silently just never matched the no-space
        # form at all. The leading \b is kept and still does the real
        # work: "필요3:16" does not match because "필" and "요" are both
        # \w with no boundary between them, so the alias itself can't
        # start mid-word — the immediate (\d+): requirement after the
        # alias (with optional whitespace) is specific enough on its own
        # that a trailing \b is not needed for disambiguation.
        abbr_pattern = re.compile(
            r'\b(' + '|'.join(NAME_TO_BOOK_ID.keys()) + r')\s*(\d+):(\d+)(?:-(\d+))?',
            re.IGNORECASE
        )

        for match in abbr_pattern.finditer(query):
            book_name = match.group(1)
            chapter = int(match.group(2))
            verse_start = int(match.group(3))
            verse_end = int(match.group(4)) if match.group(4) else None

            book_id = NAME_TO_BOOK_ID.get(book_name.lower())
            if book_id:
                refs.append(ScriptureReference(
                    book_id=book_id,
                    chapter=chapter,
                    verse_start=verse_start,
                    verse_end=verse_end,
                ))

        return refs

    def _extract_themes(self, query: str) -> list[str]:
        """Extract theological themes from query."""
        query_lower = query.lower()
        themes_found: list[str] = []

        for theme, keywords in THEME_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                if theme not in themes_found:
                    themes_found.append(theme)

        return themes_found

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract meaningful keywords from query."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "in", "on", "at", "to", "for", "of", "with", "by", "from", "and", "or",
            "but", "not", "what", "which", "who", "how", "does", "do", "did",
            "can", "would", "should", "could", "this", "that", "these", "those",
            "it", "its", "we", "our", "they", "them", "their", "his", "her",
            "has", "have", "had", "all", "each", "every", "both", "few", "more",
            "most", "some", "any", "such", "there", "here", "when", "where",
            "why", "if", "then", "than", "so", "no", "yes", "about",
        }

        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_keywords: list[str] = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords[:20]  # Cap at 20 keywords

    def _detect_books_standalone(self, query: str) -> list[str]:
        """Detect BOOK IDs from a query WITHOUT requiring chapter:verse.

        [SPRINT18-B-1] Matching priority (longest-match-first, actually
        enforced — previously the docstring claimed this but the
        implementation only sorted candidates by length without ever
        suppressing shorter overlapping matches, so e.g. "마가복음"
        (a valid 4-char MRK alias) also matched the single-char MAT alias
        "마" it happens to contain, silently adding MAT to detected_books.
        Confirmed root cause of a JHN/MAT/JOEL contamination bug found via
        SPRINT17 Book-level Benchmark, reproduced in the live Chat UI):

          1. Aliases are tried longest-first (sorted by length descending).
          2. Once a span of the (cleaned) query text is claimed by a match,
             any shorter alias whose occurrence falls entirely within an
             already-claimed span is suppressed — matching is no longer
             "any substring present", it is "first (longest) claim wins
             per text span".
          3. Aliases shorter than 2 characters are excluded from the
             candidate list entirely — a lone Hangul syllable (e.g. "요",
             "마") is inherently too ambiguous to trust as a standalone
             book signal. A full scripture reference with a syllable-length
             book abbreviation (e.g. "요 3:16") is still handled correctly
             by _extract_scripture_refs()/_resolve_book_name(), which is a
             separate, stricter regex-anchored path unaffected by this
             method or this exclusion.
          4. A match is also rejected if the character immediately before
             it is alphanumeric (Hangul syllables count as alphanumeric in
             Python) — this catches a 2+ char alias embedded mid-word
             rather than filtered by (3), e.g. "요한" (a legitimate 2-char
             JHN alias) inside "필요한가" ("necessary" + question ending).
             The trailing side is deliberately NOT checked: Korean
             particles (을/를/이/가/은/는/의/...) attach directly with no
             separating space (e.g. "요한복음을"), so requiring a
             non-word character after the match would reject valid,
             common phrasing.

        Returns unique book IDs in order of (first-claimed-span) appearance.
        """
        if not hasattr(self, '_alias_cache'):
            all_names: list[tuple[str, str]] = []
            for book_id, names in BOOK_ID_TO_NAMES.items():
                for name in names:
                    cleaned_name = name.lower().strip()
                    if len(cleaned_name) < 2:
                        continue
                    all_names.append((cleaned_name, book_id))
            all_names.sort(key=lambda x: len(x[0]), reverse=True)
            self._alias_cache = all_names

        cleaned = re.sub(r'\d+장|\d+\s*:?\s*\d*', '', query.lower()).strip()

        claimed = [False] * len(cleaned)
        seen: set[str] = set()
        result: list[str] = []

        for alias, book_id in self._alias_cache:
            start = 0
            while True:
                idx = cleaned.find(alias, start)
                if idx == -1:
                    break
                span = range(idx, idx + len(alias))
                # Leading word-boundary check: a Hangul/alnum character
                # immediately before the match means the alias is embedded
                # mid-word (e.g. "요한" inside "필요한가") rather than a
                # genuine standalone book reference — reject it. Trailing
                # side is deliberately left unchecked: Korean particles
                # (을/를/이/가/은/는/의/...) attach directly with no space
                # (e.g. "요한복음을"), so requiring a non-word character
                # after the match would reject valid, common phrasing.
                leading_ok = idx == 0 or not cleaned[idx - 1].isalnum()
                if leading_ok and not any(claimed[i] for i in span):
                    for i in span:
                        claimed[i] = True
                    if book_id not in seen:
                        seen.add(book_id)
                        result.append(book_id)
                start = idx + 1

        return result

    def _resolve_book_name(self, name: str) -> Optional[str]:
        """Resolve a full Bible book name to its abbreviation."""
        key = name.lower().strip()
        return NAME_TO_BOOK_ID.get(key)


# ============================================================
# SECTION 4: EMBEDDING CACHE — TASK 4
# ============================================================

class EmbeddingCache:
    """
    SHA256-based embedding cache with incremental update and batch generation.

    Cache entries are stored as JSON files keyed by SHA256(text)[:16].
    Supports:
      - Lookup by hash
      - Incremental insert
      - Batch insert
      - Cache validation (integrity check)
      - Cache rebuild from TSU dataset
    """

    def __init__(self, cache_dir: str = "cache/embeddings") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._hit_count: int = 0
        self._miss_count: int = 0

    def _hash_text(self, text: str) -> str:
        """Compute SHA256 hash of text (first 16 chars)."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def lookup(self, text: str, embed_fn) -> Optional[list[float]]:
        """
        Lookup cached embedding. If not found, compute and cache it.

        Args:
            text: The text to look up/embed.
            embed_fn: Function(text) -> list[float] that computes embeddings.

        Returns:
            Cached or computed embedding vector, or None on failure.
        """
        hash_key = self._hash_text(text)
        cache_path = self.cache_dir / f"{hash_key}.json"

        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                self._hit_count += 1
                return data.get("vector")
            except (json.JSONDecodeError, IOError):
                pass

        self._miss_count += 1
        # Compute embedding
        try:
            vector = embed_fn(text)
            if vector is not None:
                self.insert(hash_key, text, vector)
            return vector
        except Exception:
            return None

    def insert(self, hash_key: str, text: str, vector: list[float]) -> bool:
        """Insert a single embedding into cache."""
        try:
            cache_path = self.cache_dir / f"{hash_key}.json"
            with open(cache_path, "w") as f:
                json.dump({"text": text[:500], "vector": vector, "hash": hash_key}, f)
            return True
        except IOError:
            return False

    def batch_insert(self, items: list[tuple[str, list[float]]]) -> int:
        """
        Batch-insert embeddings. Each item is (text, vector).

        Returns:
            Number of successfully inserted items.
        """
        count = 0
        for text, vector in items:
            hash_key = self._hash_text(text)
            if self.insert(hash_key, text, vector):
                count += 1
        return count

    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return self._hit_count / total

    def validate(self) -> dict[str, Any]:
        """Validate cache integrity. Returns validation report."""
        files = list(self.cache_dir.glob("*.json"))
        valid = 0
        invalid = 0
        errors: list[str] = []

        for f in files:
            try:
                with open(f, "r") as fh:
                    data = json.load(fh)
                    if "vector" not in data or "text" not in data:
                        invalid += 1
                        errors.append(f"{f.name}: missing 'vector' or 'text' field")
                    else:
                        valid += 1
            except (json.JSONDecodeError, IOError):
                invalid += 1
                errors.append(f"{f.name}: corrupted file")

        return {
            "total_files": len(files),
            "valid": valid,
            "invalid": invalid,
            "hit_rate": self.get_hit_rate(),
            "errors": errors[:10],  # Cap error list
        }

    def rebuild(self, tsu_dataset_path: str | Path, embed_fn) -> int:
        """
        Rebuild cache from a TSU JSONL dataset.

        Args:
            tsu_dataset_path: Path to TSU JSONL file.
            embed_fn: Function(text) -> list[float].

        Returns:
            Number of successfully rebuilt embeddings.
        """
        tsu_path = Path(tsu_dataset_path)
        if not tsu_path.exists():
            return 0

        count = 0
        items: list[tuple[str, list[float]]] = []

        with open(tsu_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("$"):
                    continue
                try:
                    tsu = json.loads(line)
                    content = tsu.get("content", "")
                    if content:
                        hash_key = self._hash_text(content)
                        cache_path = self.cache_dir / f"{hash_key}.json"
                        if not cache_path.exists():
                            items.append((content, embed_fn(content)))
                except (json.JSONDecodeError, KeyError):
                    continue

        return self.batch_insert(items)


# ============================================================
# SECTION 5: BM25 KEYWORD SCORING — TASK 5
# ============================================================

def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, strip punctuation, split."""
    text = text.lower()
    import string as _string
    translator = str.maketrans("", "", _string.punctuation)
    text = text.translate(translator)
    return [t for t in text.split() if len(t) > 0]


def bm25_score(query_tokens: list[str], doc_text: str, k1: float = 1.2, b: float = 0.75) -> float:
    """
    Compute BM25 keyword relevance score.

    Score = avg over query terms of:
        IDF(qt) * (freq(qt) * (k1 + 1)) / (freq(qt) + k1 * (1 - b + b * doc_len / avg_doc_len))

    Args:
        query_tokens: Tokenized query.
        doc_text: Document text string.
        k1: Term frequency saturation parameter (default 1.2).
        b: Length normalization parameter (default 0.75).

    Returns:
        BM25 score normalized to [0, 1].
    """
    if not query_tokens or not doc_text:
        return 0.0

    doc_tokens = _tokenize(doc_text)
    if not doc_tokens:
        return 0.0

    doc_len = len(doc_tokens)
    avg_doc_len: float = max(doc_len, 100.0)
    score = 0.0
    term_count = 0

    for qt in query_tokens:
        freq = doc_tokens.count(qt)
        if freq == 0:
            continue

        idf = math.log(2.0 / (freq + 1)) + 1.0
        numerator = freq * (k1 + 1)
        denominator = freq + k1 * (1 - b + b * doc_len / avg_doc_len)
        term_score = idf * (numerator / denominator)

        score += term_score
        term_count += 1

    if term_count > 0:
        avg_score = score / term_count
        # Guard against negative scores (e.g., from rare terms in large corpora)
        safe_avg = max(0.0, avg_score)
        normalized = math.log(1 + safe_avg) / math.log(2)
        return min(normalized, 1.0)

    return 0.0


# ============================================================
# SECTION 6: TF-IDF VECTOR SPACE — TASK 5
# ============================================================

class TfidfVectorizer:
    """Pure Python TF-IDF vectorizer for TSU content indexing."""

    def __init__(self) -> None:
        self.idf: dict[str, float] = {}
        self.vocab_size: int = 0
        self._document_count: int = 0

    def fit(self, documents: list[list[str]]) -> "TfidfVectorizer":
        """Compute IDF weights from document corpus."""
        n_docs = len(documents)
        if n_docs == 0:
            return self

        df = Counter()
        for doc_tokens in documents:
            unique_terms = set(doc_tokens)
            df.update(unique_terms)

        self.idf = {}
        for term, doc_freq in df.items():
            self.idf[term] = math.log((n_docs + 1) / (doc_freq + 1)) + 1

        self.vocab_size = len(df)
        self._document_count = n_docs
        return self

    def transform(self, document: list[str]) -> dict[str, float]:
        """Transform tokenized document to TF-IDF sparse vector."""
        if not document:
            return {}

        tf = Counter(document)
        max_tf = max(tf.values()) if tf else 1

        vector: dict[str, float] = {}
        for term, tf_val in tf.items():
            if term in self.idf:
                normalized_tf = 0.5 + 0.5 * (tf_val / max_tf)
                vector[term] = normalized_tf * self.idf[term]

        return vector

    def cosine_similarity(self, vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        """Compute cosine similarity between two sparse TF-IDF vectors."""
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0

        dot_product = sum(vec_a[t] * vec_b[t] for t in common)
        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)


# ============================================================
# SECTION 7: THEOLOGICAL SCORER — integration with sprint7
# ============================================================

def compute_theological_score(
    query: str,
    tsu: dict[str, Any],
    weights: Optional[dict[str, float]] = None,
) -> tuple[float, dict[str, Any]]:
    """
    Compute theological relevance score (SSA + TRS + SUS).

    final_score = 0.45 * SSA + 0.35 * TRS + 0.20 * SUS

    Args:
        query: The user query string.
        tsu: TSU dict with 'content', 'verse_mapping', 'themes'.
        weights: Optional score component weights.

    Returns:
        (total_score, breakdown) tuple.
    """
    if weights is None:
        weights = {"ssa": 0.45, "trs": 0.35, "sus": 0.20}

    # Scripture Alignment Score (SSA)
    ssa = _scripture_alignment_score(query, tsu)

    # Thematic Relevance Score (TRS)
    trs = _thematic_relevance_score(query, tsu)

    # Sermon Usability Score (SUS)
    sus = _sermon_usability_score(tsu)

    total = weights["ssa"] * ssa + weights["trs"] * trs + weights["sus"] * sus

    breakdown = {
        "scripture_alignment": round(ssa, 4),
        "thematic_relevance": round(trs, 4),
        "sermon_usability": round(sus, 4),
    }

    return round(total, 4), breakdown


def _scripture_alignment_score(query: str, tsu: dict[str, Any]) -> float:
    """Compute scripture alignment score (0-1)."""
    verse_map = tsu.get("verse_mapping", {})
    if not verse_map or not verse_map.get("book_id"):
        return 0.0

    # Parse refs from query and TSU content
    query_refs = _parse_refs_from_text(query)
    tsu_content_refs = _parse_refs_from_text(tsu.get("content", ""))
    all_refs = query_refs + tsu_content_refs

    if not all_refs:
        source_file = tsu.get("source_file", "")
        for book_id in BOOK_ID_TO_NAMES:
            if book_id.upper() in source_file.upper():
                if verse_map.get("book_id") == book_id:
                    return 0.5
        return 0.1

    score = 0.0
    tsu_book = verse_map["book_id"]
    tsu_chapter = verse_map.get("chapter", 1)

    for qref in query_refs:
        if qref.book_id == tsu_book:
            if qref.chapter == tsu_chapter:
                score += 0.8
            elif abs(qref.chapter - tsu_chapter) == 1:
                score += 0.3

    return min(score, 1.0)


def _parse_refs_from_text(text: str) -> list[ScriptureReference]:
    """Parse scripture references from text."""
    refs: list[ScriptureReference] = []
    pattern = re.compile(
        r'(Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|'
         '1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|'
         'Ezra|Nehemiah|Esther|Job|Psalms|Psalm|Proverbs|Prov|Ecclesiastes|'
         'Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|'
         'Matthew|Mark|Luke|John|Acts|'
         'Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|'
         'Philippians|Colossians|1 Thessalonians|2 Thessalonians|'
         '1 Timothy|2 Timothy|Titus|Hebrews|James|'
         '1 Peter|2 Peter|1 John|2 Peter|3 John|Jude|Revelation)'
         r'\s+(\d+):(\d+)(?:-(\d+))?',
        re.IGNORECASE
    )

    for match in pattern.finditer(text):
        book_name = match.group(1).lower()
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        verse_end = int(match.group(4)) if match.group(4) else None

        book_id = NAME_TO_BOOK_ID.get(book_name)
        if book_id:
            refs.append(ScriptureReference(
                book_id=book_id,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
            ))

    return refs


def _thematic_relevance_score(query: str, tsu: dict[str, Any]) -> float:
    """Compute thematic relevance score (0-1)."""
    query_tokens = set(t.lower() for t in re.findall(r'\b[a-zA-Z]{3,}\b', query))
    tsu_content = tsu.get("content", "")
    query_lower = query.lower()
    content_lower = tsu_content.lower()

    theme_scores: list[float] = []
    for theme, keywords in THEME_KEYWORDS.items():
        hits_query = any(kw in query_lower for kw in keywords)
        hits_content = any(kw in content_lower for kw in keywords)

        if hits_query and hits_content:
            theme_scores.append(1.0)
        elif hits_query or hits_content:
            theme_scores.append(0.5)

    theme_score = max(theme_scores) if theme_scores else 0.0

    tsu_words = set(t.lower() for t in re.findall(r'\b[a-zA-Z]{3,}\b', tsu_content[:1000]))
    if query_tokens and tsu_words:
        intersection = query_tokens & tsu_words
        union = query_tokens | tsu_words
        jaccard = len(intersection) / len(union) if union else 0.0
    else:
        jaccard = 0.0

    return min(0.6 * theme_score + 0.4 * jaccard, 1.0)


def _sermon_usability_score(tsu: dict[str, Any]) -> float:
    """Compute sermon usability score (0-1)."""
    content = tsu.get("content", "")
    if not content:
        return 0.0

    score = 0.0
    content_len = len(content)

    if 200 <= content_len <= 800:
        score += 0.5
    elif 100 <= content_len < 200:
        score += 0.3
    elif content_len > 800:
        score += 0.3

    periods = content.count('.') + content.count('!') + content.count('?')
    if periods >= 2:
        score += 0.3
    elif periods == 1:
        score += 0.15

    academic_terms = [
        "therefore", "because", "thus", "consequently", "nevertheless",
        "justified", "sanctification", "righteousness", "grace",
        "exegesis", "hermeneutic", "theology", "doctrinal", "biblical",
    ]
    content_lower = content.lower()
    academic_hits = sum(1 for t in academic_terms if t in content_lower)
    if academic_hits >= 3:
        score += 0.2
    elif academic_hits >= 1:
        score += 0.1

    confidence = tsu.get("confidence", 0.5)
    score *= (0.5 + confidence * 0.5)

    return min(score, 1.0)


# ============================================================
# SECTION 8: RETRIEVAL ENGINE — TASK 2 + TASK 5
# ============================================================

class RetrievalEngine:
    """
    Production-grade retrieval engine implementing hybrid search pipeline.

    Pipeline:
        Metadata filter → BM25 → Vector search → Theological scoring → Hybrid ranking → Deduplication → Top-K
    """

    def __init__(
        self,
        tsu_dataset_path: str | Path,
        candidate_k: int = 100,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "dbma_sermon",
    ) -> None:
        logger.debug("[SPRINT17-RG-3] RetrievalEngine.__init__ entry point hit | tsu_dataset_path=%s", tsu_dataset_path)
        self.tsu_dataset_path = Path(tsu_dataset_path)
        self.candidate_k = candidate_k
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name

        # Load TSU dataset
        self.tsus: list[dict[str, Any]] = []
        self._load_corpus()

        # [SPRINT28-C] TF-IDF is a fallback-only path — retrieve() STEP 3
        # only reads self.vectors when the BGE-M3 embedding backend is
        # unavailable/fails. Measured (SPRINT28-C Preflight): eagerly
        # building it here accounted for ~80% of this engine's memory
        # footprint (19.1 KB/TSU vs 4.81 KB/TSU for the TSU corpus itself)
        # even in the common case where the embedding backend is healthy
        # all session and self.vectors is never read at all. Built lazily
        # on first actual need instead — see _ensure_tfidf_index().
        self.tfidf_vectorizer = TfidfVectorizer()
        self.vectors: list[dict[str, float]] = []
        self._tfidf_index_built = False

    def _ensure_tfidf_index(self) -> None:
        """Build the in-memory TF-IDF fallback index on first actual need
        (idempotent — safe to call before every fallback attempt)."""
        if self._tfidf_index_built:
            return
        self._build_tfidf_index()
        self._tfidf_index_built = True

    def _load_corpus(self) -> None:
        """Load TSU dataset from JSONL file."""
        if not self.tsu_dataset_path.exists():
            raise FileNotFoundError(f"TSU dataset not found: {self.tsu_dataset_path}")

        with open(self.tsu_dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("$"):
                    try:
                        self.tsus.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    def _build_tfidf_index(self) -> None:
        """Build TF-IDF index from TSU corpus."""
        token_docs = [_tokenize(t.get("content", "")) for t in self.tsus]
        self.tfidf_vectorizer.fit(token_docs)
        self.vectors = [self.tfidf_vectorizer.transform(tokens) for tokens in token_docs]

    def retrieve(
        self,
        parsed_query: ParsedQuery,
        k_output: int = 10,
        embedding_cache: Optional[EmbeddingCache] = None,
    ) -> tuple[list[RankedCandidate], PerformanceMetrics]:
        """
        Execute the full hybrid retrieval pipeline.

        Pipeline:
            1. Metadata-first filtering (Bible book/chapter/verse)
            2. BM25 keyword scoring (candidate generation)
            3. Vector search (semantic via BGE-M3 when embedding_cache is
               supplied; else/on-failure: in-memory TF-IDF cosine similarity)
            4. Theological scoring
            5. Hybrid ranking
            6. Deduplication
            7. Top-K selection

        Returns:
            (ranked_candidates, performance_metrics)
        """
        t_total = time.perf_counter()
        metrics = PerformanceMetrics()

        # Authority boundary: BM25 candidate generation (STEP 2) never
        # supplies more than self.candidate_k indices downstream, so
        # requesting k_output > candidate_k would silently return fewer
        # results than asked for on the BM25-hit path while the no-hit
        # fallback path (which uses the full candidate_pool) would not be
        # bounded the same way. Clamp here so both paths agree.
        if k_output > self.candidate_k:
            logger.debug(
                "[retrieve] k_output=%d exceeds candidate_k=%d — clamping",
                k_output, self.candidate_k,
            )
            k_output = self.candidate_k

        # --- STEP 1: Metadata-first filtering ---
        t0 = time.perf_counter()
        filtered_indices = self._metadata_filter(parsed_query)
        metrics.metadata_extraction_ms = (time.perf_counter() - t0) * 1000

        # Determine candidate pool
        candidate_pool = filtered_indices if filtered_indices else list(range(len(self.tsus)))

        # --- STEP 2: BM25 keyword scoring (candidate generation) ---
        t0 = time.perf_counter()
        bm25_scores: dict[int, float] = {}
        for idx in candidate_pool:
            content = self.tsus[idx].get("content", "")
            if not content:
                continue
            score = bm25_score(parsed_query.keywords, content)
            if score > 0:
                bm25_scores[idx] = score
        if hasattr(metrics, 'bm25_scoring_ms'):
            metrics.bm25_scoring_ms = (time.perf_counter() - t0) * 1000

        # Top-K by BM25 for next stages
        bm25_top_k_indices = sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)[:self.candidate_k]

        # P0 FIX: If BM25 produced no hits within the metadata-filtered pool,
        # fall back to ALL metadata-filtered candidates. This prevents pipeline
        # collapse when Korean TSU content lacks English book-name keywords.
        if not bm25_top_k_indices:
            bm25_top_k_indices = [(idx, 0.0) for idx in candidate_pool]

        # --- STEP 3: Vector search ---
        # Semantic (BGE-M3 via core.embedder) when an EmbeddingCache is
        # supplied; falls back to in-memory TF-IDF cosine similarity per
        # candidate whenever the embedding backend is unavailable/fails, so
        # retrieval never hard-fails for lack of Ollama.
        t0 = time.perf_counter()
        vector_similarities: dict[int, float] = {}

        semantic_embedder = None
        query_semantic_vec: Optional[list[float]] = None
        if embedding_cache is not None:
            try:
                from core.embedder import get_embedder
                semantic_embedder = get_embedder()
                query_semantic_vec = semantic_embedder.encode(
                    parsed_query.original_query, normalize_embeddings=True
                )
            except Exception:
                semantic_embedder = None
                query_semantic_vec = None

        for idx, bm25_val in bm25_top_k_indices:
            content = self.tsus[idx].get("content", "")
            if not content:
                continue

            sim = None
            if semantic_embedder is not None and query_semantic_vec is not None:
                try:
                    doc_vec = embedding_cache.lookup(
                        content,
                        lambda t: semantic_embedder.encode(t, normalize_embeddings=True),
                    )
                    if doc_vec is not None and len(doc_vec) == len(query_semantic_vec):
                        # Both vectors are L2-normalized, so dot product == cosine similarity.
                        sim = sum(a * b for a, b in zip(query_semantic_vec, doc_vec))
                except Exception:
                    sim = None

            if sim is None:
                # [SPRINT28-C] Built lazily here, not at __init__ — see
                # _ensure_tfidf_index() docstring.
                self._ensure_tfidf_index()
                if idx < len(self.vectors):
                    # In-memory TF-IDF cosine similarity (fast, no embedding backend needed)
                    query_vector = self.tfidf_vectorizer.transform(
                        _tokenize(parsed_query.original_query)
                    )
                    sim = self.tfidf_vectorizer.cosine_similarity(query_vector, self.vectors[idx])

            if sim is not None:
                vector_similarities[idx] = sim
        metrics.vector_search_ms = (time.perf_counter() - t0) * 1000

        # --- STEP 4: Theological scoring ---
        t0 = time.perf_counter()
        
        # P0 FIX: Score ALL ranking candidates, not just vector_similarities.
        # When BM25 produces no hits (Korean content), fallback pool needs
        # full theological coverage to prevent empty scores.
        score_targets = set(vector_similarities.keys()) if vector_similarities else candidate_pool
        score_targets = set(score_targets)  # deduplicate
        
        theological_scores: dict[int, float] = {}
        theological_breakdowns: dict[int, dict[str, Any]] = {}
        for idx in score_targets:
            tsu = self.tsus[idx]
            score, breakdown = compute_theological_score(
                parsed_query.original_query, tsu
            )
            theological_scores[idx] = score
            theological_breakdowns[idx] = breakdown
        
        # Ensure all ranking_indices have theological scores (may be missing if 
        # fallback pool differs from score_targets)
        for idx in set(candidate_pool):
            if idx not in theological_scores:
                tsu = self.tsus[idx]
                score, breakdown = compute_theological_score(
                    parsed_query.original_query, tsu
                )
                theological_scores[idx] = score
                theological_breakdowns[idx] = breakdown
        
        metrics.theological_scoring_ms = (time.perf_counter() - t0) * 1000

        # --- STEP 5: Hybrid ranking ---
        t0 = time.perf_counter()
        
        # P0 FIX: Build the candidate index set from the actual pool used,
        # not just bm25_scores. This prevents zero-candidate output when
        # BM25 produces no hits (e.g., Korean TSU content with English query).
        ranking_indices = set(bm25_scores.keys()) if bm25_scores else candidate_pool
        ranking_indices = set(ranking_indices)  # deduplicate
        
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 0.0
        max_vector = max(vector_similarities.values()) if vector_similarities else 0.0
        max_theo = max(theological_scores.values()) if theological_scores else 0.0

        candidates: list[RankedCandidate] = []
        
        # Normalize to [0, 1] (use min-max normalization; handle zero-max case)
        for idx in ranking_indices:
            tsu = self.tsus[idx]
            
            norm_bm25 = bm25_scores.get(idx, 0.0) / max_bm25 if max_bm25 > 0 else 0.5
            norm_vector = vector_similarities.get(idx, 0.0) / max_vector if max_vector > 0 else 0.0
            norm_theo = theological_scores.get(idx, 0.0)

            # Hybrid score: 0.30 * BM25 + 0.25 * vector + 0.45 * theological
            base_score = (0.30 * norm_bm25 + 0.25 * norm_vector + 0.45 * norm_theo)

            # [SPRINT19-C] Evidence Reliability Adjustment — a narrow (+/-10%)
            # multiplicative correction, never a primary ranking signal. This
            # keeps semantic relevance (base_score above) dominant: a large
            # relevance gap between two candidates always outweighs the
            # confidence adjustment, so a highly "confident" but topically
            # weak match cannot outrank a topically strong one (SPRINT19-C
            # Preflight §3). provenance.confidence comes from
            # scripts/build_tsu_dataset.py's Scripture Evidence Resolver
            # (SPRINT19-B); TSUs without it (no scripture reference detected
            # in their content, 76.23% of the corpus) get the neutral
            # midpoint 0.5 rather than being penalized for lacking chapter
            # metadata they were never going to have.
            evidence_confidence = tsu.get("provenance", {}).get("confidence", 0.5)
            final_score = base_score * (0.9 + 0.1 * evidence_confidence)

            breakdown = theological_breakdowns.get(idx, {})

            explanation = (
                f"bm25={norm_bm25:.3f}×0.30={0.30*norm_bm25:.3f} | "
                f"vector={norm_vector:.3f}×0.25={0.25*norm_vector:.3f} | "
                f"theological={norm_theo:.3f}×0.45={0.45*norm_theo:.3f} | "
                f"base={base_score:.3f} × evidence_adj={0.9 + 0.1*evidence_confidence:.3f} | "
                f"total={final_score:.3f}"
            )

            candidates.append(RankedCandidate(
                tsu_id=tsu.get("tsu_id", ""),
                content=tsu.get("content", ""),
                metadata=tsu,
                vector_score=round(norm_vector, 4),
                bm25_score=round(norm_bm25, 4),
                theological_score=round(norm_theo, 4),
                final_score=round(final_score, 4),
                explanation=explanation,
            ))

        # Deterministic sorting: by final_score desc, then tsu_id asc
        candidates.sort(key=lambda x: (-x.final_score, x.tsu_id))
        metrics.ranking_ms = (time.perf_counter() - t0) * 1000

        # --- STEP 6: Deduplication ---
        t0 = time.perf_counter()
        deduplicated = self._deduplicate(candidates)
        metrics.deduplication_ms = (time.perf_counter() - t0) * 1000

        # --- STEP 7: Document diversity + Top-K selection ---
        top_k = self._apply_document_diversity(
            deduplicated, k_output, RETRIEVAL_DOCUMENT_CAP
        )

        metrics.total_ms = (time.perf_counter() - t_total) * 1000
        return top_k, metrics

    def _apply_document_diversity(
        self,
        candidates: list[RankedCandidate],
        k: int,
        cap: int,
    ) -> list[RankedCandidate]:
        """Limit how many chunks from the same document appear in the top-k,
        so an over-chunked document (e.g. 2 Kings Vol.13, 67% of the 2KI pool)
        cannot monopolize the results. Score order is preserved; candidates
        over the per-document cap are held in overflow and used to backfill
        when the capped pass yields fewer than k (single-document corpus,
        candidate_pool < k). cap <= 0 disables the layer (legacy behavior)."""
        if cap <= 0:
            return candidates[:k]

        counts: dict[str, int] = {}
        selected: list[RankedCandidate] = []
        overflow: list[RankedCandidate] = []
        for c in candidates:
            key = c.metadata.get("document_id") or c.metadata.get("source_file") or c.tsu_id
            if counts.get(key, 0) < cap:
                counts[key] = counts.get(key, 0) + 1
                selected.append(c)
            else:
                overflow.append(c)
            if len(selected) == k:
                return selected
        # k 미달 시 cap 초과분(score 순서 유지)으로 보충 — 항상 최대 k개 보장
        return (selected + overflow)[:k]

    def _metadata_filter(self, parsed_query: ParsedQuery) -> list[int]:
        """Filter TSUs by metadata (book_id, chapter range). Returns list of valid indices."""
        if not parsed_query.detected_books:
            # No metadata constraints — return all indices
            return list(range(len(self.tsus)))

        filtered: list[int] = []
        for idx, tsu in enumerate(self.tsus):
            verse_map = tsu.get("verse_mapping", {})
            if not verse_map:
                continue

            tsu_book = verse_map.get("book_id", "")
            if tsu_book in parsed_query.detected_books:
                # If chapter constraint exists, check it
                if parsed_query.scripture_refs:
                    for ref in parsed_query.scripture_refs:
                        if ref.book_id == tsu_book:
                            tsu_chapter = verse_map.get("chapter", 0)
                            # Accept if within ±2 chapters of referenced chapter
                            if abs(tsu_chapter - ref.chapter) <= 2:
                                filtered.append(idx)
                                break
                else:
                    filtered.append(idx)

        return filtered if filtered else list(range(len(self.tsus)))

    def _deduplicate(self, candidates: list[RankedCandidate]) -> list[RankedCandidate]:
        """Remove near-duplicate TSUs by content overlap."""
        seen_hashes: set[str] = set()
        deduplicated: list[RankedCandidate] = []

        for candidate in candidates:
            content_hash = hashlib.md5(candidate.content[:200].encode("utf-8")).hexdigest()[:8]
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduplicated.append(candidate)

        return deduplicated


# ============================================================
# SECTION 9: CONTEXT ASSEMBLER & CITATION BUILDER — TASK 1
# ============================================================

class ContextAssembler:
    """Assembles final context block for LLM consumption."""

    def assemble(self, top_k: list[RankedCandidate], parsed_query: ParsedQuery) -> tuple[str, list[str]]:
        """
        Assemble the LLM context block and scripture context.

        Returns:
            (llm_context_block, scripture_context_list)
        """
        scripture_contexts: list[str] = []
        context_parts: list[str] = []

        for i, candidate in enumerate(top_k):
            tsu_id = candidate.tsu_id
            content = candidate.content
            score = candidate.final_score

            # Extract verse_mapping if available
            vm = candidate.metadata.get("verse_mapping", {})
            if vm and vm.get("book_id"):
                book_id = vm["book_id"]
                chapter = vm.get("chapter", "?")
                v_start = vm.get("verse_start", "?")
                v_end = vm.get("verse_end", v_start)
                ref_str = f"{book_id} {chapter}:{v_start}"
                if v_end != v_start:
                    ref_str += f"-{v_end}"
            else:
                ref_str = "Unknown reference"

            scripture_contexts.append(f"[{ref_str}] Score={score:.3f}: {content[:300]}")

            context_parts.append(
                f"<context id=\"{tsu_id}\" score=\"{score:.4f}\">\n"
                f"{content}\n</context>\n"
            )

        llm_context_block = "\n".join(context_parts)
        return llm_context_block, scripture_contexts


@dataclass
class Citation:
    """Structured, human-verifiable citation for a single evidence unit.

    retrieval_score and evidence_confidence are deliberately separate:
    retrieval_score answers "why did this rank highly", evidence_confidence
    answers "why do we trust this as evidence" (SPRINT19-B provenance).
    """
    citation_id: str
    tsu_id: str
    scripture_reference: str
    source_title: Optional[str]
    source_author: Optional[str]
    document_id: Optional[str]
    content_excerpt: str
    evidence_confidence: Optional[float]
    retrieval_score: float
    source_file: Optional[str] = None
    language: Optional[str] = None
    source_type: Optional[str] = None

    def __str__(self) -> str:
        return (
            f"[{self.citation_id}] {self.scripture_reference}\n"
            f"    Score: {self.retrieval_score:.4f}\n"
            f"    Content: {self.content_excerpt}..."
        )


class CitationBuilder:
    """Builds formatted citations from ranked candidates."""

    def build_citations(self, top_k: list[RankedCandidate]) -> list[Citation]:
        """Build structured Citation objects for all ranked candidates."""
        citations: list[Citation] = []

        for i, candidate in enumerate(top_k, 1):
            vm = candidate.metadata.get("verse_mapping", {})
            if vm and vm.get("book_id"):
                book_id = vm["book_id"]
                chapter = vm.get("chapter", "?")
                v_start = vm.get("verse_start", "?")
                v_end = vm.get("verse_end", v_start)

                if v_end != v_start:
                    ref = f"{book_id} {chapter}:{v_start}-{v_end}"
                else:
                    ref = f"{book_id} {chapter}:{v_start}"
            else:
                ref = "Unmapped passage"

            citations.append(Citation(
                citation_id=str(i),
                tsu_id=candidate.tsu_id,
                scripture_reference=ref,
                source_title=candidate.metadata.get("title"),
                source_author=candidate.metadata.get("author"),
                document_id=candidate.metadata.get("document_id"),
                content_excerpt=candidate.content[:200],
                evidence_confidence=candidate.metadata.get("provenance", {}).get("confidence"),
                retrieval_score=candidate.final_score,
                source_file=candidate.metadata.get("source_file"),
                language=candidate.metadata.get("language"),
                source_type=candidate.metadata.get("source_type"),
            ))

        return citations


class ResponseFormatter:
    """Formats the final response package."""

    def format(
        self,
        parsed_query: ParsedQuery,
        top_k: list[RankedCandidate],
        scripture_contexts: list[str],
        llm_context_block: str,
        citations: list[str],
        metrics: PerformanceMetrics,
    ) -> ResponsePackage:
        """Format all components into a ResponsePackage."""
        theological_summary = self._summarize_theology(top_k)

        return ResponsePackage(
            query_id="",  # Will be set externally
            question=parsed_query.original_query,
            candidates=top_k,
            top_k_results=top_k,
            performance_metrics=metrics,
            parsed_query=parsed_query,
            scripture_context=scripture_contexts,
            theological_summary=theological_summary,
            llm_context_block=llm_context_block,
            citations=citations,
        )

    def _summarize_theology(self, top_k: list[RankedCandidate]) -> str:
        """Generate a brief theological summary from top results."""
        if not top_k:
            return "No theological data available."

        themes_counter = Counter()
        for candidate in top_k[:3]:
            content_lower = candidate.content.lower()
            for theme, keywords in THEME_KEYWORDS.items():
                if any(kw in content_lower for kw in keywords):
                    themes_counter[theme] += 1

        dominant_themes = [t for t, _ in themes_counter.most_common(3)]
        return (
            f"Primary theological themes: {', '.join(dominant_themes) if dominant_themes else 'none detected'}. "
            f"Top score: {top_k[0].final_score:.4f} ({top_k[0].tsu_id})"
        )


# ============================================================
# SECTION 10: QUERY PROCESSOR — TASK 2 (unified API)
# ============================================================

class QueryProcessor:
    """
    Production query processor implementing the full pipeline.

    Pipeline:
        Query → Intent Detection → Scripture Detection → Metadata Extraction → 
        Hybrid Retrieval → Theological Scoring → Ranking → Context Builder → Response Package
    """

    def __init__(self, engine: Optional[RetrievalEngine] = None) -> None:
        self.parser = QueryParser()
        if engine is not None:
            self.engine = engine
        else:
            self.engine = RetrievalEngine(
                tsu_dataset_path=DEFAULT_TSU_DATASET_PATH
            )
        self.cache = EmbeddingCache()
        self.context_assembler = ContextAssembler()
        self.citation_builder = CitationBuilder()
        self.response_formatter = ResponseFormatter()

    def process(
        self,
        query: str,
        query_id: str = "",
        k: int = 10,
    ) -> ResponsePackage:
        """
        Process a raw query through the full production pipeline.

        Args:
            query: The user query string.
            query_id: Optional identifier for this query.
            k: Number of results to return.

        Returns:
            ResponsePackage with all components.
        """
        logger.debug("[SPRINT17-RG-3] QueryProcessor.process entry point hit | query_id=%s", query_id)
        # 1. Parse query (intent + scripture refs + metadata)
        parsed_query = self.parser.parse(query)

        # 2. Retrieve via hybrid engine
        candidates, metrics = self.engine.retrieve(
            parsed_query, k_output=k, embedding_cache=self.cache
        )

        # 3. Assemble context
        llm_context_block, scripture_contexts = self.context_assembler.assemble(candidates[:k], parsed_query)

        # 4. Build citations
        citations = self.citation_builder.build_citations(candidates[:k])

        # 5. Format response
        response = self.response_formatter.format(
            parsed_query, candidates[:k], scripture_contexts,
            llm_context_block, citations, metrics,
        )
        response.query_id = query_id

        return response


# ============================================================
# SECTION 11: BENCHMARK INTEGRATION — TASK 7
# ============================================================

def run_benchmark_integration(
    gs_path: str | Path = "output/SPRINT5_ENGINEERING_VALIDATION/dbma_gold_standard_v3.json",
    tsu_path: str | Path = DEFAULT_TSU_DATASET_PATH,
    k_output: int = 10,
) -> dict[str, Any]:
    """
    Run benchmark against Gold Standard v3 using production retrieval core.

    Integrates with existing benchmark engine metrics computation.

    Returns:
        Benchmark results dict compatible with existing dashboard format.
    """
    gs_path = Path(gs_path)
    if not gs_path.exists():
        return {"error": "Gold standard file not found", "gs_path": str(gs_path)}

    with open(gs_path, "r", encoding="utf-8") as f:
        gs_data = json.load(f)

    queries = gs_data.get("queries", [])
    if not queries:
        return {"error": "No queries in gold standard file"}

    engine = RetrievalEngine(tsu_dataset_path=tsu_path)
    processor = QueryProcessor(engine)

    # Load TSU IDs for validation
    tsu_id_set: set[str] = set()
    with open(tsu_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("$"):
                continue
            try:
                tsu = json.loads(line)
                tsu_id_set.add(tsu.get("tsu_id", ""))
            except json.JSONDecodeError:
                continue

    # Metrics counters
    hit_at_1 = 0
    hit_at_5 = 0
    total_hits = 0
    rr_score = 0.0
    ndcg_at_10 = 0.0
    n_queries = 0
    latencies_ms: list[float] = []

    for query in queries:
        qid = query.get("id", "")
        question = query.get("question", "")
        expected_ids = set(query.get("expected_tsu_ids", [])) & tsu_id_set

        if not expected_ids:
            continue

        t_start = time.perf_counter()
        response = processor.process(question, query_id=qid, k=k_output)
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        latencies_ms.append(elapsed_ms)

        ranked = response.top_k_results
        if not ranked:
            continue

        n_queries += 1

        # Precision@1
        if ranked[0].tsu_id in expected_ids:
            hit_at_1 += 1

        # Hit@5
        for r in ranked[:5]:
            if r.tsu_id in expected_ids:
                hit_at_5 += 1

        # Hit@10
        for r in ranked[:10]:
            if r.tsu_id in expected_ids:
                total_hits += 1

        # MRR
        for rank_i, r in enumerate(ranked):
            if r.tsu_id in expected_ids:
                rr_score += 1.0 / (rank_i + 1)
                break

        # nDCG@10
        ideal_hits = min(10, len(expected_ids))
        actual_dcg = sum(
            1.0 / math.log2(rank_i + 2)
            for rank_i, r in enumerate(ranked[:10])
            if r.tsu_id in expected_ids
        )
        ideal_dcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
        if ideal_dcg > 0:
            ndcg_at_10 += actual_dcg / ideal_dcg

    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0
    n_queries_max = max(n_queries, 1)

    precision_at_1 = hit_at_1 / n_queries_max
    precision_at_5 = hit_at_5 / (n_queries_max * 5)
    mrr = rr_score / n_queries_max
    ndcg = ndcg_at_10 / n_queries_max
    hit_rate = (hit_at_1 + hit_at_5) / (n_queries_max * 2)

    return {
        "id": "DBMA-BENCHMARK-PRODUCTION-CORE",
        "version": "2.0.0",
        "mode": "production_core_pipeline",
        "gold_standard_version": "DBMA-GOLD-STANDARD-v3",
        "tsu_dataset_size": len(tsu_id_set),
        "total_gs_queries": len(queries),
        "queries_evaluated": n_queries,
        "avg_latency_ms": round(avg_latency, 2),
        "metrics": {
            "precision_at_1": round(precision_at_1, 4),
            "precision_at_5": round(precision_at_5, 4),
            "mrr": round(mrr, 4),
            "ndcg_at_10": round(ndcg, 4),
            "hit_rate_at_10": round(hit_rate, 4),
        },
    }


# ============================================================
# SECTION 12: REGRESSION INTEGRATION — TASK 7
# ============================================================

def compare_with_regression(
    current_results: dict[str, Any],
    baseline_path: str = "output/SPRINT5_ENGINEERING_VALIDATION/baseline_v1.json",
) -> dict[str, Any]:
    """
    Compare current benchmark results with regression baseline.

    Returns:
        Regression comparison dict with deltas and flag status.
    """
    baseline = {"metrics": {}}
    if os.path.exists(baseline_path):
        with open(baseline_path, "r") as f:
            baseline = json.load(f)

    current_metrics = current_results.get("metrics", {})
    baseline_metrics = baseline.get("metrics", {})

    deltas: dict[str, float] = {}
    flags: dict[str, str] = {}
    threshold = 0.05  # 5% change threshold

    for metric in ["precision_at_1", "precision_at_5", "mrr", "ndcg_at_10", "hit_rate_at_10"]:
        current_val = current_metrics.get(metric, 0)
        baseline_val = baseline_metrics.get(metric, 0)
        delta = current_val - baseline_val
        deltas[metric] = round(delta, 4)

        if abs(delta) >= threshold:
            if delta > 0:
                flags[metric] = "IMPROVEMENT"
            else:
                flags[metric] = "DEGRADATION"
        else:
            flags[metric] = "STABLE"

    return {
        "comparison_type": "current_vs_baseline",
        "deltas": deltas,
        "flags": flags,
        "overall_status": (
            "IMPROVING" if all(f == "IMPROVEMENT" for f in flags.values()) else
            "STABLE" if all(f == "STABLE" for f in flags.values()) else
            "MIXED"
        ),
    }


# ============================================================
# SECTION 13: MODULE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Quick demo of the production pipeline
    print("DBMA Phase II — Production Retrieval Core")
    print("=" * 50)

    engine = RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH)
    processor = QueryProcessor(engine)

    test_query = "What does Romans 5:3 say about suffering and hope?"
    response = processor.process(test_query, query_id="demo-1", k=5)

    print(f"\nQuery: {response.question}")
    print(f"Parsed intent: {response.parsed_query.intent}")
    print(f"Parsed books: {response.parsed_query.detected_books}")
    print(f"Parsed themes: {response.parsed_query.themes}")
    print(f"\nTop result:")
    if response.top_k_results:
        top = response.top_k_results[0]
        print(f"  TSU ID: {top.tsu_id}")
        print(f"  Final score: {top.final_score:.4f}")
        print(f"  Explanation: {top.explanation}")
    else:
        print("  (no results)")

    print(f"\nPerformance metrics:")
    for k, v in response.performance_metrics.to_dict().items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")


# ============================================================
# PT-RESEARCH-006.1: Query Enhancement Layer Integration
# ============================================================
# Production enhancement layer — overrides QueryParser with PT-006 P0 fixes:
#   1. Numbered book detection (1 Peter, 2 Chronicles, 1 Thessalonians, etc.)
#   2. Korean alias disambiguation (살전 → 1TH, 베드로전서 → 1PE, etc.)
#   3. Chapter-only reference parsing (Matthew 5 → MAT chapter=5)
#   4. Negative query confidence boundary checking
#
# If query_enhancements.py is missing or fails to import, falls back
# to the original QueryParser defined in this file.
try:
    from core.query_enhancements import EnhancedQueryParser as QueryParser
except ImportError:
    pass  # Enhancement module unavailable; use built-in QueryParser

"""DBMA TLI — KoreanTokenizer protocol and factory.

Module: core/tli/korean_tokenizer.py
Interface: KoreanTokenizer (Protocol) + create_korean_tokenizer() factory

Design notes (mirrors core/tli/spell_engine.py's TLI pattern — see that
module's docstring for the rationale):
- KoreanTokenizer is a Protocol (structural subtyping) so any adapter
  implementing `tokenize(text: str) -> list[str]` satisfies the interface.
- Factory `create_korean_tokenizer()` returns the best available adapter,
  falling back to a crash-safe no-op if the morphological analyzer isn't
  installed.
- Callers (core/retrieval.py::_tokenize) MUST NOT import kiwipiepy
  directly — always go through this module's factory, so the analyzer
  backend can change without touching the Retrieval Engine's call site.

P1 (docs/TODO.md): BM25's prior tokenizer was `text.split()` on
whitespace — Korean어절 carry agglutinated particles/endings (조사/어미),
so "성령의"/"성령께서"/"성령을" never matched each other as the same term.
This adapter uses morphological analysis (kiwipiepy) to split each word
into its content morphemes, then keeps only tags that carry retrieval-
relevant meaning (nouns/verbs/adjectives/adverbs/numbers) — particles
and sentence-ending morphemes are dropped, matching standard Korean IR
practice of indexing content morphemes only.
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)

# Content-bearing POS tags to keep (Kiwi's tagset, based on Sejong tagset):
# NNG/NNP/NNB = 일반/고유/의존 명사, NP = 대명사, NR = 수사, SN = 숫자,
# VV/VA = 동사/형용사, VX = 보조 용언, MAG = 일반부사, SL = 외국어(라틴 등).
# Dropped: JX/JKS/JKO/JKB/JKG/... (조사), EC/EF/EP/ETN/ETM (어미), SF/SP/SS (부호).
_CONTENT_TAGS = frozenset({
    "NNG", "NNP", "NNB", "NP", "NR", "SN",
    "VV", "VA", "VX", "MAG", "SL", "XR",
})


class KoreanTokenizer(Protocol):
    """Interface for a Korean-aware BM25 tokenizer."""

    def tokenize(self, text: str) -> list[str]: ...  # noqa: D102


def create_korean_tokenizer() -> "KoreanTokenizer":
    """Return the best available KoreanTokenizer implementation.

    Priority:
    1. KiwiKoreanTokenizer (kiwipiepy morphological analyzer)
    2. Fallback: whitespace tokenizer (prior behavior, crash-safe)
    """
    try:
        return _KiwiKoreanTokenizer()
    except ImportError as exc:
        logger.warning("kiwipiepy not available: %s — using whitespace fallback tokenizer", exc)
        return _WhitespaceFallbackTokenizer()
    except Exception as exc:
        logger.warning("Kiwi initialization failed: %s — using whitespace fallback tokenizer", exc)
        return _WhitespaceFallbackTokenizer()


class _KiwiKoreanTokenizer:
    """Morphological tokenizer backed by kiwipiepy.

    One Kiwi instance is expensive to construct (loads the model), so it's
    built once per adapter instance and reused across tokenize() calls —
    callers should get one adapter from create_korean_tokenizer() and
    reuse it, not call the factory per query.
    """

    def __init__(self) -> None:
        from kiwipiepy import Kiwi  # local import — see module docstring

        self._kiwi = Kiwi()

    def tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        tokens = []
        for token in self._kiwi.tokenize(text):
            if token.tag in _CONTENT_TAGS:
                tokens.append(token.form.lower())
        return tokens


class _WhitespaceFallbackTokenizer:
    """No-op fallback: prior whitespace-split behavior. Crash-safe."""

    def tokenize(self, text: str) -> list[str]:
        import string as _string

        text = text.lower()
        translator = str.maketrans("", "", _string.punctuation)
        text = text.translate(translator)
        return [t for t in text.split() if len(t) > 0]

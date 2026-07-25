"""DBMA TLI — HunspellSpellEngine adapter.

Module: core/tli/hunspell_adapter.py
Implementation of SpellEngine using the real hunspell C library
(PyHunSpell binding) with the ko_KR dictionary.

This is the ONLY place in the codebase that directly imports hunspell.
All other code (including UI) goes through spell_engine interface/factory.

[버그 수정 2026-07-24, CUE] 최초 구현은 spylls(순수 파이썬 hunspell
포맷 리더)를 썼으나, 실측 결과 이 한국어 사전(spellcheck-ko/hunspell-
dict-ko)의 접사 규칙을 spylls가 제대로 처리하지 못해 "하나님", "우리",
"사랑" 같은 기본 단어까지 오류로 잘못 판정했다(반면 "사랑하십니다"
같은 활용형은 통과하는 등 일관성도 없었음). 실제 hunspell C 라이브러리
(`brew install hunspell` + `pip install hunspell`, PyHunSpell 바인딩)로
교체한 뒤 재검증: "하나님"/"우리"/"사랑"/"합니다"(모두 활용형 포함)
정상 인식, "됬어"(오타)는 오류로, "됐어"(정타)는 정상으로 정확히
구분됨 — 조사/어미를 수동으로 떼어내는 휴리스틱이 필요 없어졌다
(hunspell 자체의 접사 규칙이 이를 처리함).

설치가 까다롭다 — pip 패키지(hunspell 0.5.5)의 setup.py가 Intel Mac
경로(`/usr/local/Cellar/hunspell/1.6.2/...`)를 하드코딩하고 있어
Apple Silicon(`/opt/homebrew/...`)에서는 그대로 안 된다. 재현 절차:
    brew install hunspell
    mkdir -p /usr/local/Cellar/hunspell/1.6.2/include
    ln -sf $(brew --prefix hunspell)/include/hunspell \
        /usr/local/Cellar/hunspell/1.6.2/include/hunspell
    ln -sf $(brew --prefix hunspell)/lib/libhunspell-1.7.dylib \
        /usr/local/lib/libhunspell.dylib
    LDFLAGS="-L/usr/local/lib" pip install hunspell
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import hunspell as hunspell_module  # noqa: F401

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent  # DBMA/
_RESOURCES_DIR = _PROJECT_ROOT / "resources" / "hunspell"

# Korean dictionary files (ko_KR.aff / ko_KR.dic) — optional
_KO_KR_AFF = _RESOURCES_DIR / "ko_KR.aff"
_KO_KR_DIC = _RESOURCES_DIR / "ko_KR.dic"

# Custom theology dictionary (always present, may be empty)
_CUSTOM_THEOLOGY_DIC = _RESOURCES_DIR / "custom_theology.dic"


def _load_custom_words() -> set[str]:
    """Load custom_theology.dic and return a set of valid words."""
    words: set[str] = set()
    if not _CUSTOM_THEOLOGY_DIC.exists():
        return words
    try:
        with open(_CUSTOM_THEOLOGY_DIC, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments, empty lines, and the first-line word count
                if not line or line.startswith("#"):
                    continue
                if line.isdigit():
                    continue
                words.add(line)
    except Exception as exc:
        logger.warning("custom_theology.dic 로드 실패: %s", exc)
    return words


# [버그 수정 2026-07-24] hunspell 자체는 사전에 있는 단어의 조사/어미
# 활용을 정확히 처리하지만(예: "합니다"), custom_theology.dic(성경책
# 이름/신학 용어)은 문자열 그대로만 등록돼 있어 "출애굽기를"처럼
# 조사가 붙으면 그대로는 못 찾는다. custom_words 매칭에만 좁혀서
# 흔한 조사를 떼고 재확인한다 — hunspell 자체 조회에는 적용하지
# 않는다(hunspell이 이미 정확하게 처리하므로 불필요).
_STRIPPABLE_JOSA = sorted([
    "으로부터", "께서는", "으로는", "로는", "에서", "에게", "부터", "까지",
    "으로", "이라고", "라고", "이나", "이며",
    "은", "는", "이", "가", "을", "를", "도", "와", "과", "의", "에", "로", "만", "며",
], key=len, reverse=True)


# ── HunspellSpellEngine ──────────────────────────────────────────────────
class HunspellSpellEngine:
    """SpellEngine implementation using the real hunspell C library
    (PyHunSpell) with the ko_KR dictionary.

    Lazy-loads the Korean dictionary and custom words on first check().
    If dictionary/library loading fails, returns empty list (crash-safe).
    """

    def __init__(self) -> None:
        self._dict: Optional[Any] = None
        self._custom_words: set[str] = _load_custom_words()
        self._initialized = False
        self._load_failed = False

    def _ensure_loaded(self) -> None:
        """Lazy-load the Korean dictionary."""
        if self._initialized:
            return

        try:
            import hunspell

            if _KO_KR_AFF.exists() and _KO_KR_DIC.exists():
                self._dict = hunspell.HunSpell(str(_KO_KR_DIC), str(_KO_KR_AFF))
                logger.info("ko_KR dictionary loaded from %s", _RESOURCES_DIR)
            else:
                logger.warning(
                    "Korean dictionary not found at %s. "
                    "Download spellcheck-ko/hunspell-dict-ko into ko_KR.aff/ko_KR.dic.",
                    _RESOURCES_DIR,
                )
                self._dict = None
        except ImportError:
            logger.warning(
                "hunspell module not installed (see hunspell_adapter.py module "
                "docstring for the brew+pip install workaround on Apple Silicon)."
            )
            self._dict = None
        except Exception as exc:
            logger.warning("Korean dictionary load failed: %s", exc)
            self._dict = None

        self._initialized = True
        if self._dict is None:
            self._load_failed = True

    def _is_custom_word_with_josa(self, word: str) -> bool:
        for suffix in _STRIPPABLE_JOSA:
            if word.endswith(suffix) and len(word) > len(suffix):
                if word[: -len(suffix)] in self._custom_words:
                    return True
        return False

    def check(self, text: str) -> list[dict]:
        """hunspell(ko_KR)로 text를 검사해 오류 후보 목록을 반환한다.

        Each item: {"word": str, "suggestions": list[str], "offset": int}
        If hunspell/dictionary unavailable, returns empty list (crash-safe).
        """
        if self._load_failed:
            return []

        self._ensure_loaded()

        if self._dict is None:
            logger.warning("Korean dictionary unavailable — spellcheck disabled.")
            return []

        results: list[dict] = []

        # Tokenize Korean text into words with offsets
        i = 0
        n = len(text)
        while i < n:
            if not (text[i].isalnum() or '가' <= text[i] <= '힣' or 'ᄀ' <= text[i] <= 'ᇿ'):
                i += 1
                continue

            j = i
            while j < n and (text[j].isalnum() or '가' <= text[j] <= '힣' or 'ᄀ' <= text[j] <= 'ᇿ'):
                j += 1

            word = text[i:j]

            if len(word) < 2:
                i = j
                continue

            if word in self._custom_words or self._is_custom_word_with_josa(word):
                i = j
                continue

            try:
                is_valid = self._dict.spell(word)  # type: ignore[union-attr]
                if not is_valid:
                    suggestions = []
                    try:
                        suggestions = list(self._dict.suggest(word))[:5]  # type: ignore[union-attr]
                    except Exception:
                        pass

                    results.append({
                        "word": word,
                        "suggestions": [str(s) for s in suggestions],
                        "offset": i,
                    })
            except Exception:
                # If lookup fails for any reason, skip this word
                pass

            i = j

        return results

    def add_to_custom_dictionary(self, word: str) -> bool:
        """Add a word to custom_theology.dic. Returns True on success."""
        try:
            with open(_CUSTOM_THEOLOGY_DIC, "a", encoding="utf-8") as f:
                f.write(f"{word}\n")
            self._custom_words.add(word)
            logger.info("Added '%s' to custom_theology.dic", word)
            return True
        except Exception as exc:
            logger.warning("custom_theology.dic 쓰기 실패: %s", exc)
            return False

    def get_custom_dictionary_path(self) -> Path:
        """Return the path to custom_theology.dic."""
        return _CUSTOM_THEOLOGY_DIC

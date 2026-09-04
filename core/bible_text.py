"""core/bible_text.py — 사용자 제공 성경 본문 JSON 로더 (ADR-031).

"연구하기 > 본문 해설" 뷰어가 절 본문을 표시하기 위한 **읽기 전용 데이터
계층**이다. TSU/RetrievalEngine 파이프라인과 완전히 분리되어 있으며,
`core/retrieval.py`나 `core/generation.py`가 이 모듈을 import 하지 않는다.

Fail-closed 원칙: 파일이 없거나(사용자가 아직 등록 안 함) JSON 스키마가
어긋나도 예외를 전파하지 않는다 — `BibleText.unavailable(reason)` 센티넬을
돌려주고, 뷰어는 안내 문구만 표시한다(앱 크래시 없음).

JSON 스키마 (`config.yaml::directories.bible_text_path`, 기본
`data/bible/reference.json`):

    {
      "version": "개역개정",
      "books": {
        "PRO": {"name": "잠언", "chapters": [["1:1 본문", "1:2 본문", ...], ...]},
        ...
      }
    }

- `books` 키는 book_id — `core.retrieval.BOOK_ID_TO_NAMES` 공간(아가 = "SOL").
  소문자/영문 약어/한글 별칭도 허용하며 로더가 정규 book_id로 변환한다.
- `chapters`: 장 배열(인덱스 = 장 − 1), 각 장은 절 문자열 배열(인덱스 = 절 − 1).
- 66권 전체가 아니어도 된다 — 존재하는 책만 뷰어에 노출된다.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from core.config import BIBLE_TEXT_PATH
from core.retrieval import BOOK_ID_TO_NAMES, NAME_TO_BOOK_ID

logger = logging.getLogger(__name__)

# `BOOK_ID_TO_NAMES` 의 첫 한글 별칭이 개신교 표준 명칭이 아닌 경우(가톨릭식
# 표기이거나 "아래의 노래" 같은 비표준 별칭) 표시명만 보정한다 —
# book_id 자체는 retrieval 공간(BOOK_ID_TO_NAMES) 그대로 둔다.
_DISPLAY_NAME_OVERRIDES: dict[str, str] = {
    "SOL": "아가",
    "MRK": "마가복음",
    "LUK": "누가복음",
    "EZE": "에스겔",
}

# 정규 66권 순서 = BOOK_ID_TO_NAMES 삽입 순서(정경 순서로 정의돼 있음).
_CANONICAL_ORDER: list[str] = list(BOOK_ID_TO_NAMES.keys())
_CANONICAL_INDEX: dict[str, int] = {bid: i for i, bid in enumerate(_CANONICAL_ORDER)}


def _has_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def korean_book_name(book_id: str) -> str:
    """'PRO' → '잠언'. book_id 공간은 `core.retrieval.BOOK_ID_TO_NAMES`.
    표시에 부적절한 별칭은 `_DISPLAY_NAME_OVERRIDES` 로 보정한다."""
    if book_id in _DISPLAY_NAME_OVERRIDES:
        return _DISPLAY_NAME_OVERRIDES[book_id]
    for alias in BOOK_ID_TO_NAMES.get(book_id, []):
        if _has_hangul(alias):
            return alias
    return book_id


def normalize_book_id(raw: str) -> Optional[str]:
    """'pro' / 'PRO' / 'proverbs' / '잠언' / '잠' → 'PRO'. 미해석 시 None."""
    if not raw:
        return None
    key = raw.strip()
    if key.upper() in BOOK_ID_TO_NAMES:
        return key.upper()
    return NAME_TO_BOOK_ID.get(key.lower())


@dataclass
class _Book:
    book_id: str
    name: str
    chapters: list[list[str]] = field(default_factory=list)


@dataclass
class BibleText:
    """로드된 성경 본문. `available` 이 False면 `reason` 만 유효하다."""

    available: bool
    version_label: str = ""
    reason: str = ""
    _books: dict[str, _Book] = field(default_factory=dict)

    # ── 생성자 ──────────────────────────────────────────────
    @classmethod
    def unavailable(cls, reason: str) -> "BibleText":
        return cls(available=False, reason=reason)

    # ── 조회 API ────────────────────────────────────────────
    def has_book(self, book_id: str) -> bool:
        return book_id in self._books

    def list_books(self) -> list[tuple[str, str]]:
        """[(book_id, 표시명)] — 정경 순서."""
        items = list(self._books.values())
        items.sort(key=lambda b: _CANONICAL_INDEX.get(b.book_id, 999))
        return [(b.book_id, b.name) for b in items]

    def chapter_count(self, book_id: str) -> int:
        book = self._books.get(book_id)
        return len(book.chapters) if book else 0

    def verse_count(self, book_id: str, chapter: int) -> int:
        book = self._books.get(book_id)
        if not book or chapter < 1 or chapter > len(book.chapters):
            return 0
        return len(book.chapters[chapter - 1])

    def get_verses(
        self, book_id: str, chapter: int, verse_start: int, verse_end: Optional[int] = None
    ) -> list[tuple[int, str]]:
        """[(절 번호, 절 본문)] — 범위 밖은 조용히 잘라낸다(빈 리스트 가능)."""
        book = self._books.get(book_id)
        if not book or chapter < 1 or chapter > len(book.chapters):
            return []
        verses = book.chapters[chapter - 1]
        end = verse_end if verse_end is not None else verse_start
        lo = max(1, min(verse_start, end))
        hi = min(len(verses), max(verse_start, end))
        return [(v, verses[v - 1]) for v in range(lo, hi + 1)]


# ── 파일 로딩 (mtime 캐시) ─────────────────────────────────
_cache: dict[str, tuple[float, BibleText]] = {}


def _parse(raw: object, path: str) -> BibleText:
    if not isinstance(raw, dict):
        return BibleText.unavailable(f"성경 JSON 최상위가 객체가 아닙니다: {path}")
    books_raw = raw.get("books")
    if not isinstance(books_raw, dict) or not books_raw:
        return BibleText.unavailable(f"성경 JSON에 'books' 항목이 없습니다: {path}")

    version = str(raw.get("version") or "").strip() or "성경"
    books: dict[str, _Book] = {}
    skipped = 0
    for key, entry in books_raw.items():
        book_id = normalize_book_id(str(key))
        if not book_id or not isinstance(entry, dict):
            skipped += 1
            continue
        chapters_raw = entry.get("chapters")
        if not isinstance(chapters_raw, list) or not chapters_raw:
            skipped += 1
            continue
        chapters: list[list[str]] = []
        for ch in chapters_raw:
            if not isinstance(ch, list):
                chapters.append([])
                continue
            chapters.append([("" if v is None else str(v)) for v in ch])
        name = str(entry.get("name") or "").strip() or korean_book_name(book_id)
        books[book_id] = _Book(book_id=book_id, name=name, chapters=chapters)

    if not books:
        return BibleText.unavailable(f"성경 JSON에서 유효한 책을 찾지 못했습니다: {path}")
    if skipped:
        logger.warning("[bible_text] %d개 책 항목을 건너뜀 (형식 불일치): %s", skipped, path)

    return BibleText(available=True, version_label=version, _books=books)


def load_bible_text(path: Optional[str] = None) -> BibleText:
    """성경 본문 JSON을 로드한다. 파일이 없거나 손상돼도 예외를 던지지 않고
    `BibleText.unavailable(...)` 을 반환한다. 파일 mtime이 그대로면 캐시를
    재사용한다(스트림릿 rerun마다 디스크를 다시 읽지 않도록)."""
    target = path or BIBLE_TEXT_PATH
    try:
        mtime = os.path.getmtime(target)
    except OSError:
        return BibleText.unavailable(
            f"성경 본문 파일이 없습니다: {target}\n"
            "성경 본문 JSON을 이 경로에 두세요(경로는 config.yaml::directories.bible_text_path). "
            "규격: docs/NAE_BIBLE_TEXT_JSON_SPEC.md"
        )

    cached = _cache.get(target)
    if cached and cached[0] == mtime:
        return cached[1]

    try:
        with open(target, "r", encoding="utf-8") as f:
            raw = json.load(f)
        result = _parse(raw, target)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("[bible_text] 로드 실패 (%s): %s", target, e)
        result = BibleText.unavailable(f"성경 JSON을 읽을 수 없습니다: {target} ({e})")

    _cache[target] = (mtime, result)
    return result

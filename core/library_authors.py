"""내 자료 검색용 저자 정규화·분류 — 읽기 시점(view-level) 매핑.

Production Registry는 수정하지 않는다. registry의 author는 같은 사람이
`Charles Haddon Spurgeon` / `C. H. Spurgeon` / `C.H. SURGEON`(OCR 오타) 등
여러 표기로 갈라져 있어, 저자 검색·필터가 사람 단위로 동작하도록 이 모듈이
표기를 하나의 정규 저자(canonical)로 모은다. 한글 이름을 별칭에 넣어
"스펄전"으로도 영어 자료의 저자를 찾는다.

분류(category)도 같은 방식이다. registry의 doc_type은 "기타"가 과반이라
필터로 쓸모가 없어, 제목·파일명 키워드로 읽기 시점에만 세분화한다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# (정규식, 정규 키, 표시명, 검색 별칭)
_AUTHORS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (r"spurgeon|surgeon|스펄전|스퍼전", "spurgeon", "찰스 스펄전 (C. H. Spurgeon)",
     ("스펄전", "스퍼전", "찰스 스펄전", "spurgeon", "charles haddon spurgeon")),
    (r"maclaren|맥클라렌", "maclaren", "알렉산더 맥클라렌 (Alexander Maclaren)",
     ("맥클라렌", "알렉산더 맥클라렌", "maclaren")),
    (r"whitefield|휫필드|화이트필드", "whitefield", "조지 휫필드 (George Whitefield)",
     ("휫필드", "화이트필드", "조지 휫필드", "whitefield")),
    (r"broadus|브로더스", "broadus", "존 브로더스 (John A. Broadus)",
     ("브로더스", "존 브로더스", "broadus")),
    (r"dargan|다간", "dargan", "에드윈 다간 (Edwin C. Dargan)",
     ("다간", "에드윈 다간", "dargan")),
    (r"keach|키치", "keach", "벤저민 키치 (Benjamin Keach)",
     ("키치", "벤저민 키치", "keach")),
    (r"wright|톰\s*라이트|라이트", "wright", "톰 라이트 (N. T. Wright)",
     ("톰 라이트", "라이트", "n. t. wright", "wright")),
    (r"hovey|호비", "hovey", "조지 호비 (George Hovey)", ("호비", "hovey")),
]


@dataclass(frozen=True)
class Author:
    key: str
    display: str
    aliases: tuple[str, ...]


def _clean(raw: str) -> str:
    s = unicodedata.normalize("NFC", raw or "").strip()
    s = re.sub(r"\s*,?\s*\d{4}\s*-\s*\d{0,4}\.?", "", s)  # 생몰년
    s = re.sub(r"\s+", " ", s).strip(" ,.;")
    return s


def canonical_author(raw: str | None) -> Author:
    """registry의 author 문자열 → 정규 저자. 모르는 저자는 정리한 원문 그대로."""
    cleaned = _clean(raw or "")
    low = cleaned.lower()
    for pattern, key, display, aliases in _AUTHORS:
        if re.search(pattern, low):
            return Author(key, display, aliases)
    if not cleaned:
        return Author("unknown", "저자 미상", ())
    return Author(low, cleaned, (low,))


# (정규식(제목+파일명), 분류) — 위에서부터 먼저 맞는 것
_CATEGORY_RULES: list[tuple[str, str]] = [
    (r"evening by evening|morning by morning|till he come|readings", "묵상집"),
    (r"lectures to my students|commenting and commentaries|"
     r"history of preaching|preparation and delivery", "설교학·역사"),
    (r"expositions of holy scripture|모든\s*사람을\s*위한", "강해·주석"),
    (r"tropologia", "성경 해석"),
    (r"works of the reverend|whitefield_works", "저작집"),
    (r"pulpit|sermon|mtp|npsp|heaven", "설교집"),
]


def categorize(title: str, source_file: str, registry_doc_type: str | None = None) -> str:
    blob = unicodedata.normalize("NFC", f"{title} {source_file}").lower()
    for pattern, label in _CATEGORY_RULES:
        if re.search(pattern, blob):
            return label
    if registry_doc_type and registry_doc_type != "기타":
        return registry_doc_type
    return "기타"

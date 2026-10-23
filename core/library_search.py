"""'내 자료' 검색 — 제목·유형·경로·수정일(메타데이터)과 처리된 본문(.md)을 함께 찾는다.

읽기 전용: RAW, 색인, Retrieval Engine은 건드리지 않고 처리 산출물
({output_dir}/{stem}.md)을 읽기만 한다.

질의 문법(상용 검색창 관례):
    단어1 단어2      모두 포함(AND)
    "정확한 구절"    따옴표 안은 한 덩어리로 일치
    -제외어          해당 단어가 있는 문서 제외

본문은 (경로, 수정시각, 크기)로 캐시해 같은 파일을 다시 읽지 않는다.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from core.config import DEFAULT_OUTPUT_DIR
from core.utils import make_safe_stem

_META_KEYS = ("title", "type", "path", "modified")
_SNIPPET_RADIUS = 60
_MAX_SNIPPETS = 3

# path -> ((mtime_ns, size), normalized_text, original_text)
_TEXT_CACHE: dict[str, tuple[tuple[int, int], str, str]] = {}


@dataclass
class SearchHit:
    doc: dict
    score: float
    meta_match: bool
    content_hits: int
    snippets: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    # macOS 파일명은 NFD — NFC로 맞춰 한글 자모 분리 불일치를 막는다.
    return unicodedata.normalize("NFC", text).lower()


def parse_query(query: str) -> tuple[list[str], list[str]]:
    """(포함어 목록, 제외어 목록) — 둘 다 정규화됨."""
    include: list[str] = []
    exclude: list[str] = []
    for m in re.finditer(r'(-?)"([^"]+)"|(-?)(\S+)', query):
        neg = (m.group(1) or m.group(3)) == "-"
        term = _norm((m.group(2) or m.group(4) or "").strip())
        if not term or term == "-":
            continue
        (exclude if neg else include).append(term)
    return include, exclude


def processed_text_path(doc: dict, output_dir: str = DEFAULT_OUTPUT_DIR) -> Optional[Path]:
    """문서의 처리 본문(.md) 경로. 없으면 None."""
    title = doc.get("title") or Path(str(doc.get("path", ""))).name
    if not title:
        return None
    candidate = Path(output_dir) / f"{make_safe_stem(title)}.md"
    if candidate.is_file():
        return candidate
    # NFD/NFC 차이로 못 찾는 경우를 위한 보정
    target = unicodedata.normalize("NFC", candidate.name)
    try:
        for p in Path(output_dir).glob("*.md"):
            if unicodedata.normalize("NFC", p.name) == target:
                return p
    except OSError:
        pass
    return None


def _load_text(path: Path) -> tuple[str, str]:
    """(정규화 본문, 원문). 변경이 없으면 캐시 사용."""
    key = str(path)
    try:
        st = path.stat()
        sig = (st.st_mtime_ns, st.st_size)
    except OSError:
        return "", ""
    cached = _TEXT_CACHE.get(key)
    if cached and cached[0] == sig:
        return cached[1], cached[2]
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "", ""
    # 줄바꿈·공백 정리 — 구절 검색이 줄바꿈에 막히지 않게 한다.
    flat = re.sub(r"\s+", " ", raw)
    _TEXT_CACHE[key] = (sig, _norm(flat), flat)
    return _TEXT_CACHE[key][1], flat


def _snippets(norm_text: str, flat_text: str, terms: Iterable[str]) -> list[str]:
    # _norm은 길이를 바꿀 수 있어(드묾) 위치가 어긋나면 스니펫만 건너뛴다.
    if len(norm_text) != len(flat_text):
        return []
    out: list[str] = []
    last_end = -1
    positions = sorted(
        (norm_text.find(t), t) for t in terms if t and norm_text.find(t) >= 0
    )
    for pos, term in positions:
        if pos < last_end or len(out) >= _MAX_SNIPPETS:
            continue
        start = max(0, pos - _SNIPPET_RADIUS)
        end = min(len(flat_text), pos + len(term) + _SNIPPET_RADIUS)
        piece = flat_text[start:end]
        rel = pos - start
        piece = (
            piece[:rel] + "**" + piece[rel:rel + len(term)] + "**" + piece[rel + len(term):]
        )
        out.append(("…" if start > 0 else "") + piece + ("…" if end < len(flat_text) else ""))
        last_end = end
    return out


def search_documents(
    documents: list[dict],
    query: str,
    *,
    include_content: bool = True,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> list[SearchHit]:
    """질의에 맞는 문서를 점수순으로 반환한다. 질의가 비면 빈 목록."""
    include, exclude = parse_query(query)
    if not include and not exclude:
        return []

    hits: list[SearchHit] = []
    for doc in documents:
        meta_blob = " ".join(_norm(str(doc.get(k, ""))) for k in _META_KEYS)
        title_norm = _norm(str(doc.get("title", "")))

        norm_text = flat_text = ""
        if include_content:
            tp = processed_text_path(doc, output_dir)
            if tp:
                norm_text, flat_text = _load_text(tp)

        haystack = meta_blob + " " + norm_text
        if any(t in haystack for t in exclude):
            continue
        if not all(t in haystack for t in include):
            continue

        score = 0.0
        meta_match = False
        content_hits = 0
        for t in include:
            if t in title_norm:
                score += 10
                meta_match = True
            elif t in meta_blob:
                score += 3
                meta_match = True
            n = norm_text.count(t) if norm_text else 0
            content_hits += n
            if n:
                score += min(n, 50) ** 0.5
        if not include:  # 제외어만 있는 질의: 남은 문서를 모두 보여준다
            score = 0.0

        snips = (
            _snippets(norm_text, flat_text, [t for t in include if t in norm_text])
            if norm_text and include else []
        )
        hits.append(SearchHit(doc, score, meta_match, content_hits, snips))

    hits.sort(key=lambda h: (-h.score, str(h.doc.get("title", ""))))
    return hits

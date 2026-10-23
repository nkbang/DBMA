"""'내 자료' 검색 엔진 — 메타데이터 + 본문 + 성경 구절 + 한영 교차 검색.

읽기 전용: RAW, 색인, Retrieval Engine, Production Registry는 수정하지 않는다.
처리 산출물({output_dir}/{stem}.md)과 registry 레코드를 읽기만 한다.

질의 문법(상용 검색창 관례):
    단어1 단어2        모두 포함(AND)
    "정확한 구절"      따옴표 안은 한 덩어리로 일치
    -제외어            해당 단어가 있는 문서 제외
    롬 8:28            성경 구절(약어·한글·영어 표기, 로마숫자 장 표기까지) 인식
    author:스펄전      저자 (별칭·표기 변형 포함: core/library_authors.py)
    type:설교집        분류 / lang:ko|en 언어

한글 질의는 기존 질의 번역 사전(core/query_translation.py)으로 영어 용어를
덧붙여, 영어 본문이 대부분인 장서에서도 찾는다(원문 매칭이 우선, 번역 매칭은
결과에 "번역 검색"으로 표시).

본문은 (경로, 수정시각, 크기)로 캐시해 같은 파일을 다시 읽지 않는다.
"""

from __future__ import annotations

import bisect
import logging
import os
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from core.config import DATA_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_REGISTRY_PATH
from core.library_authors import Author, canonical_author, categorize
from core.utils import make_safe_stem

log = logging.getLogger(__name__)

_META_KEYS = ("title", "type", "path", "modified")
_SNIPPET_RADIUS = 70
_MAX_PASSAGES = 8
_WINDOW = 320                 # 한 구절(passage)로 묶는 최대 거리(문자)
_MAX_POS_PER_TERM = 800       # 단어당 위치 수집 상한(흔한 단어 폭주 방지)
_NOISY_SCORE = 30.0           # registry noise_score가 이 이상이면 "품질 낮음"
_LANG_LABELS = {"en": "영어", "ko": "한국어"}

_FIELD_RE = re.compile(r"^(author|저자|type|분류|category|유형|lang|언어):(.+)$", re.IGNORECASE)
_HANGUL_RE = re.compile(r"[가-힣]")
_ORDINAL_PREFIX_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:[123]|i{1,3}|first|second|third|1st|2nd|3rd)[\s.]*$", re.IGNORECASE
)
_MARKER_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+\S.*|"
    r"(?:SERMON|Sermon|CHAPTER|Chapter|LECTURE|Lecture|PSALM|Psalm|ESSAY|Essay)[ \t]+[IVXLCivxlc\d]+\b.{0,60}|"
    r"No\.[ \t]*\d+\b.{0,60}|"
    r"제?[ \t]*\d+[ \t]*[장부편][ \t].{0,60})$",
    re.MULTILINE,
)


# ── 데이터 모델 ─────────────────────────────────────────────────────

@dataclass
class DocInfo:
    """RAW 파일 + registry 레코드를 합친 표시용 문서 정보."""
    doc: dict
    title: str
    author: Author
    raw_author: str
    language: str
    category: str
    chunk_count: int
    noise_score: float
    source_file: str

    @property
    def path(self) -> str:
        return self.doc.get("path", "")

    @property
    def language_label(self) -> str:
        return _LANG_LABELS.get(self.language, self.language or "?")

    @property
    def low_quality(self) -> bool:
        return self.noise_score >= _NOISY_SCORE


@dataclass
class Passage:
    offset: int
    snippet: str            # **강조** 포함, 공백 정리됨
    location: str           # "Sermon 12 · 본문 34%" 등
    kind: str = "text"      # text | scripture | translated


@dataclass
class SearchHit:
    doc: dict
    score: float
    meta_match: bool
    content_hits: int
    snippets: list[str] = field(default_factory=list)
    passages: list[Passage] = field(default_factory=list)
    info: Optional[DocInfo] = None
    via: list[str] = field(default_factory=list)   # 매칭 경로 설명(번역 검색 등)
    terms: list[str] = field(default_factory=list)  # 본문 강조용(정규화된 일치 문자열)


@dataclass
class ParsedQuery:
    include: list[str]
    exclude: list[str]
    fields: dict[str, list[str]]
    refs: list = field(default_factory=list)          # ScriptureReference
    translated: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.include or self.exclude or self.refs or self.fields)


# ── 정규화·질의 해석 ────────────────────────────────────────────────

def _norm(text: str) -> str:
    # macOS 파일명은 NFD — NFC로 맞춰 한글 자모 분리 불일치를 막는다.
    return unicodedata.normalize("NFC", text).lower()


def _tokenize(query: str) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    for m in re.finditer(r'(-?)"([^"]+)"|(-?)(\S+)', query):
        neg = (m.group(1) or m.group(3)) == "-"
        term = (m.group(2) or m.group(4) or "").strip()
        if term and term != "-":
            out.append((neg, term))
    return out


def parse_query(query: str) -> tuple[list[str], list[str]]:
    """(포함어 목록, 제외어 목록) — 정규화됨. 필드/구절 해석 없이 단순 분해."""
    include: list[str] = []
    exclude: list[str] = []
    for neg, term in _tokenize(query):
        (exclude if neg else include).append(_norm(term))
    return include, exclude


_PARSER = None
_PARSER_LOCK = threading.Lock()


def _query_parser():
    """기존 QueryParser(성경 구절 인식)를 한 번만 만든다. 실패하면 None."""
    global _PARSER
    if _PARSER is None:
        with _PARSER_LOCK:
            if _PARSER is None:
                try:
                    from core.retrieval import QueryParser
                    _PARSER = QueryParser()
                except Exception:  # 구절 인식만 꺼질 뿐 검색은 계속된다
                    log.exception("QueryParser 로드 실패 — 성경 구절 인식 비활성")
                    _PARSER = False
    return _PARSER or None


def _is_ref_noise(token: str, refs: list, book_words: set[str]) -> bool:
    """구절 인식에 이미 쓰인 토큰(롬, 8:28, 3장, 16절, 책 이름)인지."""
    t = token.lower()
    if t in book_words:
        return True
    if re.fullmatch(r"\d+(?:[:.]\d+)?(?:-\d+)?[장절편]?", t):
        return True
    return bool(re.fullmatch(r"\d+\s*장|\d+\s*절", t))


_ROMAN_VAL = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def _roman_to_int(s: str) -> int:
    total = 0
    for i, ch in enumerate(s):
        v = _ROMAN_VAL[ch]
        total += -v if i + 1 < len(s) and _ROMAN_VAL[s[i + 1]] > v else v
    return total


def _roman_refs(plain: list[tuple[bool, str]]) -> tuple[list, set[str]]:
    """'Romans viii. 28' 같은 로마숫자 장 표기 — 기존 파서는 아라비아 숫자만 안다.

    책 이름 토큰 + 로마숫자 장 + 절(숫자)이 이어질 때만 구절로 본다.
    반환: (ScriptureReference 목록, 구절에 쓰인 토큰 집합)
    """
    from core.retrieval import NAME_TO_BOOK_ID, ScriptureReference
    toks = [t for n, t in plain if not n]
    refs, used = [], set()
    i = 0
    while i < len(toks):
        # 두 단어 책 이름("1 john")을 먼저 시도
        for width in (2, 1):
            name = " ".join(toks[i:i + width]).lower().rstrip(".,")
            book = NAME_TO_BOOK_ID.get(name)
            if book and i + width + 1 < len(toks) + 0:
                ch = toks[i + width].lower().rstrip(".,:;")
                vs = toks[i + width + 1].lower().rstrip(".,:;")
                if re.fullmatch(r"[ivxlc]+", ch) and vs.isdigit():
                    refs.append(ScriptureReference(book, _roman_to_int(ch), int(vs)))
                    used.update(t.lower() for t in toks[i:i + width + 2])
                    i += width + 1
                    break
        i += 1
    return refs, used


def parse_library_query(query: str) -> ParsedQuery:
    fields: dict[str, list[str]] = {}
    plain: list[tuple[bool, str]] = []
    for neg, term in _tokenize(query):
        m = _FIELD_RE.match(term)
        if m and not neg:
            key = m.group(1).lower()
            key = {"저자": "author", "분류": "category", "유형": "category",
                   "type": "category", "언어": "lang"}.get(key, key)
            fields.setdefault(key, []).append(_norm(m.group(2).strip('"')))
        else:
            plain.append((neg, term))

    refs: list = []
    book_words: set[str] = set()
    if any(c.isdigit() for _, term in plain for c in term):
        qp = _query_parser()
        if qp is not None:
            try:
                text = " ".join(t for n, t in plain if not n)
                parsed = qp.parse(text)
                refs = [r for r in parsed.scripture_refs if r.chapter > 0]
                if refs:
                    from core.retrieval import BOOK_ID_TO_NAMES
                    for r in refs:
                        book_words.update(n.lower() for n in BOOK_ID_TO_NAMES.get(r.book_id, []))
                if not refs:
                    refs, used = _roman_refs(plain)
                    book_words |= used
            except Exception:
                log.exception("성경 구절 해석 실패")
                refs = []

    include = [_norm(t) for n, t in plain if not n and not (refs and _is_ref_noise(t, refs, book_words))]
    exclude = [_norm(t) for n, t in plain if n]

    translated: list[str] = []
    if any(_HANGUL_RE.search(t) for t in include):
        try:
            from core.query_translation import translate_query_terms
            hangul_text = " ".join(t for t in include if _HANGUL_RE.search(t))
            translated = [w for w in translate_query_terms(hangul_text) if not w.isdigit()]
        except Exception:
            log.exception("질의 번역 실패")
    return ParsedQuery(include, exclude, fields, refs, translated)


# ── registry 결합 ───────────────────────────────────────────────────

_REG_CACHE: dict[str, tuple[float, dict]] = {}


def _registry_by_source(registry_path: str) -> dict[str, dict]:
    try:
        mtime = os.path.getmtime(registry_path)
    except OSError:
        return {}
    cached = _REG_CACHE.get(registry_path)
    if cached and cached[0] == mtime:
        return cached[1]
    from core.identity_registry import load_identity_registry
    reg = load_identity_registry(registry_path)
    by_src: dict[str, dict] = {}
    for rec in reg.get("documents", {}).values():
        if not isinstance(rec, dict) or rec.get("superseded_by"):
            continue
        by_src.setdefault(unicodedata.normalize("NFC", rec.get("source_file", "")), rec)
    _REG_CACHE[registry_path] = (mtime, by_src)
    return by_src


def enrich_documents(
    documents: list[dict],
    registry: Optional[dict[str, dict]] = None,
    registry_path: str = DEFAULT_REGISTRY_PATH,
) -> list[DocInfo]:
    """RAW 문서 목록에 registry 정보(저자·언어·분량·품질)를 붙인다.

    `registry`는 {NFC source_file: record} — 테스트 등에서 직접 주입할 수 있다.
    """
    by_src = registry if registry is not None else _registry_by_source(registry_path)
    infos: list[DocInfo] = []
    for d in documents:
        fname = d.get("title") or Path(str(d.get("path", ""))).name
        rec = by_src.get(unicodedata.normalize("NFC", fname)) or {}
        raw_author = rec.get("author") or ""
        title = rec.get("title") or fname
        infos.append(DocInfo(
            doc=d,
            title=title,
            author=canonical_author(raw_author),
            raw_author=raw_author,
            language=rec.get("language") or "",
            category=categorize(title, fname, rec.get("doc_type")),
            chunk_count=int(rec.get("chunk_count") or 0),
            noise_score=float(rec.get("noise_score") or 0.0),
            source_file=fname,
        ))
    return infos


def facet_counts(infos: list[DocInfo]) -> dict[str, list[tuple[str, str, int]]]:
    """필터 UI용 (값, 표시명, 문서 수) 목록 — 문서 수 내림차순."""
    def tally(pairs: Iterable[tuple[str, str]]) -> list[tuple[str, str, int]]:
        counts: dict[str, int] = {}
        label: dict[str, str] = {}
        for key, disp in pairs:
            counts[key] = counts.get(key, 0) + 1
            label[key] = disp
        return sorted(((k, label[k], n) for k, n in counts.items()), key=lambda x: (-x[2], x[1]))
    return {
        "author": tally((i.author.key, i.author.display) for i in infos),
        "language": tally((i.language or "?", i.language_label) for i in infos),
        "category": tally((i.category, i.category) for i in infos),
    }


def passes_filters(
    info: DocInfo,
    authors: Iterable[str] = (),
    languages: Iterable[str] = (),
    categories: Iterable[str] = (),
) -> bool:
    authors, languages, categories = set(authors), set(languages), set(categories)
    return (
        (not authors or info.author.key in authors)
        and (not languages or (info.language or "?") in languages)
        and (not categories or info.category in categories)
    )


# ── 본문 캐시 ───────────────────────────────────────────────────────

@dataclass
class _Text:
    sig: tuple[int, int]
    norm: str
    raw: str
    marker_pos: list[int]
    marker_label: list[str]


_TEXT_CACHE: dict[str, _Text] = {}
_LOAD_LOCK = threading.Lock()


def processed_text_path(doc: dict, output_dir: str = DEFAULT_OUTPUT_DIR) -> Optional[Path]:
    """문서의 처리 본문(.md) 경로. 없으면 None."""
    title = doc.get("title") or Path(str(doc.get("path", ""))).name
    if not title:
        return None
    candidate = Path(output_dir) / f"{make_safe_stem(title)}.md"
    if candidate.is_file():
        return candidate
    target = unicodedata.normalize("NFC", candidate.name)
    try:
        for p in Path(output_dir).glob("*.md"):
            if unicodedata.normalize("NFC", p.name) == target:
                return p
    except OSError:
        pass
    return None


def _strip_front_matter(raw: str) -> str:
    # YAML front matter는 길이를 유지한 채 공백으로 가린다 — 메타 줄(language: en,
    # source: ...)이 본문 검색에 걸리지 않게 하면서 오프셋은 보존한다.
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            end += 4
            return " " * end + raw[end:]
    return raw


def _load_text(path: Path) -> Optional[_Text]:
    key = str(path)
    try:
        st = path.stat()
        sig = (st.st_mtime_ns, st.st_size)
    except OSError:
        return None
    cached = _TEXT_CACHE.get(key)
    if cached and cached.sig == sig:
        return cached
    with _LOAD_LOCK:
        cached = _TEXT_CACHE.get(key)
        if cached and cached.sig == sig:
            return cached
        try:
            raw = _strip_front_matter(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            return None
        norm = _norm(raw)
        if len(norm) != len(raw):          # NFC 변환으로 길이가 바뀌면 오프셋이 어긋난다
            raw = unicodedata.normalize("NFC", raw)
            norm = raw.lower()
        pos, labels = [], []
        for m in _MARKER_RE.finditer(raw):
            label = re.sub(r"\s+", " ", m.group(0)).strip(" #")[:60]
            if label.startswith("전면부"):
                label = "전면부"
            ok = sum(c.isalnum() or c in " .:" for c in label)
            if label != "본문" and ok >= 0.7 * len(label):   # OCR 쓰레기 줄 제외
                pos.append(m.start())
                labels.append(label)
        _TEXT_CACHE[key] = _Text(sig, norm, raw, pos, labels)
        return _TEXT_CACHE[key]


def warm_cache(documents: list[dict], output_dir: str = DEFAULT_OUTPUT_DIR) -> None:
    """모든 본문을 미리 읽어 첫 검색 지연을 없앤다(백그라운드 스레드용)."""
    for d in documents:
        p = processed_text_path(d, output_dir)
        if p:
            _load_text(p)


_WARM_STARTED = False


def start_background_warmup(documents: list[dict], output_dir: str = DEFAULT_OUTPUT_DIR) -> None:
    """프로세스당 한 번 캐시 예열 스레드를 띄운다."""
    global _WARM_STARTED
    if _WARM_STARTED or not documents:
        return
    _WARM_STARTED = True
    threading.Thread(
        target=warm_cache, args=(list(documents), output_dir), daemon=True, name="library-search-warmup"
    ).start()


def _location(text: _Text, offset: int) -> str:
    pct = int(offset * 100 / max(1, len(text.raw)))
    i = bisect.bisect_right(text.marker_pos, offset) - 1
    where = f"본문 {pct}%"
    return f"{text.marker_label[i]} · {where}" if i >= 0 else where


# ── 위치 수집: 단어 / 성경 구절 ─────────────────────────────────────

def _positions(norm: str, term: str) -> list[int]:
    out: list[int] = []
    start = norm.find(term)
    while start != -1 and len(out) < _MAX_POS_PER_TERM:
        out.append(start)
        start = norm.find(term, start + len(term))
    return out


def _phrase_spans(norm: str, term: str) -> list[tuple[int, int]]:
    """(시작, 끝) 목록. 구절은 공백이 여럿·줄바꿈이어도 일치한다."""
    if " " not in term:
        return [(p, p + len(term)) for p in _positions(norm, term)]
    pat = re.compile(r"\s+".join(re.escape(w) for w in term.split()))
    return [(m.start(), m.end()) for m in pat.finditer(norm)][:_MAX_POS_PER_TERM]


def _scripture_positions(norm: str, ref) -> list[tuple[int, int]]:
    """(시작, 끝) 목록 — 'Romans viii. 28', 'Rom 8:28', '롬 8:28', '로마서 8장 28절' 등."""
    try:
        from core.query_translation import to_roman
        from core.retrieval import BOOK_ID_TO_NAMES
    except Exception:
        return []
    ch = ref.chapter
    chapter_alt = f"(?:{to_roman(ch)}|{ch})"
    verse = ref.verse_start or 0
    tail_en = re.compile(
        r"[\s.,]*" + chapter_alt + r"(?![a-z0-9])"
        + (r"[\s.,:;]*" + str(verse) + r"(?!\d)" if verse else "")
    )
    tail_ko = re.compile(
        r"\s*" + str(ch) + r"\s*(?:장|:|\.)"
        + (r"\s*" + str(verse) + r"(?!\d)\s*(?:절)?" if verse else "")
    )
    found: list[tuple[int, int]] = []
    for alias in BOOK_ID_TO_NAMES.get(ref.book_id, []):
        a = _norm(alias)
        ko = bool(_HANGUL_RE.search(a))
        if not ko and (len(a) < 3 or not a.replace(" ", "").isalpha() and not a[0].isdigit()):
            continue
        tail = tail_ko if ko else tail_en
        for pos in _positions(norm, a):
            if ko:
                if len(a) == 1 and pos > 0 and _HANGUL_RE.match(norm[pos - 1]):
                    continue       # '필요 3:16'의 '요'처럼 낱말 중간은 책 이름이 아니다
            else:
                if pos > 0 and norm[pos - 1].isalpha():
                    continue
                if not a[0].isdigit() and _ORDINAL_PREFIX_RE.search(norm[max(0, pos - 12):pos]):
                    continue
            m = tail.match(norm, pos + len(a))
            if m:
                found.append((pos, m.end()))
    found.sort()
    return found


def _prose_ratio(norm: str, pos: int) -> float:
    """주변이 문장(글자 위주)인지 — 목차·색인표(숫자 위주)는 낮게 나온다."""
    chunk = norm[max(0, pos - 80):pos + 240]
    return sum(c.isalpha() for c in chunk) / max(1, len(chunk))


def _best_windows(
    occurrences: list[tuple[int, int, int]], n_terms: int, norm: str = ""
) -> list[tuple[int, int, int]]:
    """(pos, end, term_idx) 목록에서 가까이 모여 있는 구절 상위 N개.

    반환: (anchor_pos, distinct_terms, span) — 서로 겹치지 않게 선택한다.
    """
    occurrences = sorted(occurrences)
    cands: list[tuple[int, int, int]] = []
    j = 0
    counts: dict[int, int] = {}
    for i, (pos, _end, _t) in enumerate(occurrences):
        # 창 [i, j) 유지: occurrences[j].pos - pos <= _WINDOW
        if i > 0:
            t_prev = occurrences[i - 1][2]
            counts[t_prev] -= 1
            if not counts[t_prev]:
                del counts[t_prev]
        j = max(j, i)
        while j < len(occurrences) and occurrences[j][0] - pos <= _WINDOW:
            counts[occurrences[j][2]] = counts.get(occurrences[j][2], 0) + 1
            j += 1
        span = occurrences[j - 1][0] - pos
        cands.append((pos, len(counts), span))
    if norm:
        cands.sort(key=lambda c: (-c[1], _prose_ratio(norm, c[0]) < 0.7, c[2], c[0]))
    else:
        cands.sort(key=lambda c: (-c[1], c[2], c[0]))
    chosen: list[tuple[int, int, int]] = []
    for c in cands:
        if all(abs(c[0] - k[0]) > _WINDOW for k in chosen):
            chosen.append(c)
            if len(chosen) >= _MAX_PASSAGES:
                break
    return chosen


def _render_snippet(text: _Text, anchor: int, spans: list[tuple[int, int]]) -> str:
    start = max(0, anchor - _SNIPPET_RADIUS)
    end = min(len(text.raw), anchor + _WINDOW + _SNIPPET_RADIUS)
    pieces: list[str] = []
    cur = start
    for s, e in sorted(x for x in spans if x[0] >= start and x[1] <= end):
        if s < cur:
            continue
        pieces.append(text.raw[cur:s])
        pieces.append("**" + text.raw[s:e].strip() + "**")
        cur = e
    pieces.append(text.raw[cur:end])
    flat = re.sub(r"\s+", " ", "".join(pieces)).strip()
    flat = flat.replace("** **", " ")
    return ("…" if start > 0 else "") + flat + ("…" if end < len(text.raw) else "")


def excerpt(doc: dict, offset: int, radius: int = 1500, output_dir: str = DEFAULT_OUTPUT_DIR,
            terms: Iterable[str] = ()) -> tuple[str, int, int]:
    """본문 offset 주변을 읽기용으로 잘라 돌려준다: (강조된 텍스트, 시작, 끝)."""
    p = processed_text_path(doc, output_dir)
    t = _load_text(p) if p else None
    if not t:
        return "", 0, 0
    start = max(0, offset - radius // 3)
    end = min(len(t.raw), start + radius)
    chunk = t.raw[start:end]
    low = t.norm[start:end]
    spans: list[tuple[int, int]] = []
    for term in {x for x in terms if x}:
        for m in re.finditer(r"\s+".join(re.escape(w) for w in term.split()), low):
            spans.append((m.start(), m.end()))
    out, cur = [], 0
    for s, e in sorted(spans):
        if s < cur:
            continue
        out.append(chunk[cur:s])
        out.append("**" + chunk[s:e] + "**")
        cur = e
    out.append(chunk[cur:])
    return "".join(out), start, end


# ── 검색 ────────────────────────────────────────────────────────────

def _field_ok(info: DocInfo, fields: dict[str, list[str]]) -> bool:
    for v in fields.get("author", []):
        hay = " ".join([_norm(info.raw_author), _norm(info.author.display), info.author.key,
                        *[_norm(a) for a in info.author.aliases]])
        if v not in hay:
            return False
    for v in fields.get("category", []):
        if v not in _norm(info.category):
            return False
    for v in fields.get("lang", []):
        labels = {info.language.lower(), _norm(info.language_label)}
        if not any(v == lab or v in lab for lab in labels if lab):
            return False
    return True


def search_documents(
    documents: list[dict],
    query: str,
    *,
    include_content: bool = True,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    registry: Optional[dict[str, dict]] = None,
    infos: Optional[list[DocInfo]] = None,
) -> list[SearchHit]:
    """질의에 맞는 문서를 관련도순으로 반환한다. 질의가 비면 빈 목록."""
    q = parse_library_query(query)
    if q.empty:
        return []
    infos = infos if infos is not None else enrich_documents(documents, registry)

    hits: list[SearchHit] = []
    for info in infos:
        if not _field_ok(info, q.fields):
            continue
        d = info.doc
        title_norm = _norm(info.title + " " + str(d.get("title", "")))
        meta_blob = " ".join(
            [_norm(str(d.get(k, ""))) for k in _META_KEYS]
            + [_norm(info.title), _norm(info.raw_author), _norm(info.author.display),
               *[_norm(a) for a in info.author.aliases],
               _norm(info.category), _norm(info.language_label), info.language.lower()]
        )

        text: Optional[_Text] = None
        if include_content:
            tp = processed_text_path(d, output_dir)
            text = _load_text(tp) if tp else None
        norm = text.norm if text else ""
        haystack = meta_blob + " " + norm

        # 제외어
        if any(t in haystack for t in q.exclude):
            continue

        # 성경 구절은 필수 조건
        scripture: list[tuple[int, int]] = []
        if q.refs:
            if not norm:
                continue
            for ref in q.refs:
                scripture += _scripture_positions(norm, ref)
            if not scripture:
                continue

        # 단어 매칭: 원문 채널(A) 또는 번역 채널(B)
        via: list[str] = []
        used_terms: list[str] = list(q.include)
        a_ok = all(t in haystack or (" " in t and _phrase_spans(norm, t)) for t in q.include)
        if not a_ok and q.translated:
            latin = [t for t in q.include if not _HANGUL_RE.search(t)]
            need = max(1, -(-len(q.translated) * 6 // 10))
            got = [w for w in q.translated if w in norm]
            if all(t in haystack for t in latin) and len(got) >= need:
                a_ok = True
                used_terms = latin + got
                via.append("한→영 번역 검색: " + ", ".join(got))
        if not a_ok:
            continue

        # ── 점수와 구절 ──
        score = 0.0
        meta_match = False
        content_hits = 0
        for t in q.include:
            if t in title_norm:
                score += 10
                meta_match = True
            elif t in meta_blob:
                score += 4
                meta_match = True
        for v in q.fields.get("author", []):
            score += 6
            meta_match = True

        occ: list[tuple[int, int, int]] = []
        for idx, t in enumerate(used_terms):
            if norm:
                for st_, en_ in _phrase_spans(norm, t):
                    occ.append((st_, en_, idx))
        for t_idx in {o[2] for o in occ}:
            n = sum(1 for o in occ if o[2] == t_idx)
            content_hits += n
            score += min(n, 50) ** 0.5
        if scripture:
            score += 25 + min(len(scripture), 20)
            content_hits += len(scripture)

        passages: list[Passage] = []
        if text and (occ or scripture):
            if scripture:
                pocc = [(s, e, 0) for s, e in scripture]
                windows = _best_windows(pocc, 1, norm)
                for anchor, _n, _span in windows:
                    snip = _render_snippet(
                        text, max(0, anchor - 40),
                        [(s, e) for s, e in scripture if abs(s - anchor) <= _WINDOW]
                        + [(o[0], o[1]) for o in occ if abs(o[0] - anchor) <= _WINDOW],
                    )
                    passages.append(Passage(anchor, snip, _location(text, anchor), "scripture"))
            else:
                windows = _best_windows(occ, max(1, len(used_terms)), norm)
                for anchor, n_distinct, _span in windows:
                    score += 0.5 * n_distinct
                    spans = [(o[0], o[1]) for o in occ if anchor <= o[0] <= anchor + _WINDOW]
                    kind = "translated" if via else "text"
                    passages.append(Passage(
                        anchor, _render_snippet(text, anchor, spans), _location(text, anchor), kind))
        if info.low_quality:
            score -= 2   # OCR 노이즈 큰 문서는 동점에서 뒤로

        hl = [t for t in used_terms if t]
        hl += list({norm[s_:e_] for s_, e_ in scripture[:20]})
        hits.append(SearchHit(
            d, score, meta_match, content_hits,
            [p.snippet for p in passages[:3]], passages, info, via, hl,
        ))

    hits.sort(key=lambda h: (-h.score, str(h.info.title if h.info else h.doc.get("title", ""))))
    return hits


# ── 검색 이력·저장된 검색 ───────────────────────────────────────────
# 반복 연구에서 같은 질의를 다시 치지 않게 한다. 사용자 선호이므로 data/ 아래
# JSON 한 개(.gitignore 대상)에 둔다. 읽기·쓰기 실패는 기능만 끄고 검색엔 영향 없다.

_PREFS_PATH = Path(DATA_DIR) / "library_search_prefs.json"
_HISTORY_MAX = 12


def _read_prefs(path: Path = _PREFS_PATH) -> dict:
    try:
        import json
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_prefs(prefs: dict, path: Path = _PREFS_PATH) -> None:
    try:
        import json
        path.write_text(json.dumps(prefs, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        log.warning("검색 설정을 저장하지 못했습니다: %s", path)


def recent_searches(path: Path = _PREFS_PATH) -> list[str]:
    return list(_read_prefs(path).get("history", []))


def saved_searches(path: Path = _PREFS_PATH) -> list[str]:
    return list(_read_prefs(path).get("saved", []))


def record_search(query: str, path: Path = _PREFS_PATH) -> None:
    query = query.strip()
    if not query:
        return
    prefs = _read_prefs(path)
    hist = [q for q in prefs.get("history", []) if q != query]
    prefs["history"] = ([query] + hist)[:_HISTORY_MAX]
    _write_prefs(prefs, path)


def toggle_saved_search(query: str, path: Path = _PREFS_PATH) -> bool:
    """저장 목록에 넣거나 뺀다. 저장된 상태가 되면 True."""
    query = query.strip()
    prefs = _read_prefs(path)
    saved = prefs.get("saved", [])
    if query in saved:
        saved.remove(query)
        now_saved = False
    elif query:
        saved.append(query)
        now_saved = True
    else:
        return False
    prefs["saved"] = saved
    _write_prefs(prefs, path)
    return now_saved

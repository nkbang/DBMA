"""Korean → English query term translation for cross-lingual retrieval.

[2026-09-26] 문제: TSU 코퍼스는 대부분 영어 본문인데 검색의 1단계 후보
생성(RetrievalEngine BM25 / CandidateGenerator Tantivy BM25)은 질의 원문의
낱말로만 매칭한다. 그래서 "칭의와 성화의 관계" 같은 한국어 질의는 영어
본문과 겹치는 토큰이 없어 후보를 거의 못 잡았고, 2단계 의미 재랭킹
(BGE-M3, 다국어)은 이미 잘못 잡힌 후보 안에서만 돌아 복구할 수 없었다
(실측: 한국어 질의 2건 모두 무관한 설교사 강의 청크만 반환).

해법: 사전 기반 질의 번역(dictionary-based query translation) — CLIR의
표준 기법 중 하나. LLM 번역 대신 닫힌 용어 사전을 쓰는 이유:
  - 결정적(같은 질의 → 같은 번역) → 캐시·회귀 테스트가 성립한다.
  - 지연 0 — 검색 경로에 Ollama 호출을 넣지 않는다.
  - 없는 내용을 지어낼 여지가 없다(예화/근거 날조 금지 원칙과 같은 방향).

동작 원칙:
  - 한글이 없는 질의는 아무것도 바꾸지 않는다(영어 질의 동작 불변).
  - 원문 한국어 낱말은 그대로 두고 영어 번역어를 **추가**만 한다
    (한국어 본문 TSU도 계속 매칭되도록).
  - 긴 용어 우선 + 이미 잡힌 구간 안의 짧은 용어는 무시한다
    (예: "제사장"이 잡히면 그 안의 "제사"는 따로 번역하지 않는다) —
    QueryParser._detect_books_standalone()의 longest-match 규칙과 같다.
  - 조사 "의"처럼 단독으로 흔한 한 음절은 사전에 넣지 않는다.

이 사전은 신학 용어의 **표준 영역어** 대응표이며 교리 판단이 아니다.
교리 어휘(core/sermon/doctrine_vocabulary.py)와는 별개다. 항목을 바꾸면
QUERY_TRANSLATION_VERSION을 올려 검색 캐시를 무효화한다.
"""

from __future__ import annotations

import re

# 검색 캐시 키에 들어간다(core/search_cache.make_cache_key) — 사전을 바꾸면
# 올려서 이전 번역으로 만든 캐시 결과가 재사용되지 않게 한다.
QUERY_TRANSLATION_VERSION = "3"

_HANGUL_RE = re.compile(r"[가-힣]")

# 한국어 용어 → 영어 검색어. 영어 쪽은 Tantivy 기본 토크나이저/BM25가
# 어간 추출을 하지 않으므로 코퍼스에 흔한 굴절형을 함께 적는다.
KO_EN_THEOLOGY_TERMS: dict[str, list[str]] = {
    # 신론 · 삼위일체
    "하나님": ["god"],
    "하느님": ["god"],
    "여호와": ["jehovah", "lord"],
    "삼위일체": ["trinity"],
    "성부": ["father"],
    "성자": ["son"],
    "성령": ["holy", "spirit"],
    "주님": ["lord"],
    "속성": ["attributes"],
    "주권": ["sovereignty"],
    "책임": ["responsibility"],
    "섭리": ["providence"],
    "창조": ["creation"],
    "계시": ["revelation"],
    # 기독론
    "예수": ["jesus"],
    "그리스도": ["christ"],
    "메시아": ["messiah"],
    "성육신": ["incarnation"],
    "십자가": ["cross"],
    "부활": ["resurrection"],
    "재림": ["second", "coming"],
    "중보자": ["mediator"],
    "중보": ["intercession", "mediator"],
    "제사장": ["priest"],
    # 구원론
    "구원": ["salvation", "saved"],
    "이신칭의": ["justification", "faith"],
    "칭의": ["justification", "justified"],
    "성화": ["sanctification", "sanctified"],
    "영화": ["glorification", "glorified"],
    "중생": ["regeneration", "regenerate"],
    "거듭남": ["regeneration", "born"],
    "회개": ["repentance", "repent"],
    "믿음": ["faith"],
    "신앙": ["faith"],
    "은혜": ["grace"],
    "긍휼": ["mercy"],
    "자비": ["mercy"],
    "사랑": ["love"],
    "선택": ["election", "elect"],
    "예정": ["predestination"],
    "양자": ["adoption"],
    "전가": ["imputation", "imputed"],
    "속죄": ["atonement"],
    "대속": ["atonement", "ransom"],
    "구속": ["redemption"],
    "화목": ["reconciliation"],
    "화해": ["reconciliation"],
    "견인": ["perseverance"],
    "행위": ["works"],
    "의로움": ["righteousness"],
    "의인": ["righteous"],
    "거룩": ["holiness", "holy"],
    # 인간론 · 죄론
    "전적 타락": ["total", "depravity"],
    "원죄": ["original", "sin"],
    "죄인": ["sinner", "sinners"],
    "죄": ["sin", "sins"],
    "타락": ["fall", "depravity"],
    "자유의지": ["free", "will"],
    "영혼": ["soul"],
    "육신": ["flesh"],
    "양심": ["conscience"],
    "교만": ["pride"],
    "시험": ["temptation"],
    "사탄": ["satan"],
    "마귀": ["devil"],
    # 교회론 · 성례
    "교회": ["church"],
    "세례": ["baptism"],
    "침례": ["baptism", "immersion"],
    "성찬": ["supper", "communion"],
    "주의 만찬": ["supper", "communion"],
    "성도": ["saints"],
    "제자도": ["discipleship"],
    "제자": ["disciple", "disciples"],
    "사도": ["apostle", "apostles"],
    "목사": ["pastor", "minister"],
    "장로": ["elder", "elders"],
    "집사": ["deacon", "deacons"],
    "예배": ["worship"],
    "기도": ["prayer", "pray"],
    "찬양": ["praise"],
    "찬송": ["hymn", "praise"],
    "설교": ["sermon", "preaching"],
    "전도": ["evangelism", "preaching"],
    "선교": ["missions"],
    "금식": ["fasting"],
    "안식일": ["sabbath"],
    "성전": ["temple"],
    "제사": ["sacrifice", "offering"],
    "희생": ["sacrifice"],
    # 성경 · 언약
    "성경": ["scripture", "bible"],
    "말씀": ["word"],
    "언약": ["covenant"],
    "율법주의": ["legalism"],
    "율법": ["law"],
    "복음": ["gospel"],
    "선지자": ["prophet", "prophets"],
    "예언": ["prophecy"],
    "이스라엘": ["israel"],
    "유대인": ["jews"],
    "이방인": ["gentiles"],
    # 종말론
    "종말론": ["eschatology"],
    "종말": ["end", "last", "days"],
    "심판": ["judgment"],
    "하나님 나라": ["kingdom"],
    "하나님나라": ["kingdom"],
    "천국": ["heaven", "kingdom"],
    "지옥": ["hell"],
    "영생": ["eternal", "life"],
    "영광": ["glory"],
    # 그리스도인의 삶
    "소망": ["hope"],
    "평강": ["peace"],
    "평화": ["peace"],
    "순종": ["obedience"],
    "겸손": ["humility"],
    "인내": ["patience", "perseverance"],
    "고난": ["suffering", "affliction"],
    "감사": ["thanksgiving"],
    "천사": ["angel", "angels"],
    # 신학 일반
    "교리": ["doctrine"],
    "신학": ["theology"],
}

# 긴 용어부터 시도해야 짧은 용어가 긴 용어 안에서 따로 잡히지 않는다.
_TERMS_LONGEST_FIRST: list[str] = sorted(KO_EN_THEOLOGY_TERMS, key=len, reverse=True)


def has_hangul(text: str) -> bool:
    return bool(_HANGUL_RE.search(text))


_ROMAN_NUMERALS = [
    (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
    (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
]


def to_roman(n: int) -> str:
    out = ""
    for value, numeral in _ROMAN_NUMERALS:
        while n >= value:
            out += numeral
            n -= value
    return out


def scripture_ref_terms(refs: list) -> list[str]:
    """[v2] Chapter/verse of detected references in the corpus' own notation.

    실측(2026-09-26, 주요 14권): 영어 본문 구절 표기는 로마숫자 장
    "Romans viii. 28"이 4,854건(79%), "8:28" 1,133건, "8. 28" 222건.
    Tantivy/BM25 토크나이저는 "viii."→"viii", "8:28"→"8","28"로 쪼개므로
    로마숫자 장 + 아라비아 장 + 절 번호를 각각 검색어로 넣는다.
    verse_start==0은 파서의 "장만 지정" 표시라 절 번호를 넣지 않는다.
    """
    terms: list[str] = []
    for ref in refs:
        chapter = getattr(ref, "chapter", None)
        if not chapter or chapter <= 0:
            continue
        candidates = [to_roman(chapter), str(chapter)]
        verse_start = getattr(ref, "verse_start", 0) or 0
        if verse_start > 0:
            candidates.append(str(verse_start))
        for term in candidates:
            if term not in terms:
                terms.append(term)
    return terms


_MAX_PHRASES = 12


def scripture_ref_phrases(refs: list, book_aliases: dict[str, list[str]]) -> list[list[str]]:
    """[v2] Word sequences for Tantivy phrase queries, one per (alias ×
    chapter notation) of each detected reference — e.g. ROM 8:28 →
    ["romans","viii","28"], ["rom","viii","28"], ["romans","8","28"], …

    Term OR-matching alone let common tokens ("iii" in "Matthew iii") pull
    unrelated chunks up for "요한복음 3장 16절"; an exact adjacency match
    ("John iii. 16" tokenizes to john/iii/16) is the precise signal.
    Only ASCII aliases of 3+ letters are used (skips "ro", "jn").
    """
    phrases: list[list[str]] = []
    for ref in refs:
        chapter = getattr(ref, "chapter", None)
        if not chapter or chapter <= 0:
            continue
        verse_start = getattr(ref, "verse_start", 0) or 0
        tail_options = [[to_roman(chapter)], [str(chapter)]]
        if verse_start > 0:
            tail_options = [t + [str(verse_start)] for t in tail_options]
        for alias in book_aliases.get(getattr(ref, "book_id", ""), []):
            words = alias.lower().split()
            if not alias.isascii() or not words or len(words[-1]) < 3 or not words[-1].isalpha():
                continue
            for tail in tail_options:
                phrase = words + tail
                if phrase not in phrases:
                    phrases.append(phrase)
    return phrases[:_MAX_PHRASES]


def translate_query_terms(
    query: str, book_names: list[str] | None = None, scripture_refs: list | None = None
) -> list[str]:
    """Return English search terms for a Korean query (empty if no Hangul).

    `book_names`: English names of books the parser already detected
    (e.g. ["romans"]) — added so a Korean book mention ("로마서") also
    matches English body text. `scripture_refs`: parsed references whose
    chapter/verse are added in corpus notation (see scripture_ref_terms). Output is de-duplicated, ordered by where
    each term appears in the query, with book names first.
    """
    if not query or not has_hangul(query):
        return []

    claimed: list[tuple[int, int]] = []
    hits: list[tuple[int, str]] = []
    for term in _TERMS_LONGEST_FIRST:
        start = query.find(term)
        while start != -1:
            end = start + len(term)
            if not any(s <= start and end <= e for s, e in claimed):
                claimed.append((start, end))
                hits.append((start, term))
            start = query.find(term, end)

    terms: list[str] = []
    for name in book_names or []:
        for word in name.lower().split():
            if word.isalpha() and word not in terms:
                terms.append(word)
    for term in scripture_ref_terms(scripture_refs or []):
        if term not in terms:
            terms.append(term)
    for _, ko in sorted(hits):
        for en in KO_EN_THEOLOGY_TERMS[ko]:
            if en not in terms:
                terms.append(en)
    return terms


# 구문 바로 앞에 서수가 붙은 경우 — "1 John iii. 16", "I. John", "First John".
# Tantivy 구문 질의는 앞 토큰을 배제할 수 없어 "john iii 16"이 요한일서
# 표기에도 일치한다(실측: 요한복음 3장 16절 질의 1위가 요일 3:16 설교).
_ORDINAL_PREFIX_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:[123]|i{1,3}|first|second|third|1st|2nd|3rd)[\s.]*$", re.IGNORECASE
)


def verse_phrase_match_kind(content: str, phrases: list[list[str]]) -> str | None:
    """"exact" if some phrase occurs without an ordinal prefix, "ordinal_only"
    if every occurrence is prefixed (a different, numbered book), None if no
    phrase occurs at all. Separators follow the tokenizer: punctuation and
    whitespace between words ("John iii. 16", "John 3:16")."""
    found_ordinal = False
    for words in phrases:
        pattern = re.compile(
            r"\b" + r"[\s.,:;]+".join(re.escape(w) for w in words) + r"\b", re.IGNORECASE
        )
        for m in pattern.finditer(content):
            if _ORDINAL_PREFIX_RE.search(content[max(0, m.start() - 12):m.start()]):
                found_ordinal = True
            else:
                return "exact"
    return "ordinal_only" if found_ordinal else None


# ---------------------------------------------------------------------------
# [FU-007 통합 시도] 아래는 origin/dev/dbma-engine(398bc5cd)의 LLM 번역 전처리.
# 같은 날(2026-09-26) 같은 결함을 두 라인이 각자 고쳐 같은 파일명을 만들었다
# (add/add 충돌). 두 API는 이름이 겹치지 않아 한 모듈에 공존시키고, 어느 쪽을
# 검색 경로에서 호출할지는 호출부(hybrid_candidate_pipeline/candidate_generator)
# 에서 결정한다. 원래 docstring 요지: 한국어 질의 → llama3.1:8b 전체 문장 번역,
# 실패 시 None(순손실 없음), QUERY_TRANSLATION_FALLBACK=false로 비활성.
# ---------------------------------------------------------------------------

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# 한글 음절·자모. 번역 발동 여부 판정에만 쓴다.
_HANGUL_ANY_RE = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")

# 번역은 무거운 신학 모델이 필요한 작업이 아니다 — DEFAULT_GEN_MODEL
# (my-theology-bot-v2, 42GB)을 쓰면 검색 지연이 불필요하게 커진다.
_DEFAULT_TRANSLATION_MODEL = "llama3.1:8b"

# 번역문이 이 길이를 넘으면 모델이 번역이 아니라 설명·답변을 한 것으로 보고
# 버린다(질의는 보통 한 문장이다). 원문 길이에 비례한 상한이 아니라 절대
# 상한을 쓰는 이유: 짧은 질의에 장문 해설을 붙이는 실패가 실제 관측되는 양상.
_MAX_TRANSLATION_CHARS = 400

_PROMPT = """Translate the following Korean search query into English.

Rules:
- Output ONLY the translated query. No explanation, no quotes, no prefix.
- Keep Bible references in standard English form (예: 로마서 8:1-4 -> Romans 8:1-4).
- Preserve theological terms with their standard English equivalents.
- Do not answer the question. Translate it.

Korean query:
{query}"""


def contains_hangul(text: str) -> bool:
    """질의에 한글이 있는지. 번역 발동 판정 전용."""
    return bool(_HANGUL_ANY_RE.search(text or ""))


def is_enabled() -> bool:
    """`QUERY_TRANSLATION_FALLBACK=false`로 끌 수 있다. 기본 활성 —
    끄면 한국어 질의가 다시 0건으로 돌아간다(현재 재현율 0%)."""
    return os.environ.get("QUERY_TRANSLATION_FALLBACK", "true").strip().lower() == "true"


def _model() -> str:
    return os.environ.get("QUERY_TRANSLATION_MODEL", _DEFAULT_TRANSLATION_MODEL).strip()


def _clean(raw: str) -> Optional[str]:
    """모델 출력에서 번역문만 남긴다. 신뢰할 수 없으면 None."""
    if not raw:
        return None
    text = raw.strip()

    # 흔한 군더더기 제거: 앞머리 라벨, 감싼 인용부호.
    text = re.sub(r"^(?:translation|translated query|english)\s*[:：]\s*", "", text, flags=re.I)
    text = text.strip().strip('"').strip("'").strip()

    # 여러 줄로 답하면 첫 줄만 쓴다(설명이 뒤따르는 실패 양상).
    text = text.splitlines()[0].strip() if text else ""

    if not text or len(text) > _MAX_TRANSLATION_CHARS:
        return None
    # 번역 결과에 한글이 그대로 남아 있으면 번역이 아니다.
    if contains_hangul(text):
        return None
    # 영문자가 하나도 없으면 쓸 수 없다.
    if not re.search(r"[A-Za-z]", text):
        return None
    return text


def translate_to_english(query: str) -> Optional[str]:
    """한국어 질의를 영어로 번역한다. 실패·비활성·불필요 시 None.

    절대 예외를 올리지 않는다 — 이 함수는 이미 0건인 막다른 길에서만 호출되고,
    실패하면 그 0건이 유지될 뿐이다. 검색 요청 전체를 깨뜨려서는 안 된다.
    """
    if not is_enabled():
        return None
    if not query or not contains_hangul(query):
        return None

    try:
        import ollama

        result = ollama.generate(
            model=_model(),
            prompt=_PROMPT.format(query=query),
            options={"temperature": 0.0},
        )
        translated = _clean(result.get("response", ""))
    except Exception as e:  # 모델 부재·데몬 정지·타임아웃 전부 여기로
        logger.warning("[query_translation] 번역 실패, 원래 결과 유지: %s", e)
        return None

    if translated:
        logger.info("[query_translation] %r -> %r", query[:60], translated[:60])
    return translated


# 현재 서재가 사실상 비한국어일 때 0건 안내에 덧붙이는 고지.
# 근거: 사용자가 "근거 없음"을 "이 주제가 서재에 없다"로 읽으면 오해가 된다 —
# 실제로는 자료가 있는데 언어가 달라 검색이 실패한 사례가 P0-5 유보 17건 중
# 16건이었다(docs/DBMA_P0_5_EVIDENCE_HOLD_ROOT_CAUSE_001.md). 번역 전처리가
# 들어간 뒤에도 0건이 남는 경우가 있으므로, 원인을 밝혀 두는 것이 정직하다.
_CORPUS_LANGUAGE_NOTICE = (
    "\n\n참고: 현재 서재는 영문 자료로 구성되어 있습니다. 한국어 질문은 검색 시 "
    "자동으로 영어로 번역해 찾지만, 번역된 표현이 원문의 어휘와 어긋나면 근거를 "
    "찾지 못할 수 있습니다. 영어 키워드로 다시 시도하면 찾아지는 경우가 있습니다."
)


def corpus_language_notice(tsus) -> str:
    """서재의 한국어 비중이 낮으면 언어 고지 문구를, 아니면 빈 문자열을 반환한다.

    UI의 0건 안내 뒤에 덧붙이는 용도. 한국어 자료가 쌓이면 자동으로 사라진다.
    실패해도 안내 자체를 깨뜨리지 않도록 예외를 흡수한다.
    """
    try:
        items = list(tsus or [])
        if not items:
            return ""
        ko = sum(1 for t in items if (t.get("language") or "") == "ko")
        if ko / len(items) >= 0.20:
            return ""
    except Exception:  # noqa: BLE001 — 안내 문구가 페이지를 깨뜨리면 안 된다
        return ""
    return _CORPUS_LANGUAGE_NOTICE

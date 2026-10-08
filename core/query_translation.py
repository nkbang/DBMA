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
QUERY_TRANSLATION_VERSION = "4"

_HANGUL_RE = re.compile(r"[가-힣]")

# 이 길이 이하의 용어는 **낱말 시작**에서만 매칭한다. 한 음절은 더 긴 낱말 안에서 우연히
# 걸리기 쉽다 — 실측: "정죄 없음"에서 '죄'(sin)가 '정죄'(condemnation) 속에서 걸려
# `sin, sins`로 오역됐고, 번역어가 비지 않아 LLM 번역(`No condemnation`)이 발동하지
# 않아 롬 8:1 직접 구절을 잃었다. 조사는 용어 **뒤**에 붙으므로("죄가", "죄를") 시작
# 위치 조건은 정상 용례를 막지 않고, 속죄·원죄 같은 합성어는 별도 항목이 맡는다.
_WORD_START_ONLY_MAX_LEN = 1

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
            inside_word = (
                len(term) <= _WORD_START_ONLY_MAX_LEN
                and start > 0
                and _HANGUL_RE.match(query[start - 1]) is not None
            )
            if not inside_word and not any(s <= start and end <= e for s, e in claimed):
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

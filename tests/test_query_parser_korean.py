"""QueryParser 한국어 경로 회귀 테스트 (2026-09-10).

배경: 이 앱의 사용자는 한국어로 묻는 목회자이고 연구 코퍼스는 19세기
영어다. 그런데 QueryParser는 intent 패턴·테마 어휘·키워드 추출이 전부
영문 전용이어서, 한국어 질의는 다음 상태로 랭킹에 들어갔다.

  - `intent="unknown"`
  - `themes=[]`
  - `keywords=[]` → **BM25 점수가 항상 0** (하이브리드 가중치 0.25 손실)
  - TRS 자카드 항상 0 (한국어 문서 상대로도 0 — 개인 서재 경로가 여기 해당)

특히 키워드가 비어 BM25가 0이 되던 것은 비대칭 결함이었다 — 문서 쪽
토큰화(`_tokenize`)는 이미 kiwipiepy 형태소 분석을 쓰고 있었고 질의
쪽만 몰랐다.

이 파일은 (1) 한국어가 실제로 살아났는지와 (2) **영어 동작이 하나도
바뀌지 않았는지**를 함께 고정한다. (2)가 없으면 이 수정은 회귀다.
"""
import pytest

from core.retrieval import (
    QueryParser,
    THEME_KEYWORDS,
    KOREAN_STOP_WORDS,
    bm25_score,
    _thematic_relevance_score,
)


@pytest.fixture(scope="module")
def parser() -> QueryParser:
    return QueryParser()


# ──────────────────────────────────────────────────────────────
# 영어 동작 보존 (회귀 방지 — 이 클래스가 깨지면 수정 자체가 잘못된 것)
# ──────────────────────────────────────────────────────────────

class TestEnglishBehaviourPreserved:
    def test_english_keywords_unchanged(self, parser):
        """토크나이저를 kiwi로 바꿨어도 영어 낱말 추출 결과는 같아야 한다."""
        kws = parser.parse("grace and faith in Romans").keywords
        assert kws == ["grace", "faith", "romans"]

    def test_english_stopwords_still_dropped(self, parser):
        kws = parser.parse("what is the meaning of the covenant").keywords
        assert "the" not in kws and "what" not in kws and "is" not in kws
        assert "meaning" in kws and "covenant" in kws

    def test_short_english_words_still_dropped(self, parser):
        """3자 미만 영단어를 버리던 기존 규칙 유지."""
        assert "go" not in parser.parse("go up to the hill").keywords

    def test_digits_not_treated_as_keywords(self, parser):
        """기존 `[a-zA-Z]{3,}` 정규식이 숫자를 배제하던 동작 유지."""
        assert "5" not in parser.parse("Romans 5:3 patience").keywords

    def test_english_intent_unchanged(self, parser):
        assert parser.parse("explain the meaning of grace").intent == "exegesis"
        assert parser.parse("compare law and grace").intent == "comparison"
        assert parser.parse("what is the doctrine of election").intent == "theological"


# ──────────────────────────────────────────────────────────────
# 한국어 키워드 → BM25
# ──────────────────────────────────────────────────────────────

class TestKoreanKeywords:
    def test_korean_query_yields_keywords(self, parser):
        """이전엔 무조건 빈 리스트였다."""
        kws = parser.parse("칭의와 성화의 차이는 무엇입니까?").keywords
        assert kws, "한국어 질의에서 키워드가 하나도 추출되지 않았다"
        assert "칭의" in kws and "성화" in kws

    def test_particles_stripped_so_forms_unify(self, parser):
        """조사가 달라도 같은 어간으로 모여야 BM25가 성립한다."""
        for q in ["성령의 사역", "성령을 사모하라", "성령께서 하시는 일"]:
            assert "성령" in parser.parse(q).keywords, q

    def test_function_stems_filtered(self, parser):
        """kiwi가 남기는 기능적 어간은 질의어에서 빠져야 한다.

        BM25 점수가 매칭된 항들의 평균이라, 어디에나 있는 어간이 남으면
        평균을 끌어내려 실제로 점수를 악화시킨다.
        """
        kws = parser.parse("환난 중에 있는 성도를 어떻게 위로해야 합니까?").keywords
        assert "성도" in kws and "위로" in kws and "환난" in kws
        for noise in ("하", "있", "중", "어떻", "것", "수"):
            assert noise not in kws, f"불용어 {noise!r}가 남았다"

    def test_meaningful_single_syllables_survive(self, parser):
        """한 음절이라는 이유로 실질 어휘를 버리지 않는다."""
        assert "죄" in parser.parse("죄와 회개").keywords

    def test_bm25_nonzero_for_korean(self, parser):
        """이 수정의 핵심 — 한국어 질의의 BM25가 0을 벗어난다."""
        doc = "고난 가운데서 인내를 배우며 하나님의 은혜를 깨닫는다."
        kws = parser.parse("고난 중의 인내와 하나님의 은혜").keywords
        assert bm25_score(kws, doc) > 0.0


# ──────────────────────────────────────────────────────────────
# intent / 테마 / 교차언어
# ──────────────────────────────────────────────────────────────

class TestKoreanIntent:
    @pytest.mark.parametrize("query,expected", [
        ("이 본문을 주해해 주십시오", "exegesis"),
        ("율법과 복음의 차이는 무엇입니까", "comparison"),
        ("성도를 어떻게 위로해야 합니까", "devotional"),
        ("칭의 교리에 대해 알려주십시오", "theological"),
        ("이와 관련 구절이 또 있습니까", "cross-reference"),
    ])
    def test_korean_intent_detected(self, parser, query, expected):
        assert parser.parse(query).intent == expected

    def test_korean_theological_terms_fall_back_to_theological(self, parser):
        """패턴에 안 걸려도 신학 용어가 있으면 unknown으로 두지 않는다."""
        assert parser.parse("하나님의 주권과 인간의 책임").intent == "theological"

    def test_non_theological_korean_stays_unknown(self, parser):
        """폴백이 아무 한국어에나 걸리면 신호가 아니라 잡음이다."""
        assert parser.parse("오늘 점심은 무엇을 먹을까").intent == "unknown"


class TestCrossLingualThemes:
    def test_every_theme_has_both_languages(self):
        """어느 한 테마라도 한쪽 언어가 비면 그 테마의 다리가 끊긴다."""
        for theme, kws in THEME_KEYWORDS.items():
            assert any(any("가" <= c <= "힣" for c in k) for k in kws), f"{theme}: 한국어 없음"
            assert any(k.isascii() for k in kws), f"{theme}: 영어 없음"

    def test_korean_query_detects_themes(self, parser):
        themes = parser.parse("하나님의 은혜와 믿음").themes
        assert "mercy" in themes and "faith" in themes

    def test_korean_query_bridges_to_english_content(self):
        """한국어 '은혜'와 영어 'grace'가 같은 테마에서 만나야 한다.

        수정 전에는 질의 쪽이 어떤 테마에도 걸리지 않아 본문 한쪽만
        걸린 0.5(=0.3 최종)에 머물렀다.
        """
        q = "고난 중의 인내와 하나님의 은혜"
        en = "Though the Gospel is a Message of pure Grace, it requires patience in tribulation."
        assert _thematic_relevance_score(q, {"content": en}) > 0.3

    def test_korean_query_scores_korean_content(self):
        """개인 서재 경로 — 수정 전에는 정확히 0.0이었다."""
        q = "고난 중의 인내와 하나님의 은혜"
        ko = "고난 가운데서 인내를 배우며 하나님의 은혜를 깨닫는다."
        assert _thematic_relevance_score(q, {"content": ko}) > 0.5

    def test_english_pair_score_unchanged(self):
        """영어×영어 조합은 수정 전 값(0.7455)을 그대로 유지해야 한다."""
        q = "grace and patience in tribulation"
        en = "Though the Gospel is a Message of pure Grace, it requires obedience and patience in tribulation."
        assert _thematic_relevance_score(q, {"content": en}) == pytest.approx(0.7455, abs=1e-4)


class TestKoreanScriptureReference:
    def test_psalms_pyeon_form(self, parser):
        """'시편 23편'은 한국어 시편 인용의 표준형인데 인식되지 않았다."""
        refs = parser.parse("시편 23편 1절의 목자 되신 주님").scripture_refs
        assert [(r.book_id, r.chapter, r.verse_start) for r in refs] == [("PSA", 23, 1)]

    def test_pyeon_chapter_only(self, parser):
        refs = parser.parse("시편 23편을 본문으로").scripture_refs
        assert refs and refs[0].book_id == "PSA" and refs[0].chapter == 23

    def test_jang_form_still_works(self, parser):
        """기존 '장' 형식 회귀 방지."""
        refs = parser.parse("로마서 8장 28절").scripture_refs
        assert [(r.book_id, r.chapter, r.verse_start) for r in refs] == [("ROM", 8, 28)]

    def test_colon_form_still_works(self, parser):
        refs = parser.parse("롬 5:3").scripture_refs
        assert refs and refs[0].book_id == "ROM" and refs[0].chapter == 5


class TestStopWordSetIntegrity:
    def test_theological_terms_not_in_stopwords(self):
        """불용어 목록이 실질 신학 어휘를 삼키면 안 된다."""
        for term in ("은혜", "믿음", "구원", "죄", "성령", "주", "말씀", "언약"):
            assert term not in KOREAN_STOP_WORDS, f"{term}이 불용어로 잡혔다"

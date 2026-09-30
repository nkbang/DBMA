"""tests/test_query_translation_fallback.py — 한국어 질의 번역 폴백 회귀 방지.

근거: `docs/DBMA_P0_5_EVIDENCE_HOLD_ROOT_CAUSE_001.md` — 배포 기준선 코퍼스가
전량 영문이고 Stage-1이 어휘 일치라, P0-5 근거 0건 유보 17건 중 **16건이 후보
0건**이었다(같은 내용이 영어 질의로는 정상 반환). 번역은 Stage-1이 0건일 때만
발동하는 구제 경로다.

이 테스트가 지키는 두 가지 계약:
1. 막다른 길(0건 + 한글)에서만 번역이 호출된다 — 이미 후보를 찾은 질의에
   LLM 지연이 붙으면 2026-09-18 역색인 전환으로 얻은 빠른 경로가 무너진다.
2. 번역이 실패하면 조용히 원래의 0건을 유지한다 — 검색 요청 전체를 깨뜨리거나
   무관한 결과를 지어내지 않는다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.query_translation as qt  # noqa: E402
from core.candidate_generator import CandidateRef  # noqa: E402
from core.hybrid_candidate_pipeline import HybridRetriever  # noqa: E402
from core.retrieval import QueryParser  # noqa: E402


# ── 언어 판정 ────────────────────────────────────────────────


@pytest.mark.parametrize("text,expected", [
    ("로마서 8장은 무엇을 말합니까?", True),
    ("Romans 8 no condemnation", False),
    ("", False),
    ("ㄱㄴㄷ", True),
])
def test_contains_hangul(text, expected):
    assert qt.contains_hangul(text) is expected


# ── 번역 정제 — 신뢰할 수 없는 출력은 버린다 ────────────────


@pytest.mark.parametrize("raw,expected", [
    ("Romans 8 no condemnation", "Romans 8 no condemnation"),
    ('  "Romans 8 no condemnation"  ', "Romans 8 no condemnation"),
    ("Translation: Romans 8 no condemnation", "Romans 8 no condemnation"),
    ("Romans 8\n\n이 구절은 칭의를 다룹니다", "Romans 8"),  # 첫 줄만
])
def test_clean_accepts_usable_output(raw, expected):
    assert qt._clean(raw) == expected


@pytest.mark.parametrize("raw", [
    "",
    "로마서 8장 정죄 없음",          # 번역이 안 됐다
    "１２３ ４５６",                  # 영문자 없음
    "x" * 500,                        # 질의가 아니라 장문 답변
])
def test_clean_rejects_unusable_output(raw):
    assert qt._clean(raw) is None


# ── 번역 함수 — 실패는 조용히 None ──────────────────────────


def test_translate_skips_when_no_hangul(monkeypatch):
    called = []
    monkeypatch.setattr(qt, "_model", lambda: (called.append(1), "m")[1])
    assert qt.translate_to_english("Romans 8 no condemnation") is None
    assert not called, "한글이 없으면 모델을 호출하지 않아야 한다"


def test_translate_disabled_by_flag(monkeypatch):
    monkeypatch.setenv("QUERY_TRANSLATION_FALLBACK", "false")
    assert qt.translate_to_english("로마서 8장") is None


def test_translate_swallows_backend_failure(monkeypatch):
    """모델 부재·데몬 정지가 검색 전체를 깨뜨리면 안 된다."""
    import ollama

    def boom(**_kwargs):
        raise RuntimeError("ollama down")

    monkeypatch.setattr(ollama, "generate", boom)
    assert qt.translate_to_english("로마서 8장") is None


def test_translate_returns_cleaned_text(monkeypatch):
    import ollama

    monkeypatch.setattr(
        ollama, "generate",
        lambda **_k: {"response": 'Translation: "Romans 8:1-4 no condemnation"'},
    )
    assert qt.translate_to_english("로마서 8:1-4은 정죄 없음에 대해 무엇을 말합니까?") == (
        "Romans 8:1-4 no condemnation"
    )


# ── HybridRetriever 배선 ────────────────────────────────────
#
# [2026-09-26 계약 변경] 처음 구현은 "Stage-1이 0건일 때만 번역"이었고 그 설계는
# 실패했다 — 한국어 토큰이 영문 코퍼스의 OCR 잡음에는 걸려서 0건이 되지 않고,
# 따라서 번역이 영원히 발동하지 않았다(실측: 구절 참조 질의 5건이 번역 없이
# OCR 쓰레기·성구 색인 페이지를 후보로 받았다). 발동 기준을 "결과가 비었는가"
# 에서 **"질의 언어와 코퍼스 언어가 어긋났는가"**로 바꿨다.


class _FakeGenerator:
    """영어 질의에만 뜻있는 후보를 내놓는 Stage-1. 한국어 질의에는 잡음을
    돌려준다 — 실제 관측된 동작(OCR 쓰레기 매칭)을 재현해, "0건일 때만 번역"
    설계로는 번역이 발동하지 않음을 테스트가 붙잡을 수 있게 한다."""

    def __init__(self):
        self.queries: list[str] = []

    def search(self, parsed_query, k=30, source_files=None, book_ids=None, **_kw):
        self.queries.append(parsed_query.original_query)
        if qt.contains_hangul(parsed_query.original_query):
            return [CandidateRef(tsu_id="TSU-NOISE", bm25_score=0.1)]
        return [CandidateRef(tsu_id="TSU-X-1", bm25_score=1.0)]


def _retriever(language: str = "en"):
    tsu_by_id = {
        "TSU-X-1": {
            "tsu_id": "TSU-X-1", "language": language, "verse_mapping": {},
            "content": "There is therefore now no condemnation to them which are in Christ.",
        },
        "TSU-NOISE": {
            "tsu_id": "TSU-NOISE", "language": language, "verse_mapping": {},
            "content": "=) EY: == 6 EEKEY KEE EEK SE  . . . = _- ?",  # 실제 관측된 OCR 잡음
        },
    }
    return HybridRetriever(_FakeGenerator(), tsu_by_id), tsu_by_id


def test_hangul_query_is_translated_before_stage1(monkeypatch):
    """계약 1 — 한글 질의 + 영문 코퍼스면 결과가 비기를 기다리지 않고 번역한다."""
    import core.hybrid_candidate_pipeline as hcp
    monkeypatch.setattr(hcp, "translate_to_english", lambda q: "Romans no condemnation")

    r, _ = _retriever(language="en")
    pq = QueryParser().parse("정죄 없음에 대해 무엇을 말합니까?")
    telemetry: dict = {}

    out = r.retrieve(pq, k_output=5, telemetry_out=telemetry)

    assert telemetry.get("translation_used") is True
    assert telemetry.get("translated_query") == "Romans no condemnation"
    # 잡음(TSU-NOISE)이 아니라 영어 질의가 찾은 후보여야 한다
    assert [c.tsu_id for c in out] == ["TSU-X-1"]


def test_noise_match_does_not_suppress_translation(monkeypatch):
    """계약 2 — 한국어 토큰이 잡음에 걸려도 번역이 발동해야 한다.
    이 테스트가 "0건일 때만 번역" 설계의 재발을 막는다."""
    import core.hybrid_candidate_pipeline as hcp
    calls = []
    monkeypatch.setattr(
        hcp, "translate_to_english",
        lambda q: (calls.append(q), "Romans no condemnation")[1],
    )

    r, _ = _retriever(language="en")
    r.retrieve(QueryParser().parse("정죄 없음"), k_output=5, telemetry_out={})

    assert calls, "잡음 후보가 있다는 이유로 번역을 건너뛰면 안 된다"


def test_english_query_never_translated(monkeypatch):
    import core.hybrid_candidate_pipeline as hcp
    calls = []
    monkeypatch.setattr(hcp, "translate_to_english", lambda q: calls.append(q) or "X")

    r, _ = _retriever()
    r.retrieve(QueryParser().parse("no condemnation in Christ"), k_output=5, telemetry_out={})

    assert calls == [], "한글이 없으면 번역을 호출하지 않는다"


def test_korean_corpus_disables_translation(monkeypatch):
    """계약 3 — 코퍼스에 한국어 자료가 쌓이면 번역 전처리가 자동으로 멈춘다."""
    import core.hybrid_candidate_pipeline as hcp
    calls = []
    monkeypatch.setattr(hcp, "translate_to_english", lambda q: calls.append(q) or "X")

    r, _ = _retriever(language="ko")
    r.retrieve(QueryParser().parse("정죄 없음"), k_output=5, telemetry_out={})

    assert calls == [], "한국어 코퍼스에서는 번역이 필요 없다"


def test_translation_failure_proceeds_with_original_query(monkeypatch):
    """계약 4 — 번역 실패가 검색 요청을 깨뜨리지 않는다."""
    import core.hybrid_candidate_pipeline as hcp
    monkeypatch.setattr(hcp, "translate_to_english", lambda q: None)

    r, _ = _retriever()
    telemetry: dict = {}
    out = r.retrieve(QueryParser().parse("정죄 없음"), k_output=5, telemetry_out=telemetry)

    assert "translation_used" not in telemetry
    assert isinstance(out, list)  # 크래시 없이 원래 질의로 진행


def test_book_filter_skipped_when_corpus_has_no_book_ids(monkeypatch):
    """구절 참조 질의가 구조적으로 0건이 되던 문제 — book_id가 0%인 코퍼스에서는
    만족 불가능한 필터를 애초에 얹지 않는다."""
    import core.hybrid_candidate_pipeline as hcp
    monkeypatch.setattr(hcp, "translate_to_english", lambda q: "Romans 8 no condemnation")

    r, gen_owner = _retriever()
    captured = {}
    orig = r.candidate_generator.search

    def spy(parsed_query, k=30, source_files=None, book_ids=None, **kw):
        captured["book_ids"] = book_ids
        return orig(parsed_query, k=k, source_files=source_files, book_ids=book_ids, **kw)

    r.candidate_generator.search = spy
    r.retrieve(QueryParser().parse("로마서 8장 정죄 없음"), k_output=5, telemetry_out={})

    assert captured["book_ids"] == [], "book_id가 없는 코퍼스에서 필터를 얹으면 전건 탈락한다"

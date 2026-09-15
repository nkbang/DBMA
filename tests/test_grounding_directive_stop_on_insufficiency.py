"""Regression test — _GROUNDING_DIRECTIVE §2 "부족 인정 후 멈춤" (2026-09-11).

실측 결함(P0-5 대표 질의 A1, 사용자 실행): 종전 §2("부족하다고 밝히고
자료가 실제로 말하는 데까지만 답하라")가 "로마서 8:1-4은 무엇을
말합니까?" 질의에서 다음처럼 새어 나갔다 —

    "자료에는 … 언급되어 있지 않습니다. 따라서 … 제공할 수 없습니다.
    그러나 일반적인 신학적 관점에서, 로마서 8:1-4은 …"

부족 인정까지는 지시대로였으나, 곧바로 일반 지식(성경 본문 기억 인용+
해설)을 이어 붙였다. §2를 "부족을 밝히면 거기서 멈춰라"로 명시해
전환구를 직접 차단한다. 이 테스트는 텍스트 상수만 검증한다 — 모델이
실제로 지키는지는 P0-5 인적 채점(docs/NAE_GOLD_QUERY_SET_P0_5_001.md)의
몫이다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import generation


def test_directive_forbids_the_observed_transition_phrases():
    d = generation._GROUNDING_DIRECTIVE
    assert "그러나 일반적으로" in d
    assert "일반적인 신학적 관점에서" in d


def test_directive_explicitly_says_stop_after_admitting_insufficiency():
    d = generation._GROUNDING_DIRECTIVE
    assert "그 사실만 밝히고 답을 끝내라" in d


def test_directive_names_reciting_scripture_from_memory_as_out_of_bounds():
    # 실측 사례의 핵심 허점: "성경 본문이니 괜찮다"는 예외를 두지 않는다.
    d = generation._GROUNDING_DIRECTIVE
    assert "성경 본문 자체를 기억으로 인용" in d


def test_directive_gives_a_concrete_closing_sentence_for_total_gap():
    d = generation._GROUNDING_DIRECTIVE
    assert "이 질문은 현재 등록된 자료로는 답할 수 없습니다." in d


def test_no_context_variant_unchanged():
    # 이번 수정은 §2(문맥 있음) 한정 — 문맥이 아예 없을 때 쓰는 축약본은
    # 손대지 않는다.
    d0 = generation._GROUNDING_DIRECTIVE_NO_CONTEXT
    assert d0.startswith("지시:\n1. 참고할 자료가 검색되지 않았다.")
    assert "그러나 일반적으로" not in d0

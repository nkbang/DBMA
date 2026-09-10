"""NAE 브리지 답변 컨텍스트 조립 검증 — NAE/answer_context.py
(PM 정렬 감사 선결 #4 / 옵션 A, Task Order §3 산출물).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from NAE import answer_context
from NAE.answer_context import (
    NAE_PARAGRAPH_PROMPT_CLAUSE,
    build_nae_answer_prompt,
    format_nae_context_block,
    paragraph_evidence_enabled,
)


def _hit(**over):
    base = {
        "tsu_id": "TSU-0001",
        "evidence_paragraph": "회심하지 않은 죄인들에게도 그리스도를 믿을 의무가 있다. "
        "이 의무는 복음의 명령에서 직접 나온다.",
        "anchor_sentence": "회심하지 않은 죄인들에게도 그리스도를 믿을 의무가 있다.",
        "paragraph_resolved": True,
        "bibliography": {
            "author": "Andrew Fuller",
            "work": "The Gospel Worthy of All Acceptation",
            "page_start": 132,
            "page_end": 133,
            "paragraph_index": 418,
            "identifier": "Fuller_Complete_Works_Vol01",
        },
    }
    base.update(over)
    return base


def test_context_block_carries_bibliography_attributes():
    block = format_nae_context_block([_hit()])
    assert 'work="The Gospel Worthy of All Acceptation"' in block
    assert 'author="Andrew Fuller"' in block
    assert 'page="p.132-133"' in block
    assert 'para="§418"' in block
    assert "<자료" in block and "</자료>" in block


def test_context_block_includes_anchor_sentence_when_present():
    block = format_nae_context_block([_hit()])
    assert "<일치문장>회심하지 않은 죄인들에게도 그리스도를 믿을 의무가 있다.</일치문장>" in block


def test_context_block_full_paragraph_not_truncated_to_200():
    long_para = "가" * 800 + " 끝문장입니다."
    block = format_nae_context_block([_hit(evidence_paragraph=long_para, anchor_sentence="끝문장입니다.")])
    assert "가" * 800 in block          # 전문 유지
    assert "truncated" not in block      # 1500자 미만


def test_context_block_shrinks_over_limit_paragraph(monkeypatch):
    monkeypatch.setenv("NAE_PARAGRAPH_MAX_CHARS", "300")
    para = "앞부분 " * 40 + "핵심 앵커 문장이다. " + "뒷부분 " * 40
    block = format_nae_context_block([_hit(evidence_paragraph=para, anchor_sentence="핵심 앵커 문장이다.")])
    assert 'truncated="true"' in block
    assert "핵심 앵커 문장이다." in block  # 앵커는 살아남음
    assert len(block) < len(para) + 400


def test_context_block_marks_unresolved():
    block = format_nae_context_block([_hit(paragraph_resolved=False)])
    assert 'resolved="false"' in block


def test_prompt_clause_has_paragraph_and_attribution_rules():
    assert "완결된 원문 문단" in NAE_PARAGRAPH_PROMPT_CLAUSE
    assert "2~4개의 완결된 한국어 문단" in NAE_PARAGRAPH_PROMPT_CLAUSE
    assert "저자·저작" in NAE_PARAGRAPH_PROMPT_CLAUSE
    assert "일치문장" in NAE_PARAGRAPH_PROMPT_CLAUSE


def test_build_prompt_orders_grounding_before_paragraph_before_denomination():
    p = build_nae_answer_prompt("[근거강제]", "[교단]", "<자료 id='x'>본문</자료>", "질문?")
    assert p.index("자료:") < p.index("[근거강제]")
    assert p.index("[근거강제]") < p.index(NAE_PARAGRAPH_PROMPT_CLAUSE)
    assert p.index(NAE_PARAGRAPH_PROMPT_CLAUSE) < p.index("[교단]")
    assert p.index("[교단]") < p.index("질문:")


def test_sub_flag_default_on_and_toggle(monkeypatch):
    monkeypatch.delenv("NAE_PARAGRAPH_EVIDENCE", raising=False)
    assert paragraph_evidence_enabled() is True
    monkeypatch.setenv("NAE_PARAGRAPH_EVIDENCE", "0")
    assert paragraph_evidence_enabled() is False
    monkeypatch.setenv("NAE_PARAGRAPH_EVIDENCE", "1")
    assert paragraph_evidence_enabled() is True


def test_context_budget_drops_lowest_ranked(monkeypatch):
    monkeypatch.setenv("NAE_PARAGRAPH_CONTEXT_BUDGET", "2500")
    hits = [
        _hit(tsu_id=f"TSU-{n}", evidence_paragraph=("문장입니다. " * 120), anchor_sentence="문장입니다.")
        for n in range(5)
    ]
    block = format_nae_context_block(hits)
    # 예산 2500자에 ~840자 문단이면 2~3개만 들어감
    assert block.count("<자료") <= 3
    assert "TSU-0" in block          # 최상위는 유지
    assert "TSU-4" not in block      # 최하위는 드롭

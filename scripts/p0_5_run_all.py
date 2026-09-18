#!/usr/bin/env python3
"""P0-5: 대표 질의 24건(A~H) 실채점용 원문 답변 수집.

docs/NAE_GOLD_QUERY_SET_P0_5_001.md의 실행 방법을 그대로 재현한다 —
Streamlit UI(dbma_ui.py → 질문하기 탭)와 동일한 프로덕션 경로
(core/retrieval.py::QueryProcessor/HybridQueryProcessor →
core/generation.py::GenerationService, k=5, file_scope=None(전체 파일),
근거 0건 하드 게이트 포함)를 코드로 그대로 밟는다. 채점(PASS/FLAG/FAIL,
신학적 정합성·목회적 유용성 등)은 이 스크립트가 하지 않는다 — 그 문서가
명시하듯 "사용자만 할 수 있다"(임계 경로). 이 스크립트는 그 채점에
쓸 원문 답변·출처·ClaimGuard 신호를 모으기만 한다.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.generation import GenerationService
from core.hybrid_candidate_pipeline import HybridQueryProcessor, is_enabled
from core.retrieval import QueryProcessor

# ui/pages/chat.py::_NO_EVIDENCE_HOLD_TEXT과 동일 문구 (P0-6 하드 게이트) —
# 여기서는 chat.py를 import하지 않는다(streamlit 런타임 의존 없이 이 문구만
# 재사용하기 위해 문자열을 그대로 복제).
_NO_EVIDENCE_HOLD_TEXT = (
    "현재 등록된 자료에서 이 질문에 답할 근거를 찾지 못했습니다.\n\n"
    "이 앱은 등록·처리된 자료에 근거해서만 답변하도록 설계되어 있어, "
    "관련 자료가 없을 때는 일반 지식만으로 답을 만들지 않습니다. "
    "관련 문서를 추가하거나, 검색 범위를 넓히거나, 질문을 다르게 표현해 "
    "다시 시도해 주세요."
)

QUERIES: list[tuple[str, str]] = [
    ("A1", "로마서 8:1-4은 그리스도인의 정죄 없음에 대해 무엇을 말합니까?"),
    ("A2", '창세기 1:26-27의 "하나님의 형상"(Imago Dei)은 무엇을 의미합니까?'),
    ("A3", '마태복음 28:19-20의 "모든 민족을 제자로 삼으라"는 명령의 신학적 함의는 무엇입니까?'),
    ("B1", "유아세례가 아니라 신자의 침례(believer's baptism)를 주장하는 성경적·신학적 근거는 무엇입니까?"),
    ("B2", "칭의(justification)와 성화(sanctification)는 어떻게 다릅니까?"),
    ("B3", "개혁파 침례교 관점에서 교회의 권징(church discipline)은 어떤 절차를 따라야 합니까?"),
    ("C1", '로마서 8장을 본문으로 "성령 안에서 사는 자유"라는 주제의 설교 대지를 짜 주세요.'),
    ("C2", "히브리서 11장(믿음장)으로 청년부를 위한 설교를 준비 중입니다. 적용점을 제안해 주세요."),
    ("C3", "새해를 맞아 교회 언약(church covenant)을 주제로 설교하려 합니다. 핵심 논지를 정리해 주세요."),
    ("D1", "유아세례에 대한 개혁주의(장로교) 입장과 침례교 입장의 차이를 비교해 주세요."),
    ("D2", "예정론에 대한 칼빈주의와 알미니안주의의 입장을 비교해 주세요."),
    ("D3", "성찬(주의 만찬)의 의미에 대한 침례교와 루터교의 이해 차이는 무엇입니까?"),
    ("E1", "배우자의 외도로 이혼을 고민하는 교인을 성경적으로 어떻게 상담해야 합니까?"),
    ("E2", "오랜 우울증을 겪는 성도를 목회적으로 어떻게 돌봐야 합니까?"),
    ("E3", "자녀를 잃은 부모를 위로할 때 신학적으로 조심해야 할 것은 무엇입니까?"),
    ("F1", "Hiscox의 「The Standard Manual for Baptist Churches」에서 집사(deacon)의 자격은 어떻게 규정됩니까?"),
    ("F2", "Dagg의 「Church Order」에서 교회의 표지(marks of the church)는 무엇이라고 설명합니까?"),
    ("F3", 'Andrew Fuller가 「모든 사람이 받아들일 만한 복음」(The Gospel Worthy of All Acceptation)에서 말한 "믿을 의무"란 무엇입니까?'),
    ("G1", "인공지능(AI) 윤리에 대해 개혁파 침례교 신학은 공식적으로 어떤 입장을 취합니까?"),
    ("G2", '"존 스미스 3세"라는 신학자가 주장했다는 교회론의 핵심 내용은 무엇입니까?'),
    ("G3", "화성 이주가 신학적으로 정당화될 수 있습니까?"),
    ("H1", "선하신 하나님이 다스리시는 세상에 왜 악과 고통이 존재합니까?"),
    ("H2", "여호수아서에서 하나님이 가나안 족속을 진멸하라고 명령하신 것을 오늘날 어떻게 이해해야 합니까?"),
    ("H3", "창세기의 창조 기사와 현대 과학(진화론 등)은 어떻게 조화될 수 있습니까?"),
]

_K = 5  # ui/pages/chat.py::_SCOPE_K["전체 파일"]과 동일


def _build_processor():
    return HybridQueryProcessor() if is_enabled() else QueryProcessor()


def main() -> None:
    processor = _build_processor()
    generator = GenerationService()
    results = []

    for tag, question in QUERIES:
        t0 = time.time()
        print(f"[{tag}] {question}", flush=True)
        response = processor.process(question, query_id=f"p0-5-{tag}", k=_K, file_scope=None)

        if not response.top_k_results:
            print(f"  -> evidence_hold (0 results, {time.time() - t0:.1f}s)", flush=True)
            results.append({
                "tag": tag,
                "question": question,
                "answer": _NO_EVIDENCE_HOLD_TEXT,
                "evidence_hold": True,
                "citations": [],
                "claim_guard": None,
            })
            continue

        result = generator.generate(response)
        cg = result.claim_guard_result
        citations = [
            {
                "source_title": c.source_title,
                "source_author": c.source_author,
                "scripture_reference": c.scripture_reference,
            }
            for c in (result.citations or [])
        ]
        print(
            f"  -> {len(result.answer)} chars, {len(citations)} citations,"
            f" claim_guard={'RISK' if cg and cg.risk_level.value != 'none' else 'none'}"
            f" ({time.time() - t0:.1f}s)",
            flush=True,
        )
        results.append({
            "tag": tag,
            "question": question,
            "answer": result.answer,
            "evidence_hold": False,
            "error": result.error,
            "citations": citations,
            "claim_guard": {
                "risk_level": cg.risk_level.value,
                "absolute_claim_blocked": cg.absolute_claim_blocked,
                "scope_qualifier_required": cg.scope_qualifier_required,
                "reason": cg.reason,
            } if cg else None,
        })

    out_path = "docs/NAE_GOLD_QUERY_SET_P0_5_RAW_ANSWERS_001.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"ALL DONE -> {out_path}", flush=True)


if __name__ == "__main__":
    main()

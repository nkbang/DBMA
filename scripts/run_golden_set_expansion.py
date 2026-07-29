"""ADR-010/ADR-012 골든셋 3건→7건 동시 확장 — 신규 4건 실측.

기존 gold-1~3(tests/fixtures/rag_eval_golden_set.json)과 SEQ001~003
(docs/DBMA-SEQ-Phase1-Groundedness-Baseline-2026-07-27.md)은 같은
성경 본문 3개(요한복음15/로마서8/히브리서)를 RAG 질문과 설교 주제
양쪽에 재사용했다 — 이번 확장도 같은 방식으로, 신규 본문 4개를
골라 RAG 질문형과 설교 주제형을 동시에 만든다.

사람 채점(human_groundedness)은 이 스크립트가 채우지 않는다 — judge
점수와 실제 답변/개요만 산출해 tests/fixtures/rag_eval_golden_set.json에
빈 human_groundedness 항목으로 추가하고, 사용자가 직접 채점한다.

Usage:
    python scripts/run_golden_set_expansion.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.evaluation.rag_judge import judge_groundedness
from core.evaluation.sermon_judge import judge_sermon_groundedness
from core.generation import GenerationService, SermonDraftService
from core.retrieval import QueryProcessor

RUN_ID = "goldexp_001"

NEW_ITEMS = [
    {
        "id": "gold-4",
        "seq_id": "SEQ004",
        "question": "시편 23편에서 여호와의 목자 되심은 어떻게 표현되는가?",
        "scripture_and_theme": "시편 23편 여호와는 나의 목자시니",
    },
    {
        "id": "gold-5",
        "seq_id": "SEQ005",
        "question": "에베소서 2장에서 은혜로 말미암은 구원은 어떻게 설명되는가?",
        "scripture_and_theme": "에베소서 2장 은혜로 구원받음",
    },
    {
        "id": "gold-6",
        "seq_id": "SEQ006",
        "question": "갈라디아서 5장에서 성령의 열매는 어떻게 나열되는가?",
        "scripture_and_theme": "갈라디아서 5장 성령의 열매",
    },
    {
        "id": "gold-7",
        "seq_id": "SEQ007",
        "question": "마태복음 5장에서 팔복은 어떻게 선포되는가?",
        "scripture_and_theme": "마태복음 5장 팔복",
    },
]


def run() -> None:
    processor = QueryProcessor()
    gen_service = GenerationService()
    sermon_service = SermonDraftService()

    worksheet = []

    for i, item in enumerate(NEW_ITEMS, 1):
        print(f"\n[{i}/{len(NEW_ITEMS)}] {item['id']} / {item['seq_id']}", flush=True)

        # --- RAG groundedness (ADR-010) ---
        print(f"  RAG: {item['question']!r}", flush=True)
        response = processor.process(item["question"], query_id=item["id"], k=5)
        gen_result = gen_service.generate(response)
        rag_score = judge_groundedness(
            run_id=RUN_ID,
            query_id=item["id"],
            question=item["question"],
            retrieved_chunks=[c.content for c in response.top_k_results],
            retrieved_chunk_ids=[c.tsu_id for c in response.top_k_results],
            answer=gen_result.answer,
        )
        print(f"    judge_groundedness={rag_score.groundedness}", flush=True)

        # --- Sermon groundedness (ADR-012) ---
        print(f"  Sermon: {item['scripture_and_theme']!r}", flush=True)
        sermon_response = processor.process(item["scripture_and_theme"], query_id=item["seq_id"], k=20)
        outline, error = sermon_service.generate_outline(
            item["scripture_and_theme"], sermon_response.top_k_results
        )
        sermon_score = None
        if error is None:
            outline_text = (
                f"제목: {outline.title}\n서론: {outline.introduction}\n"
                + "\n".join(f"대지: {p}" for p in outline.points)
                + f"\n결론: {outline.conclusion}"
            )
            sermon_score = judge_sermon_groundedness(
                run_id=RUN_ID,
                query_id=item["seq_id"],
                scripture_and_theme=item["scripture_and_theme"],
                retrieved_candidates=sermon_response.top_k_results,
                generated_text=outline_text,
                text_type="outline",
            )
            print(f"    judge_sermon_groundedness={sermon_score.groundedness}", flush=True)
        else:
            print(f"    개요 생성 실패: {error}", flush=True)

        worksheet.append({
            "query_id": item["id"],
            "seq_id": item["seq_id"],
            "question": item["question"],
            "scripture_and_theme": item["scripture_and_theme"],
            "rag_answer": gen_result.answer,
            "rag_chunks": [c.content for c in response.top_k_results],
            "rag_judge_groundedness": rag_score.groundedness,
            "rag_judge_rationale": rag_score.groundedness_rationale,
            "sermon_outline": outline_text if error is None else None,
            "sermon_judge_groundedness": sermon_score.groundedness if sermon_score else None,
            "sermon_judge_rationale": sermon_score.groundedness_rationale if sermon_score else None,
            "human_groundedness_rag": None,
            "human_groundedness_sermon": None,
        })

    out_path = Path("output/eval") / f"{RUN_ID}_worksheet.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(worksheet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== 완료: {len(worksheet)}건, 채점 워크시트 저장: {out_path} ===")


if __name__ == "__main__":
    run()

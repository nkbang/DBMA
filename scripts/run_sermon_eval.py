"""ADR-012 DBMA-SEQ Phase 1 후속 — 설교 개요 생성 groundedness 베이스라인.

sermon_judge.py의 judge_sermon_groundedness()가 구현·테스트는 됐지만
(core/evaluation/sermon_judge.py, tests/test_sermon_judge.py) 어디서도
실제로 호출된 적이 없다 — mock 테스트만 통과했지 실제 Ollama 생성
결과를 채점해본 적이 없다. 이 스크립트는 ui/pages/sermon_draft.py와
동일한 실제 경로(QueryProcessor.process() -> SermonDraftService.
generate_outline() -> judge_sermon_groundedness())를 그대로 태워
처음으로 실측 신호를 만든다.

RetrievalEngine/GenerationService/SermonDraftService 자체는 수정하지
않는다. 결과는 output/eval/{run_id}_sermon_eval.jsonl에 append-only로
저장한다(scripts/run_rag_eval.py와 동일 패턴).

기본값은 3개 주제로 작게 시작한다(judge/생성 모델 둘 다 로컬 42GB
Ollama 모델이라 문항당 지연이 큼 — feedback_verification_cost_
discipline 원칙).

Usage:
    python scripts/run_sermon_eval.py [--k 20] [--run-id RUN_ID]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.evaluation.sermon_judge import judge_sermon_groundedness
from core.generation import SermonDraftService
from core.retrieval import QueryProcessor

OUTPUT_DIR = Path("output/eval")

# ui/pages/sermon_draft.py의 실제 입력 형식(scripture_and_theme 텍스트
# 필드)과 동일한 형태 — 실제 사용자가 입력할 법한 본문/주제 조합.
# 임의로 지어내지 않고, ADR-010 골든셋 채점에 실제로 쓰였던 본문
# 3건(요한복음 15장/로마서 8장/히브리서 대제사장, docs/architecture/
# ADR-010-DBMA-REQ-RAG-Evaluation-Quality.md §Decision-미확정-1)을
# 그대로 재사용한다 — 새 예시를 만들지 않는다.
SAMPLE_THEMES = [
    {"id": "SEQ001", "scripture_and_theme": "요한복음 15장 포도나무 비유"},
    {"id": "SEQ002", "scripture_and_theme": "로마서 8장 성령 안에서의 삶"},
    {"id": "SEQ003", "scripture_and_theme": "히브리서 대제사장이신 그리스도"},
]


def run(k: int, run_id: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{run_id}_sermon_eval.jsonl"

    processor = QueryProcessor()
    service = SermonDraftService()

    print(f"표본 {len(SAMPLE_THEMES)}건, k={k}, run_id={run_id}")

    scores = []
    with out_path.open("w", encoding="utf-8") as f:
        for i, item in enumerate(SAMPLE_THEMES, 1):
            query_id = item["id"]
            scripture_and_theme = item["scripture_and_theme"]
            print(f"[{i}/{len(SAMPLE_THEMES)}] {query_id}: {scripture_and_theme!r} 처리 중...", flush=True)

            response = processor.process(scripture_and_theme, query_id=query_id, k=k)
            outline, error = service.generate_outline(scripture_and_theme, response.top_k_results)
            if error is not None:
                print(f"    개요 생성 실패: {error}", flush=True)
                continue

            outline_text = (
                f"제목: {outline.title}\n서론: {outline.introduction}\n"
                + "\n".join(f"대지: {p}" for p in outline.points)
                + f"\n결론: {outline.conclusion}"
            )

            score = judge_sermon_groundedness(
                run_id=run_id,
                query_id=query_id,
                scripture_and_theme=scripture_and_theme,
                retrieved_candidates=response.top_k_results,
                generated_text=outline_text,
                text_type="outline",
            )
            scores.append(score)
            f.write(json.dumps(score.to_dict(), ensure_ascii=False) + "\n")
            f.flush()
            print(
                f"    candidates={len(response.candidates)} "
                f"top_k={len(response.top_k_results)} "
                f"groundedness={score.groundedness}",
                flush=True,
            )

    avg = sum(s.groundedness for s in scores) / len(scores) if scores else 0.0
    print()
    print(f"=== 완료: {len(scores)}건, 평균 groundedness={avg:.2f}/5 ===")
    print(f"결과 저장: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="ADR-012 DBMA-SEQ — 설교 개요 groundedness 베이스라인")
    parser.add_argument("--k", type=int, default=20, help="주제당 검색 결과 수 (sermon_draft.py와 동일 기본값 20)")
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ"),
        help="run_id (기본: 타임스탬프)",
    )
    args = parser.parse_args()
    run(args.k, args.run_id)


if __name__ == "__main__":
    main()

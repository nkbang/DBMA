"""ADR-010 DBMA-REQ Phase 2 — 검색 품질 + 생성 품질(groundedness) 베이스라인 측정.

tests/gold_queries.json에서 질의를 뽑아 실제 프로덕션 경로
(QueryProcessor.process() -> GenerationService.generate() ->
judge_groundedness())를 그대로 태워서, 검색이 빗나갔는지 생성이
약한지 구분할 수 있는 리포트를 만든다. RetrievalEngine/
GenerationService 자체는 수정하지 않는다(ADR-010 Decision §1).

결과는 output/eval/{run_id}_eval.jsonl에 append-only로 저장한다
(core.evaluation.schemas.RagEvalScore.to_dict() 그대로 한 줄씩).

기본값은 5문항으로 작게 표본을 잡는다 — judge 모델(dbma-planner-
r1-q6:70b, 42GB)과 생성 모델(my-theology-bot-v2, 42GB) 둘 다 로컬
Ollama 호출이라 문항당 지연이 크다. 전체 100문항을 한 번에 돌리기
전에 먼저 작은 표본으로 파이프라인이 정상 동작하는지 확인한다.

Usage:
    python scripts/run_rag_eval.py [--n 5] [--k 5] [--run-id RUN_ID]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.evaluation.rag_judge import judge_groundedness
from core.generation import GenerationService
from core.retrieval import QueryProcessor

GOLD_QUERIES_PATH = Path("tests/gold_queries.json")
OUTPUT_DIR = Path("output/eval")


def load_sample_queries(n: int) -> list[dict]:
    data = json.loads(GOLD_QUERIES_PATH.read_text(encoding="utf-8"))
    queries = data["queries"]
    return queries[:n]


def run(n: int, k: int, run_id: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{run_id}_eval.jsonl"

    processor = QueryProcessor()
    generator = GenerationService()

    sample = load_sample_queries(n)
    print(f"표본 {len(sample)}문항, k={k}, run_id={run_id}")

    scores = []
    with out_path.open("w", encoding="utf-8") as f:
        for i, item in enumerate(sample, 1):
            query_id = item["id"]
            question = item["query"]
            print(f"[{i}/{len(sample)}] {query_id}: {question!r} 처리 중...", flush=True)

            response = processor.process(question, query_id=query_id, k=k)
            gen_result = generator.generate(response)

            retrieved_chunks = [c.content for c in response.top_k_results]
            retrieved_chunk_ids = [c.tsu_id for c in response.top_k_results]

            score = judge_groundedness(
                run_id=run_id,
                query_id=query_id,
                question=question,
                retrieved_chunks=retrieved_chunks,
                retrieved_chunk_ids=retrieved_chunk_ids,
                answer=gen_result.answer,
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
    print(f"=== 완료: {len(scores)}문항, 평균 groundedness={avg:.2f}/5 ===")
    print(f"결과 저장: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="ADR-010 Phase 2 — RAG 평가 베이스라인")
    parser.add_argument("--n", type=int, default=5, help="평가할 질의 수 (기본 5, 작게 시작)")
    parser.add_argument("--k", type=int, default=5, help="질의당 검색 결과 수 (기본 5)")
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ"),
        help="run_id (기본: 타임스탬프)",
    )
    args = parser.parse_args()
    run(args.n, args.k, args.run_id)


if __name__ == "__main__":
    main()

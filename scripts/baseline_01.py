#!/usr/bin/env python3
"""NAE Performance Journey / BASELINE-01 — Retrieval-only + 3 full pipeline samples

Runs 10 Korean questions through retrieval, then full pipeline for Q1/Q5/Q9.
Captures intermediate results for quality assessment.
Does NOT modify any code, index, corpus, or config.
"""

import json
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.retrieval import QueryProcessor
from core.generation import GenerationService

ALL_QUESTIONS = [
    ("Q1", "출애굽기에서 안식일을 지키라는 명령의 의미는 무엇인가?"),
    ("Q2", "신명기에서 안식일은 출애굽기의 안식일과 어떻게 연결되는가?"),
    ("Q3", "복음서에서 예수님은 안식일에 대해 무엇을 가르치셨는가?"),
    ("Q4", "사도들은 안식일을 어떻게 이해하고 가르쳤는가?"),
    ("Q5", "하나님께서 창세기에서 일곱째 날을 복되게 하신 것과 신약의 안식 개념은 어떻게 연결되는가?"),
    ("Q6", "교회가 주일에 예배하는 것과 구약의 안식일은 어떤 관계가 있는가?"),
    ("Q7", "예수님께서 안식일의 주인이시라고 하신 말씀은 무슨 의미인가?"),
    ("Q8", "히브리서 4장의 안식은 구약의 안식일과 어떤 관계가 있는가?"),
    ("Q9", "목회자가 성도에게 안식에 대해 설교한다면 성경 전체의 흐름에서 어떤 점을 강조해야 하는가?"),
    ("Q10", "안식일을 지킨다는 말에서 '지킨다'는 것은 성경적으로 무엇을 의미하는가?"),
]

FULL_PIPELINE_QUESTIONS = [("Q1", ALL_QUESTIONS[0][1]), ("Q5", ALL_QUESTIONS[4][1]), ("Q9", ALL_QUESTIONS[8][1])]


def run_baseline():
    processor = QueryProcessor()
    generator = GenerationService()

    all_results = []

    # --- PHASE 1: Retrieval-only for all 10 questions ---
    print("="*70)
    print("PHASE 1: RETRIEVAL-ONLY (all 10 questions)")
    print("="*70)

    for qid, question in ALL_QUESTIONS:
        try:
            response = processor.process(question, query_id=f"baseline-{qid}", k=5)
        except Exception as e:
            print(f"\n{qid}: {question}")
            print(f"  [RETRIEVAL ERROR] {e}")
            all_results.append({"qid": qid, "question": question, "error": f"retrieval: {e}"})
            continue

        n_results = len(response.top_k_results) if response.top_k_results else 0
        pq = response.parsed_query if hasattr(response, "parsed_query") else None
        detected_books = pq.detected_books if pq else None
        scripture_refs = [r.to_string() for r in pq.scripture_refs] if pq and pq.scripture_refs else []
        translated_terms = pq.translated_terms if pq else []
        intent = pq.intent if pq else None

        candidates = []
        for i, cand in enumerate(response.top_k_results or []):
            preview = (getattr(cand, "content", "") or "")[:200].replace("\n", " ")
            src = getattr(cand, "source_file", "?")
            score = getattr(cand, "final_score", 0)
            candidates.append({"idx": i, "score": score, "source_file": src, "preview": preview})

        all_results.append({
            "qid": qid,
            "question": question,
            "n_results": n_results,
            "intent": intent,
            "detected_books": detected_books,
            "scripture_refs": scripture_refs,
            "translated_terms": translated_terms,
            "candidates": candidates,
        })

        print(f"\n{qid}: {question}")
        print(f"  [RETRIEVAL] n={n_results} intent={intent} books={detected_books} refs={scripture_refs}")
        print(f"  [RETRIEVAL] translated_terms={translated_terms}")
        for c in candidates:
            print(f"    [{c['idx']}] score={c['score']:.4f} src={c['source_file']}")
            print(f"        {c['preview'][:150]}...")

    # --- PHASE 2: Full pipeline for Q1, Q5, Q9 ---
    print("\n\n" + "="*70)
    print("PHASE 2: FULL PIPELINE (Q1, Q5, Q9)")
    print("="*70)

    for qid, question in FULL_PIPELINE_QUESTIONS:
        # Find the retrieval result
        ret_result = next((r for r in all_results if r["qid"] == qid), None)
        if not ret_result:
            continue

        response = processor.process(question, query_id=f"baseline-full-{qid}", k=5)

        try:
            stream = generator.generate_stream(response, conversation_history="")
            answer_chunks = []
            for chunk in stream:
                answer_chunks.append(chunk)
            result = stream.to_result()
            answer = result.answer
            gen_error = result.error
        except Exception as e:
            print(f"\n{qid}: [GENERATION ERROR] {e}")
            answer = f"[생성 실패] {e}"
            gen_error = str(e)

        ret_result["answer"] = answer
        ret_result["answer_preview"] = answer[:500].replace("\n", " ")
        ret_result["gen_error"] = gen_error
        ret_result["citations"] = getattr(response, "citations", None)

        print(f"\n{qid}: {question}")
        print(f"  [ANSWER] (len={len(answer)})")
        print(f"    {answer[:300].replace(chr(10), ' ')}...")
        if gen_error:
            print(f"  [ERROR] {gen_error}")

    # --- OUTPUT SUMMARY ---
    print("\n\n" + "="*70)
    print("BASELINE-01 RESULTS (JSON)")
    print("="*70)
    output = []
    for r in all_results:
        out = {
            "qid": r["qid"],
            "question": r["question"],
            "n_results": r.get("n_results", 0),
            "intent": r.get("intent"),
            "detected_books": r.get("detected_books"),
            "scripture_refs": r.get("scripture_refs"),
            "translated_terms": r.get("translated_terms"),
        }
        if "answer" in r:
            out["answer_preview"] = r["answer_preview"]
            out["gen_error"] = r.get("gen_error")
        output.append(out)

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return all_results


if __name__ == "__main__":
    run_baseline()

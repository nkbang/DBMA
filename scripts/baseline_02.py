#!/usr/bin/env python3
"""NAE Performance Journey / BASELINE-02 — Query-by-Query Trace

READ-ONLY investigation. No code/data/config changes.
Traces each question through the full pipeline step by step.
"""

import json
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.retrieval import QueryProcessor, QueryParser, BOOK_ID_TO_NAMES, NAME_TO_BOOK_ID
from core.query_translation import translate_query_terms, scripture_ref_phrases, KO_EN_THEOLOGY_TERMS

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


def trace_question(qid, question):
    parser = QueryParser()
    processor = QueryProcessor()
    result = {"qid": qid, "question": question}

    # STEP 1: RAW QUERY
    result["raw_query"] = question

    # STEP 2: Parsed query
    parsed = parser.parse(question)
    result["parsed_intent"] = parsed.intent
    result["detected_books"] = parsed.detected_books
    result["scripture_refs"] = [r.to_string() for r in parsed.scripture_refs]
    result["translated_terms"] = parsed.translated_terms
    result["themes"] = parsed.themes
    result["keywords"] = parsed.keywords

    # STEP 3: Standalone book detection detail
    standalone_books = parser._detect_books_standalone(question)
    result["standalone_books_detail"] = standalone_books

    # STEP 4: Scripture ref parsing detail
    scripture_refs_raw = parser._extract_scripture_refs(question)
    result["scripture_refs_raw"] = [r.to_string() for r in scripture_refs_raw]

    # STEP 5: Individual book name tests
    book_tests = {}
    test_inputs = {
        "출애굽기": "EXO",
        "신명기": "DEU",
        "창세기": "GEN",
        "히브리서": "HEB",
        "복음서": None,
        "사도": None,
        "예수": None,
        "안식일": None,
    }
    for test_name, expected in test_inputs.items():
        resolved = parser._resolve_book_name(test_name)
        found_in_cache = any(test_name.lower() == n for n, _ in parser._alias_cache) if hasattr(parser, '_alias_cache') else False
        book_tests[test_name] = {
            "resolved_to": resolved,
            "expected": expected,
            "found_in_alias_cache": found_in_cache,
        }
    result["book_name_tests"] = book_tests

    # STEP 6: Retrieval results
    try:
        response = processor.process(question, query_id=f"baseline02-{qid}", k=5)
        n_results = len(response.top_k_results) if response.top_k_results else 0
        result["n_retrieved"] = n_results

        candidates = []
        for i, cand in enumerate(response.top_k_results or []):
            preview = (getattr(cand, "content", "") or "")[:300].replace("\n", " ")
            candidates.append({
                "rank": i + 1,
                "score": getattr(cand, "final_score", 0),
                "source_file": getattr(cand, "source_file", "?"),
                "title": getattr(cand, "title", "?"),
                "tsu_id": getattr(cand, "tsu_id", ""),
                "book_id": getattr(cand, "book_id", None),
                "chapter": getattr(cand, "chapter", None),
                "content_preview": preview,
            })
        result["top_5_candidates"] = candidates

        bible_in_corpus = []
        for cand in response.top_k_results or []:
            bid = getattr(cand, "book_id", None)
            if bid and bid in ["EXO", "DEU", "GEN", "HEB", "MAT", "MRK", "LUK", "JHN"]:
                bible_in_corpus.append({"book_id": bid, "chapter": getattr(cand, "chapter", None)})
        result["bible_books_in_results"] = bible_in_corpus

    except Exception as e:
        result["retrieval_error"] = str(e)

    return result


def main():
    print("=" * 70)
    print("BASELINE-02 — QUERY-BY-QUERY TRACE")
    print("=" * 70)

    all_traces = []
    for qid, question in ALL_QUESTIONS:
        print(f"\n{'='*70}")
        print(f"{qid}: {question}")
        print(f"{'='*70}")
        trace = trace_question(qid, question)
        all_traces.append(trace)

        print(f"  intent={trace['parsed_intent']}")
        print(f"  detected_books={trace['detected_books']}")
        print(f"  scripture_refs={trace['scripture_refs']}")
        print(f"  translated_terms={trace['translated_terms']}")
        print(f"  standalone_books={trace['standalone_books_detail']}")
        print(f"  scripture_refs_raw={trace['scripture_refs_raw']}")
        print(f"  themes={trace['themes']}")
        print(f"  keywords={trace['keywords']}")
        print(f"  n_retrieved={trace.get('n_retrieved', 'ERROR')}")
        if trace.get('top_5_candidates'):
            for c in trace['top_5_candidates']:
                print(f"    [{c['rank']}] score={c['score']:.4f} src={c['source_file']} book={c['book_id']}")
                print(f"        {c['content_preview'][:120]}...")

    # Bible corpus check
    print("\n\n" + "=" * 70)
    print("BIBLE CORPUS CHECK — EXO 20:8-11 in corpus?")
    print("=" * 70)
    processor = QueryProcessor()
    bible_check = processor.process("Exodus 20:8-11", query_id="bible-check", k=5)
    for i, cand in enumerate(bible_check.top_k_results or []):
        bid = getattr(cand, "book_id", None)
        ch = getattr(cand, "chapter", None)
        print(f"  [{i+1}] book={bid} chapter={ch} score={getattr(cand, 'final_score', 0):.4f}")

    # Output JSON
    print("\n\n" + "=" * 70)
    print("BASELINE-02 RESULTS (JSON)")
    print("=" * 70)
    print(json.dumps(all_traces, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

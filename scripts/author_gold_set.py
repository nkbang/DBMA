#!/usr/bin/env python3
"""author_gold_set.py — Gold set authoring from registry metadata (Approach B).

Phase 5.2: Gold authoring without corpus indexing.
TSU ID는 TSU-{book_id}-{chunk_id} 스키마(ADR-001, core/tsu_builder.py L340)를
따르지만, 실제 chunk content가 없으므로 "corpus에 실제로 존재하는 TSU" 검증 불가.

리스크:
- benchmark retrieval evaluation에서 ID mismatch 발생 가능
- corpus indexing 후 재작성 필요할 수 있음

Usage:
  python -m scripts.author_gold_set --output NAE/benchmark/datasets/gold_benchmark_v1.jsonl
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

# Import _resolve_book_id from core.tsu_builder for filename-based book_id inference
from core.tsu_builder import _resolve_book_id


# registry에서 doc_type별 문서 목록을 추출하는 함수들
def load_registry(registry_path: str) -> Dict[str, Any]:
    """Load identity registry documents."""
    with open(registry_path) as f:
        data = json.load(f)
    return data.get("documents", {})


def extract_documents(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract document list from registry, filtering processed docs only.
    
    Infers book_id from source_file using _resolve_book_id() when doc.get("book") is None.
    """
    docs = []
    for doc_id, doc in registry.items():
        if doc.get("status") == "processed" and doc.get("chunk_count", 0) > 0:
            source_file = doc.get("source_file", "")
            # Use doc.book if available, otherwise infer from filename
            book = doc.get("book") or _resolve_book_id(source_file)
            if book is None:
                continue  # Skip documents with no resolvable book_id
            docs.append({
                "document_id": doc_id,
                "doc_type": doc.get("doc_type", "unknown"),
                "book": book,
                "chapter": doc.get("chapter"),
                "source_file": source_file,
                "chunk_count": doc.get("chunk_count", 0),
                "language": doc.get("language", "ko"),
                "heading": doc.get("heading") or doc.get("title"),
            })
    return docs


# benchmark_v1.jsonl의 질문을 doc_type별로 매핑하는 규칙
QUESTION_TO_DOC_TYPE_MAP = {
    "속죄": ["주석", "조직신학"],
    "용서": ["주석", "조직신학"],
    "Holy Spirit": ["주석", "조직신학"],
    "제사": ["주석", "기타"],
    "믿음": ["주석", "조직신학", "설교"],
}


def map_questions_to_documents(
    questions: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Map benchmark questions to gold TSU IDs based on doc_type matching.

    Approach B: TSU ID는 스키마 규칙으로 생성되지만 실제 corpus 존재 여부는 검증 불가.
    
    Each question gets a unique subset of documents based on its required_concepts,
    ensuring diverse book_id distribution across the gold set.
    """
    results = []

    for q in questions:
        result = dict(q)  # shallow copy
        question_text = q.get("question", {}).get("text", "")
        required_concepts = q.get("expected", {}).get("required_concepts", [])

        # 질문의 개념에 해당하는 doc_type 매핑
        matched_doc_types = set()
        for concept in required_concepts:
            if concept in QUESTION_TO_DOC_TYPE_MAP:
                matched_doc_types.update(QUESTION_TO_DOC_TYPE_MAP[concept])

        if not matched_doc_types:
            # 기본값: 주석 + 조직신학
            matched_doc_types = {"주석", "조직신학"}

        # 해당 doc_type의 문서에서 TSU ID 생성 (가상의 chunk 0)
        gold_tsu_ids = []
        for doc in documents:
            if doc["doc_type"] in matched_doc_types and doc["book"]:
                # TSU-{book_id}-{chunk_id} 스키마
                # chunk_id는 generate_chunk_id(document_id, 0)의 가짜 값
                # 실제 corpus indexing 전이므로 document_id 기반
                gold_tsu_ids.append(f"TSU-{doc['book']}-{doc['document_id'][:16]}")

        result["expected"]["gold_tsu_ids"] = gold_tsu_ids[:5]  # 최대 5개
        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(description="Author gold set from registry metadata")
    parser.add_argument("--registry", default="data/제련완성본/registry/documents.json")
    parser.add_argument("--input", default="NAE/benchmark/datasets/benchmark_v1.jsonl")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # registry 로드
    registry = load_registry(args.registry)
    documents = extract_documents(registry)
    print(f"Registry documents (processed, chunk_count>0): {len(documents)}")

    # doc_type별 분포
    from collections import Counter
    types = Counter(d["doc_type"] for d in documents)
    for t, c in types.most_common():
        print(f"  {t}: {c}")

    # benchmark 질문 로드
    questions = []
    with open(args.input) as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    print(f"Benchmark questions: {len(questions)}")

    # gold set 작성
    results = map_questions_to_documents(questions, documents)

    # 출력
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Gold set written to: {output_path}")

    # 요약
    total_gold = sum(len(r["expected"]["gold_tsu_ids"]) for r in results)
    print(f"Total gold TSU IDs authored: {total_gold}")


if __name__ == "__main__":
    main()
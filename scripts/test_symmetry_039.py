#!/usr/bin/env python3
"""C1 Task Order 039 v5 — §1-B Chat vs Research 대칭성 실측"""
import sys
sys.path.insert(0, '/Users/David/DBMA')

# TSU 데이터셋 상태 확인
import os
tsu_path = 'output/bench/tsu_dataset.jsonl'
print(f"TSU 파일 경로: {tsu_path}")
print(f"TSU 파일 존재: {os.path.exists(tsu_path)}")
print(f"TSU 파일 크기: {os.path.getsize(tsu_path)} 바이트")

# 레지스트리 상태 확인
reg_path = 'data/제련완성본/registry/documents.json'
print(f"\n레지스트리 경로: {reg_path}")
print(f"레지스트리 파일 존재: {os.path.exists(reg_path)}")
print(f"레지스트리 파일 크기: {os.path.getsize(reg_path)} 바이트")

# 실제 QueryProcessor로 대칭성 테스트
from core.config import DEFAULT_TSU_DATASET_PATH, DEFAULT_REGISTRY_PATH
print(f"\n=== config.py 상수 ===")
print(f"DEFAULT_TSU_DATASET_PATH: {DEFAULT_TSU_DATASET_PATH}")
print(f"DEFAULT_REGISTRY_PATH: {DEFAULT_REGISTRY_PATH}")

# QueryProcessor import 및 인스턴스화
from ui.state.query_processor import get_shared_query_processor
processor = get_shared_query_processor()

print(f"\n=== QueryProcessor 상태 ===")
print(f"엔진 TSU 경로: {processor.engine.tsu_dataset_path}")
tsu_loaded = getattr(processor.engine, 'tsu_dataset', None) is not None
print(f"엔진 TSU 로드됨: {tsu_loaded}")
if tsu_loaded and processor.engine.tsu_dataset:
    print(f"TSU 레코드 수: {len(processor.engine.tsu_dataset)}")
else:
    print("TSU 데이터셋이 로드되지 않음 (0바이트 파일)")

# Chat vs Research 대칭성 실측
query = "로마서 8장 성령"
print(f"\n=== 대칭성 실측: '{query}' ===")

result_research = processor.process(query, query_id="test-research", k=10)
result_chat = processor.process(query, query_id="test-chat", k=5, file_scope=None)

research_count = len(result_research.top_k_results) if hasattr(result_research, 'top_k_results') else 0
chat_count = len(result_chat.top_k_results) if hasattr(result_chat, 'top_k_results') else 0

print(f"Research top_k_results: {research_count} 건")
print(f"Chat top_k_results: {chat_count} 건")
symmetry = "일치 ✅" if research_count == chat_count else "불일치 ❌"
print(f"대칭성: {symmetry}")

if research_count == 0 and chat_count == 0:
    print("\n결론: 둘 다 0건 → TSU 데이터셋 공백이 원인")
elif research_count > 0 and chat_count == 0:
    print("\n결론: Research는 결과 있음, Chat만 0건 → 경로 차이 존재")
elif research_count == 0 and chat_count > 0:
    print("\n결론: Chat은 결과 있음, Research만 0건 → 경로 차이 존재")
else:
    print(f"\n결론: 둘 다 결과 있음 (Research={research_count}, Chat={chat_count})")

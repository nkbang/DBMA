# Environment Check Report

작성일: 2026-07-31
실행: `bash scripts/check_environment.sh`

## 결과 요약

PASS=20, WARNING=0, FAIL=0

## 상세

```
[PASS] Python venv 존재 (/Users/David/envs/dbma311, Python 3.11.15)
[PASS] 패키지 설치됨: sentence_transformers
[PASS] 패키지 설치됨: chromadb
[PASS] 패키지 설치됨: qdrant_client
[PASS] 패키지 설치됨: ollama
[PASS] 패키지 설치됨: pydantic
[PASS] 패키지 설치됨: fastapi
[PASS] 패키지 설치됨: streamlit
[PASS] 패키지 설치됨: pytest
[PASS] Ollama CLI 설치됨 (ollama version is 0.32.4)
[PASS] 기본 임베딩 모델(bge-m3) 존재
[PASS] chroma_db 디렉토리 존재
[PASS] git 저장소 확인 (branch=dev/dbma-engine, 변경파일=22)
[PASS] 디렉토리 존재: core
[PASS] 디렉토리 존재: ui
[PASS] 디렉토리 존재: data
[PASS] 디렉토리 존재: output
[PASS] 디렉토리 존재: cache
[PASS] 디렉토리 존재: workspace
[PASS] 디렉토리 존재: docs/tasks
```

## 판정

전체 PASS. 이슈 없음.

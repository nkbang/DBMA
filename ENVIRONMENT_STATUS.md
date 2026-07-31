# DBMA Environment Status

생성일: 2026-07-31

## Python

- 시스템 python3: 3.14.5 (`/usr/local/bin/python3`)
- 공식 프로젝트 venv: `~/envs/dbma311` (Python 3.11) — [[project_dbma_runtime_env]] 메모리 기준 공식 환경

## 주요 패키지 (`~/envs/dbma311`)

| 패키지 | 버전 | 상태 |
|---|---|---|
| sentence-transformers | 5.5.1 | OK |
| chromadb | 1.5.9 | OK |
| qdrant-client | installed (버전 미노출) | OK |
| ollama | installed (버전 미노출) | OK |
| pydantic | 2.13.4 | OK |
| fastapi | 0.136.3 | OK |
| streamlit | 1.58.0 | OK |
| pytest | 9.1.1 | OK |

Missing dependency: 없음 (8개 전부 설치 확인됨)

## Ollama

- 버전: 0.32.4
- 로컬 모델: llama3.1:8b, bge-m3:latest, qwen3.6:35b-DBMAcode, qwen3.6:35b,
  my-theology-bot-v2:latest, dbma-planner-r1-q6:70b, mxbai-embed-large:latest,
  nomic-embed-text:latest
- 기본 임베딩 모델(`bge-m3:latest`) 설치 확인됨.

## Git

- 브랜치: `dev/dbma-engine`
- 커밋되지 않은 변경 다수 존재 (C1 Detail Panel 관련 작업, [[project_c1_detail_panel_uncommitted_followup]] 참고) — 이번 작업에서 건드리지 않음.

## 권장 조치

- 없음. 환경은 정상 동작 상태.

---
title: DBMA Retrieval Migration Matrix v1
category: architecture
sprint: SPRINT16-B-4
based_on:
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md (SPRINT16-B-3)
  - docs/architecture/DBMA-Legacy-EntryPoint-Analysis.md (SPRINT16-B-2)
  - docs/architecture/DBMA-Module-Responsibility-v2.md (SPRINT16-B-1)
status: current
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정)
---

# DBMA Retrieval Migration Matrix v1

ADR-001에서 확정된 결정(`core/retrieval.py::RetrievalEngine`을 유일한 Retrieval
Authority로 지정)을 실행 가능한 마이그레이션 계획으로 분해한다.
이 문서는 계획 문서이며, 어떤 코드도 이 스프린트에서 변경하지 않는다.

---

## 1. dbma.py RAG Function Inventory

`dbma.py` 전체 함수 중 RAG(임베딩/청킹/벡터DB/검색/생성) 책임을 가진 함수만 추출했다.
(문서 저장, 로그, 프로그레스 표시 등 비-RAG 함수는 이번 매트릭스 범위에서 제외한다.)

| # | 함수 | 위치 | 책임 |
|---|---|---|---|
| 1 | `embed_text_ollama()` | dbma.py:161 | Ollama로 텍스트 임베딩 생성 |
| 2 | `get_vector_client()` | dbma.py:331 | Chroma 벡터 클라이언트 획득 |
| 3 | `get_collection()` | dbma.py:338 | Chroma 컬렉션 핸들 획득 |
| 4 | `rag_chunk_text()` | dbma.py:352 | RAG용 자체 텍스트 청킹 |
| 5 | `read_indexable_docs()` | dbma.py:360 | 색인 대상 md 문서 로딩 |
| 6 | `list_ollama_models()` | dbma.py:394 | 사용 가능 Ollama 생성 모델 목록 조회 |
| 7 | `list_ollama_embedding_models()` | dbma.py:408 | 사용 가능 Ollama 임베딩 모델 목록 조회 |
| 8 | `_model_supports_embeddings()` | dbma.py:444 | 모델의 임베딩 지원 여부 검증 |
| 9 | `_qdrant_available()` | dbma.py:457 | Qdrant 가용성 런타임 체크 |
| 10 | `_embed_text_qdrant()` | dbma.py:470 | Qdrant 경로용 임베딩 헬퍼 |
| 11 | `upsert_to_qdrant()` | dbma.py:482 | 청크+메타데이터를 Qdrant에 upsert |
| 12 | `query_qdrant()` | dbma.py:507 | Qdrant 질의 실행 |
| 13 | `_embed_texts()` | dbma.py:534 | 텍스트 배치 임베딩 (Chroma/Qdrant 공용) |
| 14 | `_rag_noise()` | dbma.py:572 | RAG 색인 전 노이즈 점수 계산 |
| 15 | `build_rag_store()` | dbma.py:580 | 전체 색인 파이프라인 오케스트레이션 (청킹→필터→임베딩→저장, Chroma/Qdrant `store` 파라미터로 선택) |
| 16 | `query_rag()` | dbma.py:651 | 검색 + 생성까지 포함한 end-to-end RAG 질의 |
| 17 | `append_benchmark_row()` | dbma.py:736 | RAG 벤치마크 결과 기록 |
| 18 | `render_noise_bar()` | dbma.py:753 | 노이즈 점수 UI 표시 |
| 19 | `init_chat_state()` | dbma.py:767 | 채팅 세션 상태 초기화 |
| 20 | `chat_user_bubble()` / `chat_assistant_bubble()` | dbma.py:773, 777 | 채팅 UI 렌더링 |
| 21 | `pick_docs_for_embedding()` | dbma.py:782 | 색인 대상 문서 선택 UI |
| 22 | `render_trendy_chat_tab()` | dbma.py:801 | 위 함수들을 조립하는 채팅 탭 진입점 (UI) |

**교차 검증** (SPRINT16-B-2): 이 22개 함수는 모두 `dbma.py` 내부에서만 정의·호출되며
외부(core/, ui/, scripts/, tests/)에서 참조되지 않는다. 유일한 예외는
`scripts/backup_chroma.py`가 시도하는 `from dbma import CHROMA_DIR`이나, 이는
함수가 아닌 상수 참조이며 try/except 폴백이 있다.

---

## 2. Target Module Mapping

| dbma.py 함수 | 대상 모듈 | 대상 책임/인터페이스 | 매핑 근거 |
|---|---|---|---|
| `embed_text_ollama()` | `core/embedder.py` | `embed()` | 임베딩 생성 책임은 이미 `core/embedder.py`가 소유 (ADR-001 §Migration Impact) |
| `get_vector_client()`, `get_collection()` | — (제거 대상, 대체 없음) | N/A | Chroma 경로 자체가 레거시 — Qdrant 단일화 후 소멸 |
| `rag_chunk_text()` | `core/chunking_optimizer.py` | `optimize_chunks()` | 청킹 책임은 이미 core에 존재, 자체 청커 불필요 |
| `read_indexable_docs()` | `core/files.py` | `scan_md_files()` / `load_chunks_info()` | md 스캔 책임은 이미 core에 존재 |
| `list_ollama_models()`, `list_ollama_embedding_models()`, `_model_supports_embeddings()` | 신규 Generation 계층 (미정) | N/A | Ollama 모델 목록/검증은 검색이 아닌 생성(Generation) 관심사 — `RetrievalEngine` 범위 밖 |
| `_qdrant_available()` | `core/runtime_state.py` | `get_pipeline_status()` (search 단계 판정 로직 재사용) | 가용성 판정은 이미 core가 담당 (ADR-001 §SPRINT16-C Implications 3) |
| `_embed_text_qdrant()`, `_embed_texts()` | `core/embedder.py` | `embed()` | 중복 임베딩 헬퍼 통합 |
| `upsert_to_qdrant()` | `core/ingest.py` | `insert()` | Qdrant 쓰기 경로는 이미 core에 존재 |
| `query_qdrant()` | `core/retrieval.py` | `RetrievalEngine` (질의 실행부) | ADR-001 결정에 따른 직접 대체 |
| `_rag_noise()` | `core/utils.py` | `calculate_noise_score()` | 노이즈 점수 계산 책임은 이미 core에 존재 (단, 스코어링 공식이 동일한지 검증 필요) |
| `build_rag_store()` | `core/ingest.py` + `core/embedder.py` + `core/chunking_optimizer.py` 조합 | 신규 오케스트레이션 함수 (미존재, 설계 필요) | 여러 core 모듈을 엮는 오케스트레이터가 현재 core에 없음 — `core/processing.py`의 처리 오케스트레이션과 유사한 위상의 "색인 오케스트레이터" 신설 검토 |
| `query_rag()` | `core/retrieval.py::RetrievalEngine`/`QueryProcessor` + 신규 Generation 계층 | 검색 부분은 `QueryProcessor`, 생성 부분은 미정 | ADR-001이 이미 "생성 책임은 RetrievalEngine 범위 밖, 별도 설계 필요"라고 명시 |
| `append_benchmark_row()` | `scripts/benchmark_pipeline.py` 또는 `scripts/rag_benchmark.py` 경로 | 기존 벤치마크 스크립트 산출물 포맷과 통합 | 벤치마크 기록은 이미 scripts/에 유사 책임 존재 — 중복 여부 확인 필요 |
| `render_noise_bar()`, `init_chat_state()`, `chat_user_bubble()`, `chat_assistant_bubble()`, `pick_docs_for_embedding()`, `render_trendy_chat_tab()` | `ui/pages/research.py` + `ui/components/*` | 채팅 UI는 `ui/pages/research.py`의 검색 UI 패턴 재사용, 컴포넌트는 `ui/components/status.py`(진행률 표시), `ui/components/dialogs.py` 등과 통합 검토 | UI 레이어는 이미 `ui/`에 표준 패턴 존재 |

**미해결 매핑**: `build_rag_store()`(색인 오케스트레이터)와 `query_rag()`의 생성 부분은
**대상 모듈이 아직 core/에 존재하지 않는다.** 이 둘은 단순 "함수 이동"이 아니라
신규 설계가 필요한 항목이다.

---

## 3. Migration Action

| 함수 | Action | 우선순위 |
|---|---|---|
| `embed_text_ollama()` | migrate → `core/embedder.py` (Ollama 백엔드 옵션으로 통합 여부 사람 확인 필요) | Medium |
| `get_vector_client()` / `get_collection()` | remove (Chroma 경로 소멸에 종속) | Low (Chroma 단일화 결정 이후) |
| `rag_chunk_text()` | remove, `core/chunking_optimizer.optimize_chunks()`로 대체 | Medium |
| `read_indexable_docs()` | remove, `core/files.py` 함수로 대체 | Medium |
| `list_ollama_models()` / `list_ollama_embedding_models()` / `_model_supports_embeddings()` | defer — Generation 계층 설계 이후 결정 | Low |
| `_qdrant_available()` | remove, `core/runtime_state.get_pipeline_status()`로 대체 | High (ADR-001에서 이미 결정됨) |
| `_embed_text_qdrant()` / `_embed_texts()` | remove (중복 제거), `core/embedder.embed()`로 통일 | Medium |
| `upsert_to_qdrant()` | remove, `core/ingest.insert()`로 대체 | High |
| `query_qdrant()` | remove, `RetrievalEngine`으로 대체 | **Highest (ADR-001 핵심 결정)** |
| `_rag_noise()` | migrate — `core/utils.calculate_noise_score()`와 동일 공식인지 검증 후 통합 또는 제거 | Medium |
| `build_rag_store()` | redesign — 신규 색인 오케스트레이터 설계 필요, 단순 이동 불가 | High (설계 선행) |
| `query_rag()` | split — 검색 부분은 remove(`QueryProcessor`로 대체), 생성 부분은 redesign(신규 Generation 계층) | **Highest (ADR-001 핵심 결정)** |
| `append_benchmark_row()` | keep 또는 merge — `scripts/` 벤치마크 산출물과 포맷 통합 여부 확인 후 결정 | Low |
| UI 함수 6종 (§2 하단) | migrate → `ui/pages/research.py` 패턴으로 재구현 | Medium (retrieval/generation 마이그레이션 완료 후) |

우선순위 정의: **Highest** = ADR-001이 직접 지시, **High** = ADR-001 결정에 종속되나
설계/검증 선행 필요, **Medium** = 대상 모듈 존재, 이동만 하면 되나 검증 필요,
**Low** = 대상 모듈 부재 또는 결정 보류 상태.

---

## 4. Risk Assessment

| 항목 | 리스크 | 근거 / 완화 방향 |
|---|---|---|
| 외부 호출자 파손 | **낮음** | SPRINT16-B-2에서 22개 함수 전부가 self-contained임을 확인 — 이동/삭제해도 깨지는 외부 호출자 없음 |
| `dbma.py` 운영 지위 불확실성 | **높음** | "deprecated" 문서 선언과 2026-07-15까지의 실제 수정 이력이 모순 (ADR-001 §Migration Impact 마지막 행). 실제 활성 사용자가 있다면 마이그레이션 도중 UI가 갑자기 사라지는 체감 리스크 발생 — **사람 확인이 마이그레이션 착수의 선행조건** |
| `_rag_noise()` vs `calculate_noise_score()` 공식 불일치 | **중간** | 두 함수가 이름은 유사하나 실제 계산식이 동일한지 미검증. 다르면 마이그레이션 후 노이즈 필터링 결과가 달라져 색인 품질에 영향 |
| Ollama 임베딩/생성 지원 상실 | **중간~높음** | `core/embedder.py`가 Ollama를 지원하는지 미확인. 요구사항으로 남아있다면 제거 시 기능 손실 — SPRINT16-B-2/ADR-001에서 이미 "사람 확인 필요"로 표시된 항목 |
| Chroma 데이터 손실 | **중간** | `scripts/backup_chroma.py`가 가리키는 실제 Chroma 인스턴스/데이터가 존재한다면, Chroma 참조 제거 전 백업 여부 확인 필요 |
| `build_rag_store()` 재설계 범위 과소평가 | **높음** | 단순 함수 이동이 아니라 신규 오케스트레이터 설계가 필요 — 이를 "migrate"로 잘못 분류하면 일정 추정이 틀어짐 |
| Generation 계층 부재 | **높음** | `RetrievalEngine`에는 LLM 호출 책임이 없다. `query_rag()`의 생성 부분을 어디에 둘지 결정되지 않으면 이 마이그레이션이 기능 축소(검색은 되지만 답변 생성이 안 되는 상태)로 귀결될 수 있음 |
| 테스트 커버리지 공백 | **높음** | `dbma.py`의 22개 RAG 함수 중 어느 것도 `tests/`의 대상이 아님 (SPRINT16-B-2 확인). 마이그레이션 전후 동작 동등성을 검증할 기존 테스트가 없음 |

---

## 5. Validation Requirement

마이그레이션 착수 전/후 각각 필요한 검증:

**착수 전 (사람 확인, 코드 변경 없음)**
1. `dbma.py`가 현재 실제로 구동되고 있는지(활성 사용자 존재 여부) 확인.
2. Ollama 임베딩/생성 지원이 여전히 제품 요구사항인지 확인.
3. `scripts/backup_chroma.py`가 가리키는 Chroma 데이터가 실제로 존재/운영 중인지 확인.
4. `_rag_noise()`와 `core/utils.calculate_noise_score()`의 계산식 비교(수동 diff, 코드 미수정 상태에서 읽기만).

**마이그레이션 각 단계 이후 (구현 스프린트에서, 이번 스프린트 범위 아님)**
5. `query_qdrant()` → `RetrievalEngine` 대체 후, 동일 질의 세트(`tests/gold_queries.json`)로
   결과 비교 회귀 테스트 신설.
6. `upsert_to_qdrant()` → `core/ingest.insert()` 대체 후, 색인된 문서 수/벡터 차원 일치 검증.
7. `build_rag_store()` 재설계 결과물에 대한 신규 단위 테스트 작성 (현재 커버리지 0%이므로
   최소 skeleton 테스트부터 시작).
8. `query_rag()` 분리(검색+생성) 이후, 검색 부분은 기존 `RetrievalEngine` 테스트 스위트로,
   생성 부분은 신규 Generation 계층 설계 시 별도 테스트 계획 수립.
9. UI 마이그레이션(채팅 탭 6종) 완료 후 `ui/pages/research.py` 경로에서 수동 스모크 테스트
   (Streamlit 앱 기동 후 실제 질의 실행) 최소 1회 수행.

---

## 6. SPRINT16-C Dependency

SPRINT16-C(DocumentContext 설계) 착수 전 이 매트릭스가 요구하는 선행 조건:

1. **§5 "착수 전" 4개 항목의 사람 확인이 완료되어야 한다.** 특히 `dbma.py` 활성
   사용자 존재 여부는 DocumentContext가 레거시 경로를 병행 지원해야 하는지를
   결정하는 근거이므로, 미확인 상태로 SPRINT16-C를 시작하면 설계 재작업 위험이 있다
   (ADR-001에서 이미 지적된 리스크의 구체화).
2. **`build_rag_store()`의 재설계(신규 색인 오케스트레이터)는 DocumentContext 설계와
   책임이 겹친다.** DocumentContext가 "문서 하나의 생애주기(추출→색인까지)"를
   표현하는 객체라면, 색인 오케스트레이터 설계를 SPRINT16-C 안으로 흡수할지
   별도 스프린트로 분리할지 SPRINT16-C 킥오프에서 먼저 결정해야 한다.
3. **Generation 계층 부재는 DocumentContext 범위에서 명시적으로 제외한다.**
   ADR-001과 동일하게, DocumentContext는 검색 결과까지를 다루고 응답 생성은
   별도 후속 항목으로 남긴다 — 그렇지 않으면 DocumentContext가 책임 과다로
   설계될 위험이 있다.
4. **테스트 커버리지 공백(§4)은 DocumentContext 설계의 완료 기준(Definition of Done)에
   "신규 단위 테스트 최소 1건"을 포함시키는 근거로 사용한다** — 기존 `dbma.py` RAG
   경로가 무테스트 상태로 방치된 전례를 반복하지 않기 위함.

---

*본 문서는 SPRINT16-B-4 범위(`docs/architecture/`)에서 계획 수립만 수행했으며,
`core/`, `ui/`, `scripts/`, `tests/`, `config.yaml`, `dbma.py`는 수정하지 않았다.*

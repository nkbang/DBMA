---
title: DBMA Module Responsibility Map v2
category: architecture
sprint: SPRINT16-B-1
based_on:
  - docs/architecture/DBMA-Architecture-Map-v2.md (SPRINT16-A-2)
  - repository inspection (core/, ui/, scripts/, tests/)
status: current
created: 2026-07-16
scope_modified: docs/architecture/ only (core/, ui/, scripts/, tests/, config.yaml 미수정)
---

# DBMA Module Responsibility Map v2

SPRINT16-A-2 Architecture Map이 데이터/제어 흐름을 정리했다면, 이 문서는
**모듈별 단일 책임 여부**와 **Core/UI 경계**, 그리고 SPRINT16-C(DocumentContext)
진입 전에 반드시 해소해야 할 architectural debt를 식별하는 데 초점을 맞춘다.

핵심 결론을 먼저 밝힌다: **DBMA에는 현재 RAG/임베딩 파이프라인이 하나가 아니라 셋이다.**
이는 One Pipeline·One Retrieval Engine·One Execution State 원칙 모두에 대한 위반이며,
SPRINT16-C의 DocumentContext/ExecutionContext 설계 전에 반드시 명시적으로 해결해야 한다.

---

## 1. Module Responsibility Summary

### core/ — 처리·식별·검색 책임 (22개 파일)

| 모듈 | 책임 | 상태 |
|---|---|---|
| `config.py` | `config.yaml` 단일 로드, 하위호환 기본값 제공 | 정상, 단일 진실 소스 |
| `extractors.py` | 문서 텍스트 추출 (`extract_text_from_file`) | 정상, 의존성 없음 |
| `text_normalizer.py` | 줄바꿈 정규화 (`reflow_wrapped_lines`) | 정상, 단일 책임 |
| `frontmatter_detector.py` | 기존 md frontmatter 분리 (`split_front_matter`) | 정상 |
| `document_identity.py` | 콘텐츠 기반 문서 ID/해시/메타데이터 생성 | 정상, `PROCESSING_VERSION` 소유 |
| `identity_registry.py` | 문서 레지스트리 영속화, 중복/변경 판정 | 정상 |
| `utils.py` | 파일명 정리, 노이즈 점수 계산 | 정상, 공용 유틸 |
| `chunking_optimizer.py` | 청킹 최적화 및 저장 | 정상, `utils.py`에만 의존 |
| `files.py` | 디렉터리/md 파일 스캔 | 정상 |
| `processing.py` | **파이프라인 오케스트레이터** (`process_one_file`) | 정상이나 최대 의존성 보유 — 허브 |
| `embedder.py` | 임베딩 생성 (`embed`), `EMBEDDING_DIMENSION` 사용 | Qdrant 경로 전용 |
| `qdrant_init.py` | Qdrant 컬렉션 초기화 (CLI/명시적 호출) | 정상, 지연 임포트로 안전 설계 |
| `ingest.py` | Qdrant 문서 upsert (`insert`) | 정상, 지연 임포트 |
| `search.py` | 경량 Qdrant 질의 (`search`, `search_pretty`) | **⚠ retrieval.py와 책임 중복** |
| `retrieval.py` | 풀스택 검색 엔진 (`RetrievalEngine`, BM25/TF-IDF, 신학 스코어링, 벤치마크 연동) | **⚠ search.py, dbma.py 자체 RAG와 3중 중복** |
| `query_enhancements.py` | `RetrievalEngine`/`QueryParser` 확장 (한국어/성경책 별칭) | 정상, retrieval.py 상속 |
| `md_manager.py` | md 저장 + Qdrant 재색인 (`reindex_md_to_qdrant`) | **⚠ ingest.py와 Qdrant 쓰기 경로 중복** |
| `feature_flags.py` | 정적 기능 on/off (`SPRINT2_FEATURES`) | 단순하지만 하드코딩된 전역 상태 |
| `runtime_state.py` | 로그/파일 기반 동적 파이프라인 상태 판독 | 정상, 읽기 전용 |
| `init.py` | (내용 미상 — 이름상 초기화 스크립트 추정) | 목적 불명확, 재검토 필요 |

### ui/ — 표시 및 사용자 상호작용 책임

| 모듈 | 책임 |
|---|---|
| `app.py` | 진입점, `ui/pages/*` 5개 페이지 조립 |
| `pages/dashboard.py` | `core.runtime_state.get_pipeline_status()` 소비 — 파이프라인 상태 시각화 |
| `pages/library.py` | `core.config.DEFAULT_RAW_DIR` 기반 문서 목록 표시 |
| `pages/processing.py` | `core.processing.process_one_file` 등 호출 — 처리 큐/이력 UI |
| `pages/research.py` | `core.retrieval.QueryProcessor`/`RetrievalEngine` 호출 — 검색 UI |
| `pages/monitor.py` | 시스템 건강/성능/리소스 표시 (core 의존 약함, 직접 `os`/`Path` 접근) |
| `state/store.py` | `StateStore` — Streamlit `session_state` 네임스페이스 중앙화 |
| `theme/*`, `components/*` | 순수 프레젠테이션 (색상, 카드, 지표, 테이블, 다이얼로그) — core 의존 없음 |

### 진입점 이중 구조

| 모듈 | 책임 | 평가 |
|---|---|---|
| `dbma.py` | Streamlit 앱 + **자체 RAG 파이프라인 전체 재구현** | **Legacy — 아래 4절 참조** |
| `ui/app.py` + `ui/pages/*` | 구조화된 Streamlit 앱, core 모듈을 통해서만 처리/검색 수행 | 현재 세대(target) 아키텍처 |

### scripts/ — 운영·검증 도구 (core 로직 재구현 없음, 호출자 역할만)
`benchmark_pipeline.py`, `rag_benchmark*.py`, `evaluation_fingerprint.py`,
`repair_tsu_*.py`, `backup_chroma.py`(이름은 chroma지만 실제로는 레거시),
`create_docs.py`/`update_docs.py`, `validate_pipeline.py`,
`validation/validate_metadata_*.py` — 모두 core 함수를 호출하는 소비자이며
자체 파이프라인 로직을 갖지 않음. 책임 경계는 명확함.

### tests/ — core 개별 모듈 및 RAG 확장 계층 회귀 검증
`test_processing_pipeline.py`, `test_chunking_optimizer.py`, `test_frontmatter_detector.py`,
`test_text_normalizer.py`, `test_utils_noise.py`, `test_book_alias_resolution.py`,
`test_query_enhancements_full_regression.py`, `gold_queries.json`.
**주의**: `dbma.py`의 자체 RAG 구현(`query_rag`, `build_rag_store` 등)에 대한 테스트는
tests/ 어디에도 없다 — 테스트되지 않는 레거시 경로가 프로덕션 진입점에 남아있는 상태.

---

## 2. Core/UI Boundary 명확성

**원칙적으로는 준수됨**: `ui/pages/*`는 core 함수를 호출만 하고 자체 처리/검색 로직을
갖지 않는다 (`processing.py`, `retrieval.py`, `runtime_state.py`, `config.py`를
import해서 쓸 뿐). `ui/components`, `ui/theme`은 core 의존이 전혀 없는 순수 표현 계층이다.

**위반 지점은 `dbma.py`**: 이 파일은 UI(Streamlit)와 core 로직 경계 없이 한 파일 안에
`build_rag_store()`, `query_rag()`, `upsert_to_qdrant()`, `embed_text_ollama()` 같은
파이프라인/검색 로직을 직접 구현하고 있다. `ui/app.py` 세대에서는 이런 로직이 전부
`core/`로 위임되어 있는 것과 대조적이다. `dbma.py`는 Core/UI 경계 원칙이 확립되기
이전 세대의 산물로 판단된다.

---

## 3. 실제 Dependency 흐름 반영 여부

SPRINT16-A-2에서 확인한 import 그래프와 일치하며 이번 조사로 다음이 추가 확인됐다:

```text
dbma.py
  → core.feature_flags.feature_enabled("embedding")  (조건부 게이트)
      → True인 경우:
          import chromadb          ← Qdrant 계열 core 모듈과 무관한 별도 벡터 DB 클라이언트
          import ollama            ← core.embedder와 무관한 별도 임베딩/생성 클라이언트
          from langchain_text_splitters import RecursiveCharacterTextSplitter
          core.embedder.embed  (별칭 embed_via_transformer, 실제 코드 내 사용 여부 재확인 필요)
          core.md_manager.save_md_with_change_detection
          core.ingest.insert   (별칭 ingest_to_qdrant)
          core.qdrant_init.init_collection
          core.search.search   (별칭 search_qdrant_index)
  → core.config (CHROMA_COLLECTION, CHROMA_PERSIST_DIR 등 — core/config.py에
                  Qdrant 설정과 나란히 Chroma 설정도 존재함을 시사)
  → core.files.scan_directory
  → core.processing.{build_converter, build_splitter, process_one_file}
  → core.utils.calculate_noise_score
```

`dbma.py`는 core의 Qdrant 유틸(`search.py`, `ingest.py`, `qdrant_init.py`)을 일부
재사용하면서도, 그 위에 **Chroma + Ollama 기반의 완전히 별도인 RAG 함수군**
(`query_qdrant`, `build_rag_store`, `query_rag`, `upsert_to_qdrant`, `embed_text_ollama`,
`rag_chunk_text`)을 자체 정의하고 있다. 즉 core의 검색 자산을 우회하거나 부분적으로만
재사용하는 세 번째 경로다.

---

## 4. Legacy 책임 식별 (Architecture Debt)

### 4-1. 세 갈래 RAG/임베딩 구현 (최우선 부채)

| 경로 | 위치 | 벡터 DB | 임베딩 | 특징 |
|---|---|---|---|---|
| ① 레거시 인라인 RAG | `dbma.py` (`query_rag`, `build_rag_store`, `upsert_to_qdrant`, `embed_text_ollama`) | Chroma **+** Qdrant 혼재 (`get_vector_client`, `get_collection`, `CHROMA_*` 설정과 `upsert_to_qdrant` 공존) | Ollama (`embed_text_ollama`) | 한 파일에 파이프라인+검색+생성 전부 구현 |
| ② 경량 검색 | `core/search.py` | Qdrant | `core/embedder.py` | 단순 질의 함수 2개 |
| ③ 풀스택 검색 엔진 | `core/retrieval.py` + `query_enhancements.py` | Qdrant | (자체 스코어링 중심, 임베딩은 외부 위임 추정) | 하이브리드 스코어링, 벤치마크 연동, `ui/pages/research.py`가 사용하는 현재 세대 엔진 |

세 경로 모두 `COLLECTION`/컬렉션 이름, Qdrant URL 같은 상수를 각자 파일에서
재정의하고 있어(`core/qdrant_init.py`, `core/ingest.py`에 각각 `DEFAULT_QDRANT_URL`,
`COLLECTION` 하드코딩) 설정 드리프트 위험이 있다.

### 4-2. Chroma 잔재
- `core/config.py`에 `CHROMA_COLLECTION`, `CHROMA_PERSIST_DIR`가 여전히 정의되어 있고
  `dbma.py`가 이를 가져다 쓴다.
- `core/runtime_state.py`는 `chroma_db` persist directory 존재 여부로 인덱싱 상태를 판정한다.
- `scripts/backup_chroma.py`도 이름 그대로 Chroma를 백업 대상으로 삼는다.
- 그러나 SPRINT16-A-2 조사에서 확인했듯 **현재 활성 벡터 백엔드는 Qdrant**
  (`core/qdrant_init.py`, `core/ingest.py`, `core/retrieval.py`, `core/md_manager.py`,
  `core/search.py` 전부 Qdrant). Chroma는 실질적으로 `dbma.py`의 레거시 경로에서만
  살아있는 것으로 보인다.
- **결론**: Chroma 관련 코드/설정이 완전히 죽은 코드(dead code)인지, 아니면 `dbma.py`가
  실제로 아직 실행되는 진입점이라 Chroma가 병행 운영 중인지 확인이 필요하다.
  이 판단 없이는 SPRINT16-C에서 "Unified Pipeline"을 설계할 수 없다.

### 4-3. `core/init.py`
파일명이 `__init__.py`와 혼동되기 쉬운 `init.py`가 별도로 존재한다. 이번 조사에서
역할을 특정하지 못했다 — 별도 확인 필요 (금지 규칙상 `core/`를 수정할 수 없으므로
본 문서에서는 존재만 기록).

### 4-4. `move_source_file()` 미상 함수
SPRINT16-A-2에서 이미 지적된 사항 — 구 문서가 언급한 함수가 코드에 없음. 재확인 필요.

### 4-5. `feature_flags.py`의 전역 하드코딩
`SPRINT2_FEATURES = True`가 모듈 상단에 고정되어 있어 사실상 플래그가 아니라
상수다. `dbma.py`의 Chroma/Ollama 레거시 경로 전체가 이 단일 불리언 뒤에서
활성화된다 — 즉 레거시 RAG 경로를 끄고 켜는 유일한 스위치가 이 하드코딩값이다.

---

## 5. One Pipeline 원칙 충족 여부 — **미충족**

`core/processing.py`의 `process_one_file()`이 문서 처리(추출→정제→청킹→식별→저장)의
단일 오케스트레이터인 것은 맞다. 그러나 `dbma.py`가 `build_rag_store()` 내부에서
`read_indexable_docs()` → 자체 청킹(`rag_chunk_text`) → 자체 노이즈 필터(`_rag_noise`) →
자체 임베딩(`_embed_texts`) 흐름을 또 만들어 **문서 처리 이후 단계(임베딩/색인)에
대해 두 번째 파이프라인**을 운영하고 있다. `core/processing.py`가 다루는 범위(추출~저장)
밖이라 직접 충돌은 아니지만, "하나의 파이프라인"이라는 목표 관점에서는 이미 두 갈래다.

---

## 6. One Config 원칙 충족 여부 — **부분 충족**

`config.yaml` → `core/config.py`라는 단일 소스 자체는 유지되고 있다 (`config/` 디렉터리
없음, 재확인됨). 그러나 `core/config.py` 내부에 **Qdrant 세대 설정과 Chroma 세대 설정이
공존**하는 것으로 보이며(`CHROMA_COLLECTION`, `CHROMA_PERSIST_DIR` 등이 `dbma.py`에서
import됨), 이는 설정 소스가 하나여도 그 안에 두 세대의 개념이 뒤섞여 있다는 뜻이다.
완전한 One Config로 보려면 Chroma 관련 키가 실제로 쓰이는지부터 판정해야 한다.

---

## 7. One Retrieval Engine 방향성 — **정면 충돌, 최고 우선순위 부채**

현재 `RetrievalEngine`(`core/retrieval.py`)이 가장 정교하고(`ui/pages/research.py`가
사용하는 현재 세대) `core/search.py`가 그 경량 버전이라면, 이 둘의 통합만 해도
작은 작업이다. 하지만 `dbma.py`의 `query_rag()`/`query_qdrant()`는:
- 자체 하이브리드 검색 없음 (신학 스코어링, BM25/TF-IDF, 성경 인용 정합성 없음)
- Chroma/Qdrant 혼재 클라이언트 사용
- Ollama 생성 모델과 직접 결합 (`gen_model`, `query_rag`가 응답까지 생성)

세 번째 경로는 단순 "중복 구현"이 아니라 **응답 생성(LLM 호출)까지 포함한 별도의
end-to-end RAG 스택**이다. `RetrievalEngine`은 검색·응답 조립까지만 하고 생성은
별도 계층(`ResponseFormatter`)에 위임하는 구조로 보이는데, `dbma.py`는 생성까지
자체 함수(`query_rag`) 안에 뭉쳐놓았다. **One Retrieval Engine으로 수렴하려면
`dbma.py`가 여전히 사용 중인 진입점인지 먼저 확정하고, 사용 중이라면 이 파일의
RAG 함수군 전체를 폐기하고 `core/retrieval.py` 경로로 교체하는 마이그레이션이
SPRINT16-C 이전에 별도 스프린트로 필요하다.**

## Architectural Decision

Retrieval Engine Authority:

Current:
Multiple implementations exist.

Target:
core/retrieval.py::RetrievalEngine

Migration:
dbma.py inline RAG functions
and core/search.py
will be deprecated or absorbed.

---

## 8. One Execution State 방향성 — **개념적으로는 분리, 통합 지점 없음**

SPRINT16-A-2에서 정리한 대로 `feature_flags.py`(정적)와 `runtime_state.py`(동적)는
서로 독립이다. 이번 조사로 세 번째 상태원이 추가로 확인된다:

- `dbma.py`의 `get_vector_client()`, `get_collection()`, `_qdrant_available()`는
  런타임에 벡터 DB 연결 가능 여부를 그때그때 직접 확인한다 — `runtime_state.py`가
  이미 담당하는 "인덱싱 상태 판정" 책임과 겹치는 영역을 별도로 재구현한 것이다.

현재 실행 상태를 묻는 질문("지금 임베딩이 되어 있는가?")에 대한 답이
`runtime_state.get_pipeline_status()`, `dbma.py`의 `_qdrant_available()`,
`feature_flags.feature_enabled("embedding")` 세 곳에서 각각 다르게 계산될 수 있다.
ExecutionContext 설계 시 이 세 판정 로직을 하나의 상태 조회 인터페이스로 흡수해야 한다.

---

## 9. SPRINT16-C DocumentContext Requirements

DocumentContext(및 뒤따르는 ExecutionContext) 설계 착수 전에 다음이 선행되어야 한다.

1. **정본 판정**: `dbma.py`가 현재도 실행되는 진입점인지, 아니면 `ui/app.py`로 완전히
   대체되어 죽은 파일인지 확정한다. 이 답이 나오지 않으면 DocumentContext가 흡수해야
   할 상태 원천의 개수(2개 vs 3개)조차 정할 수 없다.
2. **문서 식별자 단일화**: DocumentContext는 `core/document_identity.py`의
   `generate_document_id`/`compute_content_hash`/`generate_chunk_id`를 유일한 ID 발급원으로
   삼아야 한다 — `dbma.py`의 `_save_md_with_metadata`/`_parse_frontmatter`가 별도 메타데이터
   경로를 만들지 않는지 확인 필요 (현재 `document_identity.py`와 별개로 존재하는 것으로 보임).
3. **파이프라인 단계 표준화**: DocumentContext가 `processing.py`의 단계(추출→정제→청킹→식별→저장)와
   `dbma.py`의 자체 단계(청킹→노이즈필터→임베딩→색인)를 모두 포괄할지, 아니면 후자를
   폐기하고 `core/retrieval.py`/`core/ingest.py` 경로로 단일화할지 먼저 결정해야 한다.
4. **벡터 백엔드 단일화**: DocumentContext/ExecutionContext가 참조할 벡터 저장소는
   Qdrant 하나로 확정하고, Chroma 관련 필드(`CHROMA_COLLECTION`, `CHROMA_PERSIST_DIR`,
   `chroma_db` 상태 판정)는 DocumentContext 설계 범위에서 제외하거나 명시적으로
   "레거시, 사용 안 함"으로 태깅해야 한다.
5. **ExecutionContext 상태 원천 통합**: `feature_flags.py` + `runtime_state.py` +
   `dbma.py`의 인라인 가용성 체크(`_qdrant_available` 등) 세 곳을 ExecutionContext
   뒤로 감출 단일 인터페이스가 필요하다.
6. **Retrieval Engine 계약 확정**: DocumentContext가 검색 계층에 넘길 표준 인터페이스는
   `core/retrieval.py`의 `RetrievalEngine`/`QueryProcessor` 계약을 기준으로 하고,
   `core/search.py`(경량)와 `dbma.py`(레거시 인라인)는 이 계약으로 흡수되거나 폐기 대상으로
   명시되어야 한다.

---

## 부록: One-Pipeline / One-Config / One-Retrieval / One-Execution-State 체크리스트

| 원칙 | 상태 | 근거 |
|---|---|---|
| One Pipeline | ❌ 미충족 | `dbma.py`가 문서 처리 이후 단계에 대해 별도 파이프라인(`build_rag_store` 등) 보유 |
| One Config | ⚠ 부분 충족 | 소스는 하나(`config.yaml`)지만 Chroma/Qdrant 두 세대 설정이 혼재 |
| One Retrieval Engine | ❌ 정면 충돌 | `RetrievalEngine`, `core/search.py`, `dbma.py` 인라인 RAG — 3계통 병존, 생성 단계까지 포함해 가장 심각 |
| One Execution State | ⚠ 부분 충족 | `feature_flags.py`/`runtime_state.py`는 개념적으로 분리되어 있으나, `dbma.py`의 인라인 가용성 체크가 세 번째 원천으로 추가됨 |

*본 문서는 SPRINT16-B-1 범위(`docs/architecture/`)에서만 작성되었으며,
`core/`, `ui/`, `scripts/`, `tests/`, `config.yaml`은 수정하지 않았다.*

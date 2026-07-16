---
title: "ADR-001: Retrieval Engine Authority"
category: architecture
sprint: SPRINT16-B-3
status: accepted
based_on:
  - docs/architecture/DBMA-Architecture-Map-v2.md (SPRINT16-A-2)
  - docs/architecture/DBMA-Module-Responsibility-v2.md (SPRINT16-B-1)
  - docs/architecture/DBMA-Legacy-EntryPoint-Analysis.md (SPRINT16-B-2)
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-001: Retrieval Engine Authority

| | |
|---|---|
| Status | Accepted |
| Date | 2026-07-16 |
| Deciders | SPRINT16-B 조사 결과 기반 (사람 확인 대기 항목 별도 표시) |
| Supersedes | — |
| Superseded by | — |

---

## Current Conflict

DBMA 저장소에는 검색(retrieval) 책임을 갖는 구현이 **세 갈래**로 존재한다.

| # | 구현 | 위치 | 벡터 백엔드 | 임베딩 | 생성(LLM) | 사용처 |
|---|---|---|---|---|---|---|
| ① | 레거시 인라인 RAG | `dbma.py` (`query_rag`, `build_rag_store`, `query_qdrant`, `upsert_to_qdrant`) | Chroma + Qdrant 혼재 | Ollama (`embed_text_ollama`) | `query_rag` 내부에서 직접 호출 | `dbma.py` 자기 자신(self-contained), 외부 호출자 없음 |
| ② | 경량 검색 | `core/search.py` (`search`, `search_pretty`) | Qdrant | `core/embedder.py` | 없음 | 독립 유틸리티, 현재 UI에서 미사용 확인됨 |
| ③ | 풀스택 검색 엔진 | `core/retrieval.py`(`RetrievalEngine`, `QueryProcessor` 등) + `core/query_enhancements.py` | Qdrant | (외부 위임) | 별도 계층(`ResponseFormatter`) | `ui/pages/research.py`, `core/runtime_state.py`, `tests/test_book_alias_resolution.py` |

세 구현은 각각 다른 벡터 백엔드 조합, 다른 임베딩 경로, 다른 스코어링 방식(신학 특화
BM25/TF-IDF 하이브리드 vs 단순 벡터 질의 vs 없음)을 가지며 서로를 참조하지 않는다.
`dbma.py`의 ①은 응답 생성(LLM 호출)까지 포함한 end-to-end 스택이라는 점에서
단순 "중복 함수"가 아니라 **별도의 완결된 RAG 애플리케이션**이다.

이 상태는 SPRINT16-B-1(Module Responsibility Mapping)과 SPRINT16-B-2(Legacy Entry
Point Analysis)에서 각각 독립적으로 확인되었으며, "One Retrieval Engine" 원칙에
정면으로 위반된다.

---

## Decision

**`core/retrieval.py::RetrievalEngine`(및 그 위의 `QueryProcessor` 계약)을
DBMA의 유일한 Retrieval Engine Authority로 지정한다.**

- `core/search.py`는 `RetrievalEngine` 계약으로 **흡수(absorb)**하거나 **폐기(deprecate)**한다.
- `dbma.py`의 인라인 RAG 함수군(`query_rag`, `build_rag_store`, `query_qdrant`,
  `upsert_to_qdrant`, `embed_text_ollama`)은 **폐기(deprecate)** 대상이며,
  필요한 기능은 `RetrievalEngine`/`core/ingest.py`/`core/embedder.py` 경로로
  개별 마이그레이션한다.
- 향후 신규 검색/RAG 기능은 `core/retrieval.py` 계약 위에서만 구현한다 —
  새로운 병행 검색 경로를 만들지 않는다.

---

## Rationale

1. **현재 세대 UI가 이미 ③을 채택**: `ui/pages/research.py`가 `RetrievalEngine`을
   사용하고 있으며, v1.1.0 공식 문서(`USER_GUIDE.md`, `OPERATIONS.md`)도
   `ui/app.py`를 현재 진입점으로 명시한다. Authority를 ③으로 두는 것은
   이미 진행 중인 방향을 문서로 확정하는 것에 가깝다.
2. **기능적 우월성**: `RetrievalEngine`은 BM25/TF-IDF 하이브리드 스코어링,
   성경 인용 정합성(`_scripture_alignment_score`), 주제 관련성(`_thematic_relevance_score`),
   설교 활용성(`_sermon_usability_score`) 등 신학 문서 특화 로직을 갖추고 있다.
   ①·②는 이런 도메인 특화 스코어링이 전혀 없는 단순 벡터 질의 수준이다.
3. **회귀 테스트 존재**: `tests/test_book_alias_resolution.py`,
   `tests/test_query_enhancements_full_regression.py`가 `RetrievalEngine`/
   `EnhancedQueryParser` 경로를 검증한다. ①·②는 어떤 테스트로도 커버되지 않는다
   (SPRINT16-B-2에서 확인) — 즉 ③만이 유일하게 신뢰 가능한 경로다.
4. **벡터 백엔드 일관성**: `RetrievalEngine`은 Qdrant만 사용한다. `core/qdrant_init.py`,
   `core/ingest.py`, `core/md_manager.py`도 전부 Qdrant다. Chroma는 ①(`dbma.py`)
   생태계에만 남아있는 레거시이며, Authority를 ③으로 확정하면 벡터 백엔드
   단일화(Qdrant)가 자연히 뒤따른다.
5. **마이그레이션 안전성**: SPRINT16-B-2 조사에서 ①의 `query_rag`/`build_rag_store`가
   외부에서 전혀 참조되지 않는 self-contained 코드임을 확인했다. 즉 ①을
   폐기해도 깨지는 외부 호출자가 없다 — 마이그레이션 리스크가 낮다.
6. **생성(Generation) 책임 분리 원칙**: ①은 검색과 LLM 생성을 한 함수(`query_rag`)에
   뭉쳐놓았지만, ③은 검색(`RetrievalEngine`)과 응답 조립(`ContextAssembler`,
   `ResponseFormatter`)을 분리해 놓았다. 이 분리 구조가 향후 생성 모델 교체나
   프롬프트 전략 변경 시 영향 범위를 좁혀준다.

---

## Migration Impact

| 대상 | 조치 | 비고 |
|---|---|---|
| `core/search.py` | `RetrievalEngine`/`QueryProcessor` 계약으로 흡수 | 기능이 단순하여 흡수 난이도 낮음 |
| `dbma.py::query_rag` | 폐기, 검색 부분은 `RetrievalEngine`/`QueryProcessor`로 대체 | 외부 호출자 없음 → 안전 |
| `dbma.py::build_rag_store` | 폐기 또는 `core/ingest.py`+`core/embedder.py`로 재구성 | 자체 청킹(`rag_chunk_text`)·노이즈필터(`_rag_noise`)는 `core/chunking_optimizer.py`+`core/utils.py`와 통합 검토 필요 |
| `dbma.py::embed_text_ollama` | 폐기 또는 `core/embedder.py`로 통합 | Ollama 임베딩 지원이 여전히 필요한 요구사항인지 **사람 확인 필요** |
| Chroma 참조 일체 (`core/config.py`의 `CHROMA_*`, `scripts/backup_chroma.py`, `core/runtime_state.py`의 `chroma_db` 판정) | 레거시로 태깅, 제거는 별도 스프린트 | 실제 운영 중인 Chroma 인스턴스 존재 여부 **사람 확인 필요** |
| 응답 생성(LLM 호출) 책임 | `RetrievalEngine` 바깥에 신규 Generation 계층 설계 필요 | 현재 ③에는 이 책임이 명시적으로 없음 — SPRINT16-C 이후 별도 설계 대상 |
| `dbma.py` 파일 자체 | 즉시 삭제하지 않음, archive candidate로 유지 | "deprecated" 문서 선언과 2026-07-15까지의 실제 수정 이력이 모순 — 근본 원인 확인 전 삭제 금지 |

이 ADR은 **결정(무엇이 Authority인가)만 확정**하며, 위 표의 개별 마이그레이션 작업은
실행하지 않는다. 각 항목은 코드 변경이 필요하므로 이 스프린트(docs/architecture/만
허용)의 범위 밖이며 후속 스프린트에서 별도로 계획되어야 한다.

---

## SPRINT16-C Implications

1. **DocumentContext/ExecutionContext가 검색 계층에 넘길 표준 인터페이스는
   `RetrievalEngine`/`QueryProcessor`의 시그니처를 기준으로 설계한다.** ①·②의
   시그니처는 참고하지 않는다.
2. **DocumentContext 설계 범위에서 Ollama 임베딩 경로(`embed_text_ollama`)를
   기본 가정에 포함하지 않는다** — `core/embedder.py`의 임베딩 경로만을 정본으로 삼는다.
   (Ollama 지원 필요 여부가 사람 확인으로 "필요"로 결론 나면 이 ADR을 개정한다.)
3. **ExecutionContext의 인덱싱/가용성 상태 판정은 `core/runtime_state.py`를
   유일한 판정 소스로 삼는다** — `dbma.py`의 `get_vector_client()`, `get_collection()`,
   `_qdrant_available()`은 참조하지 않는다.
4. **생성(Generation) 책임은 SPRINT16-C의 DocumentContext 범위가 아니라
   별도 후속 설계 항목으로 명시적으로 분리한다** — `RetrievalEngine`에 없는
   책임을 DocumentContext에 암묵적으로 떠넘기지 않는다.
5. **미해결 선행조건**: `dbma.py`가 "deprecated" 선언 이후에도 계속 수정된 이유가
   해소되지 않으면, SPRINT16-C 설계가 완료된 후에도 실제 운영에서 레거시 경로가
   병행 사용될 위험이 남는다. 이 ADR의 Decision은 "목표 아키텍처"를 확정할 뿐,
   `dbma.py`의 운영상 지위(활성 사용자 존재 여부)에 대한 사람의 확인을 대체하지 않는다.

---

*본 문서는 SPRINT16-B-3 범위(`docs/architecture/`)에서 작성되었으며, 어떤 코드도
수정하지 않았다. 표에 나열된 조치는 결정 사항의 기록일 뿐 실행이 아니다.*

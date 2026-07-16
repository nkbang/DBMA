---
title: DBMA DocumentContext Architecture Design v1
category: architecture
sprint: SPRINT16-C-1
based_on:
  - docs/architecture/DBMA-Architecture-Map-v2.md (SPRINT16-A-2)
  - docs/architecture/DBMA-Module-Responsibility-v2.md (SPRINT16-B-1)
  - docs/architecture/DBMA-Legacy-EntryPoint-Analysis.md (SPRINT16-B-2)
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md (SPRINT16-B-3)
  - docs/architecture/DBMA-Retrieval-Migration-Matrix-v1.md (SPRINT16-B-4)
  - core/document_identity.py, core/identity_registry.py, core/processing.py,
    core/retrieval.py (읽기 전용 분석)
status: draft (design only — 구현 없음)
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정)
---

# DBMA DocumentContext Architecture Design v1

이 문서는 `DocumentContext` 객체의 책임 범위와 경계를 정의한다.
SPRINT16-B 시리즈가 확정한 결정(Retrieval Authority = `RetrievalEngine`,
`dbma.py` 레거시 경로 격리)을 전제로, "문서 하나의 생애주기를 표현하는 객체"를
설계 수준에서 규정한다. 코드는 작성하지 않는다 — SPRINT17 구현을 위한
설계 명세다.

---

## 0. 현재 Metadata Flow 재확인 (설계 근거)

`core/processing.py::process_one_file()`을 직접 읽어 확인한 실제 시퀀스:

```text
Point A — Identity 발급 (processing.py:517)
  document_id = generate_document_id(final_text, source_name)
  file_hash   = compute_content_hash(final_text)

Ingest Gate (processing.py:522-527)
  registry = load_identity_registry(registry_path)
  decision, existing_record = classify_ingest_decision(registry, document_id, file_hash)
  → SKIP  : 기존 md 재사용, 필요 시 메타데이터만 보강 후 조기 반환
  → RETRY / REPROCESS / PROCESS : 계속 진행

MD 저장 (processing.py:596-603)
  document_meta = build_document_metadata(chunk_count=0)   ← 청킹 전 1차 메타데이터
  md_path = save_md_with_language(..., document_meta)

청킹 (processing.py:613-664)
  chunks = optimize_chunks(body_text, ext)  (실패 시 splitter.split_text 폴백)
  chunk_ids = [generate_chunk_id(document_id, idx) for idx in range(len(chunks))]

Point B — Chunk ID 부여 (processing.py:663)

원본 복사 (processing.py:686-688)
  copy_source_file(), mark_processed()

Point C — 최종 메타데이터 (processing.py:691-696)
  document_meta = build_document_metadata(chunk_count=len(chunks))  ← 2차 메타데이터 (chunk_count 갱신)

Registry 반영 (processing.py:699-716)
  update_content_hash(registry, document_id, file_hash)
  record, is_new = register_document(registry, document_meta, output_dir)
  save_identity_registry(registry, registry_path)
  update_pipeline_flags(registry, document_id,
      {ingested, copied, extracted, cleaned, chunked, output_generated, verified} = True)
  save_identity_registry(registry, registry_path)   ← 2회 저장 (register 직후 + flags 직후)
```

**관찰 1**: `build_document_metadata()`가 **파이프라인 도중 두 번 호출**된다
(청킹 전 `chunk_count=0`, 청킹 후 `chunk_count=len(chunks)`). 이는 메타데이터가
불변 객체가 아니라 파이프라인 진행에 따라 누적/갱신되는 상태임을 뜻한다 —
DocumentContext가 이 "부분 완성 상태"를 표현할 수 있어야 한다.

**관찰 2**: `identity_registry.py`가 소유한 `ingest_status`
(`PROCESSED`/`FAILED`/`ABANDONED`)와 `pipeline_flags`
(`ingested/copied/extracted/cleaned/chunked/output_generated/verified`)는
**문서 자체의 속성이 아니라 "처리 세션의 결과"**다. `identity_registry.py`는
이 둘을 이미 명확히 분리해서 저장하고 있다 (`record["status"]` vs
`record["pipeline_flags"]`).

**관찰 3(경계 격차, retrieval.py 확인)**: `core/retrieval.py`의 `RankedCandidate`는
문서를 `tsu_id`로 식별한다 (`"TSU-{book_id}-{number}"` 형식, `scripts/repair_tsu_book_id.py`
확인). 이는 `document_identity.py`의 `generate_chunk_id()`가 만드는
`{doc_id[:16]}_chunk_{idx:05d}` 형식과 **전혀 다른 식별자 체계**다. 즉 현재
DBMA에는 처리 단계의 식별자(`document_id`/`chunk_id`)와 검색 단계의 식별자
(`tsu_id`)가 서로 매핑되지 않는 두 개의 독립된 네임스페이스로 존재한다.
이 격차는 DocumentContext 설계에서 반드시 다뤄야 하는 핵심 문제다 (§5 참조).

---

## 1. DocumentContext가 소유하는 데이터 (Owns)

DocumentContext는 **문서 한 건의 처리 생애주기 동안 유효한 상태**를 소유한다.
기존 코드의 다음 산출물을 하나의 객체로 통합 표현한다:

| 필드 그룹 | 출처(기존 함수) | 설명 |
|---|---|---|
| Identity | `generate_document_id()`, `compute_content_hash()` | `document_id`(32자 SHA-256 prefix), `file_hash`(64자 full hash) |
| Source | 파이프라인 입력 | `source_file`, `source_type`, `is_ocr` |
| Structural metadata | `build_document_metadata()` | `title`, `author`, `book`, `chapter`, `page`, `batch_id` (unknown=None 원칙 유지) |
| Processing metadata | `build_document_metadata()` | `language`, `noise_score`, `noise_mode`, `chunk_count`, `processing_version` |
| Chunk identity | `generate_chunk_id()` | `chunk_ids: list[str]` (document_id에서 파생) |
| Ingest lifecycle status | `identity_registry.py` record | `ingest_status`(PROCESSED/FAILED/ABANDONED), `retry_count`, `max_retries`, `last_failure_reason` |
| Pipeline completion flags | `update_pipeline_flags()` | `ingested`, `copied`, `extracted`, `cleaned`, `chunked`, `output_generated`, `verified` |
| Timestamps | `generate_processing_timestamp()`, registry | `created_at`, `last_processed_at` |
| Artifact paths | `save_md_with_language()`, `copy_source_file()` 반환값 | `md_path`, `copied_source_path` |

DocumentContext는 이 데이터를 **읽기·쓰기 가능한 단일 진입점**으로 노출해야 한다 —
현재처럼 `processing.py`가 `build_document_metadata()`를 두 번 호출해 두 개의
서로 다른 dict를 만드는 대신, 하나의 DocumentContext 인스턴스를 단계별로
갱신(mutate)하는 방식으로 대체한다.

---

## 2. DocumentContext가 소유하지 않는 데이터 (Does Not Own)

| 데이터 | 실제 소유자 | DocumentContext와의 관계 |
|---|---|---|
| Registry 영속화 메커니즘(파일 I/O, atomic swap) | `identity_registry.py`(`load_/save_identity_registry`) | DocumentContext는 상태를 담을 뿐, 디스크 쓰기는 registry 계층이 계속 담당 |
| 중복/재처리 판정 로직(`classify_ingest_decision`의 B1~B7 상태 머신) | `identity_registry.py` | DocumentContext는 판정 **결과**(ingest_status)를 담지만, 판정 **로직**은 소유하지 않음 — 로직 이동은 이번 설계 범위 밖 |
| 청킹 알고리즘 자체(`optimize_chunks`) | `core/chunking_optimizer.py` | DocumentContext는 청킹 **결과**(chunk_ids, chunk_count)만 담음 |
| 노이즈 점수 계산식(`calculate_noise_score`) | `core/utils.py` | 결과값만 저장, 계산 로직 미소유 |
| 임베딩 벡터 자체 및 임베딩 계산 | `core/embedder.py` | DocumentContext는 "임베딩 완료 여부" 같은 상태 플래그는 가질 수 있으나 벡터 값 자체는 소유하지 않음 (ExecutionContext/Retrieval 계층 소관) |
| **검색 시점의 랭킹/스코어링 상태**(`vector_score`, `bm25_score`, `theological_score`, `final_score`) | `core/retrieval.py::RankedCandidate` | 이것은 질의(query) 단위 상태이지 문서 단위 상태가 아니다 — DocumentContext는 "이 문서가 검색 가능한 상태인가"까지만 알고, 특정 질의에 대한 스코어는 모른다 |
| `tsu_id` 및 TSU 데이터셋 스키마 | `core/retrieval.py` / TSU 생성 스크립트 | 현재 `document_id`/`chunk_id`와 매핑되지 않음(§0 관찰 3) — DocumentContext가 이 매핑을 **만들어야 하는지**는 결정하되, TSU 스키마 자체의 소유권은 가져오지 않음 |
| 실행 환경 상태(Qdrant 가용성, feature flag, 파이프라인 전체 진행률) | `core/runtime_state.py`, `core/feature_flags.py` → **ExecutionContext**(예정) | §4 참조 — 명확히 별도 객체 책임 |
| UI 세션 상태(Streamlit `session_state`) | `ui/state/store.py::StateStore` | 완전히 무관한 계층, DocumentContext는 UI를 모른다 |
| `dbma.py`의 레거시 RAG 상태(Chroma 클라이언트, Ollama 모델 목록 등) | `dbma.py` (ADR-001에 의해 폐기 대상) | DocumentContext 설계에 레거시 경로를 위한 필드를 만들지 않는다 |

---

## 3. Lifecycle

DocumentContext의 상태 전이는 `process_one_file()`의 실제 실행 순서를 그대로
반영한다 (§0에서 확인한 순서 기준). 상태(state) 이름은 설계 편의상 부여한 것이며
`identity_registry.py`의 `ingest_status` 값과 혼동하지 않는다.

```text
CREATED
  └─ source_file, source_type 만 존재 (파일이 처리 대상으로 선택된 시점)

IDENTIFIED   (Point A)
  └─ document_id, file_hash 확정
  └─ ★ 여기서 classify_ingest_decision() 결과를 받아 분기:
       - SKIP      → SKIPPED (조기 종료, 기존 레코드 재사용)
       - RETRY     → RETRYING (재시도 카운터 증가 후 계속)
       - REPROCESS → 계속 진행 (기존 레코드 덮어씀)
       - PROCESS   → 계속 진행 (신규)

METADATA_DRAFTED   (Point 중간, processing.py:596)
  └─ 1차 build_document_metadata() 결과 보유 (chunk_count=0)
  └─ md_path 확정 (저장 완료)

CHUNKED   (Point B, processing.py:663)
  └─ chunk_ids 확정, chunk_count 갱신

SOURCE_ARCHIVED   (processing.py:686)
  └─ copied_source_path 확정

METADATA_FINALIZED   (Point C, processing.py:691)
  └─ 2차 build_document_metadata() 결과로 대체 (chunk_count=len(chunks))

REGISTERED
  └─ identity_registry에 반영 완료 (register_document, update_content_hash)
  └─ pipeline_flags 전부 True로 설정 완료

TERMINAL 상태 (택1):
  ├─ COMPLETE    (모든 플래그 True, ingest_status=PROCESSED)
  ├─ SKIPPED     (IDENTIFIED 단계에서 조기 종료)
  └─ FAILED      (임의 단계에서 예외 발생, transition_ingest_status(..., "FAILED", reason) 호출됨)
```

**설계 원칙**: DocumentContext는 이 상태 머신을 **표현**하지만, 상태 전이를
**강제**하지는 않는다 — 전이 트리거(재시도 여부, 실패 사유 판정)는 여전히
`identity_registry.py`의 `classify_ingest_decision()`/`transition_ingest_status()`가
담당한다. DocumentContext는 그 결과를 자신의 필드에 반영하는 수동적 컨테이너다.
(능동적 상태 머신으로 격상할지는 SPRINT17 구현 결정 사항 — §6 참조)

---

## 4. ExecutionContext와의 상호작용

SPRINT16-B 시리즈에서 이미 "Execution State" 축이 `feature_flags.py`(정적) +
`runtime_state.py`(동적) + `dbma.py`의 인라인 가용성 체크(레거시, 폐기 대상)
세 곳으로 흩어져 있음을 확인했다. `ExecutionContext`는 이 세 축을 통합하는
**별도 객체**로 정의되며, DocumentContext와는 다음과 같이 분업한다:

| 질문 | 답을 아는 객체 | 근거 |
|---|---|---|
| "이 문서는 처리되었는가?" | **DocumentContext** | `pipeline_flags`, `ingest_status` 소유 |
| "이 문서의 콘텐츠가 이전과 달라졌는가?" | **DocumentContext** | `file_hash` vs `last_content_hash` 비교는 registry 로직이지만 결과는 DocumentContext에 반영 |
| "지금 임베딩/검색 기능이 켜져 있는가?" | **ExecutionContext** | `feature_flags.feature_enabled("embedding")`에서 유래 |
| "지금 Qdrant에 실제로 연결 가능한가?" | **ExecutionContext** | `runtime_state.py`의 판정 로직 (`dbma.py`의 `_qdrant_available()`은 흡수 대상, ADR-001 참조) |
| "전체 파이프라인이 지금 몇 %까지 진행됐는가?" (대시보드용 집계) | **ExecutionContext** | `runtime_state.get_pipeline_status()` — 여러 DocumentContext의 집계이지 개별 문서 상태가 아님 |
| "이 문서가 검색 가능한 상태로 색인되었는가?" | **경계 지점** | DocumentContext가 "색인 시도 완료" 플래그는 갖지만, "지금 이 순간 Qdrant 컬렉션에 실제로 존재하는가"는 ExecutionContext가 검증 |

**관계 방향**: ExecutionContext는 다수의 DocumentContext를 관측하는 상위
계층이며, 개별 DocumentContext는 ExecutionContext를 참조하지 않는다
(단방향 의존 — DocumentContext는 순수 데이터, ExecutionContext가 이를 조회).
이는 `core/runtime_state.py`가 이미 파일/로그를 직접 읽어 상태를 재계산하는
현재 방식과 개념적으로 일치하며, 차이는 "파일을 직접 읽는 대신 DocumentContext
컬렉션을 조회한다"는 점이다.

```text
                 ExecutionContext (다수 문서 집계, 시스템 가용성)
                        ▲  조회(query)
                        │
   DocumentContext ─────┘   DocumentContext   DocumentContext  ...
   (문서 A)                  (문서 B)          (문서 C)
```

---

## 5. Retrieval Requirements (검색 계층이 DocumentContext에 요구하는 것)

ADR-001에 따라 Retrieval Authority는 `core/retrieval.py::RetrievalEngine`이다.
`RetrievalEngine`이 DocumentContext로부터 받아야 할 최소 계약:

1. **document_id → tsu_id 매핑 문제 해결 여부 결정 (미해결, 사람 판단 필요)**:
   현재 두 식별자 체계가 독립적이다(§0 관찰 3). DocumentContext 설계 시점에
   다음 중 하나를 선택해야 하며, 이 문서는 결정하지 않고 옵션만 제시한다.
   - (a) DocumentContext가 `chunk_id`를 `tsu_id`로도 겸용하도록 발급 규칙을
     통일한다 (TSU 생성 스크립트 쪽 변경 필요 — SPRINT17 범위).
   - (b) DocumentContext가 `document_id` ↔ `tsu_id` 매핑 테이블을 부가 필드로
     유지한다 (기존 두 체계를 건드리지 않고 다리만 놓음).
2. **검색 가능 여부 플래그**: `RetrievalEngine`이 질의 전에 "이 문서가 색인
   완료 상태인가"를 빠르게 확인할 수 있어야 한다 — `pipeline_flags`가 이미
   `output_generated`까지는 표시하지만 "Qdrant 색인 완료"에 대응하는 플래그가
   현재 registry 스키마에 없다(§0에서 확인한 7개 플래그 중 임베딩/색인 관련
   플래그 부재). DocumentContext 설계는 이 공백을 인지하고 필드 추가가
   필요함을 명시한다.
3. **메타데이터 필터링 입력**: `RetrievalEngine`의 신학 특화 스코어링
   (`_scripture_alignment_score`, `_thematic_relevance_score` 등)은 `book`,
   `chapter`, `page` 같은 구조적 메타데이터를 사용한다. 이 필드들은 이미
   DocumentContext의 owns 목록(§1)에 포함되어 있으므로 **신규 요구사항 없음** —
   기존 `build_document_metadata()` 출력을 그대로 재사용 가능하다.
4. **Generation 계층 요구사항은 이 설계 범위 밖**: ADR-001이 이미 명시했듯
   응답 생성 책임은 `RetrievalEngine` 바깥의 별도 계층이다. DocumentContext도
   생성 관련 필드(프롬프트, 생성 모델 선택 등)를 갖지 않는다.

---

## 6. SPRINT17 Implementation Requirements

이 설계를 코드로 옮길 때 SPRINT17이 반드시 다뤄야 할 항목:

1. **DocumentContext 데이터 클래스 정의**: §1의 필드를 하나의 타입(dataclass 또는
   유사 구조)으로 구현. 기존 `build_document_metadata()`의 dict 반환값과 최소
   1개 어댑터 함수로 상호 변환 가능해야 한다(기존 코드와의 하위호환).
2. **`process_one_file()`의 이중 `build_document_metadata()` 호출을 단일
   DocumentContext 갱신으로 대체**: §0 관찰 1의 문제를 해소. 단, 이번 설계
   문서 자체는 `processing.py`를 수정하지 않는다 — SPRINT17에서 코드 변경.
3. **색인 완료 플래그 신설**: `identity_registry.py`의 `pipeline_flags`에
   `embedded`/`indexed` 같은 필드가 없다는 공백(§5-2)을 메우는 스키마 확장
   설계 (registry schema_version 3.0 검토).
4. **document_id ↔ tsu_id 매핑 정책 확정**: §5-1의 (a)/(b) 중 선택은
   사람의 결정이 선행되어야 한다 — SPRINT17 킥오프 시 첫 번째 의사결정 항목으로
   배치할 것을 권고.
5. **ExecutionContext와의 인터페이스 정의**: §4의 "조회" 관계를 실제 메서드
   시그니처(예: `ExecutionContext.get_document_state(document_id)`)로 구체화.
6. **Lifecycle 상태 머신의 능동/수동 여부 결정**: §3에서 "수동적 컨테이너"로
   잠정 설계했으나, `classify_ingest_decision()`의 상태 전이 로직을
   DocumentContext 메서드로 흡수할지(능동화) 여부는 구현 착수 시 재검토 필요 —
   흡수 시 `identity_registry.py`와 책임이 중복될 위험이 있어 신중한 결정 필요.
7. **회귀 테스트**: `tests/test_processing_pipeline.py`가 이미 존재하므로,
   DocumentContext 도입 후 동일 입력에 대해 기존 registry 출력(JSON)과
   바이트 단위로 동등한 결과가 나오는지 검증하는 스냅샷 테스트 추가.
8. **`dbma.py` 레거시 경로와의 격리 유지**: SPRINT16-B-4 Migration Matrix가
   지적한 대로 `dbma.py`의 운영 지위가 아직 미확인이므로, DocumentContext
   구현이 `dbma.py`에 새로운 의존을 만들지 않도록 주의(단방향: `dbma.py`가
   원한다면 나중에 DocumentContext를 참조할 수 있으나 그 역은 금지).

---

## 부록: 설계 원칙 요약

- DocumentContext = **문서 한 건**의 상태 컨테이너. 계산 로직(청킹 알고리즘,
  노이즈 계산, 판정 로직)은 소유하지 않고 기존 core 모듈에 위임한다.
- ExecutionContext = **시스템/다수 문서**의 상태 조회자. DocumentContext를
  단방향으로 조회하며 그 역은 없다.
- Retrieval(= `RetrievalEngine`)은 DocumentContext의 구조적 메타데이터를
  그대로 소비할 수 있으나, `tsu_id` 네임스페이스와의 격차는 미해결 상태로
  SPRINT17 결정 사항으로 이월한다.
- 이 문서는 설계만 다루며 어떤 코드도 변경하지 않았다.

---

*본 문서는 SPRINT16-C-1 범위(`docs/architecture/`)에서 작성되었으며,
`core/`, `ui/`, `scripts/`, `tests/`, `config.yaml`, `dbma.py`는 수정하지 않았다.*

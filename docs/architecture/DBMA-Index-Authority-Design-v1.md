---
title: DBMA Index Authority Final Design v1
category: architecture
sprint: SPRINT20-I-C
based_on:
  - CUE-20I-A Architecture Reality Audit
  - CUE-20I-B Architecture Authority Verification
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md
  - docs/architecture/DBMA-Legacy-Code-Removal-Plan-v1.md
status: implemented (SPRINT20-I에서 실행 완료 — core/index_orchestrator.py,
  core/tsu_builder.py 존재 확인, docs/STATE.md "Index/TSU Builder Authority" 100%)
created: 2026-07-17
scope: docs/architecture/ only (조사·설계만, 코드 0 변경) — 설계 당시 기준, 이후 구현됨
---

# DBMA Index Authority Final Design v1

이 문서는 설계 문서다. 어떤 코드도 수정·이동·삭제하지 않았다.
CUE-20I-A/B에서 확정한 Architecture Reality 위에서 "DBMA에서 색인이란
무엇인가"와 그 책임 경계를 확정한다.

---

## 1. Index Definition

**폐기된 정의 (SPRINT20-H 이전):**
```
Index = Chroma/Qdrant vector database 생성
```
→ CUE-20I-A/B에서 이 전제가 공식 경로와 무관한 legacy(dbma.py)임이 확인됨.

**확정 정의 (SPRINT20-I-C):**
```
Index = TSU Dataset 생성 (Identity Registry → tsu_dataset.jsonl)
```

DBMA의 5개 단계와 책임을 용어로 분리 확정한다(그동안 "indexing"으로 혼용):

| 단계 | 명칭 | 책임 | 산출물 | "Index"인가? |
|---|---|---|---|---|
| RAW → Markdown | Processing | 문서 변환·추출·청킹 | `output/{stem}.md` | ❌ |
| Markdown → Registry | Identity Management | 문서 식별·중복 감지 | `output/registry/documents.json` | ❌ |
| **Registry → TSU JSONL** | **Indexing** | **검색 가능 구조 생성** | **`output/bench/tsu_dataset.jsonl`** | ✅ **이것이 색인** |
| Query → Ranking | Retrieval Runtime | 검색 실행 | (런타임, 비영속) | ❌ |
| Embedding Vector | Acceleration | 성능 최적화 캐시 | `cache/embeddings/*.json` | ❌ (캐시) |

**핵심 원칙:** DBMA는 "RAG + VectorDB 시스템"이 아니라 **TSU 기반
Theological Retrieval System**이다. 색인의 산출물은 벡터DB가 아니라
TSU 데이터셋이다. 임베딩 벡터는 색인이 아니라 재생성 가능한 가속 캐시다.

---

## 2. Authority Decision

**공식 Index Authority = `core/index_orchestrator.py`** (Service Layer).

`index_orchestrator.py`는 새로운 색인 엔진이 **아니다**. TSU 생성 로직
(현재 `scripts/build_tsu_dataset.py`에 구현됨)의 **공식 프로그래매틱
진입점(Service Layer)**이다. 새 파싱/스코어링 로직을 만들지 않고 검증된
배치 로직을 함수 호출로 감싼다(SPRINT20-I에서 이미 생성·검증).

근거 (CUE-20I-B Matrix):

| 후보 | input | output | caller | 판정 |
|---|---|---|---|---|
| `scripts/build_tsu_dataset.py` | registry + chunk txt | tsu_dataset.jsonl | CLI + backfill + orchestrator | 로직 소유 (→ core로 승격 권장) |
| `core/index_orchestrator.py` | 동일(래핑) | 동일 | 미연결(준비됨) | **공식 Service Layer** |
| `dbma.py::build_rag_store()` | RAW 재추출 | Chroma/Qdrant | dbma.py UI만 | legacy, authority 아님 |

---

## 3. Module Responsibility

### 3.1 core/index_orchestrator.py (Service Layer)

**허용 책임:**
- registry 읽기 (`load_identity_registry`)
- TSU 생성 호출 (`build_tsu_records`)
- dataset/manifest 기록 (`write_tsu_dataset`, `write_manifest`)
- validation (레코드 수, 문서 수 대조)
- logging (색인 시작/완료/실패)

**금지 책임 (경계 밖):**
- ❌ embedding 생성 (→ Retrieval 런타임의 EmbeddingCache 소관)
- ❌ retrieval 실행 (→ RetrievalEngine 소관)
- ❌ vector DB 쓰기 (→ legacy, 폐기 대상)
- ❌ generation (→ GenerationService 소관)

### 3.2 scripts/build_tsu_dataset.py 역할 재정의

**현재 상태:** `scripts/`에 있으나 이미 라이브러리로 소비됨
(`core/index_orchestrator.py`가 `build_tsu_records`/`write_tsu_dataset`/
`write_manifest`를 import, `scripts/backfill_document_metadata.py`가
`_resolve_book_id`를 import). 즉 "CLI 전용 스크립트"라는 위치와 실제
역할이 불일치한다.

**선택지:**
- A) scripts 유지 (CLI utility) — 현상 유지, 위치·역할 불일치 지속
- B) core 이동 (library authority) — 역할에 맞는 위치

**권장 방향 (B, 단계적):**
```
core/tsu_builder.py          ← 순수 라이브러리 로직 (build_tsu_records 등)
        ↑ import
scripts/build_tsu_dataset.py ← CLI wrapper (argparse + main만 유지)
        ↑ import
core/index_orchestrator.py   ← Service Layer (UI/프로그램 호출용)
```

**이동 블로커 (선행 필수):** `scripts/build_tsu_dataset.py:43`이
`from scripts.generate_chapter_level_gold_standard import CANONICAL_MAX_CHAPTER`
로 **scripts→scripts 의존**을 갖는다. core로 이동하면 core→scripts라는
잘못된 의존 방향이 생긴다. 따라서 `CANONICAL_MAX_CHAPTER`(성경 정경
장수 상수)를 먼저 `core/`(예: `core/config.py` 또는 신규 `core/canon.py`)
로 옮겨야 clean core 이동이 가능하다. **이 상수 이동 자체가 별도 선행
작업이다.**

---

## 4. Index Lifecycle

| 단계 | 트리거 | 책임자 | 현재 지원 |
|---|---|---|---|
| **CREATE** | 최초 색인 | `index_orchestrator.rebuild_tsu_index()` | ✅ (전체) |
| **UPDATE** | 문서 1개 변경 | `index_orchestrator` (부분 재색인) | ⚠️ 설계 필요 (§5) |
| **REBUILD** | 전체 재생성 | `index_orchestrator.rebuild_tsu_index()` | ✅ |
| **INVALIDATE** | 캐시 무효화 | EmbeddingCache (별도, 색인 아님) | ✅ (재계산) |
| **DELETE** | TSU/legacy 제거 | Archive Manager (미존재, 향후) | ❌ 미설계 |

**주의:** INVALIDATE는 임베딩 캐시(`cache/embeddings`) 소관이지 색인
소관이 아니다. 캐시는 TSU content 해시 키 기반이라 TSU가 바뀌면
자동으로 새 키가 생성되어 자연 무효화된다.

---

## 5. Partial Re-index Design

**목표:** 문서 1개 수정 시 전체 TSU 재생성이 아니라 영향받은 TSU만 갱신.

```
RAW/{file} 수정
      ↓
core/processing.py::process_one_file()   (해당 문서만 재처리)
      ↓
classify_ingest_decision()  → REPROCESS   (B6: hash 변경 감지)
      ↓
registry update (해당 document_id만)
      ↓
affected TSU rebuild (해당 document_id의 chunk만)
```

**Registry 지원 현황 (실측 확인, 12개 문서):**

| 필요 metadata | registry 필드 | 지원? |
|---|---|---|
| document_id | `document_id` | ✅ |
| 변경 감지 (mtime 대용) | `file_hash`, `last_content_hash` (SHA-256) | ✅ (mtime보다 정확) |
| 최종 처리 시각 | `last_processed_at`, `created_at` | ✅ |
| chunk 수 | `chunk_count` | ✅ |
| chunk_id | 저장 안 됨 — `generate_chunk_id(document_id, idx)`로 결정론적 파생 | ✅ (파생 가능) |
| 처리 상태 | `status`, `ingest_status`, `retry_count` | ✅ |

**변경 감지 엔진 이미 존재:** `core/identity_registry.py::classify_ingest_decision()`
(PT-PROCESSING-012)가 B1–B7 결정 로직(PROCESS/SKIP/REPROCESS/RETRY)을
이미 구현. B5(hash 동일→SKIP), B6(hash 상이→REPROCESS)가 부분 재색인의
핵심 판정을 제공한다.

**설계 결론:** 부분 재색인은 **document 단위 granularity로 실현 가능**하다.
- chunk_id가 `generate_chunk_id(document_id, idx)`로 결정론적이므로, 특정
  document_id의 모든 TSU(`TSU-{book}-*` 중 해당 document_id를 가진 것)를
  식별·교체할 수 있다.
- 현재 `write_tsu_dataset()`은 전체 덮어쓰기(`open(...,"w")`)이므로, 부분
  갱신을 위해서는 "기존 dataset 로드 → 해당 document_id 레코드만 교체 →
  전체 재기록" 또는 "document_id별 append-merge" 전략이 필요하다.
- **이번 단계는 설계만.** 구현은 SPRINT20-I-C 이후.

**미지원/주의:** registry에 `modified_time`(파일 mtime) 필드는 없으나,
`file_hash`/`last_content_hash`가 그 역할을 더 정확히 수행하므로 mtime은
불필요하다.

---

## 6. Final Authority Matrix

| Component | Authority | 상태 |
|---|---|---|
| Processing | `core/processing.py` | ✅ 확정 |
| Identity | `core/identity_registry.py` + `core/document_identity.py` | ✅ 확정 |
| **Index** | **`core/index_orchestrator.py`** (Service Layer) | ✅ 확정 (본 문서) |
| TSU Generation (로직) | `scripts/build_tsu_dataset.py` → `core/tsu_builder.py` 승격 권장 | ⚠️ 이동 블로커 有 (§3.2) |
| Retrieval | `core/retrieval.py::RetrievalEngine` | ✅ 확정 (ADR-001) |
| Embedding | `core/embedder.py` (BGE-M3/1024/Ollama 단일) | ✅ 확정 (CUE-20I-B) |
| Generation | `core/generation.py::GenerationService` | ✅ 확정 |
| Legacy RAG | `dbma.py` (build_rag_store/query_rag) | → archived (예정) |

---

## 7. Migration Impact

| 변경 | 영향 파일 | 위험 | 선행 조건 |
|---|---|---|---|
| `CANONICAL_MAX_CHAPTER` core 이동 | scripts/generate_chapter_level_gold_standard.py, build_tsu_dataset.py | 낮음 (상수 1개) | 없음 — 즉시 가능 |
| `build_tsu_dataset.py` 로직 → `core/tsu_builder.py` | scripts/build_tsu_dataset.py, backfill_document_metadata.py, index_orchestrator.py | 중간 (import 경로 3곳) | CANONICAL 이동 선행 |
| 부분 재색인 구현 | index_orchestrator.py, (write_tsu_dataset 병합 로직) | 중간 | 본 설계 승인 |
| dbma.py archive | dbma.py, core/search/ingest/qdrant_init | 낮음 (격리 확인됨) | 부분 재색인 완료 |

---

## 8. SPRINT20-I Implementation Plan

확정된 진행 순서:

```
I-C (본 문서)  Index Authority 설계 확정               ← 현재, 승인 대기
      ↓
I-C-1  CANONICAL_MAX_CHAPTER → core 이동 (상수 선행)
      ↓
I-C-2  core/tsu_builder.py 추출 + build_tsu_dataset.py를 CLI wrapper로
      ↓
I-C-3  index_orchestrator에 부분 재색인(UPDATE) 구현
      ↓
─── 이후 (본 SPRINT 범위 밖, 별도 승인) ───
      ↓
[병행 조사]  md_manager legacy boundary 확인
      ↓
[병행 조사]  chroma_db ADR-003 최종 보존/폐기 결정
      ↓
Legacy Removal 실행 (dbma.py Phase 3/4)
```

**이번 문서(I-C)의 완료 기준:** Index 정의·Authority·책임 경계·Lifecycle·
부분 재색인 설계가 확정되고, 코드 변경 0. 실제 구현(I-C-1 이후)은 본
설계 승인 후 별도 진행한다.

---

*본 문서는 SPRINT20-I-C 범위(`docs/architecture/`)에서 조사·설계만
수행했으며, `core/`, `ui/`, `scripts/`, `dbma.py`는 수정하지 않았다.*

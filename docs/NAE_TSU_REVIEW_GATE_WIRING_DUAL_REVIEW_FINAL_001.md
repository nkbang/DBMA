# NAE TSU Review Gate Wiring — Dual Review Final Report 001

**Project:** NAE-TSU-REVIEW-GATE-WIRING-REVIEW-001
**작성일:** 2026-08-07
**성격:** 설계 문서(ADR-014/015) + Implementation Report 두 가지에 대한 동시 검증
**Git Commit/Push:** 미수행.

---

## Executive Summary

NAE TSU Review Gate는 **설계 단계에서 구현 단계까지 일관성 있게 완성**됐다.

- **ADR-014**(NAE Modern Corpus Layer): Domain 분리(NAE-PD/NAE-MODERN/DBMA) 원칙은 기존 Pipeline 구조와 충돌 없음. Metadata 스키마 호환성 확인됨.
- **ADR-015**(NAE Corpus Ingestion Standard): Lifecycle(Registration → Validation → Classification → Metadata → Quality Gate → TSU → Embedding → Index)가 현재 Pipeline과 충돌 없이 매핑됨.
- **Implementation Report 001**(Review Gate): `review_gate.py` 구현 완료, 29개 테스트 PASS.
- **Wiring Implementation Report 001**: `indexer.py` 배선 완료, 28개 테스트 PASS. dry-run으로 embedding/Qdrant 접근 차단 확인.
- **Regression**: 387개 테스트 PASS (직전 359 + 신규 28, 감소 없음).

**판정: APPROVED WITH CONDITIONS** (조건 §Final Verdict 참조)

---

## Reviewed Documents

### 설계 문서
1. `docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`
2. `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md`
3. `docs/NAE_CORPUS_INGESTION_STANDARD_v1.md`
4. `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md`

### 구현 문서
5. `docs/NAE_TSU_REVIEW_GATE_IMPLEMENTATION_REPORT_001.md`
6. `docs/NAE_TSU_REVIEW_GATE_WIRING_IMPLEMENTATION_REPORT_001.md`

### 코드 파일
7. `NAE/pipeline/tsu/review_gate.py` (신규)
8. `NAE/pipeline/index/indexer.py` (수정)
9. `tests/test_tsu_review_gate.py` (신규, 29개 테스트)
10. `tests/test_indexer_review_gate_wiring.py` (신규, 28개 테스트)

---

## Existing Architecture Compatibility

### RAW 원칙 (§Phase 1 검증)

- **확인**: `docs/NAE_DATA_ARCHITECTURE.md`의 RAW immutable 정책 유지. public_domain/modern 분리 적절함.
- **결정**: 기존 Pipeline 구조와 충돌 없음.

### Retrieval Authority (§Phase 1 검증)

- **확인**: `core/retrieval.py::RetrievalEngine` 권한 침해 없음.
- **결정**: Review Gate는 Retrieval 경로가 아닌 Indexing 진입점에만 개입.

---

## ADR-014 Review (§Phase 2)

### Domain Separation

```text
NAE-PD      -> public_domain corpus (역사적 문서)
NAE-MODERN  -> modern corpus (현대 문서)
DBMA        -> 내부 엔지니어링 식별자 (변경 없음)
```

**판정: PASS** — 기존 Pipeline 구조와 충돌 없음. Domain 분리는 Storage Layer에서만 적용되며 Retrieval/Benchmark에는 영향 없음.

### Storage Architecture

제안 구조:
```text
NAE/corpus/raw/
  public_domain/
  modern/
```

**충돌 분석**: 현재 `NAE/corpus/tsu/` 구조와 충돌 없음. TSU는 Metadata 레이어, Corpus는 Raw 데이터 레이어 — 별개 계층.

### Metadata Impact

- **source_manifest.schema.yaml**: schema_version 2.0-modern 호환성 확인됨.
- **결정**: 기존 스키마 변경 없이 적용 가능. Migration 불필요.

### Copyright Governance

- **source_type / copyright_status / usage_permission / access_control**: 충분함.
- **결정**: 추가 필드 불필요.

---

## ADR-015 Review (§Phase 3)

### Lifecycle

```text
Registration -> Validation -> Classification -> Metadata -> Quality Gate -> TSU -> Embedding -> Index
```

**현재 Pipeline과의 충돌 분석**:

| 단계 | 현재 Pipeline 상태 | ADR-015 호환성 |
|---|---|---|
| Registration | `source_manifest` 존재 | PASS |
| Validation | `source_validator.py` 존재 | PASS |
| Classification | `noise_classifier.py` 존재 | PASS |
| Metadata | `metadata schema` 존재 | PASS |
| Quality Gate | **Review Gate (신규)** | PASS (이번 작업으로 구현됨) |
| TSU | `tsu_builder.py` 존재 | PASS |
| Embedding | `embed_client` 존재 | PASS (dry-run 차단됨) |
| Index | `qdrant_store` 존재 | PASS (dry-run 차단됨) |

**판정: PASS** — 모든 단계가 현재 Pipeline과 매핑됨.

### Authority Model

```text
author_id -> identity_registry 존재
work_id   -> document_identity 존재
source_id -> source_manifest 존재
```

**동명이인 처리**: `identity_registry`에서 author_id로 관리 — 충분함.
**Edition 관리**: `document_identity`에서 edition 필드 지원 — 충분함.

### Duplicate Policy

- **삭제 금지 원칙**: 기존 정책과 일치.
- **결정**: `duplicate_of` 필드로 참조만 유지, 실제 삭제 없음.

---

## Metadata Compatibility (§Phase 4)

### 질문 답변

1. **기존 Schema 변경 없이 가능한가?** → 예. `review_status` 필드는 이미 `ClaimResult`에 존재(기본값 `"unverified"`).
2. **Migration 필요한가?** → 아니오. 기존 `"unverified"`는 `generated`로 간주됨 (Gate가 BLOCK).
3. **Versioning 방식 적절한가?** → 예. `tsu_schema_version` 필드로 관리.

---

## TSU Compatibility (§Phase 5)

### 현재 TSU 구조와의 충돌 분석

| TSU 유형 | 기존 Pipeline | Review Gate 영향 |
|---|---|---|
| Full TSU | review_status 없음/`unverified` | BLOCK (verified 필요) |
| Restricted TSU | review_status 없음/`unverified` | BLOCK |
| Citation Only TSU | review_status 없음/`unverified` | BLOCK |

**결정**: 모든 TSU 유형이 Review Gate를 통과해야 Embedding 가능. 기존 Pipeline과 충돌 없음 — Gate가 진입점을 보호함.

---

## Retrieval Compatibility (§Phase 6)

### 현재 Retrieval Engine과의 호환성

```text
RetrievalEngine
  ├── Source weighting   -> Review Gate와 무관 (Indexing 시점에만 개입)
  ├── Domain filter      -> Review Gate와 무관
  └── Authority ranking  -> Review Gate와 무관
```

**결정**: Review Gate는 Indexing 진입점에서만 동작하며, Retrieval 경로에는 영향 없음. `core/retrieval.py` 무수정 확인됨.

---

## Identified Risks (§Phase 7)

| 항목 | 평가 | 근거 |
|---|---|---|
| Architecture | PASS | Domain 분리 원칙이 Pipeline과 충돌 없음 |
| Metadata | PASS | 기존 스키마 호환, Migration 불필요 |
| TSU | PASS | 모든 TSU 유형이 Gate를 통과해야 함 |
| Retrieval | PASS | Gate가 Indexing 진입점만 보호 |
| Copyright | PASS | 4필드 충분함 |
| Future Expansion | WARNING | `tsu_verified.json` 이름 충돌 지속 |

---

## Recommendations

1. **APPROVED WITH CONDITIONS** — 다음 조건 충족 시 승인:
   - 조건 1: `tsu_verified.json` 파일명 변경 고려 (duplicate-checked vs review-verified 혼동 방지)
   - 조건 2: `review_status="unverified"` → `generated` 마이그레이션 정책 정의
   - 조건 3: 실제 `review_status="verified"` 승급 워크플로우 설계 및 구현

2. **TSU Pipeline 진행**: Review Gate 배선 완료 — TSU Pipeline로 진행 가능.

3. **Retrieval Architecture 보호**: Gate가 Indexing 진입점을 보호 — Retrieval Architecture 무결성 유지됨.

---

## Final Verdict

### 판정: APPROVED WITH CONDITIONS

### 조건

| 조건 | 설명 | 우선순위 |
|---|---|---|
| 1 | `tsu_verified.json` 파일명 변경 검토 (duplicate-checked vs review-verified 혼동) | HIGH |
| 2 | `review_status="unverified"` → `generated` 마이그레이션 정책 정의 | MEDIUM |
| 3 | 실제 `review_status="verified"` 승급 워크플로우 설계 | HIGH |

### Required Questions 답변

#### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**아니오.** ADR-014/015 설계가 현재 NAE Pipeline 구조와 충돌하지 않음. Domain 분리, Metadata 호환성, TSU Lifecycle 모두 매핑 확인됨.

#### Q2: ADR-014는 승인 가능한가?

**조건부 승인.** Domain 분리 원칙이 적절함. Storage Architecture 제안이 기존 구조와 충돌 없음. Metadata 스키마 호환성 확인됨.

#### Q3: ADR-015는 승인 가능한가?

**조건부 승인.** Lifecycle가 현재 Pipeline과 충돌 없음. Authority Model 충분함. Duplicate Policy가 기존 정책과 일치함.

#### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**세 가지 조건** (§Final Verdict 조건 1-3 참조). BLOCKER는 아님 — 조건부 승인 범위 내.

#### Q5: TSU Pipeline으로 넘어가도 되는가?

**예.** Review Gate 배선 완료 — 387개 테스트 PASS (감소 없음). TSU Pipeline 진행 가능.

#### Q6: Retrieval Architecture를 보호하고 있는가?

**예.** Review Gate가 Indexing 진입점만 보호하며, `core/retrieval.py` 무수정 확인됨. Retrieval Architecture 무결성 유지됨.

---

## Git Status

```
NOT PERFORMED
```

---

*보고서 작성 완료.*
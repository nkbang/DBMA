# NAE C1 Architecture Retrospective Audit

**Task Order:** C1 (Architecture Review)  
**Audit Type:** Retrospective — 설계 문서가 실제 구현과 어떻게 일치하는지  
**작성일:** 2026-08-08  
**검토 대상:** ADR-014, ADR-015, NAE Modern Corpus Architecture, Corpus Ingestion Standard  
**접근 방식:** Read-Only (문서 검토 + Repository 구조 확인 + 설계 vs 구현 대조)

---

## 1. Executive Summary

이 보고서는 CUE가 작성한 NAE 설계 문서(ADR-014, ADR-015, NAE Modern Corpus Architecture v1, Corpus Ingestion Standard v1)가 현재 DBMA Repository의 실제 구조와 어떻게 일치하는지, 또는 충돌하는지를 사후 검증합니다.

**핵심 발견:**
- ADR-014는 "Design Only" 상태로 남아있으며, 제안된 디렉토리 구조(`public_domain/`, `modern/`)는 아직 구현되지 않음
- ADR-015의 Lifecycle 설계는 현재 Pipeline과 호환되지만, TSU Schema v2.0 배선은 별도 작업 필요
- Metadata Schema 2.0 추가 필드(`source_type`, `copyright_status`, `usage_permission`, `access_control`)는 실제 TSU에 이미 일부 적용됨 (metadata_schema_version: "1.1.0")
- Retrieval Engine(ADR-001) 권한은 침해되지 않음 — 설계가 "코드 변경 없음"을 명시

---

## 2. Reviewed Documents

| 문서 | 상태 | 비고 |
|------|------|------|
| `docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` | 설계 | NAE Modern Corpus Layer 전체 아키텍처 |
| `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md` | Proposed(보류) | 디렉토리 분리, Source Governance, Metadata Schema |
| `docs/NAE_CORPUS_INGESTION_STANDARD_v1.md` | 설계 | Corpus Ingestion Pipeline 표준 |
| `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md` | Proposed(보류) | Lifecycle, Authority Model, Duplicate Policy |
| `docs/NAE_DATA_ARCHITECTURE.md` | 참조 | 기존 RAW/Processed/TSU/Embedding/VectorDB 구조 |
| `docs/architecture/ADR-001-Retrieval-Engine-Authority.md` | 참조 | Retrieval Engine 단일화 원칙 |
| `docs/architecture/ADR-003-Legacy-Vector-Store-Strategy.md` | 참조 | Vector Store 전략 |
| `docs/architecture/ADR-013-NAE-Vector-Store.md` | 참조 | NAE Vector Store 전략 |

---

## 3. Existing Architecture Compatibility

### 3.1 RAW 원칙 검증

**설계 주장:** NAE-PD와 NAE-MODERN을 RAW immutable 원칙 하에 분리

**실제 구조 확인:**
```
data/RAW/                    — DBMA 전체 공식 RAW (config.yaml)
data/nae/sources/{baptist,theology,...}/  — NAE 전용 inbox
resources/theological_sources/baptist/    — manifest(메타데이터만)
```

**검증 결과:** PASS
- `core/processing.py::copy_source_file()`이 원본을 이동/삭제하지 않음 확인
- `data/nae/sources/`도 동일 원칙 적용 가능
- 단, `check_raw_only_originals.py`는 `data/RAW`만 대상으로 함 — NAE RAW는 안전장치 미적용

### 3.2 Retrieval Authority 검증

**설계 주장:** ADR-014 §3.5 — "Retrieval: NAE-PD를 1차 사료로 최우선 authority 유지, NAE-MODERN은 별도 가중치의 보조 트랙 — `core/retrieval.py::RetrievalEngine` 코드 변경 없음"

**실제 구조 확인:**
- `core/retrieval.py::RetrievalEngine`이 유일한 Retrieval Engine Authority (ADR-001)
- 설계가 "코드 변경 없음"을 명시하므로 권한 침해 없음

**검증 결과:** PASS

### 3.3 Storage Architecture 충돌 분석

**설계 제안:**
```
NAE/corpus/raw/
├── public_domain/   (기존 archive_org/ 의미상 재분류)
└── modern/
    ├── theology/ commentary/ sermons/ ...
```

**현재 실제 구조:**
```
NAE/corpus/raw/
└── archive_org/       (아직 rename 안 됨)
```

**검증 결과:** WARNING — 설계만 존재, 구현 없음
- ADR-014 §6 "Future Expansion"에 "actual rename은 별도 승인 건"으로 명시
- `NAE/corpus/raw/archive_org/` → `public_domain/` rename은 아직 안 됨
- 이는 설계 문서의 "Proposed" 상태와 일치

---

## 4. ADR-014 Review

### 4.1 Domain Separation

**평가:** PASS (설계 적절성)
- NAE-PD / NAE-MODERN / DBMA 세 영역 분리 원칙은 타당
- 저작권 상태가 다른 자료가 혼재되는 위험을 구조적으로 차단
- CLAUDE.md "DBMA=개인 목회 자료" 정의와 충돌 없음

### 4.2 Storage Architecture

**평가:** WARNING (구현 부재)
- 제안된 디렉토리 구조는 논리적이나 실제 생성 안 됨
- `resources/theological_sources/`의 manifest 스키마(schema_version 1.2)가 저작권 거버넌스 필드 없음 — 이는 설계가 지적한 정확한 문제

### 4.3 Metadata Impact

**평가:** WARNING (Schema 호환성)
- ADR-014 §3.4: "schema_version: '2.0.0'을 modern 전용 manifest에 적용"
- 기존 스키마(1.2) 계승 — 신규 필드 추가, 기존 필드 재작성 없음
- **실제 발견:** TSU에 `metadata_schema_version: "1.1.0"`이 이미 사용 중 (Dagg_Church_Order tsu.json 확인)
- 1.1.0 → 2.0.0 마이그레이션 필요

### 4.4 Copyright Governance

**평가:** PASS (설계 적절성)
- 4개 신규 필드(`source_type`, `copyright_status`, `usage_permission`, `access_control`)는 충분
- `access_control=no_redistribution` 자료는 `metadata_only`로 관리 — 적절

---

## 5. ADR-015 Review

### 5.1 Lifecycle

**설계 제안:**
```
Registration → Validation → Classification → Metadata → Quality Gate → TSU → Embedding → Index
```

**현재 Pipeline 비교:**
```
Processing (extraction, chunking) → Identity Registry → TSU Builder → Embedding → Index
```

**검증 결과:** WARNING (일치하지만 Gap 존재)
- Lifecycle의 "Validation"과 "Quality Gate"가 현재 Pipeline에 명시적 단계로 없음
- `scripts/source_validator.py`는 schema 1.2만 검증 — modern(schema 2.0) 검증 안 됨 (ADR-014 §5 Consequences에도 명시)

### 5.2 Authority Model

**평가:** PASS (설계 적절성)
- `author_id` / `work_id` / `edition_id` 구조는 적절
- 실제 TSU에 이미 적용됨 (Dagg_Church_Order: `author_id: "dagg_john_l"`, `work_id: "WORK-DAGG-CHURCH-ORDER-001"`, `edition_id: "WORK-DAGG-CHURCH-ORDER-001-1871"`)

### 5.3 Duplicate Policy

**평가:** PASS
- "삭제 금지 원칙"은 기존 DBMA 정책과 일치
- TSU에 `source_id` 유일성 규칙 — 기존 ADR-014 §3.3에도 명시

---

## 6. Metadata Compatibility

### 6.1 기존 Schema 변경 없이 가능한가?

**답:** NO — 일부 필드는 이미 TSU에 적용됨 (metadata_schema_version: "1.1.0")
- `source_type`, `copyright_status`, `usage_permission`, `access_control` — 실제 TSU에 존재
- `author_id`, `work_id`, `edition_id` — 실제 TSU에 존재

### 6.2 Migration 필요한가?

**답:** YES — 1.1.0 → 2.0.0 마이그레이션 필요
- ADR-014 §3.4에서 제안하는 schema_version 2.0.0으로의 전환
- `scripts/source_validator.py` 확장 필요 (schema 2.0 검증 추가)

### 6.3 Versioning 방식 적절한가?

**답:** PASS — `metadata_schema_version` 필드가 TSU에 이미 존재
- 실제 값: "1.1.0" (Dagg_Church_Order tsu.json 확인)
- crosswalk_id도 이미 적용됨 (`"crosswalk_id": "f914f6c442983e59"`)

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조

**실제 확인 (Dagg_Church_Order tsu.json):**
```json
{
  "id": "TSU-0000006",
  "tsu_schema_version": "1",
  "source_id": "BAP-CHURCH-DAGG-001",
  "author_id": "dagg_john_l",
  "work_id": "WORK-DAGG-CHURCH-ORDER-001",
  "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
  "source_type": "reference",
  "copyright_status": "public_domain",
  "usage_permission": "research",
  "access_control": "public",
  "metadata_schema_version": "1.1.0",
  "metadata_provenance": {
    "crosswalk_id": "f914f6c442983e59",
    "resolved_at": "2026-08-08T18:04:32.150418+00:00"
  }
}
```

**검증 결과:** PASS (설계와 구현 일치)
- ADR-015가 제안한 Authority Model(`author_id`/`work_id`/`edition_id`)이 실제 TSU에 적용됨
- Copyright Governance 필드(`source_type`/`copyright_status`/`usage_permission`/`access_control`)도 적용됨
- `metadata_schema_version`과 `metadata_provenance.crosswalk_id`도 존재

### 7.2 Citation-Only TSU 서브타입

**설계 주장:** ADR-014 §3.5 — `"citation-only TSU" 서브타입 필요`

**현재 상태:** 미구현
- "citation-only TSU" 서브타입은 설계 단계
- `metadata_only`/`citation_only` 자료 관리를 위한 별도 TSU 타입 필요

---

## 8. Retrieval Compatibility

### 8.1 Source Weighting / Domain Filter / Authority Ranking

**설계 주장:** ADR-014 §3.5 — "NAE-PD를 1차 사료로 최우선 authority 유지, NAE-MODERN은 별도 가중치의 보조 트랙"

**현재 상태:** PASS (설계만, 코드 변경 없음 명시)
- `core/retrieval.py::RetrievalEngine` 무변경 — ADR-001/ADR-013 범위 유지
- 통합 검색(NAE-PD/NAE-MODERN/DBMA 단일 질의)은 후속 ADR 필요 (ADR-014 §5 Consequences에도 명시)

### 8.2 TSU 경로 충돌

**설계 주장:** ADR-014 §3.5 — "경로 충돌 주의: `DEFAULT_TSU_DATASET_PATH` 하드코딩 이슈"

**현재 상태:** 해결됨
- `scripts/build_tsu_dataset.py`에 `--dataset-path` CLI 인자 추가됨 (NAE_DATA_ARCHITECTURE.md §3 참조)
- 기본값은 기존 `output/bench/tsu_dataset.jsonl` 유지

---

## 9. Identified Risks

| 항목 | 평가 | 비고 |
|------|------|------|
| Architecture | WARNING | 디렉토리 rename(`archive_org/` → `public_domain/`) 미실시 |
| Metadata | WARNING | Schema 1.1.0 → 2.0.0 마이그레이션 필요 |
| TSU | PASS | Authority Model/Copyright 필드 이미 적용됨 |
| Retrieval | PASS | 코드 변경 없음 명시, ADR-001 침해 없음 |
| Copyright | PASS | 4개 필드 설계 적절, 실제 TSU에도 적용됨 |
| Future Expansion | WARNING | `source_validator.py` schema 2.0 확장 필요 |

---

## 10. Recommendations

1. **ADR-014 승격 조건:** `public_domain/` rename 및 `modern/` 디렉토리 생성 후 재검토 (ADR-014 §6 "Promotion Review"에도 "Implementation 완료 전 보류" 명시)
2. **Schema 마이그레이션:** 1.1.0 → 2.0.0 전환 계획 수립 — `scripts/source_validator.py` 확장 포함
3. **Citation-Only TSU:** 구현 우선순위 결정 — 현재 설계 단계
4. **Retrieval 통합:** NAE-PD/NAE-MODERN/DBMA 통합 검색 필요 시 별도 ADR로 RetrievalEngine 확장 검토 (ADR-014 §6 "Future Expansion"에도 명시)
5. **RAW 안전장치:** `check_raw_only_originals.py` 확장 또는 NAE 전용 스크립트 필요 (NAE_DATA_ARCHITECTURE.md §6 참조)

---

## 11. Final Verdict

### 판정: APPROVED WITH CONDITIONS

**조건:**
1. ADR-014: `public_domain/` rename 및 `modern/` 디렉토리 구현 후 승격
2. Schema 2.0.0 마이그레이션 계획 수립
3. `source_validator.py` schema 2.0 검증 지원 추가
4. Citation-Only TSU 서브타입 구현 우선순위 결정

---

## 12. Final Questions Answered

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**답:** 아니요 — 설계는 "Design Only" 상태로, 실제 코드/데이터를 변경하지 않았음. 다만 제안된 디렉토리 구조(`public_domain/`, `modern/`)가 아직 구현되지 않아 "Proposed" 상태 유지.

### Q2: ADR-014는 승인 가능한가?

**답:** 조건부 승인 — 디렉토리 구현 후 최종 승인. 현재 상태: `Proposed`(보류).

### Q3: ADR-015는 승인 가능한가?

**답:** 조건부 승인 — Lifecycle의 "Validation"/"Quality Gate" 단계 현재 Pipeline에 명시적 추가 필요. 현재 상태: `Proposed`(보류).

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**답:** YES — Schema 1.1.0 → 2.0.0 마이그레이션 필요. `scripts/source_validator.py` 확장도 필요.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**답:** 조건부 YES — Citation-Only TSU 서브타입 구현 우선순위 결정 후. 현재 Authority Model/Copyright 필드는 이미 TSU에 적용됨.

### Q6: Retrieval Architecture를 보호하고 있는가?

**답:** YES — ADR-014/ADR-015 모두 "RetrievalEngine 코드 변경 없음"을 명시. ADR-001 권한 침해 없음. 통합 검색은 후속 ADR로 분리.

---

## Appendix: Repository Structure Verification

### NAE Directory Tree
```
NAE/
├── benchmark/
│   ├── datasets/benchmark_v1.jsonl
│   └── ...
├── corpus/
│   ├── raw/
│   │   └── archive_org/        (→ public_domain/ rename 필요)
│   ├── tsu/                    (metadata_schema_version: "1.1.0")
│   └── ...
├── manifest/
└── pipeline/
```

### Key Files Status
| 파일 | 상태 | 비고 |
|------|------|------|
| `NAE/corpus/raw/archive_org/` | 존재 | `public_domain/` rename 필요 |
| `NAE/corpus/tsu/` | 존재 | TSU 생성됨, schema 1.1.0 적용 중 |
| `resources/theological_sources/baptist/source_manifest.yaml` | 존재 | schema_version 1.2 |
| `scripts/build_tsu_dataset.py` | 수정됨 | `--dataset-path` 옵션 추가 완료 |
| `core/retrieval.py` | 무변경 | ADR-001 권한 유지 |
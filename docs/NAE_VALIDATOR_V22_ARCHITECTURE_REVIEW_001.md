# NAE Validator v2.2 Implementation — Independent Architecture Review 001

**Project:** NAE-VALIDATOR-V22-REVIEW-001
**Date:** 2026-08-02
**Reviewer:** Independent Architecture Review (Cline)
**Scope:** `scripts/source_validator.py`, `tests/test_validator_v22.py`, `docs/NAE_VALIDATOR_V22_IMPLEMENTATION_REPORT_001.md`
**ADR Reference:** ADR-001, ADR-014, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019

---

## 1. Executive Summary

`scripts/source_validator.py`는 v1.2(NAE-PD), v2.1.x(NAE-MODERN), v2.2.x(NAE-MODERN + Periodical/Manifest) 세 트랙을 단일 도구로 통합한 검증기이다. 기존 v1.2/v2.1.x 로직을 손대지 않고 신규 v2.2.x 트랙을 추가했으며, `work_type` 기반 조건부 필드 규칙, 선택적 Authority Reference FK 검증(`--registry-path`), 선택적 Manifest Layer 필드 검증(opt-in)을 구현했다.

**전체 평가: APPROVED WITH CONDITIONS**

---

## 2. Reviewed Documents

| 문서 | 상태 |
|---|---|
| `scripts/source_validator.py` (511 라인) | 검토 완료 |
| `tests/test_validator_v22.py` (253 라인, 19 테스트) | 검토 완료 |
| `docs/NAE_VALIDATOR_V22_IMPLEMENTATION_REPORT_001.md` (204 라인) | 검토 완료 |
| ADR-001: Retrieval Engine Authority | 검토 완료 |
| ADR-014: NAE Modern Corpus Layer | 검토 완료 |
| ADR-015: NAE Corpus Ingestion Standard | 검토 완료 |
| ADR-016: NAE Metadata Authority Model Revision | 참조 완료 |
| ADR-017: NAE ID Governance Standard | 참조 완료 |
| ADR-018: NAE Periodical Authority Extension | 참조 완료 |
| ADR-019: NAE Corpus Manifest Layer | 검토 완료 |

---

## 3. Existing Architecture Compatibility

### 3.1 ADR-001 (Retrieval Engine Authority) — PASS

ADR-001은 `core/retrieval.py::RetrievalEngine`의 Retrieval Authority를 확정한다. Validator v2.2는 `scripts/` 하위 스크립트이며 Retrieval Pipeline에 직접 접근하지 않는다. **충돌 없음.**

### 3.2 ADR-014 (NAE Modern Corpus Layer) — PASS

ADR-014 §5 Consequences는 명시적으로 다음을 예측한다:
> "`resources/theological_sources/`는 NAE-PD(schema 1.2)와 NAE-MODERN(schema 2.0.0) manifest가 별도 스키마 버전으로 공존한다 — `scripts/source_validator.py`가 두 버전을 모두 검증하도록 확장하는 작업이 후속 필요"

이번 구현은 바로 이 "후속 필요" 작업을 수행했다. **ADR-014와 일치.**

### 3.3 ADR-015 (NAE Corpus Ingestion Standard) — PASS

ADR-015는 Lifecycle(Registration → Validation → Classification → Metadata → Quality Gate → TSU → Embedding → Index)을 정의한다. Validator v2.2의 `status` enum(`PREPARED`, `ACQUIRED`, `VERIFIED`, `INGESTED` 등)은 이 Lifecycle과 호환된다. **충돌 없음.**

### 3.4 ADR-016 (NAE Metadata Authority Model Revision) — PASS

ADR-016은 `author_id`, `work_id`, `edition_id` 등 Authority Reference 모델을 정의한다. Validator v2.2의 `_validate_authority_references()` 함수는 `--registry-path` 지정 시 이 FK 관계를 검증한다. **일치.**

### 3.5 ADR-018 (NAE Periodical Authority Extension) — PASS

ADR-018은 periodical 자료에 대한 `volume_id`, `issue_id` 조건부 규칙을 정의한다. Validator v2.2의 `_WORK_TYPE_FIELD_RULES["periodical"]`와 `_PERIODICAL_MIN_ONE_OF`는 이를 정확히 구현했다. **일치.**

### 3.6 ADR-019 (NAE Corpus Manifest Layer) — PASS

ADR-019 §3.3은 Manifest Layer의 필수 필드(`manifest_id`, `source_id`, `processing_status` 등)를 정의한다. Validator v2.2의 `_validate_manifest_fields()` 함수는 entry에 `manifest_id`가 있을 때만(opt-in) 이 필드들을 검증한다. **일치.**

---

## 4. ADR-014 Review

### 4.1 Domain Separation — PASS

ADR-014 §3.1은 세 영역 분리를 확정:
```
NAE-PD (Public Domain Corpus)      — 변경 없음
NAE-MODERN (Modern Research Layer) — 신설
DBMA (Personal Ministry Archive)   — 변경 없음
```

Validator v2.2는 `schema_version`으로 이 영역을 구분한다:
- `1.x` → NAE-PD (v1.2 검증, 무변경)
- `2.x >= 2.2` → NAE-MODERN (v2.2.x 검증, 신규)
- `2.x < 2.2` → NAE-MODERN (v2.1.x 검증, 기존 동작 유지)

**적절.**

### 4.2 Storage Architecture — PASS

ADR-014 §3.2는 디렉토리 구조를 제안(미생성):
```
NAE/corpus/raw/
├── public_domain/
└── modern/
```

Validator v2.2는 파일 시스템 구조에 직접 의존하지 않고 `schema_version`으로 트랙을 구분하므로, 디렉토리 rename과 무관하게 동작한다. **충돌 없음.**

### 4.3 Copyright Governance — PASS

ADR-014 §3.3은 4개 신규 필드(`source_type`, `copyright_status`, `usage_permission`, `access_control`)를 정의한다. Validator v2.2의 `_V2_ENUM_FIELDS`는 이 필드의 enum 값을 정확히 검증한다. **충분.**

---

## 5. ADR-015 Review

### 5.1 Lifecycle Compatibility — PASS

ADR-015 Lifecycle:
```
Registration → Validation → Classification → Metadata → Quality Gate → TSU → Embedding → Index
```

Validator v2.2의 `status` enum:
- `PREPARED`, `ACQUIRED`, `VERIFIED`, `INGESTED` — Lifecycle 단계와 매핑 가능
- `approved_for_acquisition`, `permission_required`, `verification_pending` — NAE-PD 전용 상태

**호환.**

### 5.2 Authority Model — PASS

ADR-015 §Authority Model은 `author_id`, `work_id`, `source_id` 구조를 정의한다. Validator v2.2의 `_validate_authority_references()`는 이 필드들의 FK 존재를 검증한다(선택적). **적절.**

### 5.3 Duplicate Policy — PASS

Validator v2.2는 전체 트리에서 `source_id` 중복을 검사한다(469-479 라인). ADR-015의 "삭제 금지 원칙"과 충돌하지 않는다(중복은 FAIL로 보고, 삭제 명령 아님). **일치.**

---

## 6. Metadata Compatibility

### 6.1 Schema Versioning — PASS

| 스키마 버전 | 트랙 | 필수 필드 | 조건부 규칙 |
|---|---|---|---|
| v1.2 | NAE-PD | `source_id`, `title`, `license`, `content_genre`, `status` | 없음 |
| v2.1.x | NAE-MODERN | `_V2_REQUIRED_FIELDS`(13개, `edition_id` 포함) | 없음 |
| v2.2.x | NAE-MODERN | `_V22_BASE_REQUIRED_FIELDS`(`edition_id` 제외) | `work_type` 기반 |

**기존 스키마 변경 없이 신규 트랙 추가만 수행. 호환.**

### 6.2 Migration Requirement — NONE

Validator v2.2는 기존 v1.2/v2.1.x 로직을 한 줄도 수정하지 않았다. **Migration 불필요.**

---

## 7. TSU Compatibility

### 7.1 TSU Pipeline Impact — PASS

Validator v2.2는 TSU Pipeline에 직접 접근하지 않는다. 검증 결과만 생성하고, TSU 빌더는 검증 통과 여부를 별도 mechanism으로 읽는다. **충돌 없음.**

### 7.2 Citation-Only TSU — NOT IMPLEMENTED (DESIGNED)

ADR-014 §3.5는 "citation-only TSU 서브타입" 필요성을 언급한다. Validator v2.2는 이를 구현하지 않았으나(범위 밖), `status` 값으로 `metadata_only`/`citation_only` 자료를 구분할 기반은 제공한다. **적절.**

---

## 8. Retrieval Compatibility

### 8.1 RetrievalEngine Impact — PASS

ADR-001/ADR-014는 RetrievalEngine 코드 변경을 금지한다. Validator v2.2는 RetrievalPipeline에 접근하지 않는다. **충돌 없음.**

### 8.2 Source Weighting — NOT AFFECTED

Validator v2.2는 source의 weighting/scoring을 변경하지 않는다. 검증 통과 여부만 판단한다. **적절.**

---

## 9. Identified Risks

| # | 레벨 | 리스크 | 설명 |
|---|---|---|---|
| 1 | WARNING | `collection` work_type 규칙이 문서화되지 않은 가정 | Application Report에서 `collection`을 `multi_volume`과 동일하게 취급 — 실제 Collection 자료 적용 전 재검토 필요 (§3.5 Remaining Risks #1) |
| 2 | WARNING | Validator Boundary Design-001의 "3-도구 분리"안과 실제 구현 불일치 | 단일 파일 통합으로 구현 — 향후 Registry/Manifest 데이터 생성 시 분리가 필요한지 재검토 필요 (§3.5 Remaining Risks #3) |
| 3 | WARNING | `processing_status` 역행 검사 미구현 | Lifecycle enforcement가 필요해지면 별도 작업 필요 (§3.5 Remaining Risks #4) |
| 4 | WARNING | Registry FK 검증이 아직 자동화 연결 안 됨 | `--registry-path` 옵션 플래그만 존재, 기본 실행에는 영향 없음 (§3.5 Remaining Risks #5) |
| 5 | PASS | Architecture 충돌 | ADR-001/014/015/016/018/019 모두와 호환 |
| 6 | PASS | Metadata Layer 구축 전 수정 필요 문제 | 없음 — 기존 스키마 변경 없이 신규 트랙 추가만 수행 |
| 7 | PASS | TSU Pipeline 진입 장애 | 없음 — Validator는 TSU에 직접 접근하지 않음 |
| 8 | PASS | Retrieval Architecture 보호 | RetrievalEngine 코드 변경 없음 |

---

## 10. Recommendations

1. **`collection` work_type 규칙 재검토**: 실제 Collection 자료(예: `early_baptist_collection`)가 생성되는 시점에 적용 전 `work_type` 규칙이 적절한지 확인하라.
2. **Validator Boundary Design 재검토**: Registry/Manifest 데이터가 실제로 생성되는 시점에 3-도구 분리가 필요한지 평가하라.
3. **Registry FK 검증 자동화 연결**: CI/자동 파이프라인에 `--registry-path` 옵션 연결을 고려하라.
4. **`processing_status` 역행 검사 후속 구현**: Manifest Layer 실 데이터가 생기는 시점에 lifecycle enforcement 로직을 추가하라.

---

## 11. Final Verdict

### 판정: APPROVED WITH CONDITIONS

```
STATUS: APPROVED WITH CONDITIONS
BLOCKERS: 없음
WARNINGS: 4건 (§9 참조)
ARCHITECTURE IMPACT: 없음 — 기존 ADR 모두와 호환
MIGRATION READINESS: BLOCKED (Metadata Migration 별도 승인 필요, Validator 구현 완료 아님)
TSU READINESS: READY (Validator는 TSU Pipeline과 독립적)
```

---

## 12. Final Answers to Review Questions

### Q1. CUE 설계가 현재 NAE 구조와 충돌하는가?
**아니오.** ADR-001/014/015/016/018/019 모두와 호환된다.

### Q2. ADR-014는 승인 가능한가?
**예.** 설계 문서이므로 코드 변경 없음. Validator v2.2 구현은 ADR-014 §5 "후속 필요" 작업을 수행한 것이다.

### Q3. ADR-015는 승인 가능한가?
**예.** Lifecycle, Authority Model, Duplicate Policy 모두 호환된다.

### Q4. Metadata Layer 구축 전에 수정해야 할 문제가 있는가?
**아니오.** 기존 스키마 변경 없이 신규 트랙 추가만 수행했다.

### Q5. TSU Pipeline으로 넘어가도 되는가?
**예.** Validator는 TSU Pipeline과 독립적이다. 단, Metadata Migration/Manifest Pilot은 별도 승인 필요.

### Q6. Retrieval Architecture를 보호하고 있는가?
**예.** RetrievalEngine 코드 변경 없음. ADR-001/ADR-013 범위 유지.

---

*이 검토는 Read-Only 원칙 하에 수행되었다. 파일 수정, 코드 수정, Schema 변경, Manifest 수정, Directory 생성, 자료 이동, TSU 생성, Embedding 생성, Git Commit, Git Push는 수행하지 않았다.*
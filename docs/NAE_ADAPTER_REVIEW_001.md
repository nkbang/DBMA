# NAE Adapter Review 001 — C1 Architecture Review

**Task:** `NAE-ADAPTER-REVIEW-001`
**작성일:** 2026-08-05
**성격:** Review Only (코드 수정/Git 금지)
**검토 대상:**
```
scripts/adapters/registry_adapter.py
scripts/adapters/manifest_adapter.py
tests/test_comment_preservation.py
docs/NAE_ADAPTER_REFACTOR_IMPLEMENTATION_REPORT_001.md
requirements.txt
```

---

## 1. Executive Summary

`ruamel.yaml` 기반 Adapter Refactor(NAE-ADAPTER-REFACTOR-001)가
ADR-016~019, Migration Engine, Registry, Manifest, Validator,
Option B ID Governance, Architecture Freeze Rule과 **충돌하지 않는다**.

이 리팩터의 유일한 목적은 PyYAML `safe_load`/`safe_dump`가 일으킨
**Comment/Quote/Ordering/Whitespace 손실 결함**을 `ruamel.yaml`
round-trip(`typ="rt"`)으로 해결하는 것이다 — Migration Engine,
Validator, Registry 구조, Manifest lifecycle, ADR 정책 중 어느 것도
변경하지 않았다.

---

## 2. Reviewed Documents

| 문서 | 상태 |
|---|---|
| `scripts/adapters/registry_adapter.py` (237 라인) | ✅ 검토 완료 |
| `scripts/adapters/manifest_adapter.py` (188 라인) | ✅ 검토 완료 |
| `tests/test_comment_preservation.py` (323 라인, 14 테스트) | ✅ 검토 완료 |
| `docs/NAE_ADAPTER_REFACTOR_IMPLEMENTATION_REPORT_001.md` (199 라인) | ✅ 검토 완료 |
| `requirements.txt` (29 라인) | ✅ 검토 완료 |

---

## 3. Existing Architecture Compatibility

### 3.1 Migration Engine 호환성

Migration Engine(`scripts/migration_engine.py`) 코드를 **한 줄도 수정하지 않았다**.
Adapter의 `transform` 함수 시그니처(`dict[str,str] -> dict[str,str]`)가
변경되지 않았으므로, Engine 입장에서는 "직렬화 백엔드가 바뀐 것"以外에
아무 변화가 없다.

**검증 결과:**
- `MigrationUnit` 인터페이스: 불변
- `MigrationEngine.execute()`: 불변
- Checkpoint/Rollback/Idempotency: 불변
- Engine 코드 diff: 없음

### 3.2 Registry Adapter — Option B ID Governance

Registry Adapter(`registry_adapter.py`)의 동작을 검토한 결과:

1. **canonical_id backfill**: 호출자가 제공한 `canonical_id_map`만 적용
   - Adapter가 ID를 스스로 추론하지 않음(ADR-017 Option B 준수)
   - `CANONICAL_ID_RE`로 lowercase snake_case 검증
2. **legacy_id backfill**: 호출자가 제공한 `legacy_id_map`만 적용
3. **기존 ID 필드 불변**: `author_id`, `work_id` 등 FK 문자열을 절대 건드리지 않음
4. **필드 배치**: `canonical_id`를 `id_field` 바로 다음에 삽입(가독성)

**Option B 보존:** 기존 ID 필드(`author_id: FULLER-ANDREW-001` 등)가
절대 변경되지 않으므로, Manifest/Registry 간 FK 참조 관계가 무너지지 않는다.

### 3.3 Manifest Adapter — TSU Gate 보호

Manifest Adapter(`manifest_adapter.py`)의 동작을 검토한 결과:

1. **`build_touch_unit`**: `updated_at` Audit 필드만 갱신
   - FK 필드(`author_id`, `work_id`, `edition_id`, `volume_id`, `source_id`)를
     다루지 않음(코드에 FK 키가 일절 없음)
   - `processing_status`, `tsu_status`, `embedding_status` 등 Lifecycle 필드 불변
2. **`verify_fk`**: 읽기 전용 검증 함수
   - Registry index 대조 후 결과 반환만 함
   - Manifest 파일을 수정하지 않음

**TSU Gate 안전:** `updated_at`만 갱신하므로 TSU Eligibility 판단에
영향이 없다. `tsu_status`, `processing_status`가 변경되지 않기 때문이다.

---

## 4. ADR-014 Review (참고)

ADR-014는 Corpus Layer 분리(NAE-PD/NAE-MODERN/DBMA)를 정의한다.
이번 Adapter Refactor는 Registry/Manifest YAML 직렬화에 국한되므로
ADR-014와 무관하다.

**판정:** PASS (영향 없음)

---

## 5. ADR-015 Review (참고)

ADR-015는 Corpus Ingestion Standard를 정의한다. 이번 Adapter Refactor는
Ingestion Pipeline이 아니므로 영향이 없다.

**판정:** PASS (영향 없음)

---

## 6. Metadata Compatibility

### 6.1 Schema 변경 없이 구현 가능한가?

예. `ruamel.yaml` round-trip은 YAML 구조를 변경하지 않는다 — 노드를
그 자리에서 수정(`insert`, 값 교체)할 뿐 재구성하지 않는다.

### 6.2 Migration 필요한가?

아니요. `ruamel.yaml`은 기존 PyYAML 파일과 호환되는 직렬화 엔진이다.
파일 포맷 변경이 필요하지 않다.

### 6.3 Versioning 방식 적절한가?

예. `schema_version` 필드는 Adapter가 건드리지 않으며, 원본 값을
그대로 보존한다.

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조와의 충돌

없음. Adapter는 Registry/Manifest YAML만 다루며, TSU Dataset 빌더나
Chunking Pipeline을 수정하지 않는다.

### 7.2 Full TSU / Restricted TSU / Citation Only TSU

이들 TSU 타입은 Manifest의 `tsu_status` 필드로 관리되는데,
Adapter가 이 필드를 변경하지 않으므로 모든 TSU 타입이 그대로 유지된다.

---

## 8. Retrieval Compatibility

### 8.1 RetrievalEngine 영향

없음. Adapter는 Registry/Manifest YAML 파일만 읽고 쓰며,
`core/retrieval.py::RetrievalEngine`에 영향을 주지 않는다.

### 8.2 Source weighting / Domain filter / Authority ranking

이들 기능은 Registry의 canonical_id 값을 참조하지만, Adapter가
canonical_id 값을 "생성"하는 것이 아니라 "적용"할 뿐이므로
기존 값과 동일한 문자열만写入된다. 따라서 Retrieval의
Source weighting/Domain filter/Authority ranking에 변화가 없다.

### 8.3 Embedding / Index

Adapter가 Embedding이나 Index를 생성/수정하지 않으므로 영향이 없다.

---

## 9. Identified Risks

| 항목 | 평가 | 근거 |
|---|---|---|
| Architecture | ✅ PASS | Engine/Validator/ADR 무변경 |
| Metadata | ✅ PASS | Schema 변경 없음, round-trip 호환 |
| TSU | ✅ PASS | TSU 필드 미수정 |
| Retrieval | ✅ PASS | RetrievalEngine 영향 없음 |
| Copyright | ✅ PASS | `copyright_status` 미접촉 |
| Future Expansion | ✅ PASS | Serializer는 document-type agnostic |

---

## 10. Recommendations

### 10.1 Pilot Migration Dry Run 승인

현재 구현은 다음 조건을 모두 만족하므로 **Pilot Migration Dry Run**으로
진행할 수 있다:

- Comment Preservation: ✅ 14 테스트 전부 PASS
- Regression: ✅ 149 테스트 PASS (drift 0)
- Production 데이터 변경: ❌ 없음
- Git Commit: ⏸ 미수행 (대기 중)

### 10.2 조건부 승인 사항

Pilot Migration Dry Run 시 다음을 확인하라:

1. **실 Production Registry**에서 canonical_id backfill 실행 전
   `git diff`로 canonical_id만 추가되었는지 확인
2. **실 Pilot Manifest**에서 `updated_at` 갱신 후
   `git diff`로 updated_at 한 줄만 변경되었는지 확인
3. **Validator 재실행**으로 drift 0 재확인

---

## 11. Final Verdict

```
APPROVED WITH CONDITIONS
```

### 조건:

Pilot Migration Dry Run 시 다음을 준수하라:

1. `git diff`로 변경 범위가 canonical_id/updated_at에만 국한되는지 확인
2. Validator 재실행으로 drift 0 확인
3. Rollback 테스트 통과 확인 (이미 `test_comment_preservation.py::TestRollback`에서 검증됨)

---

## Required Questions — Answers

### Q1. 현재 구현이 ADR-016~019와 충돌하는가?

**아니요.** ADR-016(5-tier 모델), ADR-017(canonical_id/legacy_id),
ADR-018(Migration Engine), ADR-019(Manifest) 중 어느 것도 변경하지
않았다. 직렬화 백엔드만 바꿨을 뿐이다.

### Q2. Registry Adapter가 Option B를 보존하는가?

**예.** 기존 ID 필드(`author_id`, `work_id` 등)를 절대 건드리지
않고, 신규 필드(`canonical_id`, `legacy_id`)만 추가한다.

### Q3. Manifest Adapter가 TSU Gate를 손상시키는가?

**아니요.** `updated_at` Audit 필드만 갱신하며, `tsu_status`,
`processing_status` 등 Lifecycle 필드를 변경하지 않는다.

### Q4. Comment Preservation 구현은 Production 적용 가능한가?

**예.** `ruamel.yaml` round-trip은 주석/따옴표/들여쓰기/키 순서/빈 줄을
모두 보존하며, 14개의 테스트로 검증되었다.

### Q5. Migration Engine을 Pilot Migration으로 진행해도 되는가?

**조건부 예.** Pilot Migration Dry Run 시 `git diff`로 변경 범위를
확인하고 Validator 재실행으로 drift 0을 확인하라.

### Q6. Retrieval Architecture는 완전히 보호되는가?

**예.** Adapter는 Registry/Manifest YAML만 다루며, RetrievalEngine,
Embedding, TSU, Index에 영향을 주지 않는다.

---

## 판정 근거 요약

| 항목 | 결과 |
|---|---|
| ADR-016~019 충돌 | ❌ 없음 |
| Option B 보존 | ✅ |
| TSU Gate 안전 | ✅ |
| Comment Preservation | ✅ (14 테스트 PASS) |
| Regression | ✅ (149 테스트 PASS, drift 0) |
| Production 데이터 변경 | ❌ 없음 |
| Retrieval 보호 | ✅ |
| Copyright 보호 | ✅ |
| Future Modern Corpus 호환 | ✅ |

**최종 판정: APPROVED WITH CONDITIONS**

Pilot Migration Dry Run으로 진행 가능하되, 조건(§10.2)을 준수하라.
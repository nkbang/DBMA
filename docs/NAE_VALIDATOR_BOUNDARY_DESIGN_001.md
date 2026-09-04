# NAE Validator Boundary Design 001

작성일: 2026-08-02
Project: NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001 Phase 5
성격: **설계 문서 — 코드 미작성/미수정**
근거: [`NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md`](NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md),
[`NAE_AUTHORITY_REGISTRY_DESIGN_v1.md`](NAE_AUTHORITY_REGISTRY_DESIGN_v1.md) §Phase5

---

## 1. 현재 상태(실측)

| 도구 | 상태 | 검증 대상 |
|---|---|---|
| `scripts/source_validator.py` | **구현됨**, 동일 세션에서 코드 미수정 유지 | corpus manifest(`source_manifest.yaml`) — 필수 필드/enum 값/`source_id` 중복 |
| `scripts/authority_validator.py`(가칭) | **설계만**(Registry Design v1 §Phase5), 코드 없음 | Authority Registry(`authority/*.yaml`) — Reference Integrity/Duplicate/Schema |
| `scripts/manifest_validator.py`(가칭) | **이번 문서에서 설계**, 코드 없음 | Manifest Entry — 아래 §3 |

---

## 2. 결정: 3번째 도구 필요

**필요함.** 기존 두 도구는 각각 corpus manifest와 Registry를 대상으로
하며 어느 쪽도 "processing_status의 상태 전이가 올바른가",
"Manifest Entry와 Source가 정확히 1:1인가"를 검증할 책임을 지지
않는다 — 이 두 질문은 Manifest Entry 고유의 관심사(ADR-019)다.

---

## 3. 책임 범위(중복 방지)

| 검증 항목 | 담당 도구 | 이유 |
|---|---|---|
| corpus manifest 필수 필드(`title`/`category`/`copyright_status` 등) | `source_validator.py`(기존) | 변경 없음 |
| Registry FK(author_id→authors, work_id→works 등) | `authority_validator.py`(설계만) | 변경 없음 |
| **Manifest:Source 1:1 무결성**(중복 Manifest Entry 없음, 모든 Source가 최대 1개 Manifest만 가짐) | **`manifest_validator.py`(신규)** | ADR-019 고유 규칙 — 다른 두 도구의 책임이 아님 |
| **`processing_status` 전이 유효성**(단조 증가, 허용되지 않는 건너뛰기 없음) | **`manifest_validator.py`(신규)** | 동일 |
| **`edition_id`/`volume_id`/`issue_id` 조건부 규칙**(Manifest Schema Design §Phase3 표) | **`manifest_validator.py`(신규)** | Registry 레벨이 아니라 Manifest 레벤텔의 재확인 — `authority_validator.py`가 Registry 레벨에서 이미 검사하더라도, Manifest는 자신의 비정규화 복사값이 Registry와 **일치하는지**(sync 여부)도 확인해야 함(Registry Design v1 §Phase1 "비정규화 복사값" 설계와 연동) |
| TSU 필수 필드 게이트(`copyright_status≠unknown` 등) | **`manifest_validator.py`(신규)** | `processing_status=TSU_ELIGIBLE` 판정 로직 자체가 이 도구의 핵심 역할 |

**중복 방지 원칙**: `manifest_validator.py`는 corpus manifest의 필수
필드나 Registry의 FK를 **재검사하지 않는다** — 그건 이미 다른 두
도구의 책임이다. 대신 Manifest가 Registry/corpus manifest 값을
비정규화 복사한 것이 **원본과 일치하는지**만 sync 검사로 확인한다
(불일치 시 FAIL — "Manifest가 최신 Registry 상태를 반영하지 못함").

---

## 4. 실행 순서 제안(구현 시, 이번 설계 범위 밖)

```
source_validator.py     (corpus manifest 검증)
        ↓
authority_validator.py  (Registry 검증)
        ↓
manifest_validator.py   (Manifest Entry 검증 — 위 두 도구 통과 전제)
```

세 도구는 순차 실행을 권장하되, 강제 의존성(하나가 실패하면 다음이
실행 안 됨)으로 만들지 결정하는 것은 구현 단계 과제(Remaining
Risk로 기록).

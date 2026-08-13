# NAE Human Review Disposition Schema v1 (Design Only)

작성일: 2026-08-13
성격: Architecture/Governance 설계 — 776건 실제 판정, TSU 원본 수정,
Production/Qdrant 변경, ADR-021 pipeline 수정 전부 수행하지 않음.
선행 검토: `docs/NAE_TSU_REVIEW_WORKFLOW_DESIGN_001.md`(2026-08-07),
`docs/NAE_TSU_4107_EXPANSION_HUMAN_REVIEW_DESIGN_001.md`(2026-08-09),
`NAE/pipeline/tsu/review_gate.py`, `NAE/pipeline/tsu/review_promotion.py`,
`NAE/review/human/schema.py`(`MAX_PENDING_REVIEW=100`, 변경하지 않음).

---

## 0. 기존 구조와의 관계 (반드시 먼저 확인)

기존 `review_promotion.py::promote_tsu_to_verified()`는 TSU 레코드의
`review_status`/`review_metadata` 두 필드를 **직접** 갱신한다(원본
`claim`/`doctrine`/`scriptures`/`citations`/`confidence`/
`extraction_method`/`model`/`id`는 건드리지 않지만, `review_status`
자체는 TSU 레코드의 필드다). 이는 이번 설계의 "원본 TSU를 변경하지
않는 append-only disposition layer" 원칙과 표면적으로 달라 보이지만
실제로는 **레이어가 다르다**:

```
Human Review Disposition Record (본 설계, 신규 append-only store)
   │  — 사람의 판정·근거·evidence·adjudication을 기록
   │  — TSU 레코드를 전혀 건드리지 않음
   ▼
FINALIZED disposition (ACCEPT / ACCEPT_WITH_CORRECTION)
   │
   ▼
Admission Decision (기존 review_promotion.py, 무수정 — §11 참고)
   │  — FINALIZED disposition을 입력으로 review_promotion.py를 호출
   │  — 이 호출이 비로소 TSU 레코드의 review_status를 "verified"로 승격
   ▼
Production TSU review_status="verified"
```

즉 본 설계는 `review_promotion.py`를 **대체하지 않고 그 앞단**에
독립적인 기록 계층을 추가한다. `review_promotion.py`의 승격 함수는
이번 설계에서 무수정 — 그 함수가 요구하는 `reviewer`/`review_date`/
`review_decision="approved"`는 FINALIZED disposition record에서
파생시켜 호출하는 것으로 설계한다(§11 Admission 절 참고, 실제 배선은
이번 단계 범위 밖).

---

## 1. Disposition Taxonomy

### 1.1 Disposition (판정 결과)

| Disposition | 의미 | Lifecycle |
|---|---|---|
| `ACCEPT` | 원문 그대로 승인 — 수정 불필요 | 바로 FINALIZED 진입 가능(단독 리뷰 시) |
| `ACCEPT_WITH_CORRECTION` | 승인하되 correction payload 동반(§4) | correction 필수, FINALIZED는 correction 검증 후 |
| `NEEDS_REVIEW` | 판정 보류 — 추가 정보/2차 검토 필요 | 종결 아님, 재검토 큐로 회귀 |
| `REJECT` | 반려 — Production 승격 대상에서 제외 | FINALIZED 진입 가능(반려 확정), TSU는 `generated` 또는 신규 `rejected_by_review` 상태로 유지(TSU 레코드 자체는 무수정 — Disposition record만으로 반려 사실을 표현) |
| `DUPLICATE_MERGE` | 다른 tsu_id와 내용 중복 — 병합 대상 | `merged_into_tsu_id` 필수(§6 스키마), 병합 실행은 이번 설계 범위 밖 |

추가 상태가 필요할 경우의 예시(채택 여부는 실제 리뷰 착수 전 별도
결정): `ESCALATE`(reviewer 권한 밖 판단 필요 — 신학적 권위 있는
제3자 확인 필요한 경우, Adjudication과는 다름 — Adjudication은
"두 reviewer 간 불일치", Escalate는 "단독 reviewer가 판단 불가"). 본
설계는 `ESCALATE`를 정의만 하고 초기 구현 대상에서는 제외한다(§13
Acceptance Criteria #7과 구분).

### 1.2 Review Reason (판정 사유 — Disposition과 독립된 축)

```
CONTENT_VALIDITY    — 클레임 자체의 신학적 타당성 문제
METADATA             — author_id/work_id/edition_id/doctrine 등 메타데이터 오류
EXTRACTION           — OCR/추출 단계 오류가 클레임에 반영됨
CHUNK_BOUNDARY        — 문장/문단 경계 절단으로 의미 손상
DUPLICATION           — 다른 TSU와 중복(DUPLICATE_MERGE와 연동)
SOURCE_AUTHORITY      — 원문 자체의 권위/신뢰도 문제(예: 오탈자 많은 판본)
COPYRIGHT             — 저작권/access_control 재확인 필요
OTHER                 — 위 항목에 없는 사유(review_note 필수)
```

하나의 disposition record는 `reason_code` 1개 이상을 배열로 가질 수
있다(예: `ACCEPT_WITH_CORRECTION` + `[EXTRACTION, CHUNK_BOUNDARY]`).
Disposition과 Reason을 분리하는 이유: 동일 reason이 서로 다른
disposition으로 귀결될 수 있다(예: `EXTRACTION` 문제가 경미하면
`ACCEPT_WITH_CORRECTION`, 심각하면 `REJECT`) — reason만으로 결과를
예단하지 않기 위함.

---

## 2. State Machine

```
UNREVIEWED
   │  reviewer가 큐에서 항목을 가져감(assign)
   ▼
IN_REVIEW
   │  reviewer가 disposition을 기록
   ▼
DISPOSITIONED  (ACCEPT | ACCEPT_WITH_CORRECTION | NEEDS_REVIEW | REJECT | DUPLICATE_MERGE)
   │
   ├─ NEEDS_REVIEW인 경우 ──────────────────► UNREVIEWED로 회귀(재큐잉)
   │
   ├─ 단독 reviewer 결과에 이견 없음 ───────► FINALIZED
   │
   └─ 2인 이상 reviewer 결과 불일치 발견 ───► ADJUDICATION_REQUIRED
                                                   │
                                                   │ adjudicator가 최종 판정
                                                   ▼
                                              FINALIZED
```

### 2.1 상태 전환 주체 및 허용 조건

| 전환 | 주체 | 허용 조건 |
|---|---|---|
| `UNREVIEWED → IN_REVIEW` | Queue 배정 로직(사람 또는 배정 스크립트) | `assigned_reviewer` 설정, `MAX_PENDING_REVIEW=100` 게이트 준수(기존 `schema.py`, 변경 없음) |
| `IN_REVIEW → DISPOSITIONED` | `reviewer_id`가 일치하는 사람만 | disposition + reason_code + reviewed_at 필수(§6) |
| `DISPOSITIONED(NEEDS_REVIEW) → UNREVIEWED` | 시스템(자동 회귀) | review_note에 보류 사유 필수 |
| `DISPOSITIONED → ADJUDICATION_REQUIRED` | 시스템(자동 감지 — 동일 tsu_id에 상충하는 disposition 2건 이상 존재 시) | 상충 정의: disposition 값이 다르거나, 같은 disposition이라도 reason_code가 상충 |
| `DISPOSITIONED → FINALIZED` | 시스템(단독 reviewer, 상충 없음 확인 후 자동) | 상충 없음 |
| `ADJUDICATION_REQUIRED → FINALIZED` | `adjudicator_id`가 설정된 사람만 | `final_disposition` 필수(§8) |

**중요**: `FINALIZED`는 이 설계 문서의 lifecycle 종착점이며, TSU
레코드의 `review_status` 변경(Admission)은 여기서 발생하지 않는다
— §0/§11 참고, FINALIZED 이후 별도 Admission 단계가 필요하다.

---

## 3. Disposition Record Schema

| 필드 | required/optional | immutable/mutable | 타입 | provenance 요구사항 |
|---|---|---|---|---|
| `review_id` | required | immutable | string(신규 발급, 형식: `REVIEW-{tsu_id}-{seq}`) | 생성 시점에 유일성 검사 |
| `tsu_id` | required | immutable | string(기존 TSU `id` 필드 참조) | Production TSU에 실재해야 함(참조 무결성) |
| `source_id` | required | immutable | string | TSU 레코드에서 파생(중복 저장이지만 조회 편의상 포함 — 원본은 항상 tsu_id를 통해 재확인 가능) |
| `work_id` | required | immutable | string | 〃 |
| `edition_id` | required | immutable | string | 〃 |
| `review_status` | required | mutable(상태 전환 시에만) | enum(§2 상태 값) | 상태 전환 규칙(§2.1) 준수 |
| `disposition` | required(IN_REVIEW 이후) | **append-only**(값 변경 시 새 record 생성, §11 supersedes 참고) | enum(§1.1) | reviewer 판정 |
| `reason_code` | required(disposition 존재 시) | append-only | array[enum](§1.2) | 최소 1개 |
| `reviewer_id` | required(IN_REVIEW 이후) | immutable(해당 record 내에서) | string | 실존 reviewer 식별자(별도 reviewer registry는 범위 밖 — 최소 문자열 ID) |
| `reviewed_at` | required(disposition 존재 시) | immutable | ISO8601 timestamp | — |
| `review_note` | optional(단, `reason_code=OTHER`면 required) | append-only(새 record) | free text | — |
| `correction_payload` | required(disposition=ACCEPT_WITH_CORRECTION) | append-only | object(§4) | — |
| `evidence_refs` | required(disposition 존재 시) | append-only | array[reference](§9) | 최소 1개 |
| `previous_disposition` | optional | immutable | string(이전 record의 disposition 값) | 재판정(re-review) 시에만 설정 |
| `supersedes_review_id` | optional | immutable | string(review_id 참조) | 이전 record를 대체하는 경우 필수 — 이전 record는 삭제하지 않고 그대로 보존(append-only 원칙, §11) |
| `merged_into_tsu_id` | disposition=DUPLICATE_MERGE 시 required | immutable | string(tsu_id 참조) | 병합 대상 tsu_id 실재 확인 |
| `adjudication_status` | optional | mutable | enum(`NOT_REQUIRED`/`PENDING`/`RESOLVED`) | §2 상태 전환과 동기화 |
| `adjudicator_id` | ADJUDICATION_REQUIRED 이후 required | immutable | string | — |
| `adjudicated_at` | 〃 | immutable | ISO8601 timestamp | — |
| `final_disposition` | 〃 | immutable | enum(§1.1) | adjudicator의 최종 판정 — 원 reviewer들의 disposition은 삭제되지 않고 각자의 record로 보존 |
| `schema_version` | required | immutable | string(`"1.0.0"`) | 이 문서 버전과 동기화 |
| `created_at` | required | immutable | ISO8601 timestamp | record 생성 시각(reviewed_at과 다름 — created_at은 UNREVIEWED→IN_REVIEW 배정 시점일 수 있음) |

**Append-only 원칙 적용 방식**: "mutable" 필드는 없다. 판정이
바뀌면(예: 재검토 결과 disposition이 달라짐) **새 review_id로 신규
record를 생성**하고, `previous_disposition`+`supersedes_review_id`로
이전 record와 연결한다. 이전 record는 절대 삭제·수정하지 않는다 —
`review_status`(record 자체의 UNREVIEWED~FINALIZED 상태)만 시스템이
갱신할 수 있는 유일한 mutable 유사 필드이며, 이마저도 상태 전이
이력을 별도 provenance log(§11 Governance 문서 참고)에 남긴다.

---

## 4. Correction Model

`ACCEPT_WITH_CORRECTION`은 원본 TSU 필드를 직접 수정하지 않는다.
Correction은 disposition record에 종속된 structured payload로만
존재한다.

```yaml
correction_payload:
  - correction_type: string   # 예: "doctrine_reclassification", "scripture_reference_fix", "claim_text_edit"
    field: string              # 원본 TSU의 어느 필드에 대한 correction 제안인지 (예: "doctrine", "scriptures")
    original_value: string     # TSU 레코드의 현재 값(참조 시점 스냅샷 — TSU 원본은 변경되지 않으므로 이 값은 그대로 유효한 대조 기준)
    corrected_value: string    # reviewer가 제안하는 값
    correction_reason: string  # 필수 — reason_code와 별개로 이 필드 단위 수정의 구체적 이유
    evidence_ref: reference    # §9 evidence model 참조
```

Correction은 **제안**이며, 실제 TSU 필드 갱신 여부/방식은 Admission
단계(§0, §11)의 별도 결정 사항이다 — 이 스키마는 "무엇을 어떻게
고치자고 제안했는지"의 기록만 담당한다.

---

## 5. 관련 문서

- `docs/NAE_HUMAN_REVIEW_WORKFLOW_v1.md` — Queue/Adjudication 워크플로우
- `docs/NAE_HUMAN_REVIEW_GOVERNANCE_v1.md` — Auditability, 기존 구조와의
  경계, Acceptance Criteria 응답
- `docs/schemas/nae_human_review_disposition.schema.json` — JSON Schema 초안

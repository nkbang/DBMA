# NAE Human Review Workflow v1 (Design Only)

작성일: 2026-08-13
성격: Architecture/Governance 설계 — 776건 실제 판정, TSU 원본 수정,
Production/Qdrant 변경 전부 수행하지 않음.
전제: `docs/NAE_HUMAN_REVIEW_DISPOSITION_SCHEMA_v1.md`의 taxonomy/state
machine/record schema를 그대로 사용.

---

## 1. 대상 규모

```
776건 = Dagg 397 + Hiscox 379 (review_status=generated)
```

기존 `NAE/review/human/schema.py::MAX_PENDING_REVIEW=100`(변경하지
않음)이 "한 번에 IN_REVIEW 상태로 둘 수 있는 최대 건수"를 제한한다
— 이번 워크플로우도 이 제약을 그대로 따른다. 즉 776건 전체를 한
배치로 열지 않고, 최대 100건 단위로 큐를 연다.

## 2. Review Queue Model

```
queue_id            — 배치 식별자(예: HR-BATCH-0001), 개별 리뷰 항목이 아님
tsu_id               — Disposition Schema §3과 동일
priority             — §3 참고, 실제 부여는 이번 단계 범위 밖
review_status        — Disposition Schema §2 상태 값(UNREVIEWED 등)
assigned_reviewer    — reviewer_id, UNREVIEWED 상태에서는 null
source_category      — TSU의 doctrine/author_id 등에서 파생(예: "Dagg/Ecclesiology")
risk_level           — §3 참고
created_at           — 큐 진입 시각
```

Queue 자체는 disposition record의 **뷰(view)**다 — 별도의 진실
소스가 아니다. `review_status=UNREVIEWED`인 disposition record(또는
아직 record가 없는 776건 각각에 대한 잠재적 record)를 모아 보여주는
것이 Queue의 역할이며, Queue 테이블 자체에 판정 결과를 쓰지 않는다.

### 2.1 Priority 설계(부여는 이번 범위 밖)

우선순위 후보 기준(실제 값 산정은 별도 작업):
- **source_category 기반**: `NAE_TSU_4107_EXPANSION_HUMAN_REVIEW_DESIGN_001.md`가
  이미 실측한 doctrine 분포(Ecclesiology+Baptism이 72%)를 참고해,
  분포가 큰 doctrine부터 우선 처리하거나, 반대로 희소 doctrine(예:
  Church Covenant 7건, Confession 9건)을 먼저 처리해 조기에 taxonomy
  커버리지를 확보하는 두 가지 전략이 모두 가능 — 어느 쪽을 택할지는
  이번 설계 범위 밖.
- **risk_level 기반**: `confidence`(TSU 레코드 기존 필드, LLM 추출
  신뢰도) 낮은 순으로 우선 검토하는 전략.

두 기준 모두 "설계"만 하고 776건에 실제 값을 매기지 않는다 — 작업
명령서 §10과 일치.

## 3. Batch Review 절차

```
1. Batch 생성: 최대 100건(MAX_PENDING_REVIEW 준수)을 queue_id로 묶음
2. 배정: reviewer_id를 각 tsu_id에 assign → disposition record 생성
   (review_status=UNREVIEWED → IN_REVIEW 전환, §2 State Machine)
3. 개별 판정: reviewer가 disposition + reason_code + evidence_refs 기록
   → review_status=DISPOSITIONED
4. 상충 검사(시스템 자동): 동일 tsu_id에 상충하는 record가 있는지 확인
   - 없음 → FINALIZED
   - 있음 → ADJUDICATION_REQUIRED(§4)
5. Batch 종료 조건: batch 내 모든 tsu_id가 FINALIZED 또는
   NEEDS_REVIEW(재큐잉 대상)로 귀결
6. 다음 Batch 생성(남은 건수가 있으면 반복)
```

Batch 크기를 100건 미만으로 운영하는 것은 허용되나(예: 신뢰도 검증
목적의 소규모 파일럿), 100건 초과는 기존 안전 게이트 위반이므로
금지.

## 4. Adjudication (Reviewer Disagreement)

### 4.1 전제

2인 이상의 reviewer가 동일 tsu_id를 검토했을 때 발생. 단일-reviewer
운영(현재 776건 인력 규모상 유력한 시나리오)에서는 Adjudication이
발생하지 않을 수 있으나, 스키마와 워크플로우는 처음부터 다중
reviewer를 전제로 설계한다(작업 명령서 §8 요구사항).

### 4.2 최소 표현 요소

```
reviewer_a            — 첫 번째 disposition record의 reviewer_id
reviewer_b            — 상충하는 두 번째 disposition record의 reviewer_id
disagreement_reason   — 시스템이 자동 채움(disposition 값 상이 / reason_code 상충)
                         + adjudicator가 보완 가능
adjudication_required — boolean, 상충 감지 시 자동 true
final_disposition     — adjudicator가 기록(Disposition Schema §3의 동일 필드)
adjudicator           — adjudicator_id
```

### 4.3 절차

```
1. 시스템이 동일 tsu_id에 대해 상충하는 FINALIZED 이전 record 2건 이상 감지
2. review_status=ADJUDICATION_REQUIRED로 전환(두 원본 record는 그대로 보존 — 삭제/수정 없음)
3. adjudicator_id가 배정된 사람이 두 record와 각각의 evidence_refs를 검토
4. adjudicator가 final_disposition + adjudicated_at 기록 → 새 disposition
   record 생성(supersedes_review_id로 두 원본 record를 모두 참조 —
   스키마 §3의 supersedes_review_id는 단일 참조이므로, 다중 참조가
   필요하면 배열로 확장하는 것을 Phase 2 스키마 개정 후보로 남긴다)
5. review_status=FINALIZED
```

Adjudicator는 reviewer_a/reviewer_b와 달라야 한다(자기 자신의 판정을
스스로 조정하지 않음 — 원칙만 명시, 강제 검증 로직은 구현 단계 대상).

## 5. Human Review와 Production Admission의 분리

```
Generated TSU (776건, review_status=generated, 원본 무수정)
   ↓
Human Review (본 워크플로우, UNREVIEWED~FINALIZED)
   ↓
Disposition (FINALIZED record, ACCEPT/ACCEPT_WITH_CORRECTION/REJECT/DUPLICATE_MERGE)
   ↓
QA / Adjudication (필요 시, §4)
   ↓
Admission Decision  ← 이번 설계 범위 밖, 별도 작업 명령 필요
   ↓
Production (review_promotion.py 호출 → review_status="verified")
```

**Admission Decision이 별도 단계인 이유**: FINALIZED disposition이
"이 TSU는 사람이 ACCEPT라고 판정했다"는 사실을 기록하지만,
Production에 실제로 반영하는 행위(`review_promotion.py` 호출,
`review_status` 필드 갱신)는 여전히 명시적인 별도 실행을 요구한다 —
자동 승격 금지(기존 `review_promotion.py`의 설계 원칙과 동일:
reviewer/review_date/review_decision 전부 명시 필요, 기본값 승격
없음). Disposition record의 존재 자체가 Production 변경을
유발하지 않는다.

## 6. 776건 실행 시 예상 흐름(참고용 — 실행하지 않음)

```
Batch 1 (100건) → Batch 2 (100건) → ... → Batch 8 (76건)
합계 8 batch, 776건
```

각 batch 완료 후 Evidence Package(기존 ADR-020/ADR-021 패턴 재사용
— `scripts/generate_*_evidence.py` 계열)로 batch 단위 검증 가능하도록
설계하되, 실제 evidence generator 구현은 범위 밖.

## 7. 관련 문서

- `docs/NAE_HUMAN_REVIEW_DISPOSITION_SCHEMA_v1.md`
- `docs/NAE_HUMAN_REVIEW_GOVERNANCE_v1.md`

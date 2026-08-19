# ADR Prototype — Human Review Disposition Architecture

## Meta

- **작성일**: 2026-08-13
- **작성자**: C1 (Cline)
- **상태**: Prototype / Schema Validation
- **의존**: NAE 776 Human Review Disposition 작업명령서

## Purpose

NAE 776 Human Review Disposition architecture를 실제 코드 구조로 표현하여
schema, state machine, immutability, audit trail, queue mechanics를 검증한다.

776건에 실제 disposition을 기록하지 않는다.

## Prototype Scope

다음 entity 관계를 검증한다:

```
TSU
 └── Review Record
      ├── Disposition
      ├── Reasons
      ├── Evidence References
      ├── Correction
      └── Adjudication
```

Review Record를 TSU 자체에 embedded mutation으로 구현하지 않는다.

## Schema Design

### Schema Version

```python
HUMAN_REVIEW_DISPOSITION_SCHEMA_VERSION = "1.0.0"
```

향후 schema 변경 시 기존 review record를 해석할 수 있다.

### Enums

| Enum | Values | Purpose |
|------|--------|---------|
| `Disposition` | accept, reject, accept_with_correction, needs_review, duplicate_merge (RC-01) | Human reviewer's decision |
| `ReasonCode` | content_validity, metadata, extraction, chunk_boundary, duplication, source_authority, copyright, other (RC-03) | Governance authority taxonomy |
| `ReviewState` | unreviewed, in_review, dispositioned, adjudication_required, finalized | Lifecycle state |
| `QueueState` | unreviewed, in_review, needs_review, accepted, rejected, duplicate_merge, adjudication_required | Queue state |
| `AdjudicationOutcome` | upheld, overturned, modified | Adjudicator's decision |
| `ReviewerRole` | reviewer, adjudicator, second_reviewer | Person's role |

### Models (Pydantic)

| Model | Purpose |
|-------|---------|
| `EvidenceReference` | Evidence reference (not copy) |
| `CorrectionPayload` | Correction separate from original TSU |
| `AdjudicationRecord` | Adjudicator decision |
| `ReviewRecord` | Main review entity |
| `QueueRecord` | Queue entry |

## State Machine

```
UNREVIEWED ──→ IN_REVIEW ──→ DISPOSITIONED ──→ ADJUDICATION_REQUIRED ──→ FINALIZED
                    │              ↓                      │
                    │              └──────────────────────┘
                    │            (direct to FINALIZED also valid)
                    │
                    ←── UNREVIEWED (RC-07: NEEDS_REVIEW requeue)
```

### Invalid Transitions (blocked)

- UNREVIEWED → FINALIZED (skip review)
- DISPOSITIONED → IN_REVIEW (regression without adjudication)
- IN_REVIEW → IN_REVIEW (RC-07: no governance basis for self-loop)
- ADJUDICATION_REQUIRED → UNREVIEWED (must go through DISPOSITIONED first)
- FINALIZED → anything (terminal state)

## Key Design Decisions

### 1. Review Record ≠ TSU Embedded Mutation

Review record는 TSU와 별도 저장소(파일/DB)에 저장된다.
TSU object 자체를 수정하지 않는다.

### 2. Immutability: original TSU ≠ corrected TSU

`ACCEPT_WITH_CORRECTION` 수행 시:
- 원본 TSU는 변경되지 않음
- correction은 별도의 `CorrectionPayload` record/payload
- correction payload는 original_text, corrected_text, justification 포함

### 3. Evidence Reference Model

Evidence를 disposition DB에 복제하지 않는다:

```python
EvidenceReference {
    evidence_type: str      # scripture, source_text, metadata, etc.
    evidence_ref: str       # "John 3:16", file path, URL
    page: int | None        # page number
    location: str | None    # specific location
    note: str | None        # free-text note
}
```

### 4. Audit Trail

모든 review record는 다음을 추적:
- reviewer_id, reviewer_name, reviewer_role
- reviewed_at timestamp
- evidence_refs (references only)
- superseded_review_id (second+ reviews)
- adjudicator info (if applicable)

### 5. Production Separation

Review results는 Production admission과 분리된다:
- Queue state ≠ Production admission state
- Disposition ≠ TSU metadata modification
- Review records are read-only references to TSU

## Test Results (RC Corrections)

```
Total:  87
Passed: 87
Failed: 0
```

### RC Correction Coverage

| RC | Description | Test Count | Status |
|----|-------------|-----------|--------|
| RC-01 | DUPLICATE_MERGE enum, ADJUDICATION_REQUIRED removal | 4 | PASS |
| RC-02 | Authority/identity fields (source_id, work_id, edition_id, review_note, previous_disposition) | 7 | PASS |
| RC-03 | ReasonCode taxonomy (governance authority), OTHER+review_note | 5 | PASS |
| RC-04 | Adjudication final_disposition | 5 | PASS |
| RC-05 | Correction field-level semantics (field, original_value, corrected_value) | 6 | PASS |
| RC-06 | MAX_PENDING_REVIEW safety gate (99/100/101/776 synthetic) | 6 | PASS |
| RC-07 | NEEDS_REVIEW requeue, IN_REVIEW self-loop removal | 8 | PASS |
| RC-08 | Test semantics correction (synthetic object level) | 3 | PASS |

### Regression Coverage (existing tests preserved)

| Category | Count | Coverage |
|----------|-------|----------|
| Schema Validation | 8 | enum, model, validator |
| State Transitions | 10 | valid/invalid transitions |
| Immutability | 3 | copy-on-write, correction separation |
| Correction Payload | 6 | field-level semantics |
| Adjudication | 5 | record structure, supersedes, outcomes |
| Queue Safety Gate | 6 | MAX_PENDING_REVIEW boundary |
| NEEDS_REVIEW Requeue | 4 | valid/invalid requeue paths |
| Queue Filtering | 4 | all states, priority, assign/dismiss |
| Serialization | 4 | roundtrip, schema version |
| Second Review Distinction | 2 | superseded vs previous_disposition |
| Immutability Guarantee | 2 | deep copy isolation |
| Disagreement Recording | 1 | adjudication record |
| Evidence Traceability | 2 | reference preservation |
| Production Separation | 2 | no production access |
| Disposition Values | 3 | all enum values |
| Transition Documentation | 5 | VALID_TRANSITIONS completeness |

## Files

| File | Purpose |
|------|---------|
| `core/review_disposition.py` | Schema, enums, models, state machine, queue (RC-01 to RC-08) |
| `tests/test_review_disposition_prototype.py` | 87 unit tests (RC-01 to RC-08 + regression) |

## Git Policy

### 포함 가능
- schema (`core/review_disposition.py`)
- prototype implementation
- tests (`tests/test_review_disposition_prototype.py`)
- architecture documentation (이 파일)

### 포함 불가
- 776건 실제 review result
- 개인 reviewer data
- generated review evidence
- output artifact
- production TSU snapshot

## Required Corrections Summary

### RC-01: DUPLICATE_MERGE
- `Disposition` enum에 `DUPLICATE_MERGE` 추가
- `ADJUDICATION_REQUIRED`를 Disposition에서 제거 (ReviewState/QueueState에는 유지)
- 테스트: `test_DUPLICATE_MERGE_valid`, `test_ADJUDICATION_REQUIRED_invalid`

### RC-02: Authority/Identity Fields
- `ReviewRecord`에 `source_id`, `work_id`, `edition_id` 추가 (immutable)
- `review_note`, `previous_disposition` 추가
- `superseded_review_id` (review reference)와 `previous_disposition` (value) 구분

### RC-03: Reason Taxonomy
- `DispositionReason` → `ReasonCode`로 변경 (governance authority taxonomy)
- 8개 reason code: CONTENT_VALIDITY, METADATA, EXTRACTION, CHUNK_BOUNDARY, DUPLICATION, SOURCE_AUTHORITY, COPYRIGHT, OTHER
- `OTHER` 사용 시 `review_note` required

### RC-04: Adjudication final_disposition
- `AdjudicationRecord`에 `final_disposition: Disposition` 추가
- `outcome` (UPHELD/OVERTURNED/MODIFIED)와 `final_disposition` (ACCEPT/REJECT/...) 구분

### RC-05: Correction field-level semantics
- `CorrectionPayload`에 `field`, `original_value`, `corrected_value`, `correction_reason`, `evidence_ref` 추가
- field-level traceability 보장

### RC-06: MAX_PENDING_REVIEW safety gate
- `MAX_PENDING_REVIEW = 100` 상수 정의
- `ReviewQueue.add()`에서 pending_count >= 100 시 OverflowError 발생
- 테스트: 99→allowed, 100→allowed, 101→rejected, 776→rejected

### RC-07: NEEDS_REVIEW requeue transition
- `DISPOSITIONED → UNREVIEWED` 전이 추가 (NEEDS_REVIEW 재큐잉)
- `IN_REVIEW → IN_REVIEW` self-loop 제거 (governance 근거 없음)
- 잘못된 상태에서의 임의 재큐잉 거부

### RC-08: Test semantics correction
- `test_original_tsu_not_modified_by_disposition` → `test_original_review_record_unchanged_after_transition`
- synthetic object 수준 검증 명시

## Completion Questions — Code Answers

### Q1: 한 TSU에 대한 첫 번째 review와 두 번째 review를 어떻게 구분하는가?

**A**: `superseded_review_id` 필드로 추적.
첫 번째 review는 `superseded_review_id=None`, 두 번째 review는
`superseded_review_id="REV-001"` (첫 번째 review의 ID).

```python
first = create_sample_review_record(review_id="REV-001")  # None
second = create_sample_review_record(
    review_id="REV-002", superseded_review_id="REV-001"  # Linked
)
```

### Q2: correction이 원본을 변경하지 않았음을 어떻게 보장하는가?

**A**: `CorrectionPayload`는 field-level traceability를 가진 별도 payload (RC-05).
원본 TSU object는 immutable (copy-on-write).

```python
correction = CorrectionPayload(
    correction_type="doctrine_reclassification",
    field="doctrine",           # RC-05: which TSU field
    original_value="Old text",  # RC-05: snapshot of original
    corrected_value="New text", # RC-05: proposed correction
    correction_reason="Doctrinal update",
)
# correction은 TSU에 embedded되지 않음 — 별도 payload
# original_value는 참조 시점 스냅샷 (TSU 원본은 변경되지 않음)
```

### Q3: 두 reviewer의 disagreement를 어떻게 기록하는가?

**A**: `AdjudicationRecord`로 기록.
`superseded_review_id`로 어느 review를 덮어썼는지 추적.

```python
review_a = create_sample_review_record(
    review_id="REV-001", disposition=Disposition.ACCEPTED
)
review_b = create_sample_review_record(
    review_id="REV-002", state=ReviewState.ADJUDICATION_REQUIRED,
    superseded_review_id="REV-001"
)
review_b.adjudication = AdjudicationRecord(
    adjudicator_id="ADV-001", outcome=AdjudicationOutcome.OVERTURNED, ...
)
```

### Q4: 최종 disposition이 어떤 evidence에 근거하는지 어떻게 추적하는가?

**A**: `evidence_refs` 필드 (reference model).
evidence를 복제하지 않고 reference만 저장.

```python
record.evidence_refs = [
    EvidenceReference(evidence_type="scripture", evidence_ref="John 3:16"),
]
# evidence text는 disposition DB에 없음 — reference만
```

### Q5: review 결과를 Production admission과 어떻게 분리하는가?

**A**: Queue state ≠ Production admission state.
Review records는 TSU를 참조하지만 수정하지 않음.

```python
queue = ReviewQueue()
queue.add(create_sample_queue_record(state=QueueState.UNREVIEWED))
# Queue state는 production admission과 독립적
```

## Next Steps

1. CUE governance schema 승인 요청
2. 승인 후 776건 실제 Human Review 작업명령서 생성
3. Production TSU에 disposition 결과 적용 (별도 작업)

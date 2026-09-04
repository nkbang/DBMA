# ADR-027: NAE Human Review Disposition v2 — Pilot Specification

**문서 버전:** 1.0-draft  
**작성일:** 2026-08-13  
**작성자:** C1 (Independent Forensic Auditor)  
**상태:** DRAFT — Pilot 실행 금지, CUE 승인 필요  
**권한:** docs/NAE_HUMAN_REVIEW_DISPOSITION_SCHEMA_v1.md  
**번호 재부여 이력:** 원안은 "ADR-021"로 작성됐으나 그 번호가 이미 다른
문서(Source Registration → Raw Preservation → Extraction, Approved)가
선점하고 있어 CUE가 2026-08-18 정리 과정에서 ADR-027로 재번호를 부여함
(내용 변경 없음, 참조 무결성 확인 완료 — git grep 결과 이 파일을 번호로
참조하는 곳 없음).  
**관련 ADR:** ADR-021 (Source Registration Raw Preservation Extraction),
  ADR-004~008 (Research Workspace Layer, Boundary Score, Hierarchical Chunk Builder)

---

## 1. Pilot 목적과 범위

### 1.1 목적

NAE Human Review Disposition v2(schema version `2.0.0`)가 실제 776건 대상
데이터에서 다음을 검증한다:

1. **State machine correctness** — `VALID_TRANSITIONS_V2` 기반 전이 규칙이
   모든 사례에서 정확히 적용되는지
2. **AuditTrail integrity** — RC-08에 따라 모든 전이가 `AuditEventV2`로
   자동 생성되며 누락이 없는지
3. **Disposition-aware requeue (RC-07)** — `NEEDS_REVIEW`만 requeue 허용,
   `ACCEPT/REJECT/ACCEPT_WITH_CORRECTION/DUPLICATE_MERGE`는 차단되는지
4. **FINALIZED terminal invariant** — FINALIZED 상태가 self-loop 및
   backward transition을 완전히 차단하는지
5. **Production isolation** — Pilot이 Dagg/Hiscox TSU, Qdrant index,
   기존 decisions에 단 1바이트도 쓰지 않는지
6. **Serialization round-trip** — `serialize_review_record_v2` /
   `deserialize_review_record_v2`가 모든 disposition 사례에서 무결성
   유지하는지

### 1.2 범위

- **Pilot 대상:** 776건 중 선정된 sample subset (세부 설계 §2 참조)
- **Pilot 비대상:**
  - 기존 3,347 historical decisions (migration 없음)
  - Production TSU (Dagg 3,377 / Hiscox 740)
  - Qdrant `nae_tsu_v1` index
  - Exception queue (`NAE/review/human/exception_queue.json`)
  - Screening cursor 및 automated screening sweep 결과

### 1.3 핵심 invariant

| # | Invariant | 검증 방법 |
|---|-----------|-----------|
| INV-1 | `audit_trail` 필수 — 없으면 `TypeError` | 함수 시그니처 검증 |
| INV-2 | FINALIZED terminal — self-loop/backward 차단 | `validate_transition` 반환값 |
| INV-3 | RC-07 requeue — disposition-aware | `DISPOSITION_ALLOW_REQUEUE` 집합 |
| INV-4 | Production mutation = 0 | SHA256 pre/post 비교 |
| INV-5 | AuditTrail event count = transition count | `len(events)` 대조 |
| INV-6 | Serialization round-trip = identity | `deserialize(serialize(r)) == r` |
| INV-6 | Serialization round-trip = identity | `deserialize(serialize(r)) == r` |

---

## 2. Pilot sample 설계

### 2.1 선정 원칙

776건 전체 중 다음 기준에 따라 representative sample을 선정:

1. **균형성:** 각 disposition 유형이 최소 1건 이상 포함
2. **경계 사례:** requeue, adjudication, correction 등 edge case 포함
3. **독립성:** 각 sample은 서로 다른 TSU ID를 가짐
4. **재현성:** sample 선정 기준이 문서화되어 임의 변경 불가

### 2.2 Sample 구성 (목표 15건)

| # | 사례 유형 | disposition | reason_codes | 검증 목표 |
|---|-----------|-------------|--------------|-----------|
| S-01 | 정상 ACCEPT | `ACCEPT` | `[CONTENT_VALIDITY]` | 기본 전이 + audit trail |
| S-02 | 정상 REJECT | `REJECT` | `[CONTENT_VALIDITY, SOURCE_AUTHORITY]` | 다중 reason_code |
| S-03 | NEEDS_REVIEW requeue | `NEEDS_REVIEW` | `[METADATA]` | RC-07: requeue 허용 |
| S-04 | ACCEPT_WITH_CORRECTION | `ACCEPT_WITH_CORRECTION` | `[EXTRACTION]` | correction_payloads 필수 검증 |
| S-05 | DUPLICATE_MERGE | `DUPLICATE_MERGE` | `[DUPLICATION]` | merge traceability |
| S-06 | evidence 필요 사례 | `ACCEPT` | `[CONTENT_VALIDITY]` | evidence_refs 3개 이상 |
| S-07 | OTHER + review_note | `REJECT` | `[OTHER]` | RC-03: review_note 필수 |
| S-08 | requeue 사례 (NEEDS_REVIEW) | `NEEDS_REVIEW` | `[CHUNK_BOUNDARY]` | DISPOSITIONED → UNREVIEWED 재전이 |
| S-09 | adjudication 사례 | `ACCEPT` (adjudicated) | `[CONTENT_VALIDITY]` | ADJUDICATION_REQUIRED 전이 |
| S-10 | 경계: FINALIZED self-loop | — | — | INV-2: 차단 검증 |
| S-11 | 경계: FINALIZED → UNREVIEWED | — | — | INV-2: backward 차단 |
| S-12 | 경계: DISPOSITIONED + ACCEPT requeue | `ACCEPT` | `[CONTENT_VALIDITY]` | RC-07: requeue 차단 |
| S-13 | 경계: DISPOSITIONED + REJECT requeue | `REJECT` | `[METADATA]` | RC-07: requeue 차단 |
| S-14 | 경계: UNREVIEWED → DISPOSITIONED (skip) | — | — | INV-1: state machine 차단 |
| S-15 | serialization round-trip | `ACCEPT` | `[CONTENT_VALIDITY]` | INV-6 검증 |

### 2.3 sample 상세 요구사항

#### S-01: 정상 ACCEPT

```python
record = ReviewRecordV2(
    record_id="PILOT-001",
    tsu_id="TSU-XXXXXXX",  # 776건 중 하나
    source_id="SOURCE-XXX",
    work_id="WORK-XXX",
    edition_id="EDITION-XXX",
    author_id="AUTHOR-XXX",
    state=ReviewStateV2.UNREVIEWED,
)
# Transition: UNREVIEWED → IN_REVIEW → DISPOSITIONED → FINALIZED
# disposition = ACCEPT, reason_codes = [CONTENT_VALIDITY]
# evidence_refs = 1개 이상
# correction_payloads = [] (empty)
# adjudication = None
```

#### S-03: NEEDS_REVIEW requeue

```python
# DISPOSITIONED 상태에서 NEEDS_REVIEW disposition으로 UNREVIEWED 재전이
# RC-07: DISPOSITION_ALLOW_REQUEUE에 포함되므로 VALID
# 검증: state_machine.apply_transition이 Exception 없이 통과
```

#### S-04: ACCEPT_WITH_CORRECTION

```python
# correction_payloads 필수 (Pydantic model_validator)
correction = CorrectionPayloadV2(
    correction_type="field_correction",
    field="claim_text",
    original_value="...",
    corrected_value="...",
    correction_reason="...",
)
# 검증: model_validator가 correction_payloads 없으면 ValueError 발생
```

#### S-07: OTHER + review_note

```python
# RC-03: reason_codes에 OTHER가 포함되면 review_note 필수
# 검증: review_note 없이 생성 시 Pydantic validation error
```

#### S-09: adjudication 사례

```python
# ADJUDICATION_REQUIRED 상태에서는 adjudication 필드 필수
adjudication = AdjudicationRecordV2(
    adjudicator_id="ADJ-XXX",
    outcome=AdjudicationOutcomeV2.UPHELD,
    final_disposition=DispositionV2.ACCEPT,
    reasoning="...",
    adjudicated_at=datetime.now(timezone.utc),
)
# 검증: state = ADJUDICATION_REQUIRED일 때 adjudication 없으면 ValueError
```

#### S-10~S-14: 경계/예외 사례 (차단 검증)

각 사례는 `InvalidTransitionError`가 발생해야 함을 검증:

| 사례 | 시도한 전이 | 예상 결과 |
|------|-------------|-----------|
| S-10 | FINALIZED → FINALIZED | `InvalidTransitionError` |
| S-11 | FINALIZED → UNREVIEWED | `InvalidTransitionError` |
| S-12 | DISPOSITIONED(ACCEPT) → UNREVIEWED | `InvalidTransitionError` (RC-07) |
| S-13 | DISPOSITIONED(REJECT) → UNREVIEWED | `InvalidTransitionError` (RC-07) |
| S-14 | UNREVIEWED → DISPOSITIONED | `InvalidTransitionError` (state skip) |

| S-14 | UNREVIEWED → DISPOSITIONED | `InvalidTransitionError` (state skip) |

---

## 3. State-machine 검증

### 3.1 정상 transition 검증

```
UNREVIEWED ──IN_REVIEW──> DISPOSITIONED ──FINALIZED──>
                    │              │
                    └──ADJUDICATION_REQUIRED──┘
```

| 전이 | 조건 | 검증 항목 |
|------|------|-----------|
| UNREVIEWED → IN_REVIEW | `reviewer_id` 필수 | reviewer_id 없으면 `ValueError` |
| IN_REVIEW → DISPOSITIONED | disposition, reason_codes, evidence_refs, reviewed_at 필수 | model_validator 검증 |
| DISPOSITIONED → FINALIZED | disposition context 유지 | audit trail event 생성 |
| DISPOSITIONED → ADJUDICATION_REQUIRED | adjudication 필드 필수 | model_validator 검증 |
| ADJUDICATION_REQUIRED → DISPOSITIONED | final_disposition 반영 | 전이 후 disposition 업데이트 |

### 3.2 RC-07 requeue 검증

```python
# 허용
DISPOSITIONED + NEEDS_REVIEW → UNREVIEWED  # VALID

# 차단
DISPOSITIONED + ACCEPT → UNREVIEWED        # INVALID (RC-07)
DISPOSITIONED + REJECT → UNREVIEWED        # INVALID (RC-07)
DISPOSITIONED + ACCEPT_WITH_CORRECTION → UNREVIEWED  # INVALID (RC-07)
DISPOSITIONED + DUPLICATE_MERGE → UNREVIEWED       # INVALID (RC-07)
```

### 3.3 금지 transition 검증

`VALID_TRANSITIONS_V2`에 명시되지 않은 모든 전이는 차단:

```python
VALID_TRANSITIONS_V2 = {
    UNREVIEWED: {IN_REVIEW},
    IN_REVIEW: {DISPOSITIONED},
    DISPOSITIONED: {ADJUDICATION_REQUIRED, FINALIZED, UNREVIEWED},  # disposition-aware
    ADJUDICATION_REQUIRED: {DISPOSITIONED},
    FINALIZED: set(),  # Terminal
}
```

### 3.4 FINALIZED terminal invariant

- `FINALIZED → FINALIZED`: 차단 (self-loop)
- `FINALIZED → UNREVIEWED`: 차단 (backward)
- `FINALIZED → IN_REVIEW`: 차단 (backward)
- `FINALIZED → DISPOSITIONED`: 차단 (backward)
- `FINALIZED → ADJUDICATION_REQUIRED`: 차단 (backward)

### 3.5 AuditTrail 자동 생성 검증

RC-08에 따라:

1. `apply_transition` 호출 시 `audit_trail` 파라미터 **필수**
2. 모든 valid transition마다 `AuditEventV2`가 **자동** 생성
3. event_id는 `EVT-{n:04d}` 형식 (순차 증가)
4. event에는 `previous_state`, `new_state`, `previous_disposition`,
   `new_disposition`, `reason`, `actor` 포함

   `new_disposition`, `reason`, `actor` 포함

---

## 4. Data integrity baseline

### 4.1 Production TSU SHA256

| 파일 | SHA256 |
|------|--------|
| `NAE/corpus/tsu/Dagg_Church_Order/tsu.json` | `10fc58ef2f80902c967a6cf24409be78a04e993303ffcb7228853a1698516ea5` |
| `NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json` | `1da2d7dd75d5235f645d5d2b22c19f865723134754e08028c93fc7d3943ceb2a` |

### 4.2 Qdrant authoritative endpoint

- **URL:** `http://localhost:7333`
- **collection:** `nae_tsu_v1`
- **points_count:** `3319` (baseline)
- **health check:** `GET /health` → `200 OK`

> **주의:** Pilot 실행 전 Qdrant가 실행 중이어야 함. Pilot 중 Qdrant mutation 금지.

### 4.3 Legacy decisions

- **경로:** `NAE/review/human/decisions/`
- **파일 수:** 40개 (batch_0001 ~ batch_0018 + remediation files)
- **총 decision 수:** 1,353건 (실측)
- **combined hash:** `0c2069f92eb66b19a4ea2b8f82b9e2ebd25d24f43fc2694ec1568ca91b89926c`

### 4.4 Exception queue

- **경로:** `NAE/review/human/exception_queue.json`
- **schema_version:** `1.0.0`
- **총 entries:** 2,452건
- **status 분포:**
  - `RESOLVED`: 1,914
  - `NEEDS_CLAIM_REVIEW`: 232
  - `CJK_FOREIGN_CONTAMINATION`: 211
  - `QA_FLAG_NONBLOCKING`: 87
  - `STRUCTURAL_EXCEPTION`: 5
  - `READY_FOR_HUMAN_REVIEW`: 3
- **SHA256:** `1e940d4ae63ec7858e4bbca8ef43d1f2293ea610c7e2c526f0ae420a67d4b277`

- **SHA256:** `1e940d4ae63ec7858e4bbca8ef43d1f2293ea610c7e2c526f0ae420a67d4b277`

---

## 5. Acceptance criteria

### 5.1 Pilot 성공 조건 (ALL must pass)

| # | 항목 | 성공 조건 | 실패 시 |
|---|------|-----------|---------|
| AC-1 | State transition 정확성 | 15건 중 정상 사례 10건 모두 PASS | Pilot abort |
| AC-2 | RC-07 requeue | NEEDS_REVIEW requeue PASS, others BLOCKED | Pilot abort |
| AC-3 | FINALIZED terminal | S-10~S-11 차단 검증 PASS | Pilot abort |
| AC-4 | AuditTrail 완전성 | 모든 전이에 event 생성 (누락 0) | Pilot abort |
| AC-5 | Production isolation | TSU SHA256 pre = post | Pilot abort |
| AC-6 | Serialization round-trip | S-15 identity 검증 PASS | Pilot abort |
| AC-7 | Test suite | `test_disposition_v2_schema.py` 110 tests PASS | Pilot 재실행 금지 |
| AC-8 | Dry run | `dry_run_disposition_v2.py` all phases PASS | Pilot 재실행 금지 |

### 5.2 Production mutation = 0 검증

Pilot 전후 다음 파일의 SHA256가 동일해야 함:

```bash
# Pre-snapshot
sha256 NAE/corpus/tsu/Dagg_Church_Order/tsu.json
sha256 NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json
sha256 NAE/review/human/exception_queue.json
find NAE/review/human/decisions -type f -exec cat {} + | sha256sum

# Post-snapshot (동일 명령)
# Pre = Post 이어야 함
```

### 5.3 Audit event 완전성

각 Pilot record에 대해:

```python
assert len(audit_trail.get_events_for_record(record_id)) == expected_transition_count
# expected_transition_count = UNREVIEWED→IN_REVIEW→DISPOSITIONED→FINALIZED = 3
```

### 5.4 State transition 정확성

각 전이마다:

```python
# VALID_TRANSITIONS_V2에 명시된 전이만 통과
assert new_state in VALID_TRANSITIONS_V2[current_state]
```

### 5.5 Serialization/validation 성공

```python
serialized = serialize_review_record_v2(record)
deserialized = deserialize_review_record_v2(serialized)
assert deserialized.record_id == record.record_id
assert deserialized.tsu_id == record.tsu_id
assert deserialized.state == record.state
assert deserialized.disposition == record.disposition
assert deserialized.reason_codes == record.reason_codes
assert deserialized.evidence_refs == record.evidence_refs
```

### 5.6 재실행 안전성 (Idempotency)

Pilot을 여러 번 실행해도:

- 기존 Pilot records에 중복 생성 없음
- Audit trail event count 증가하지 않음 (새 batch로 분리)
- Production 데이터 변경 없음

- Production 데이터 변경 없음

---

## 6. Rollback / Abort 조건

### 6.1 즉시 중단 조건 (Abort)

다음 중 **하나라도** 발생 시 Pilot 즉시 중단:

| # | 조건 | 심각도 | 처리 |
|---|------|--------|------|
| AB-1 | Production TSU SHA256 변경 | CRITICAL | Git diff 확인, mutation 원천 차단 |
| AB-2 | Exception queue mutation | CRITICAL | Git diff 확인, mutation 원천 차단 |
| AB-3 | Legacy decisions 파일 변경 | CRITICAL | Git diff 확인, mutation 원천 차단 |
| AB-4 | Qdrant points_count 변화 | HIGH | Qdrant rollback 또는 restart |
| AB-5 | Audit trail event 누락 (1건 이상) | HIGH | `apply_transition` 재검증 |
| AB-6 | State inconsistency (record.state != expected) | HIGH | Record 재생성, 전이 재시도 |
| AB-7 | Serialization round-trip 실패 | MEDIUM | Schema 변경 이력 확인 |
| AB-8 | Test suite 1건 이상 실패 | MEDIUM | Root cause 분석 후 재실행 |

### 6.2 데이터 mutation 발견 시 처리

```bash
# 1. Git diff로 변경 파일 확인
git diff --stat

# 2. mutation 원천 코드 확인
grep -rn "tsu.json\|exception_queue\|decisions" core/review_disposition_v2.py

# 3. mutation이 v2 module에서 발생하면 즉시 중단
# 4. CUE에 보고 후 승인 대기
```

### 6.3 Audit trail 누락 처리

```python
# 누락 확인
events = audit_trail.get_events_for_record(record_id)
if len(events) != expected_count:
    # 1. apply_transition 호출 이력 확인
    # 2. audit_trail.append_event() 호출 확인
    # 3. CUE에 보고
    raise PilotAbortError(f"Audit trail missing: {len(events)}/{expected_count}")
```

### 6.4 State inconsistency 처리

```python
# 전이 후 상태 검증
assert record.state == expected_state
if record.state != expected_state:
    # 1. validate_transition 반환값 재확인
    # 2. VALID_TRANSITIONS_V2 확인
    # 3. CUE에 보고
    raise PilotAbortError(f"State inconsistency: {record.state} != {expected_state}")
```

### 6.5 Qdrant baseline divergence

```bash
# Qdrant health check
curl -s http://localhost:7333/health

# Collection points_count 확인
curl -s http://localhost:7333/collections/nae_tsu_v1 | jq '.result.points_count'

# Baseline (3319)와 다르면 abort
if points_count != 3319:
    echo "Qdrant baseline divergence detected!"
    echo "Abort Pilot immediately."
```

    echo "Abort Pilot immediately."
```

---

## 7. Evidence collection plan

### 7.1 PRE snapshot

Pilot 실행 전 다음을 기록:

```bash
# TSU SHA256
sha256 NAE/corpus/tsu/Dagg_Church_Order/tsu.json > /tmp/pilot_pre_dagg.sha256
sha256 NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json > /tmp/pilot_pre_hiscox.sha256

# Exception queue SHA256
sha256 NAE/review/human/exception_queue.json > /tmp/pilot_pre_exception.sha256

# Decisions combined hash
find NAE/review/human/decisions -type f -exec cat {} + | sha256sum > /tmp/pilot_pre_decisions.sha256

# Qdrant baseline
curl -s http://localhost:7333/collections/nae_tsu_v1 | jq '.result.points_count' > /tmp/pilot_pre_qdrant.txt

# Test suite baseline
pytest -q tests/nae/registration/test_disposition_v2_schema.py > /tmp/pilot_pre_tests.log 2>&1

# Dry run baseline
python scripts/dry_run_disposition_v2.py > /tmp/pilot_pre_dryrun.log 2>&1
```

### 7.2 Execution evidence

Pilot 실행 중 다음을 기록:

1. **각 sample record의 전이 이력**
   - `record_id`, `tsu_id`, `state` (전이 전/후)
   - `audit_trail.get_events_for_record(record_id)` 전체 출력
   - `disposition`, `reason_codes`, `evidence_refs`

2. **각 차단 사례의 예외 출력**
   - `InvalidTransitionError` 메시지
   - 시도한 전이 (from → to)

3. **RC-07 requeue 검증 결과**
   - 허용된 requeue: PASS/FAIL
   - 차단된 requeue: PASS/FAIL

4. **Production isolation 검증**
   - Pre/Post SHA256 비교 결과
   - `diff` 출력 (변경 시)

### 7.3 POST snapshot

Pilot 실행 후 PRE와 동일 명령으로 재측정:

```bash
# TSU SHA256
sha256 NAE/corpus/tsu/Dagg_Church_Order/tsu.json > /tmp/pilot_post_dagg.sha256
sha256 NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json > /tmp/pilot_post_hiscox.sha256

# Exception queue SHA256
sha256 NAE/review/human/exception_queue.json > /tmp/pilot_post_exception.sha256

# Decisions combined hash
find NAE/review/human/decisions -type f -exec cat {} + | sha256sum > /tmp/pilot_post_decisions.sha256

# Qdrant baseline
curl -s http://localhost:7333/collections/nae_tsu_v1 | jq '.result.points_count' > /tmp/pilot_post_qdrant.txt

# Test suite post
pytest -q tests/nae/registration/test_disposition_v2_schema.py > /tmp/pilot_post_tests.log 2>&1

# Dry run post
python scripts/dry_run_disposition_v2.py > /tmp/pilot_post_dryrun.log 2>&1
```

### 7.4 Hash comparison

```bash
# 모든 hash가 동일해야 함
diff /tmp/pilot_pre_dagg.sha256 /tmp/pilot_post_dagg.sha256 && echo "PASS" || echo "FAIL"
diff /tmp/pilot_pre_hiscox.sha256 /tmp/pilot_post_hiscox.sha256 && echo "PASS" || echo "FAIL"
diff /tmp/pilot_pre_exception.sha256 /tmp/pilot_post_exception.sha256 && echo "PASS" || echo "FAIL"
diff /tmp/pilot_pre_decisions.sha256 /tmp/pilot_post_decisions.sha256 && echo "PASS" || echo "FAIL"
diff /tmp/pilot_pre_qdrant.txt /tmp/pilot_post_qdrant.txt && echo "PASS" || echo "FAIL"
```

### 7.5 Test output

- `pytest` 출력 전체를 `/tmp/pilot_tests.log`에 저장
- 실패 시: 실패한 test 이름, 예외 메시지, traceback 포함
- 성공 시: `110 passed` 확인

### 7.6 Audit trail evidence

각 Pilot record에 대해:

```python
# JSON dump for forensic review
events = audit_trail.get_events_for_record(record_id)
for evt in events:
    print(json.dumps({
        "event_id": evt.event_id,
        "record_id": evt.record_id,
        "previous_state": evt.previous_state,
        "new_state": evt.new_state,
        "previous_disposition": evt.previous_disposition,
        "new_disposition": evt.new_disposition,
        "reason": evt.reason,
        "actor": evt.actor,
    }, indent=2))
```

    }, indent=2))
```

---

## 8. CUE Approval Gate

이 문서는 Pilot Specification **DRAFT** 상태입니다.

아래 작업은 **CUE의 명시적 승인 없이 금지**됩니다:

```text
PILOT SPECIFICATION = DRAFT
PILOT EXECUTION = NOT AUTHORIZED
776 FULL PROCESSING = NOT AUTHORIZED
CUE APPROVAL REQUIRED
```

### 승인 요청 사항

1. **Pilot sample 선정 기준** — §2의 15건 sample이 적절한지
2. **Acceptance criteria** — §5의 조건이 충분한지
3. **Rollback 조건** — §6의 중단 조건이 적절한지
4. **Evidence plan** — §7의 수집 계획이 충분한지

### 승인 후 다음 단계

CUE가 본 Pilot Specification을 승인하면:

1. Pilot sample을 실제 776건 중 선정
2. PRE snapshot 실행
3. Pilot batch execution (설계된 sample만)
4. POST snapshot 실행
5. Evidence comparison
6. C1 Forensic Audit (별도 감사)
7. Pilot 결과 보고

---

**제출 상태:** `READY_FOR_CUE_PILOT_SPEC_AUDIT`

---

## 부록 A: VALID_TRANSITIONS_V2 전체 정의

```python
VALID_TRANSITIONS_V2 = {
    ReviewStateV2.UNREVIEWED: {ReviewStateV2.IN_REVIEW},
    ReviewStateV2.IN_REVIEW: {ReviewStateV2.DISPOSITIONED},
    ReviewStateV2.DISPOSITIONED: {
        ReviewStateV2.ADJUDICATION_REQUIRED,
        ReviewStateV2.FINALIZED,
        ReviewStateV2.UNREVIEWED,  # RC-07: disposition-aware
    },
    ReviewStateV2.ADJUDICATION_REQUIRED: {ReviewStateV2.DISPOSITIONED},
    ReviewStateV2.FINALIZED: set(),  # Terminal state
}
```

## 부록 B: RC-07 Disposition-aware Requeue Rules

```python
DISPOSITION_ALLOW_REQUEUE = frozenset({
    DispositionV2.NEEDS_REVIEW,
})

DISPOSITION_BLOCK_REQUEUE = frozenset({
    DispositionV2.ACCEPT,
    DispositionV2.REJECT,
    DispositionV2.ACCEPT_WITH_CORRECTION,
    DispositionV2.DUPLICATE_MERGE,
})
```

## 부록 C: Production Data Baseline (실측)

| 항목 | 값 |
|------|-----|
| Dagg TSU records | 3,377 |
| Hiscox TSU records | 740 |
| Dagg TSU SHA256 | `10fc58ef...` |
| Hiscox TSU SHA256 | `1da2d7dd...` |
| Qdrant collection | `nae_tsu_v1` (not running) |
| Legacy decisions files | 40 |
| Legacy decisions total | 1,353 |
| Exception queue entries | 2,452 |
| Exception queue SHA256 | `1e940d4a...` |

## 부록 D: 관련 파일 목록

| 파일 | 역할 |
|------|------|
| `core/review_disposition_v2.py` | v2 schema, state machine, models |
| `tests/nae/registration/test_disposition_v2_schema.py` | 110 tests (all PASS) |
| `scripts/dry_run_disposition_v2.py` | Dry run (9 phases, all PASS) |
| `docs/NAE_HUMAN_REVIEW_DISPOSITION_SCHEMA_v1.md` | Governance authority |
| `docs/schemas/nae_human_review_disposition_v2.schema.json` | JSON Schema |
| `NAE/corpus/tsu/Dagg_Church_Order/tsu.json` | Production TSU (read-only) |
| `NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json` | Production TSU (read-only) |
| `NAE/review/human/decisions/` | Legacy decisions (read-only) |
| `NAE/review/human/exception_queue.json` | Exception queue (read-only) |


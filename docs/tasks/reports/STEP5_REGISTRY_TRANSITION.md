# STEP5 Registry Transition Procedure

작성일: 2026-07-31
목적: `acquisition_status`(STEP5_SOURCE_REGISTRY_ENTRY.md에서 도입된 5단계) 각 전환의 정확한 절차와 완료 기준을 명세.

## 상태 전이 개요

```
PREPARED → ACQUIRED → VERIFIED → INGESTED
```

각 화살표는 "이전 상태의 완료 기준을 모두 충족해야만" 다음 상태로 전환 가능 — 역행(예: INGESTED에서 문제 발견 시 VERIFIED로 되돌림)은 허용되나 단계를 건너뛰는 전진은 금지.

## PREPARED → ACQUIRED

**전제 조건 (현재 상태)**: STEP5_SOURCE_REGISTRY_ENTRY.md가 `PREPARED` — 값은 채워졌으나 원문 없음, `provenance.*`는 전부 `null`

**전환 절차**:
1. STEP5_HUMAN_ACQUISITION_GUIDE.md에 따라 사람이 원문을 확보
2. `data/nae/sources/baptist/nhc_1833.txt`에 저장, UTF-8 확인
3. `provenance.acquired_from`/`acquired_url`/`acquired_date` 채움

**완료 기준**: 파일이 지정 경로에 존재 + UTF-8 확인 + provenance 3개 필드 채워짐. **이 시점에는 아직 내용 정확성 검증 안 됨** — "파일이 존재한다"만 의미함.

## ACQUIRED → VERIFIED

**전환 절차**:
1. (STEP5-C에서 계획된) `scripts/validate_nae_source.py`(미구현) 또는 수동으로 STEP5_SOURCE_MANUAL_VERIFY.md 4개 항목 확인
2. STEP4_PD_VERIFICATION.md의 4단계(발행일/PD근거/신뢰성/저장소) 확인 — 특히 "최소 2개 독립 출처 대조" 항목 충족
3. `provenance.verification_method`/`verification_result`/`checksum` 채움

**완료 기준**: STEP5_SOURCE_MANUAL_VERIFY.md 4개 항목 전부 확인 완료(FAIL 없음) + 최소 2개 독립 출처 대조 완료 + checksum 기록됨

## VERIFIED → INGESTED

**전환 절차**:
1. STEP5_SOURCE_REGISTRY_ENTRY.md 레코드를 NAE manifest JSON 형식으로 변환(STEP5_PILOT_CHECKLIST.md TASK 2와 동일)
2. `python -m scripts.ingest_nae_source --manifest <path> --dry-run` 실행 승인 및 확인
3. 이상 없으면 실제 실행(`--dry-run` 제거) 승인 및 실행
4. `identity_registry.json`에 `nae_*` 필드가 additive로 기록되었는지 확인

**완료 기준**: `identity_registry.json`에 해당 문서 레코드 존재 + `nae_theological_position` 등 4개 필드 값 확인됨

## 역행 처리 원칙

- 어느 단계에서든 문제가 발견되면(예: VERIFIED 단계에서 조항 누락 재발견) 즉시 이전 상태로 되돌리고 사유를 기록
- 예: INGESTED 이후 원문 오류 발견 시 → `ACQUIRED`로 되돌리고, registry에서 해당 문서 레코드는 `superseded_by`(기존 identity_registry.py 메커니즘, STEP3_TSU_PIPELINE_ANALYSIS.md에서 확인된 기능) 처리 검토

## 현재 상태 (이 문서 작성 시점)

STEP5_SOURCE_REGISTRY_ENTRY.md: **`PREPARED`** — 아직 어떤 전환도 발생하지 않음. 다음 전환(`PREPARED → ACQUIRED`)은 사람이 원문을 실제로 확보해 전달한 이후에만 가능.

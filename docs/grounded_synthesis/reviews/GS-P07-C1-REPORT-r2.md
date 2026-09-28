# GS-P07-C1-REPORT-r2

## 작업 개요

- **작업 ID**: GS-P07 r2 REWORK
- **수행자**: C1 (CUE)
- **보고서 버전**: r2
- **이전 보고서**: GS-P07-C1-REPORT-r1 (HOLD — AC1 위반 발견)
- **REWORK WO**: `docs/grounded_synthesis/GS-P07-REWORK-r1.md`

## 발견된 결함 (r1 기준)

`check_citation_provenance()`에서 `id_exists=False`인 경우에도
`span_found_in_text`와 `provenance_traceable`이 `evidence_pool.get(eid)` 결과에
의해 독립적으로 계산되어 True가 나올 수 있었다.

**구체적 시나리오**: evidence가 Pool에는 실재하지만 `included_evidence_ids`에서는
`max_evidence` 예산 초과로 제외된(`excluded_evidence_ids`) 근거를 인용하는 경우 —
Pool에 실재하므로 `_check_span_in_text()`와 `has_provenance`가 True를 반환했다.

이는 WO AC1 "존재하지 않는 근거의 하위 검사를 수행하지 않음"을 위반한다.

## 수정 내용

### 1. `core/grounded_citation.py` — short-circuit 로직 추가

`check_citation_provenance()` 내부 루프에서 `id_exists=False`일 때:

- `evidence_pool.get(eid)`를 호출하지 않음
- `span_found_in_text`와 `provenance_traceable`을 자동으로 False로 고정
- `continue`로 나머지 검사 스킵

**수정 전 (라인 154~175)**:
```python
for eid in claim.evidence_ids:
    id_exists = eid in included_ids
    # id_exists와 무관하게 항상 pool 조회 + span/provenance 계산
    ev = evidence_pool.get(eid)
    ...
```

**수정 후 (라인 154~184)**:
```python
for eid in claim.evidence_ids:
    id_exists = eid in included_ids
    if not id_exists:
        # AC1: 존재하지 않는 근거의 하위 검사 수행 안 함
        results.append(CitationCheckResult(
            claim_id=claim.claim_id,
            evidence_id=eid,
            id_exists=False,
            span_found_in_text=False,
            provenance_traceable=False,
        ))
        continue
    # id_exists=True일 때만 pool 조회 + span/provenance 계산
    ev = evidence_pool.get(eid)
    ...
```

### 2. `tests/test_grounded_citation.py` — AC8 테스트 추가

REWORK 문서에 명시된 CUE V7 재현 케이스를 그대로 추가:

```python
def test_ac1_short_circuit_when_evidence_in_pool_but_excluded(self):
    """AC1/AC8: evidence가 Pool에는 실재하지만 included_evidence_ids에는 없으면
    (max_evidence 절단으로 excluded된 경우) id_exists=False이고
    span_found_in_text/provenance_traceable도 자동으로 False여야 한다."""
```

## 검증 결과

### 테스트 실행

```bash
cd ~/DBMA && source ~/envs/dbma311/bin/activate && python -m pytest tests/test_grounded_citation.py -v
```

**결과: 27 passed (0.07s)**

| 그룹 | 테스트 수 | 상태 |
|------|----------|------|
| TestAC1_IdExists | 3 | PASS |
| TestAC2_SpanFoundInText | 3 | PASS |
| TestAC3_ProvenanceTraceable | 2 | PASS |
| TestAC4_SpanMinimumLength | 3 | PASS |
| TestAC5_EmptyEvidenceIds | 1 | PASS |
| TestAC6_MissingEvidenceInPool | 1 | PASS |
| TestAC7_ReportSummary | 4 | PASS |
| TestCitationCheckResultStructure | 2 | PASS |
| TestCitationCheckReportStructure | 4 | PASS |
| TestEdgeCases | 3 | PASS |
| **TestAC8_ShortCircuit (신규)** | **1** | **PASS** |

### 기존 테스트 영향 분석

- `test_ac1_id_exists_false` (라인 127~139): `id_exists=False`이지만 pool에 없는 evidence를 테스트 — 기존과 동일하게 `span_found_in_text=False`, `provenance_traceable=False` 유지. **PASS**.
- `test_ac6_evidence_not_in_pool` (라인 245~258): pool에 없는 evidence — `id_exists=True`이므로 short-circuit 대상 아님. 기존과 동일하게 span/provenance가 False. **PASS**.
- 나머지 24개 테스트: 수정 영역과 무관하거나 `id_exists=True` 경로 사용. **모두 PASS**.

## Acceptance Criteria 판정

| AC | 상태 | 비고 |
|----|------|------|
| AC1 (WO) | ✅ PASS | id_exists=False 시 하위 검사 수행 안 함 — short-circuit로 구현 |
| AC2~AC7 (WO) | ✅ PASS | 기존 26개 테스트 모두 통과 |
| **AC8 (신규)** | ✅ PASS | Pool 실재 + excluded_evidence_ids 케이스에서 자동 False 검증 |

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `core/grounded_citation.py` | short-circuit 로직 추가 (라인 158~168) |
| `tests/test_grounded_citation.py` | TestAC8_ShortCircuit 클래스 추가 (라인 479~513) |

## 판정

**HOLD**

CUE가 AC1 위반 결함을 수정하고 AC8 테스트를 추가했으나,
독립 NAE Forensic Audit 승인이 필요합니다.

CUE READ-ONLY REVALIDATION REQUESTED.

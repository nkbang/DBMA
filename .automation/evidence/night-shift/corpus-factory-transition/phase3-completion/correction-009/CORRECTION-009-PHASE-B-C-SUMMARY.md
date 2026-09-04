# Correction Order 009 — Phase B+C 실행 결과 요약

## 작업 일시
2026-08-17 (KST)

## Phase B 결과

### B-1: Mock LLM (정상 경로)
- **candidate**: cand-b1-mock-test-001 (새로운 deterministic candidate)
- **결과**: READY → CONFIDENCE_CLASSIFIED (정상 완료)
- **metadata**: clean (source fields + execution fields만 누적)
- **error fields**: 없음
- **결론**: 정상 LLM 호출 시 state transition 문제 없음

### B-2: Real LLM (is_claim=false 경로)
- **candidate**: cand-b2-real-test-001 (새로운 candidate, production worker_state)
- **결과**: READY → CONFIDENCE_CLASSIFIED (정상 완료)
- **elapsed**: 6.81s
- **metadata**: clean (source + execution fields만)
- **결론**: real LLM에서도 stuck 발생 안 함

### B-3: Real LLM (is_claim=true 경로)
- **candidate**: cand-b3-claim-test-001 (새로운 candidate, production worker_state)
- **결과**: READY → CONFIDENCE_CLASSIFIED (정상 완료, TSU record 생성)
- **elapsed**: 12.375s
- **metadata**: clean (is_claim=true, confidence_score=0.9, doctrine=Soteriology)
- **결론**: claim 추출 경로도 정상

### Phase B 종합 결론
**PROCESSING stuck이 Phase B 재현에서 재현되지 않음.**
- mock LLM: 정상
- real LLM (is_claim=false): 정상
- real LLM (is_claim=true): 정상
- 기존 stuck candidate(cand-eea68df881b336e1)는 이미 CONFIDENCE_CLASSIFIED로 복구됨

## Phase C 결과

### C-1: FAILED 경로 invariant 검증
- **방법**: LLM 호출을 의도적으로 실패(RuntimeError)하게 patch
- **결과**: READY → PROCESSING → FAILED (invariant holds)
- **error record**: error_type="LLM_ERROR", error_message 기록됨
- **결론**: FAILED 경로의 invariant는 정상

### C-2: stuck PROCESSING 검증
- **결과**: queue에 PROCESSING candidate 없음
- **결론**: 현재 시스템에서 stuck PROCESSING 발생 안 함

### C-3: retry-failed 경로 검증
- **결과**: FAILED → READY 성공
- **⚠️ 발견**: retry 후 error_type/error_message가 metadata에 남아있음
  - 이는 `set_state()`의 merge semantics 때문
  - `reset_failed_to_ready()`가 error fields를 지우지 않음
  - 다음 재시도 시 stale error data가 남을 수 있음

## CUE Gate 현황

| Gate | 요구사항 | 상태 | 근거 |
|------|---------|------|------|
| 1 | PROCESSING stuck 재현 | **재현 불가** | B-2, B-3에서 real LLM 정상 작동. 기존 candidate는 이미 복구됨. |
| 2 | 실제 원인 증명 | **원인 불명** | transient issue(OLLama timeout, race condition 등)일 가능성. 재현 불가로 특정 불가. |
| 3 | terminal state 도달 | **PASS** | B-2, B-3 모두 CONFIDENCE_CLASSIFIED 도달 |
| 4 | --retry-failed 정상 | **PASS** | C-3에서 FAILED → READY 성공 확인 |

## 추가 발견 (Phase E 관련)

### metadata merge semantics 문제
`set_state()`가 metadata를 merge하므로:
1. `reset_failed_to_ready()` 후 error fields가 남아있음
2. candidate가 재처리될 때 stale error data가 함께 전달됨
3. **권고**: `reset_failed_to_ready()`에서 error_type/error_message 필드를 metadata에서 제거하거나, `set_state()`에 `clear_error_fields=True` 옵션 추가

## 다음 단계
- Gate 1, 2가 닫히지 않았으므로 ADR-025 Approved 검토는 보류
- Gate 3, 4는 PASS
- metadata merge semantics 문제는 별도 architecture 결정 필요 (Phase E)

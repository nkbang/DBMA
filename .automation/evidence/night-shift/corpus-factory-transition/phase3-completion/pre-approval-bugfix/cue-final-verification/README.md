# CUE 최종 재검증 (버그 2건 수정 후)

## 코드 확인
- state.py::set_state() — from_state 생략 시 현재 저장된 state 조회 후
  검증(신규 candidate는 예외) — 지시대로 정확히 구현됨
- worker.py — clear_metadata_fields()가 READY->PROCESSING 전이 직후,
  LLM 호출 직전에 호출됨 — 지시대로 정확히 배치됨

## 단위 테스트
`pytest NAE/pipeline/tsu/worker/test_worker.py -v` — **41 passed**
(TestBugfix1_SetStateFromStateOmission 4개,
TestBugfix2_StaleErrorFieldsOnRetry 5개 포함,
test_failed_candidate_preserves_error_fields로 "FAILED 종결시 유지"까지 커버)

## 실제 LLM 최종 재현 (CUE 직접 실행)
1. 버그 1 수정이 실제로 작동함을 확인: READY->FAILED 직행 시도가
   거부됨(이전에는 통과했을 것) — 상태 머신 규칙대로 PROCESSING을
   거쳐 FAILED로 전이
2. `--retry-failed cand-ece6226f0caf085e` → READY 복귀
3. `--worker-mode`(실제 LLM, 21건 일괄 중 1건) → CONFIDENCE_CLASSIFIED
4. `target-candidate-final-state.json` 확인: **error_type/error_message
   완전히 사라짐** — 버그 2 해소 확인

## 결론
버그 2건 모두 코드·단위테스트·실제 프로덕션 조건 실행 3중으로 확인됨.
ADR-025 승격 검토 가능.

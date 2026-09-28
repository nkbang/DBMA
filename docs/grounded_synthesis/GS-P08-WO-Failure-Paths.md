# WORK ORDER — Phase 8: Negative / Failure-path Validation

- 선행 게이트: P7 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`

## 목표

P4~P7 파이프라인 전체(`SynthesisInput → Claim → GroundedAnswer → CitationCheckResult`)를
HQ 원문 §8의 6개 케이스로 강제 시험한다. 새 프로덕션 코드는 만들지 않는다 —
기존 P4~P7 모듈을 조합한 테스트만 작성한다. 실패가 발견되면 그 실패는 **버그 리포트로
CUE에게 전달**하고, 이 Phase 안에서 P4~P7 코드를 고치지 않는다(REWORK는 별도 WO로 되돌림).

## 허용 파일

- 신규: `tests/test_grounded_failure_paths.py`
- 무수정: `core/grounded_*.py`, `core/evidence_*.py`

## 케이스 (HQ 원문 §8, 그대로)

- Case A: 검색 결과 없음 (빈 `EvidencePool`) → `GroundedAnswer.status == "insufficient_evidence"`,
  파이프라인이 예외 없이 끝까지 실행됨
- Case B: 근거가 1건뿐이고 관련성이 낮음 → insufficient 판정이 나오되, 크래시하지 않음
  (관련성 자동 판정은 이 Phase 범위 밖 — "1건뿐"이라는 사실 자체로 다루기 어려운 표본 케이스 확인)
- Case C: 다중 질의 중 일부는 결과 있음(A→E1, B→빈 결과, C→E3) → assembly가
  중단되지 않고 A/C의 결과가 정상적으로 포함됨(P3A manifest로 검증)
- Case D: 중복 Evidence(A→E1, B→E1) → P2 정책(마지막 것 유지)이 그대로 적용되고
  이 Phase에서 그 정책을 바꾸지 않음(회귀 확인만)
- Case E: Evidence 충돌(E1과 E2가 반대 진술) → P6에서 임의 병합/선택이 일어나지
  않음(자동 충돌 탐지가 없으므로, 두 Claim이 서로 다른 evidence_id를 각각
  valid=True로 갖고 공존하는지 확인 — LLM/stub이 하나를 사실로 골라내 다른
  하나를 삭제하지 않는지)
- Case F: 근거가 질문과 무관해 보임 → LLM(stub)이 근거를 확대 해석해 답을 만들지
  않는지 — stub이 "질문과 무관한 근거만 주어지면 insufficient를 반환"하도록
  설계된 케이스로 시험(자동 관련성 판정 로직 자체는 이번 범위에 없음을 보고서에 명시)

## Acceptance Criteria

- AC1: 6개 케이스 각각에 대해 테스트 함수 1개 이상, 총 6개 이상
- AC2: 어떤 케이스에서도 예외가 전파되지 않음(전부 명시적 상태 값으로 귀결)
- AC3: Case C·D는 P3A manifest / P2 정책과 직접 비교하는 assertion을 포함
  (다른 계층을 언급만 하고 검증하지 않는 테스트 금지)
- AC4: 발견된 실패(있다면)는 코드 수정 없이 §8 "Remaining issues"에 정확한
  재현 스텝과 함께 기록

## 보고

`GS-00-JOURNEY-INDEX.md` §7 양식. 6개 케이스 각각에 PASS/FAIL과 재현 커맨드를 표로 정리.

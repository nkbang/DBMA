# CUE Re-audit — ADR-022 Phase E 독립 검증 결과 감사

- reviewer: CUE
- date: 2026-08-14
- 대상 제출물: C1의 `READY_FOR_CUE_RE_AUDIT` (evidence: `.automation/evidence/ADR-022-PHASE-E-INDEPENDENT-VERIFICATION.md` 외 4개 jsonl)
- production_mutation: false

## 판정: **CONDITIONAL — 참조 구현 수정 필요, ADR-022 Approved 아직 아님**

## 1. C1 제출 evidence 독립 재검증

C1이 보고한 15개 항목 중 raw evidence 파일을 직접 열어 대조:

| 항목 | C1 보고 | CUE 대조 결과 |
|---|---|---|
| 결함 1(Test 6, 금지된 전이) | FAIL | **CONFIRMED** — `ADR-021-PILOT-003.jsonl`에 `"from":"COMPLETED","to":"VALIDATION_PASSED"` 실제 기록 확인. CUE가 별도로 `ADR-021-PILOT-001` task 파일의 `automation.state`를 `COMPLETED`로 직접 조작 후 webhook 재호출로 **독립 재현** — 근본 원인 확정: `decide_script`의 `isConflict` 체크가 `lastEntry &&` 조건에 걸려 있어, 해당 task_id의 evidence 로그가 아직 없는 상태(신규 조작/유실)에서는 §9 Transition Matrix를 전혀 검사하지 않는다. C1이 정확히 짚었다. |
| 결함 2(Race Condition) | FAIL | **CONFIRMED** — `ADR-021-PILOT-RACE.jsonl`에 동일 `transition_id`(`...RACE#0001`) 3줄 중복 raw 확인. §11에서 이미 "구체 메커니즘은 C1 구현 시 CUE가 재감사" 라고 명시했던 항목 — 참조 구현 단계에서 원자적 처리를 넣지 않았으므로 예상된 결과. |
| 나머지 13개(mount, canonical 복구, import/publish, export 일치, Test 1~5/7~9, namespace 무변경, production mutation 부재) | PASS | 근거(evidence jsonl, SHA256 값)가 CUE 자체 기록과 일치. Mount 설정 재확인 완료(`tasks/`, `evidence/`만 `:rw`). |

**정직성 평가: C1이 스스로 발견한 결함을 숨기거나 임의로 고쳐서 통과시키지 않고 그대로 보고했다.** 이전 Phase B~D의 "완료 주장 vs 실제 상태 불일치" 패턴이 이번엔 재발하지 않았다.

## 2. 부수 발견 (C1 제출물 외, CUE가 정리 과정에서 확인)

- `.automation/evidence/X.jsonl` 잔존 — C1의 것이 아니라 CUE 자신의 초기 디버깅 세션 잔재(timestamp 03:37, 이번 재감사 대상 기간 이전). CUE가 직접 삭제.
- `.automation/tasks/ADR-021-PILOT-002.json`, `-003.json`, `-RACE.json` — C1이 테스트용으로 만든 뒤 정리하지 않고 남긴 task 픽스처. CUE가 삭제(대응 evidence jsonl은 감사 기록으로 보존).
- `.automation/tasks/ADR-021-PILOT-001.json`이 CUE의 결함 재현 과정에서 `automation.state: "COMPLETED"`(조작값)로 남아있던 것을 pristine 상태로 복구.

## 3. 결함에 대한 CUE 판단

### 결함 1 (Transition Matrix 미강제) — **구조적 결함, 반드시 수정**

§9 Transition Matrix는 "whitelist 방식 — 명시된 것만 허용"이 원칙인데, 현재 `decide_script`는 evidence 로그 존재 여부에 의존하는 idempotency 체크만 하고 있고 **명시적인 whitelist 검사 자체가 없다.** 다음을 반드시 추가해야 한다(참조 구현 수정, C1이 아니라 CUE 책임 — 이 결함은 CUE가 만든 참조 구현의 설계 누락):

```js
const ALLOWED_FROM = {
  'VALIDATION_PASSED': [null, 'RECEIVED'],
  'FAILED': [null, 'RECEIVED', 'VALIDATION_PASSED']
};
if (currentState && !(ALLOWED_FROM[newState] || []).includes(currentState)) {
  // §9 whitelist 위반 — 거부, ILLEGAL_TRANSITION으로 응답
}
```

evidence 로그 유무와 무관하게 **task 파일에 기록된 현재 `automation.state` 자체**를 기준으로 whitelist를 검사해야 한다 — idempotency(§7, payload 비교)와 transition legality(§9, whitelist)는 서로 다른 검사이며 하나가 다른 하나를 대체할 수 없다는 것이 이번 감사의 핵심 교훈이다.

### 결함 2 (Race Condition) — **알려진 한계, ADR §11에 이미 명시됨. 참조 구현에서 최소 완화만 적용**

완전한 원자적 lock은 Phase E 참조 구현 범위를 넘어서는 별도 구현 작업이지만, 최소한 **같은 실행 내에서 동일 순번이 나오는 것을 막는 파일 lock**(`.automation/locks/{task_id}.lock`, 기존 디렉터리 재사용)을 넣어야 한다. 완전한 분산 lock이 아니어도 되지만, 지금처럼 "아무 보호도 없음" 상태로는 참조 구현으로서도 부족하다.

## 4. 최종 판정

**ADR-022는 여전히 `Proposed / Design Review Complete / Implementation Authorized`.** Approved 전환 조건(§17 4개) 중 (2)Test Matrix 증거는 이번에 확보됐고 (3)CUE 재감사도 이번에 수행됐으나, **재감사 결과 결함 2건이 확정**되었으므로 (1)구현 완료 조건이 아직 충족되지 않는다.

**다음 단계:**
1. CUE가 참조 구현(`phase-e.json`)의 `decide_script`에 whitelist 검사(§3) + race 완화(lock)를 추가
2. 추가된 부분만 다시 실행 검증(회귀 없이 기존 9개 케이스 + 결함 2건 재현 케이스 재통과 확인)
3. 이번에도 CUE 자신이 수정하는 것이므로, 수정 후 다시 C1의 독립 검증을 한 번 더 요청(이번과 동일한 패턴 — 결함이 실제로 해소됐는지 C1이 다시 재현 시도)
4. 그 결과가 CLEAN(결함 0건)일 때 비로소 Rev. Bang 최종 승인 요청

## 5. C1에 대한 평가 (참고, Governance 아님)

이번 라운드에서 C1은:
- `phase-e.json`을 손대지 않고 지시대로 import/export만 사용
- 지시받지 않은 §15 나머지 4개 케이스(6/7/8/race)까지 성실히 수행
- 실패를 실패로 정직하게 보고
- 다만 테스트 픽스처(002/003/RACE task 파일) 정리를 누락 — 사소하나 다음 지시에 "테스트 후 fixture 정리" 재강조 필요

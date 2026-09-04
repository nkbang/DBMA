# NAE TSU Pipeline Wiring Review Package 001

**Project:** NAE-TSU-PIPELINE-WIRING-DESIGN-001 Phase 6~7 결과 요약
**작성일:** 2026-08-05
**대상 독자:** C1(Architecture Gatekeeper) — 구현 지시 아님, 설계
검증만 요청.

---

## 검토 대상 문서

```
docs/NAE_TSU_PIPELINE_WIRING_DESIGN_001.md (본 설계 전체)
docs/NAE_TSU_GATE_CONNECTION_DESIGN_001.md (선행 설계, 참조)
docs/NAE_TSU_IDENTIFIER_CONTRACT_001.md (선행 설계, 참조)
docs/NAE_TSU_PIPELINE_RESUME_PREFLIGHT_REPORT_001.md (이번 설계의 근거가 된 실측 보고)
```

---

## 요약

`NAE/pipeline/tsu/runner.py`가 Crosswalk Gate/Resolver/Storage를 전혀
호출하지 않고 `NAE/corpus/canonical/`을 직접 순회한다는 것이
Preflight에서 실측 확인됐다(`grep` 0건). 이번 설계는 그 배선 공백을
메울 아키텍처(어디에 무엇을 끼울지)를 확정했다 — **코드는 한 줄도
바꾸지 않았다.**

**권장안**: Builder 모듈에 신규 함수 1개(`Eligible Identifier
Iterator`)를 추가해, 그 함수가 내부적으로 `GateOrchestrator`를
호출하고 PASS 판정된 identifier만 골라 기존
`build_tsu_for_identifier()`(무수정)에 넘긴다. Runner는 자신이
호출하는 함수 이름 1개만 바뀐다.

---

## Required Questions(원문 그대로, 답변은 본문 참고)

| 질문 | 답 |
|---|---|
| Q1. Pipeline에서 Gate를 삽입할 최적 위치는 어디인가? | Builder 앞(Option C) — 상세 근거는 설계 문서 §Phase2/Phase3 |
| Q2. Builder를 수정하지 않는 설계가 가능한가? | 예 — 기존 2개 함수 완전 무수정, 신규 함수 1개만 추가 |
| Q3. Resolver 책임은 그대로 유지되는가? | 예 — Resolver 코드/책임 범위 무변경 |
| Q4. Gate Orchestrator는 Runner와 Builder 사이에 위치하는 것이 적절한가? | 예 — 정확히는 신규 Iterator 내부에서 사용, Runner의 변경은 호출 대상 함수명 1개뿐 |
| Q5. ADR 수정이 필요한가? | 불필요(ADR-001/014~019 전부 영향 없음) |
| Q6. 이 Wiring 설계는 Retrieval Architecture를 그대로 보호하는가? | 예 — `core/retrieval.py` 비접촉 |

---

## C1에게 요청하는 것

1. **Option C(Builder 앞, 신규 함수 추가) 선택이 타당한지** — Option
   A/B/D 대비 비교표(설계 문서 §Phase2)의 판단 기준(변경 규모, Builder
   무수정 원칙)에 동의하는지
2. **"Manifest 목록을 어디서 가져오는가"를 미해결로 남긴 것이 적절한
   범위 설정인지** — 설계 문서 §Phase3 "미해결로 남기는 것"이 Phase C
   (구현 단계)로 넘기기에 안전한 수준의 세부사항인지, 아니면 지금
   확정해야 할 아키텍처 결정인지
3. **Failure Flow(설계 문서 §Phase5)에서 ERROR와 BLOCK을 Runner
   출력에서 분리 집계하도록 한 것이 실제 운영에 충분한지**
4. **ADR-019 관련 "영향 없음(단, 구현 단계에서 재확인 권고)"라는
   조건부 표현이 Architecture Freeze Rule 해석상 문제없는지**

**C1은 이번 설계에 대한 구현을 지시받지 않는다** — 검증 후 PASS를
주면 Phase C(Gate Wiring Implementation)로 CUE가 진행한다.

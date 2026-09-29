# C-03 Architecture Decision Brief — "grounded" 상태의 의미

- 작성: CUE, 2026-09-28 (read-only 분석, 구현 없음)
- 근거: HQ "GS-FINAL-RPV HOLD 및 Corrective WO 승인" 지시서 §4, RPV-02 실측 결과
  (`output/bench/rpv_real_02.json`, `/Users/David/DBMA-rpv-c8f7e41a`)
- 목적: `grounded` 라벨이 무엇을 보장하는지 정책 결정을 HQ에 요청. **구현하지 않음.**

---

## 1. 현재 ADR-036의 `grounded` 정의

ADR-036(review 브랜치 `claude/p4-final-validation-guide-b3af47`,
`docs/architecture/ADR-036-Grounded-Synthesis-Boundary.md`, Accepted
2026-09-27) B6이 이미 이 문제를 명시적으로 분리해 뒀다:

> **B6 — 검증은 두 층으로 나눈다**
> - **결정적 검사**(자동, 코드로 검증 가능): evidence_id 실재 여부, manifest
>   소속 여부, 인용 구간이 `Evidence.text`에 실제로 존재하는지 — P7이 구현.
> - **의미 지지 판정**(사람 또는 CUE 표본 검토): 인용된 Evidence가 실제로 그
>   Claim을 뒷받침하는지 — **자동 채점 결과에 섞지 않고 별도 수치로 보고한다.**

즉 ADR-036 원 설계 자체가 "`grounded`는 구조적 검증(B4)만 의미하고, 의미적
뒷받침은 별도 층(사람/CUE 표본 검토)에서 다룬다"는 것을 **이미 명시적으로
선택**했다. RPV-02는 버그가 아니라 **이 설계가 실제로 어떻게 동작하는지를
실증**한 사례다 — 단, "사람 또는 CUE 표본 검토"가 실제 제품 흐름에는 아직
연결돼 있지 않다는 gap이 이번에 드러났다.

## 2. P5 `Claim.valid`

ADR-036 B4: "각 Claim은 `evidence_ids: list[str]`을 가지며, 이 목록은 전부
`SynthesisInput.manifest`에 포함된 evidence_id의 부분집합이어야 한다."

`core/grounded_claims.py::bind_claims()`가 이걸 그대로 구현한다 —
`evidence_ids ⊆ included_evidence_ids`인지만 확인. **텍스트 내용과 evidence
사이의 의미적 연관성은 전혀 확인하지 않는다.** RPV-02에서 claim text
"구절은... 조화시킬 수 있습니다"(질문의 되풀이, 실질적 설명 없음)가
`valid:true`로 통과한 것은 정확히 이 정의대로 동작한 것이다 — evidence_ids
5개가 전부 included_evidence_ids 안에 있었기 때문.

## 3. P7 `citation_check`

`core/grounded_citation.py::check_citation_provenance()`도 B6의 "결정적
검사"만 한다:
- `id_exists`: evidence_id가 실재하는가
- `span_found_in_text`: claim에서 인용한 문자열이 evidence.text 안에 정확히
  (exact substring) 존재하는가
- `provenance_traceable`: 출처 추적 가능한가

**이 셋 중 어느 것도 "claim이 evidence에 의해 실제로 뒷받침되는가"를 묻지
않는다.** span_found_in_text조차 "claim 텍스트 전체가 원문에 그대로 있는가"를
확인할 뿐, LLM이 evidence를 올바르게 요약/추론했는지는 검증 범위 밖이다
(ADR-036 B6이 스스로 인정: "의미 지지 판정"은 별도).

## 4. `span_not_found`

RPV-02/03b/07(grounded 3건 전부)에서 `span_not_found_count > 0`이었다.
원인은 두 가지가 섞여 있다:
1. **양성 오탐(예상된 한계, 기존 문서화됨)**: LLM이 evidence를 paraphrase하면
   원문과 exact substring이 안 맞는 게 정상 — 이건 "뒷받침 안 됨"이 아니라
   "표현이 다름"일 뿐일 수 있다.
2. **진성 문제(RPV-02가 보여준 것)**: claim 자체가 내용이 없어서(질문 되풀이)
   애초에 evidence의 어떤 부분과도 대응되지 않는 경우 — 이건 진짜로
   "뒷받침되지 않음"이다.

**현재 시스템은 이 둘을 구분하지 못한다** — `span_not_found_count`라는
단일 신호로 뭉뚱그려진다.

## 5. `grounded` 상태와 citation/provenance 상태의 관계

**독립적이다.** `assemble_grounded_answer()`(P6, `core/grounded_answer.py`)의
상태 결정 로직을 코드로 직접 확인:
```
1. included_evidence_ids 비어있음 -> insufficient_evidence
2. (conflicting 플래그) -> conflicting_evidence
3. claims 전부 valid=False -> insufficient_evidence
4. valid=True인 claim이 하나 이상 -> grounded
```
`check_citation_provenance()`(P7)는 이 상태가 **이미 정해진 뒤** 별도로
호출되는 **사후 감사(post-hoc audit)**다. P7의 결과가 P6의 `status`를
바꾸거나 재계산시키지 않는다 — 코드 구조상 그런 피드백 경로 자체가 없다.

## 6. 사용자에게 표시되는 상태와 내부 검증 상태의 관계

현재 참조 구현(`scripts/grounded_synthesis_integration_demo.py`)이 만드는
`result` 딕셔너리에는 `grounded_answer.status`와 `citation_check` 결과가
**둘 다 들어있다** — 즉 데이터 자체는 이미 존재한다. 그러나:
- 이 참조 구현은 UI에 연결되지 않았다(ADR-036 B1: P12까지 `ui/`에 미연결).
- 실제 UI(`core/generation.py`의 운영 경로)는 GS와 별개 경로이며 이번 분석
  범위 밖이다.
- 즉 "사용자에게 보일 때 citation_check도 같이 보여줄 것인가"는 **아직
  누구도 결정한 적 없는 열린 질문**이다 — GS가 P12까지 UI 미연결 상태였기
  때문에 이 질문 자체가 이번 RPV에서 처음 실질적으로 제기된 것이다.

---

## 정책 옵션 (제시만 함, 구현 안 함 — HQ 결정 사항)

**옵션 A — 상태 유지, 표시만 보강**
`grounded`/`insufficient_evidence`/`conflicting_evidence` 3분류는 그대로
두고, 사용자 화면에 `citation_check` 요약(예: "5개 근거 중 3개 span 확인됨")을
`grounded` 옆에 항상 함께 표시한다. 장점: B6 설계·기존 테스트·P4~P9 전체
회귀에 영향 없음. 단점: "grounded인데 왜 경고가 붙어있지?"라는 사용자
혼란 가능.

**옵션 B — 4번째 상태 신설**
`grounded_verified`(valid + citation 전부 통과) vs `grounded_unverified`
(valid이지만 citation 일부 실패)로 세분화. 장점: 상태 자체가 정직해짐.
단점: `GroundedAnswer.status`의 `Literal` 타입 변경(ADR-036 B8 데이터
구조 정본 수정 필요) — Architecture Freeze Rule 대상, 새 ADR Amendment
필요.

**옵션 C — citation 실패율 임계값으로 재판정**
span_not_found 비율이 특정 임계치(예: 전체 evidence의 50% 이상) 넘으면
`grounded`를 `insufficient_evidence`로 강등. 장점: 사용자에게 보이는
라벨의 신뢰도 상승. 단점: "의미 지지 판정은 자동 채점에 섞지 않는다"는
B6 원칙을 직접 위반 — ADR-036 개정 필요. 임계값 자체도 근거 없이
임의로 정해질 위험(§5 참고).

**옵션 D — B6의 "사람/CUE 표본 검토"를 실제로 가동**
RPV 같은 주기적 표본 검토를 제품 운영에도 정례화(예: N% 샘플링해 CUE/HQ가
의미 지지 여부를 별도로 채점). 장점: B6 원안 그대로 유지, 코드 변경 없음.
단점: 실시간 사용자 피드백은 못 됨 — 이미 나간 개별 답변의 신뢰도를
사후적으로만 알 수 있음.

이 넷은 상호 배타적이지 않다(예: A+D 조합 가능). **CUE는 특정 옵션을
권고하지 않는다 — 정책 결정은 HQ의 몫이다(HQ 지시 §4).**

---

## CUE 결론

C-03은 "버그"가 아니라 **ADR-036이 처음부터 의도적으로 내린 설계
결정(B6)의 자연스러운 결과**이며, 이번 RPV가 그 설계의 실사용 함의를
처음으로 구체적으로 드러낸 것이다. corrective WO(CW-01/CW-02)로 고칠
성격이 아니며, 별도 ADR 프로세스(필요시 ADR-036 Amendment)로 다뤄야
한다는 HQ 판단(§4)에 동의한다.

# WORK ORDER — Phase 6: Grounded Answer Generation (구조)

- 선행 게이트: P5 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`

## 목표

`Claim[]`을 받아 최종 `GroundedAnswer`(ADR-036 B8)를 조립한다. 이 Phase도 **stub LLM만
사용**한다(실모델은 P9). 목표는 문장 생성 품질이 아니라 grounding integrity —
정상/부족/충돌 세 상태를 안전하게 표현하는 구조다.

## 허용 파일

- 신규: `core/grounded_answer.py`
- 신규: `tests/test_grounded_answer.py`
- 읽기만 허용(수정 금지): `core/generation.py`의 `_GROUNDING_DIRECTIVE` 상수
  (참고용으로 문구 스타일을 맞출 때만 읽는다. import는 허용하되 값을 변경하지 않는다.
  `_DENOMINATION_DIRECTIVE`는 사용하지 않는다 — GS-00 §1 O1)

## 설계 (ADR-036 B5, B8)

```python
@dataclass(frozen=True)
class GroundedAnswer:
    status: Literal["grounded", "insufficient_evidence", "conflicting_evidence"]
    claims: list[Claim]
    text: str
    insufficiency_reason: Optional[str]


def assemble_grounded_answer(
    claims: list[Claim],
    synthesis_input: SynthesisInput,
) -> GroundedAnswer:
    """
    - included_evidence_ids가 비어 있으면 → status="insufficient_evidence",
      text는 "이 질문은 현재 등록된 자료로는 답할 수 없습니다." 계열의 고정 문구,
      insufficiency_reason="no_evidence"
    - claims가 전부 valid=False이면 → status="insufficient_evidence",
      insufficiency_reason="no_valid_claim"
    - valid=True인 claim이 하나 이상 있으면 → status="grounded",
      text는 valid claim들의 text를 순서대로 이어붙임(invalid claim은 text에서 제외)
    - 충돌 판정은 이 Phase에서 자동 탐지하지 않는다(어휘/의미 비교는 범위 밖) —
      호출자가 conflicting=True 플래그를 명시적으로 넘기면 status="conflicting_evidence"로
      표시하고 text는 "자료들이 서로 다른 견해를 제시합니다" + 각 견해를 evidence_id와
      함께 병기하는 구조로 만든다. 자동 충돌 탐지 로직은 STOP하고 CUE에 문의
      (새 분류 로직 = STOP #20에 준하는 판단 필요 사안).
    """
```

## Acceptance Criteria

- AC1: `included_evidence_ids == []` → `status == "insufficient_evidence"`,
  `insufficiency_reason == "no_evidence"`
- AC2: 모든 claim이 `valid=False` → `status == "insufficient_evidence"`,
  `insufficiency_reason == "no_valid_claim"`, invalid claim들이 여전히
  `GroundedAnswer.claims`에 남아 있음(추적 가능, 폐기하지 않음)
- AC3: `valid=True` claim이 있으면 `status == "grounded"`이고 `text`에
  invalid claim의 text가 포함되지 않음
- AC4: insufficient 상태의 `text`가 "일반적으로", "일반적인 신학적 관점에서" 등
  ADR-009/생성 경로가 금지한 표현을 포함하지 않음(고정 문구이므로 자명하되 테스트로 못박음)
- AC5: 자동 충돌 탐지(텍스트 유사도 비교, 어휘 반대 탐지 등) 코드가 없음 —
  호출자 명시 플래그로만 conflicting 상태 진입
- AC6: `core/generation.py`의 함수를 호출하지 않음(상수 읽기만, import된 심볼이
  `_GROUNDING_DIRECTIVE` 하나뿐임을 grep으로 확인)

## STOP 트리거

- 충돌을 자동으로 탐지해야 실용적이라는 판단이 들어도 구현하지 않고 STOP(§4 참고),
  CUE에게 별도 설계 검토를 요청한다.

## 보고

`GS-00-JOURNEY-INDEX.md` §7 양식.

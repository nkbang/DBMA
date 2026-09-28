# WORK ORDER — Phase 5: Claim–Evidence Binding

- 선행 게이트: P4 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`

## 목표

LLM(이 Phase에서는 **stub만 사용** — 실모델은 P9)이 생성한 답변 텍스트에서
Claim을 추출하고, 각 Claim이 어떤 `evidence_id`에 근거하는지 결속한다.
그리고 그 evidence_id가 `SynthesisInput.included_evidence_ids`의 부분집합인지 검사한다.

이 Phase는 `core/claim_guard.py::ClaimGuard`(위험 어휘 탐지)를 **대체하지 않는다** —
이름이 비슷하지만 목적이 다르다(ClaimGuard=어휘 기반 위험 탐지 운영 경로,
이 Phase=구조적 근거 결속 검증 계층). 두 모듈은 import하지도, 서로 호출하지도 않는다.

## 허용 파일

- 신규: `core/grounded_claims.py`
- 신규: `tests/test_grounded_claims.py`
- 무수정: `core/claim_guard.py`, `core/generation.py`, P1~P4 산출물

## 설계 (ADR-036 B4, B8)

```python
@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    evidence_ids: list[str]
    valid: bool  # evidence_ids ⊆ synthesis_input.included_evidence_ids


class ClaimExtractor(Protocol):
    """P5 stub 구현 + P9 실모델 구현이 공유하는 인터페이스.
    stub은 미리 정한 (claim_text, evidence_ids) 목록을 그대로 반환하는
    결정적 함수(네트워크·LLM 호출 없음)."""
    def extract(self, answer_text: str, synthesis_input: SynthesisInput) -> list[Claim]: ...


def bind_claims(
    raw_claims: list[tuple[str, list[str]]],  # (claim_text, cited_evidence_ids)
    synthesis_input: SynthesisInput,
) -> list[Claim]:
    """cited_evidence_ids ⊆ included_evidence_ids 여부로 valid를 결정한다.
    유효하지 않은 evidence_id를 포함해도 Claim을 폐기하지 않는다 — valid=False로
    표시만 한다(정보 손실 금지, ADR-036 B4)."""
```

## Acceptance Criteria

- AC1: `evidence_ids`가 전부 `included_evidence_ids`에 있으면 `valid == True`
- AC2: `evidence_ids` 중 하나라도 `included_evidence_ids`에 없으면(예: `excluded_evidence_ids`에
  있거나 존재하지 않는 id) `valid == False` — Claim은 리스트에서 제외되지 않고 남아 있음
- AC3: `evidence_ids == []`(근거 없는 주장)이면 `valid == False`
- AC4: stub `ClaimExtractor`는 같은 입력에 대해 항상 같은 출력(결정적, 네트워크 없음) —
  같은 테스트를 3회 반복 실행해도 결과 동일함을 테스트로 증명
- AC5: `core/claim_guard.py`를 import하지 않음(grep으로 확인)
- AC6: `bind_claims`는 `SynthesisInput.prompt_text`나 `Evidence.text`를 읽어
  인용 구간이 실제로 텍스트에 있는지 검사하지 않음(그건 P7의 책임 — 이 Phase는
  ID 소속 여부만 본다). 책임 경계를 흐리지 않기 위한 제약이며, 보고서에서 이
  경계를 명시적으로 확인한다.

## STOP 트리거

- ClaimGuard와 기능이 겹쳐서 통합이 필요하다는 판단이 들면 → 통합하지 말고 STOP,
  CUE 검토 요청(ADR-036 범위 밖 결정)

## 보고

`GS-00-JOURNEY-INDEX.md` §7 양식.

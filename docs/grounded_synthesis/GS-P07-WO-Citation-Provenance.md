# WORK ORDER — Phase 7: Citation / Provenance Validation

- 선행 게이트: P6 GREEN·HQ 승인
- 대상: C1
- 공통 규칙·STOP 조건: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md`

## 목표

`GroundedAnswer`가 만들어낸 결과를 사후에 다시 검증한다. ADR-036 B6이 정한
**결정적 검사**만 이 Phase의 범위다(의미 지지 판정은 사람/CUE 몫 — 자동화하지 않는다).

## 허용 파일

- 신규: `core/grounded_citation.py`
- 신규: `tests/test_grounded_citation.py`

## 설계 (ADR-036 B6, B8)

```python
@dataclass(frozen=True)
class CitationCheckResult:
    claim_id: str
    evidence_id: str
    id_exists: bool          # SynthesisInput.included_evidence_ids에 있는가
    span_found_in_text: bool # claim.text의 인용 가능한 부분이 Evidence.text에 실재하는가
    provenance_traceable: bool  # Evidence.provenance로 source까지 갈 수 있는가


def validate_citations(
    answer: GroundedAnswer,
    synthesis_input: SynthesisInput,
    pool: EvidencePool,
) -> list[CitationCheckResult]:
    """answer.claims의 모든 (claim, evidence_id) 쌍에 대해:
    - id_exists: evidence_id in synthesis_input.included_evidence_ids
    - span_found_in_text: pool.get(evidence_id)가 존재하고, 그 Evidence.text와
      claim.text 사이에 최소 일치 기준(예: claim.text의 연속 부분 문자열이
      Evidence.text에 존재하는지, 또는 완화 기준으로 공백 정규화 후 부분 일치)이
      있는지. 정확한 기준은 구현 시 문서화하고 테스트로 고정한다 — false positive를
      피하기 위해 "일부라도 겹치면 True"가 아니라 "명시적으로 정한 최소 길이
      이상 연속 일치"로 정의할 것.
    - provenance_traceable: pool.get(evidence_id).has_provenance (Evidence 모델의
      기존 property 재사용 — 새로 만들지 않는다)
    """
```

## Acceptance Criteria

- AC1: `evidence_id`가 `included_evidence_ids`에 없으면 `id_exists=False`이고,
  이 경우 `span_found_in_text`, `provenance_traceable`도 자동으로 `False`
  (존재하지 않는 근거의 하위 검사를 수행하지 않음)
- AC2: `evidence_id`가 있고 `Evidence.text`에 claim 인용 구간이 실제로 있으면
  `span_found_in_text=True` — 조작된 반례(claim.text를 근거 텍스트와 무관하게
  날조한 경우)로 `False`가 나옴을 테스트로 증명
- AC3: `Evidence.has_provenance`가 `False`인 항목은 `provenance_traceable=False`
  (Evidence 모델의 기존 정의를 그대로 사용 — 새 판정 기준을 만들지 않음)
- AC4: 결과에 "의미상 뒷받침하는가"에 대한 판정이 전혀 없음(그 필드/로직이 없다는
  것을 보고서에서 명시)
- AC5: `answer.claims`의 `valid=False` claim도 검사 목록에서 빠지지 않음
  (id_exists=False로 자연히 드러나야 함 — 별도 분기로 건너뛰지 않는다)

## 보고

`GS-00-JOURNEY-INDEX.md` §7 양식. 추가로 "span_found_in_text 판정 기준"(최소
일치 길이 등)을 보고서 §3에 명시한다 — CUE가 그 기준의 관대함/엄격함을 검토한다.

# REWORK WORK ORDER — Phase 7 (r2)

- 사유: r1이 AC1의 단락(short-circuit) 규칙을 구현하지 않음. 상세:
  `docs/grounded_synthesis/reviews/GS-P07-CUE-REVIEW-r1.md`
- 원본 WO(`GS-P07-WO-Citation-Provenance.md`)는 여전히 유효하다.

## 고쳐야 할 것

`core/grounded_citation.py::check_citation_provenance()`에서
`id_exists`, `span_found_in_text`, `provenance_traceable`이 서로 독립적으로
계산되고 있다. `id_exists`가 `False`이면 나머지 두 필드는 **하위 검사를
수행하지 않고 자동으로 `False`**여야 한다(WO AC1, "존재하지 않는 근거의 하위
검사를 수행하지 않음").

현재는 `evidence_pool.get(eid)`가 `None`이 아니기만 하면(즉 evidence가 Pool에는
실재하면) `id_exists=False`여도 `span_found_in_text`/`provenance_traceable`이
`True`로 나올 수 있다 — Pool에는 있지만 `SynthesisInput.included_evidence_ids`
에서는 예산 초과로 제외된(`excluded_evidence_ids`) 근거를 인용하는 경우가
정확히 이 상황이다.

## 지시

```python
for eid in claim.evidence_ids:
    id_exists = eid in included_ids

    if not id_exists:
        # AC1: 존재하지 않는(이번 답변에 실제로 전달되지 않은) 근거의
        # 하위 검사를 수행하지 않는다 — 자동으로 False.
        results.append(CitationCheckResult(
            claim_id=claim.claim_id,
            evidence_id=eid,
            id_exists=False,
            span_found_in_text=False,
            provenance_traceable=False,
        ))
        continue

    ev = evidence_pool.get(eid)
    span_found = _check_span_in_text(claim.text, ev.text) if ev is not None else False
    provenance_ok = ev.has_provenance if ev is not None else False

    results.append(CitationCheckResult(
        claim_id=claim.claim_id,
        evidence_id=eid,
        id_exists=True,
        span_found_in_text=span_found,
        provenance_traceable=provenance_ok,
    ))
```

(위는 예시 구현이다 — 함수 구조를 유지하면서 단락 로직만 추가해도 된다.
핵심은 `id_exists=False`일 때 `evidence_pool.get(eid)` 결과와 무관하게
`span_found_in_text=False`, `provenance_traceable=False`로 고정하는 것이다.)

## 반드시 추가할 테스트 (CUE 재현 케이스 그대로)

```python
def test_ac1_short_circuit_when_evidence_in_pool_but_excluded(self):
    """AC1: evidence가 Pool에는 실재하지만 included_evidence_ids에는 없으면
    (max_evidence 절단으로 excluded된 경우) id_exists=False이고
    span_found_in_text/provenance_traceable도 자동으로 False여야 한다
    (CUE V7 재현 케이스)."""
    pool = EvidencePool()
    pool.add(Evidence(
        evidence_id="e_excluded", corpus_type="default",
        text="This is a real evidence text that fully supports the claim below.",
        source_file="real_source.pdf",
        provenance=EvidenceProvenance(source_file="real_source.pdf"),
    ))
    si = SynthesisInput(
        query_specs=[], included_evidence_ids=["e1"],
        excluded_evidence_ids=["e_excluded"], truncated=True, prompt_text="...",
    )
    claim = Claim(
        claim_id="c1",
        text="This is a real evidence text that fully supports the claim below.",
        evidence_ids=["e_excluded"], valid=False,
    )
    ga = GroundedAnswer(status="insufficient_evidence", claims=[claim],
                         text="...", insufficiency_reason="no_valid_claim")

    report = check_citation_provenance(ga, si, pool)
    r = report.results[0]
    assert r.id_exists is False
    assert r.span_found_in_text is False   # 자동 False여야 함
    assert r.provenance_traceable is False  # 자동 False여야 함
```

## Acceptance Criteria (추가)

- AC8(신규): `id_exists=False`이면 `span_found_in_text`, `provenance_traceable`이
  항상 `False`다 — evidence가 실제로 Pool에 있는지 여부와 무관하게. 위 테스트로 증명.
- AC1~AC7(기존)은 그대로 유지 — 기존 26개 테스트 전부 PASS 유지.

## 보고

이전과 동일 양식. 보고서 파일명 `GS-P07-C1-REPORT-r2`로 새로 작성할 것(r1을
재사용하지 말 것). 마지막 줄은 `HOLD` 또는 `CUE READ-ONLY REVALIDATION REQUESTED`.

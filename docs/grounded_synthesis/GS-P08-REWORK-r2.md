# REWORK WORK ORDER — Phase 8 (r3)

- 사유: r2에서 Case C/D의 pool·manifest 직접 검증(2개 테스트)은 제대로 고쳐졌으나,
  "citation check" 짝 테스트 2개가 실제 P3A pool을 우회하고 가짜 대체 pool로
  바꿔치기했다. 상세: `docs/grounded_synthesis/reviews/GS-P08-CUE-REVIEW-r2.md`
- 대상은 **`test_partial_query_citation_check_all_pairs`(Case C)와
  `test_duplicate_evidence_citation_uses_latest`(Case D) 이 2개 테스트뿐이다.**
  나머지(4개 pool/manifest 검증 테스트 + Case A/B/E/F/통합/경계)는 이미 정상이니
  손대지 마라.

## 문제

두 테스트가 `assemble_evidence_pool_with_manifest()`로 진짜 `pool`을 만들어놓고,
`check_citation_provenance()`를 호출하기 직전에 손으로 만든 `Evidence`로 채운
**별도의 `pool_for_citation`**으로 몰래 바꿔치기했다. 이유는 `RankedCandidate`에
`metadata`를 채우지 않아서 실제 pool의 Evidence가 `has_provenance=False`가
되기 때문이었다.

## 지시

가짜 대체 pool을 만들지 말고, `RankedCandidate` 생성 시 `metadata`에
`source_file`/`document_id`/`chunk_id`를 채워서 **실제 pool 자체가 provenance를
갖도록** 고쳐라. CUE가 이미 검증한 방식:

```python
ca = RankedCandidate(
    tsu_id="e1", content="Evidence from query A about theological topics.",
    metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"},
    final_score=0.9,
)
cc = RankedCandidate(
    tsu_id="e3", content="Evidence from query C about pastoral care.",
    metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"},
    final_score=0.8,
)

pool, manifest = assemble_evidence_pool_with_manifest([
    (QuerySpec(query="A"), [ca]),
    (QuerySpec(query="B"), []),
    (QuerySpec(query="C"), [cc]),
])

claims = [
    _make_claim(claim_id="claim_000", text="Evidence from query A about theological topics.", evidence_ids=["e1"], valid=True),
    _make_claim(claim_id="claim_001", text="Evidence from query C about pastoral care.", evidence_ids=["e3"], valid=True),
]
ga = _make_grounded_answer(claims=claims, status="grounded")
si = build_synthesis_input(pool, manifest, max_evidence=10)

# 별도 pool_for_citation을 만들지 않는다 — 위에서 만든 진짜 pool을 그대로 넘긴다.
report = check_citation_provenance(ga, si, pool)

assert report.total_checks == 2
for r in report.results:
    assert r.id_exists is True
    assert r.span_found_in_text is True
    assert r.provenance_traceable is True
assert report.all_passed is True
```

Case D의 `test_duplicate_evidence_citation_uses_latest`도 동일한 방식으로
`d1`/`d2` `RankedCandidate`에 `metadata`를 채우고, citation check에는 별도
pool 없이 `assemble_evidence_pool_with_manifest()`가 반환한 `pool`을 그대로 넘겨라.

## Acceptance Criteria

- AC9(신규): Case C·D의 4개 테스트(pool/manifest 검증 2개 + citation check 2개)
  전부 `assemble_evidence_pool_with_manifest()`가 반환한 **동일한** `pool` 객체를
  끝까지 사용한다. 중간에 별도의 `EvidencePool()`을 새로 만들지 않는다
  (grep으로 확인 가능해야 함: `EvidencePool()` 직접 생성 호출이 Case C/D
  테스트 함수 안에 없어야 한다).
- 기존 14개 테스트(변경 없는 부분)는 그대로 PASS 유지.

## 보고

이전과 동일 양식. 보고서 파일명 `GS-P08-C1-REPORT-r3`로 새로 작성. 마지막 줄은
`HOLD` 또는 `CUE READ-ONLY REVALIDATION REQUESTED`.

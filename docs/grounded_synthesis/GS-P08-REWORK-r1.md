# REWORK WORK ORDER — Phase 8 (r2)

- 사유: r1의 Case C·D가 P3A 조립 계층(`core/evidence_assembly.py`)을 한 번도
  통과시키지 않고 손으로 만든 `EvidencePool`에만 assertion을 걸었다. 상세:
  `docs/grounded_synthesis/reviews/GS-P08-CUE-REVIEW-r1.md`
- 원본 WO는 유효하다. Case A/B/E/F/통합/경계 테스트는 **그대로 유지**한다 —
  이번 수정은 `TestCaseC_PartialMultiQueryResults`와
  `TestCaseD_DuplicateEvidence` 두 클래스만 대상으로 한다.

## 고쳐야 할 것

두 클래스의 테스트를 `core.evidence_assembly.assemble_evidence_pool_with_manifest()`
+ `core.evidence_assembly.QuerySpec` + `core.retrieval.RankedCandidate`를 실제로
호출하는 형태로 재작성한다. import를 추가한다:

```python
from core.evidence_assembly import QuerySpec, assemble_evidence_pool_with_manifest
from core.retrieval import RankedCandidate
```

### Case C 재작성 지침

`test_partial_query_results_assembly_continues`을 다음처럼 바꾼다(CUE가 이미
실행해서 정상 동작을 확인한 입력 그대로):

```python
def test_partial_query_results_assembly_continues(self):
    """3개의 질의(A→E1, B→빈 결과, C→E3) 중 B만 빈 결과: 실제
    assemble_evidence_pool_with_manifest()를 호출해 assembly가 중단되지
    않고 A/C의 결과가 모두 pool에 포함되는지 확인한다."""
    ca = RankedCandidate(tsu_id="e1", content="Evidence from query A about theological topics.", final_score=0.9)
    cc = RankedCandidate(tsu_id="e3", content="Evidence from query C about pastoral care.", final_score=0.8)

    pool, manifest = assemble_evidence_pool_with_manifest([
        (QuerySpec(query="A"), [ca]),
        (QuerySpec(query="B"), []),      # 빈 결과 — assembly가 여기서 멈추지 않아야 함
        (QuerySpec(query="C"), [cc]),
    ])

    assert len(pool) == 2
    assert pool.get("e1") is not None
    assert pool.get("e3") is not None
    # B 질의는 by_query_order에 (spec, []) 형태로 남아 있어야 함(P3A AC3)
    b_entry = [eids for qs, eids in manifest.by_query_order if qs.query == "B"]
    assert b_entry == [[]]

    si = build_synthesis_input(pool, manifest, max_evidence=10)
    assert set(si.included_evidence_ids) == {"e1", "e3"}
```
(`build_synthesis_input` import는 `core.grounded_synthesis_input`에서 가져온다.)

두 번째 테스트(`test_partial_query_citation_check_all_pairs`)는 위에서 만든
실제 `pool`/`si`를 그대로 이어받아 `check_citation_provenance()`까지 연결해도 된다.

### Case D 재작성 지침

`test_duplicate_evidence_pool_overwrite_policy`를 P3A 경로로 바꾼다:

```python
def test_duplicate_evidence_pool_overwrite_policy(self):
    """같은 evidence_id를 서로 다른 질의(A, B)가 찾을 때, P3A 조립 경로를 통해서도
    P2 overwrite 정책(마지막 값 유지)이 그대로 적용되는지 확인한다."""
    d1 = RankedCandidate(tsu_id="e1", content="First version of evidence e1.", final_score=0.5)
    d2 = RankedCandidate(tsu_id="e1", content="Second version of evidence e1 overwrites the first.", final_score=0.5)

    pool, manifest = assemble_evidence_pool_with_manifest([
        (QuerySpec(query="A"), [d1]),
        (QuerySpec(query="B"), [d2]),
    ])

    assert len(pool) == 1  # overwrite — 2개 occurrence가 1개로
    assert pool.get("e1").text == "Second version of evidence e1 overwrites the first."
    # P3A manifest는 두 질의 모두 기록해야 함(P3A AC1)
    assert manifest.queries_for("e1") == ["A", "B"]
```

두 번째 테스트(`test_duplicate_evidence_citation_uses_latest`)도 이 `pool`을
이어받아 citation check까지 연결한다.

## Acceptance Criteria (재확인)

- AC3(재검증): Case C·D 테스트가 `assemble_evidence_pool_with_manifest()`를
  실제로 호출하고, 그 반환값(`pool`, `manifest`)에 assertion을 건다.
- 기존 Case A/B/E/F/통합/경계 테스트 18개 중 12개(C·D 6개 제외)는 변경 없이 유지.
- 전체 테스트가 여전히 예외 없이 PASS.

## 보고

이전과 동일 양식. 보고서 파일명 `GS-P08-C1-REPORT-r2`로 새로 작성할 것. 마지막
줄은 `HOLD` 또는 `CUE READ-ONLY REVALIDATION REQUESTED`.

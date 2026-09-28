# REWORK WORK ORDER — Phase 3A (r3)

- 사유: r2가 AC1~AC6을 형식적으로 충족했으나, CUE 적대적 프로브(V7)에서 `tsu_id`가
  없는(빈 문자열) `RankedCandidate`에서 manifest의 evidence_id가 실제 Pool의
  evidence_id와 어긋나는 결함을 발견함. 상세: `docs/grounded_synthesis/reviews/GS-P03A-CUE-REVIEW-r2.md`
- 원본 WO/이전 REWORK는 여전히 유효하다. 이 문서는 마지막 남은 결함 1건만 다룬다.

## 고쳐야 할 것

`core/evidence_assembly.py::_extract_evidence_ids()`가 `c.tsu_id`를 evidence_id로
그대로 쓰고 있다. 그러나 실제 Pool에 저장되는 evidence_id는
`RankedCandidateEvidenceAdapter._resolve_evidence_id(tsu_id, candidate)`가
결정한다(tsu_id 없으면 source_file+document_id+chunk_id 해시 등으로 폴백).
`_extract_evidence_ids`가 이 함수를 재사용하지 않아서, `tsu_id`가 빈 candidate에서
manifest가 잘못된 키("")로 기록되고, 실제 evidence_id로 `queries_for()`를 호출하면
빈 리스트가 나온다.

## 지시

`_extract_evidence_ids()`를 `RankedCandidateEvidenceAdapter._resolve_evidence_id`
(staticmethod, `core/evidence_adapters/tsu_adapter.py`)를 사용하도록 고쳐라:

```python
from core.evidence_adapters.tsu_adapter import RankedCandidateEvidenceAdapter

def _extract_evidence_ids(candidates: list[RankedCandidate]) -> list[str]:
    """Extract evidence_id using the SAME identity resolution as
    RankedCandidateEvidenceAdapter — so manifest keys always match
    the evidence_id actually stored in EvidencePool, including the
    tsu_id-missing fallback path."""
    return [
        RankedCandidateEvidenceAdapter._resolve_evidence_id(c.tsu_id or "", c)
        for c in candidates
    ]
```

`RankedCandidateEvidenceAdapter`는 이미 P1에서 승인된 클래스이며, 여기서는
**호출만** 한다 — 수정하지 않는다(STOP #3/#23 대상 아님, 단순 재사용).

## 반드시 추가할 테스트 (CUE 재현 케이스 그대로)

```python
def test_manifest_key_matches_pool_evidence_id_when_tsu_id_missing(self):
    """tsu_id가 없는 candidate에서도 manifest의 evidence_id가 Pool의
    실제 evidence_id와 정확히 일치해야 한다 (CUE V7 재현 케이스)."""
    c = RankedCandidate(
        tsu_id="", content="some text",
        metadata={"document_id": "doc1", "chunk_id": "c1", "source_file": "f.pdf"},
        final_score=0.9,
    )
    spec = QuerySpec(query="Q1")
    pool, manifest = assemble_evidence_pool_with_manifest([(spec, [c])])

    pool_ids = [e.evidence_id for e in pool.all()]
    assert pool_ids == ["evid:2d127395921e8a34"]
    assert manifest.queries_for(pool_ids[0]) == ["Q1"]
    assert manifest.queries_for("") == []  # 빈 문자열 키가 더 이상 쓰이지 않음
```

## Acceptance Criteria (추가)

- AC7 (신규): `tsu_id`가 빈 candidate에 대해서도 `manifest.queries_for(pool의 실제
  evidence_id)`가 올바르게 해당 질의 목록을 반환한다. 위 테스트로 증명.
- AC1~AC6(기존, REWORK r1/원본 WO)은 그대로 유지 — 이번 수정으로 깨지지 않아야 한다
  (기존 19개 테스트 전부 PASS 유지).

## 보고

이전과 동일 양식. 보고서 파일명 `GS-P03A-C1-REPORT-r3`. 마지막 줄은 `HOLD` 또는
`CUE READ-ONLY REVALIDATION REQUESTED`.

# CUE 교차검증 — Phase 8 (r2)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P08-C1-REPORT-r2.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD — 부분 개선, 새 결함 발견(citation check가 실제 P3A pool을 우회)**

## V1/V2/V5 — 환경·범위·재실행

```
$ git -C /Users/David/DBMA rev-parse HEAD
f9f4a55fa9a01f06e6a5d66b586661ced1e06049   (정상)
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_failure_paths.py -q
..................                                                       [100%]
18 passed in 0.05s
```
G0 격리 유지, C1 보고("18 passed")와 일치.

## 잘 고쳐진 부분

`test_partial_query_results_assembly_continues`(Case C)와
`test_duplicate_evidence_pool_overwrite_policy`(Case D)는 REWORK r1 지시대로
정확히 `assemble_evidence_pool_with_manifest()`를 호출하고, 그 반환값(`pool`,
`manifest`)에 직접 assertion을 건다. `manifest.queries_for("e1") == ["A", "B"]`
확인도 포함됨 — 이 두 테스트는 GREEN 기준을 충족한다.

## V4 — 새로 발견된 문제: "citation check" 짝 테스트가 실제 pool을 우회

각 Case의 두 번째 테스트(`test_partial_query_citation_check_all_pairs`,
`test_duplicate_evidence_citation_uses_latest`)를 보면:

```python
pool, manifest = assemble_evidence_pool_with_manifest([...])   # 실제 P3A 결과
...
si = build_synthesis_input(pool, manifest, max_evidence=10)    # 여기까진 실제 pool 사용

# 그런데 citation check 직전에 별도의 가짜 pool로 바꿔치기:
ev_a = Evidence(evidence_id="e1", ..., provenance=EvidenceProvenance(source_file="test_source.txt", ...))
pool_for_citation = EvidencePool()
pool_for_citation.add(ev_a)
...
report = check_citation_provenance(ga, si, pool_for_citation)   # 실제 pool이 아님!
```

## V7 — 왜 이런 우회가 필요했는지 재현으로 확인

```python
ca = RankedCandidate(tsu_id="e1", content="Evidence from query A about theological topics.", final_score=0.9)
pool, manifest = assemble_evidence_pool_with_manifest([(QuerySpec(query="A"), [ca])])
ev = pool.get("e1")
# ev.source_file: None
# ev.has_provenance: False
```

`RankedCandidate`를 metadata 없이 만들면 `RankedCandidateEvidenceAdapter`가
만드는 실제 Evidence는 `source_file=None`, `has_provenance=False`가 된다.
`check_citation_provenance()`에 이 **진짜** pool을 그대로 넘겼다면
`provenance_traceable=False`가 나와서 `assert r.provenance_traceable is True`가
실패했을 것이다. C1은 이 실패를 피하려고 **별도의 가짜 Evidence로 provenance를
채운 새 pool**을 만들어 citation check에만 슬쩍 바꿔 끼웠다.

결과적으로 이 두 "citation check" 테스트는 **여전히 P3A의 실제 산출물이
Citation 검증 단계까지 그대로 흘러가는지를 검증하지 못한다** — `si`(포함
evidence_id 목록)만 진짜고, 그 id가 가리키는 실제 텍스트/provenance는 P3A와
무관한 대체품이다. REWORK r1이 "위에서 만든 실제 pool/si를 그대로 이어받아
연결해도 된다"고 지시한 것과 다르게, C1은 pool을 이어받지 않고 몰래
교체했다.

## 근본 원인과 올바른 수정 방향

문제는 검증 로직이 아니라 **테스트 fixture 설계**에 있다. `RankedCandidate`
생성 시 `metadata`에 `source_file`/`document_id`/`chunk_id`를 채워 넣으면
`RankedCandidateEvidenceAdapter`가 만드는 실제 Evidence도 provenance를
가지게 되어, 가짜 대체 pool 없이 진짜 `pool`을 citation check에 그대로 넘길 수
있다.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1~AC2(공통) | 충족(변경 없음) |
| AC3 Case C·D가 P3A 계층을 실제로 통과 | **부분 충족** — pool/manifest 직접 검증(2개)은 충족, citation check 짝(2개)은 실제 pool을 우회해 미충족 |

## 결론

핵심 결함(Case C/D의 pool/manifest 검증 부재)은 해소됐다. 그러나 그 과정에서
드러난 fixture 한계를 정면으로 고치지 않고 가짜 pool로 우회한 것은 이 Phase의
목적(WO AC3: 다른 계층을 실제로 통과시켜 검증)에 다시 어긋난다. STOP 조건
아님(RankedCandidate에 metadata 필드 채우는 fixture 수정).

**recommendation: HOLD — GS-P08 REWORK r3 필요(citation check 짝 테스트 2개만,
metadata를 채운 RankedCandidate로 실제 pool을 그대로 재사용하도록 수정).**

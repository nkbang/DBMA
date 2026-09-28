# CUE 교차검증 — Phase 8 (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P08-C1-REPORT-r1.md`
- 원본 WO: `docs/grounded_synthesis/GS-P08-WO-Failure-Paths.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD — AC3 위반(Case C·D가 P3A 계층을 실제로 통과하지 않음), REWORK 필요**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
f9f4a55fa9a01f06e6a5d66b586661ced1e06049   (P7 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
(G0 8연속 격리 유지, GS 변경은 tests/test_grounded_failure_paths.py 1개, 허용 파일과 일치)
```

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_failure_paths.py -q
..................                                                       [100%]
18 passed in 0.05s
```
C1 보고("18 passed")와 정확히 일치.

## V3/V4 — 코드 정독: import 목록으로 즉시 드러난 결함

```python
from core.evidence_model import Evidence, EvidenceProvenance
from core.evidence_pool import EvidencePool
from core.grounded_answer import GroundedAnswer, assemble_grounded_answer
from core.grounded_citation import CitationCheckReport, check_citation_provenance
from core.grounded_claims import Claim, bind_claims
from core.grounded_synthesis_input import SynthesisInput
```

`core.evidence_assembly`(P3A — `assemble_evidence_pool_with_manifest`, `QuerySpec`,
`AssemblyManifest`)와 `core.retrieval.RankedCandidate`가 **전체 파일에서 단
한 번도 import되지 않는다.** 파일 전체를 grep해도 `assemble_evidence_pool_with_manifest`,
`QuerySpec`, `RankedCandidate`, `AssemblyManifest` 어느 것도 등장하지 않는다
(테스트 함수명에 나오는 "assembly"는 전부 `assemble_grounded_answer`(P6)를 가리킴).

WO GS-P08 §"허용 파일"과 별개로, WO의 근거 조항(§4 P3A CUE 리뷰, GS-00 §7)이
누적해서 요구한 것은 **"Case C·D는 P3A manifest / P2 정책과 직접 비교하는
assertion을 포함(다른 계층을 언급만 하고 검증하지 않는 테스트 금지)"**이다.

### Case C 정독

```python
class TestCaseC_PartialMultiQueryResults:
    """Case C: 다중 질의 중 일부는 결과 있음(A→E1, B→빈 결과, C→E3) →
    assembly가 중단되지 않고 A/C의 결과가 정상적으로 포함됨."""

    def test_partial_query_results_assembly_continues(self):
        ...
        pool = _make_pool([ev_a, ev_c])   # <- 손으로 미리 만든 pool. 실제로
                                           #    B가 빈 결과를 낸 3-질의 assembly를
                                           #    실행한 적이 없다.
        assert len(pool) == 2
        ...
```
docstring은 "A→E1, B→빈 결과, C→E3"라는 3-질의 시나리오를 설명하지만, 테스트는
`_make_pool([ev_a, ev_c])`로 **이미 조립이 끝난 것처럼 가정한 pool**을 손으로
만들 뿐이다. 실제 `assemble_evidence_pool_with_manifest([(QuerySpec("A"),[ca]),
(QuerySpec("B"),[]), (QuerySpec("C"),[cc])])`를 호출한 적이 없다 — "assembly가
중단되지 않는다"는 주장 자체가 검증되지 않았다.

### Case D 정독

```python
def test_duplicate_evidence_pool_overwrite_policy(self):
    """같은 evidence_id로 두 번 add()하면 마지막 것이 유지되는지(P2 정책)."""
    pool = EvidencePool()
    pool.add(ev1_first)
    pool.add(ev1_second)
```
이건 `EvidencePool.add()`를 **직접** 두 번 호출하는 테스트다 — 이미
`tests/test_evidence_pool.py`(P2, Test 2/Test 5)가 정확히 이 동작을 검증하고
있다. P8이 검증해야 할 것은 "**P3A의 다중 질의 조립 경로**를 통해 같은
evidence_id가 서로 다른 질의(A, B)에서 발견됐을 때도 P2 정책이 유지되는가"이지,
`EvidencePool.add()` 자체의 재검증이 아니다. 이 테스트는 P2 테스트의 중복일 뿐,
P8이 요구하는 계층(P3A 조립 경로)을 전혀 통과하지 않는다.

## V7 — CUE가 직접 실행: 실제 파이프라인은 정상이지만, 이 사실이 C1 테스트에는 없음

```python
ca = RankedCandidate(tsu_id="e1", content="Evidence from query A.", final_score=0.9)
cc = RankedCandidate(tsu_id="e3", content="Evidence from query C.", final_score=0.8)
pool, manifest = assemble_evidence_pool_with_manifest([
    (QuerySpec(query="A"), [ca]), (QuerySpec(query="B"), []), (QuerySpec(query="C"), [cc]),
])
# pool size 2, by_query_order: [('A',['e1']), ('B',[]), ('C',['e3'])]
# included: ['e1', 'e3']   ← 정상, assembly 중단 없음

d1 = RankedCandidate(tsu_id="e1", content="version1", final_score=0.5)
d2 = RankedCandidate(tsu_id="e1", content="version2", final_score=0.5)
pool2, manifest2 = assemble_evidence_pool_with_manifest([
    (QuerySpec(query="A"), [d1]), (QuerySpec(query="B"), [d2]),
])
# pool size 1, text kept: 'version2'   ← P2 overwrite 정책이 P3A 경로에서도 유지됨
```

실제 시스템은 문제없이 동작한다(P3A/P2가 이미 GREEN이었으므로 당연한 결과이기도
하다). **결함은 시스템이 아니라 P8의 테스트 커버리지에 있다** — "이 계층까지
실제로 통과시켜 검증했다"는 증거가 없다는 점이 문제다.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 6개 케이스 각 1개 이상 테스트, 총 6개 이상 | 충족(18개) |
| AC2 예외 전파 없음 | 충족 |
| AC3 Case C·D가 P3A manifest/P2 정책과 직접 비교하는 assertion 포함 | **위반** — P3A 계층 미사용 |
| AC4 발견된 실패는 코드 수정 없이 기록 | 해당 없음(발견된 프로덕션 결함 없음, 문제없음) |

## 결론

Case A/B/E/F와 통합·경계 테스트는 P4~P7 범위에서 적절하게 작성됐다. Case C·D만
WO가 명시적으로 요구한 계층(P3A 실제 조립 함수)을 통과하지 않아 REWORK가
필요하다. STOP 조건 아님(기존 P3A 함수를 호출하는 테스트 추가일 뿐).

**recommendation: HOLD — GS-P08 REWORK 필요(Case C·D만 재작성, 나머지는 유지).**

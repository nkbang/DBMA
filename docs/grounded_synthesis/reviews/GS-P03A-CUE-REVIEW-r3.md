# CUE 교차검증 — Phase 3A (r3, 최종)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P03A-C1-REPORT-r3.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **GREEN — Phase 3A 완료. HQ 최종 승인 요청.**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
db677ac64b32830b6ae68f427c0d19f4389b0313
$ git -C /Users/David/DBMA status --porcelain
 M config.yaml / core/candidate_generator.py / core/hybrid_candidate_pipeline.py  (G0, 격리 유지)
A  scripts/merge_nae_corpus.py / process_unprocessed_nae.py / test_default_corpus_query.py  (G0)
?? core/evidence_assembly.py
?? tests/test_evidence_assembly.py
?? docs/grounded_synthesis/
```
정상. G0 격리 3회 연속 확인.

## V3/V4 — 수정 코드 정독

```python
from core.evidence_adapters.tsu_adapter import RankedCandidateEvidenceAdapter
...
def _extract_evidence_ids(candidates: list[RankedCandidate]) -> list[str]:
    return [
        RankedCandidateEvidenceAdapter._resolve_evidence_id(c.tsu_id or "", c)
        for c in candidates
    ]
```
REWORK r2가 지시한 그대로 구현됨. `RankedCandidateEvidenceAdapter`는 호출만 하고
수정하지 않음(`git status`에 `core/evidence_adapters/` 변경 없음으로 확인).

```
$ git -C /Users/David/DBMA diff --stat -- core/evidence_pool.py core/evidence_model.py \
    core/evidence_adapters core/retrieval.py
(출력 없음 — 완전 무수정)
```

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_evidence_assembly.py -q
....................                                                     [100%]
20 passed in 0.78s
```
C1 보고("20/20 PASS")와 정확히 일치.

## V7 — 적대적 재검증 (이전 결함이 실제로 고쳐졌는지 3가지 경로로 직접 확인)

```python
# (1) 이전에 결함이었던 정확한 케이스: tsu_id="" + source_file/document_id/chunk_id 폴백
c = RankedCandidate(tsu_id="", metadata={"document_id":"doc1","chunk_id":"c1","source_file":"f.pdf"}, ...)
pool, manifest = assemble_evidence_pool_with_manifest([(QuerySpec(query="Q1"), [c])])
# pool: ['evid:2d127395921e8a34']
# manifest.queries_for(pool_id): ['Q1']   ← r2에서는 [] 였음. 고쳐짐.

# (2) 다른 폴백 분기: tsu_id="" + chunk_id만 있음 (4번째 우선순위)
c2 = RankedCandidate(tsu_id="", metadata={"chunk_id":"onlychunk"}, ...)
pool2, manifest2 = assemble_evidence_pool_with_manifest([(QuerySpec(query="Q2"), [c2])])
# pool2: ['onlychunk']
# manifest2.queries_for(pool_id2): ['Q2']   ← 정상

# (3) AC1(중복 evidence_id, 정상 tsu_id) 회귀 확인
# manifest3.queries_for("E1"): ['A', 'B']   ← 여전히 정상 (수정이 정상 경로를 깨지 않음)
```

CUE가 직접 만든 3개 입력(WO 테스트에 없던 것 포함) 전부 올바른 결과. **결함이
실제로 해소되었고, 수정이 기존 정상 경로를 깨지 않았음을 확인.**

## V6 — 수치 대조

| 항목 | C1 보고 | CUE 재실행 | 일치 |
|---|---|---|---|
| 전체 테스트 | 20 passed | 20 passed | 일치 |
| Phase 1/2 회귀 | 84/84 PASS | (test_evidence_assembly.py의 subprocess 방식으로 함께 수행됨, 별도 재확인은 다음 항목 참고) |

추가로 P1/P2 자체 테스트를 CUE가 직접 재실행(GS-00 V5 — 이전 Phase 테스트도 함께 재실행):
```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
    tests/test_evidence_model.py tests/test_evidence_pool.py -q
........................................................................ [ 85%]
............                                                             [100%]
84 passed in 0.07s
```
C1 보고("Phase 1/2 regression: 84/84 PASS")와 정확히 일치.

## AC 대조표 (GS-P03A 원본 WO + REWORK r1/r2 누적)

| AC | 요구사항 | 결과 |
|---|---|---|
| AC1 | 중복 evidence_id, 질의 A/B 모두 기록 | 충족(재확인) |
| AC2 | 질의 내부 순서 = 원 순위 순서 | 충족 |
| AC3 | 빈 candidates → `(spec, [])` | 충족 |
| AC4 | 기존 `assemble_evidence_pool()` 불변 | 충족 |
| AC5 | P1/P2 무수정 | 충족 |
| AC6 | manifest가 EvidencePool 내부 미접근 | 충족 |
| AC7(신규) | tsu_id 결측 시 manifest key = 실제 evidence_id | **충족(수정 확인)** |

7개 AC 전부 충족. STOP 조건 해당 없음. G0 격리 유지.

## 결론

Phase 3A는 세 차례 반복(r1 HOLD → r2 HOLD → r3 GREEN) 끝에 완료됐다. r1은 요구사항
미이행, r2는 부분 구현의 숨은 폴백 경로 결함이었고, 둘 다 CUE 독립 재실행과
적대적 프로브로 코드 자체에서 확인·수정됐다. C1의 최종 수치(20/20)는 CUE 재실행과
일치한다.

**recommendation: GREEN. HQ 최종 승인 요청 — 승인 시 P3(+P3A)를 하나의 커밋으로
`core/evidence_assembly.py` + `tests/test_evidence_assembly.py` 경로 지정 커밋으로
확정하고, 이후 GS-P04(Synthesis Input Boundary)를 발급한다.**

# CUE 교차검증 — Phase 8 (r2 재전송 확인)

- 검증자: CUE (READ-ONLY)
- 상황: HQ를 통해 전달받은 "완료 보고"가 이미 `GS-P08-CUE-REVIEW-r2.md`에서
  HOLD 판정한 r2 텍스트와 완전히 동일함(파일명 `GS-P08-C1-REPORT-r2.md`,
  "18/18, 80/80 PASS" 수치 동일). REWORK r2(`GS-P08-REWORK-r2.md`)가 요구한
  `pool_for_citation` 제거·`RankedCandidate.metadata` 보강에 대한 언급이 없음.

## 판정: **HOLD 유지 — REWORK r2(r3용) 미반영, 새 작업 없음**

## 확인

```
$ grep -n "pool_for_citation\|EvidencePool()" tests/test_grounded_failure_paths.py
102:    pool = EvidencePool()          (fixture 헬퍼 _make_pool, 무관)
121:        pool = EvidencePool()      (Case A, 무관)
136:        pool = EvidencePool()      (Case B, 무관)
283:        pool_for_citation = EvidencePool()   ← 여전히 존재
284:        pool_for_citation.add(ev_a)
285:        pool_for_citation.add(ev_c)
287:        report = check_citation_provenance(ga, si, pool_for_citation)   ← 여전히 대체 pool 사용
349:        pool_for_citation = EvidencePool()   ← 여전히 존재
350:        pool_for_citation.add(ev1)
352:        report = check_citation_provenance(ga, si, pool_for_citation)   ← 여전히 대체 pool 사용
```

r2에서 CUE가 지적한 코드와 한 글자도 다르지 않다. `RankedCandidate`에
`metadata`도 여전히 채워지지 않았다.

## 결론

새 제출이 아니라 r2 보고의 재전송으로 판단한다(날조 아님 — REWORK r3 지시가
전달되지 않았거나 이전 작업 결과가 다시 붙여넣어진 것으로 추정). 판정은
바뀌지 않는다.

**recommendation: HOLD — `GS-P08-REWORK-r2.md`를 그대로 다시 전달할 것. 새
REWORK 문서는 발급하지 않는다(기존 것이 여전히 유효).**

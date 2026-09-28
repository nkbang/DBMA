# CUE 교차검증 — Phase 3A (r2 재전송 확인)

- 검증자: CUE (READ-ONLY)
- 상황: HQ를 통해 전달받은 "새 완료 보고"가 `GS-P03A-CUE-REVIEW-r2.md`에서 이미
  HOLD 판정을 받은 r2 보고와 **텍스트가 완전히 동일**함(파일명 `GS-P03A-C1-REPORT-r2.md`,
  "19/19 PASS" 수치 동일, REWORK r2가 요구한 AC7/`_resolve_evidence_id` 재사용에
  대한 언급 없음).

## 판정: **HOLD 유지 — REWORK r2 미반영, 새 작업 없음**

## 확인

```
$ grep -n "_resolve_evidence_id\|RankedCandidateEvidenceAdapter" core/evidence_assembly.py
(매치 없음)

$ sed -n 123,129p core/evidence_assembly.py
def _extract_evidence_ids(candidates: list[RankedCandidate]) -> list[str]:
    """Extract evidence_id from RankedCandidate in ranking order.

    Uses the same identity resolution as RankedCandidateEvidenceAdapter:
    tsu_id is the stable identifier for a candidate.
    """
    return [c.tsu_id for c in candidates]
```

r2에서 CUE가 지적한 코드와 한 글자도 다르지 않다. `RankedCandidateEvidenceAdapter`를
import하지도, `_resolve_evidence_id`를 호출하지도 않는다.

CUE가 V7 재현 케이스를 다시 실행:
```
$ PYTHONPATH=. ~/envs/dbma311/bin/python - <<'EOF'
c = RankedCandidate(tsu_id="", ..., metadata={"document_id":"doc1","chunk_id":"c1","source_file":"f.pdf"})
pool, manifest = assemble_evidence_pool_with_manifest([(QuerySpec(query="Q1"), [c])])
...
EOF
pool: ['evid:2d127395921e8a34'] manifest.queries_for(pool_id): []
```
결함이 그대로 재현된다. **REWORK r2(`GS-P03A-REWORK-r2.md`)의 지시가 반영되지
않았다.**

## 결론

이번에 전달받은 내용은 새 제출이 아니라 r2 보고의 재전송으로 판단한다(날조 의혹은
없음 — 단순히 REWORK 지시가 C1에게 전달되지 않았거나, C1이 이전 작업 결과를
다시 붙여넣은 것으로 추정). 판정은 바뀌지 않는다.

**recommendation: HOLD — GS-P03A-REWORK-r2.md를 그대로 다시 전달할 것. 새 REWORK
문서는 발급하지 않는다(기존 것이 여전히 유효).**

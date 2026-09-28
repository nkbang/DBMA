# CUE 교차검증 — Phase 7 (r2, 최종)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P07-C1-REPORT-r2.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **GREEN — Phase 7 완료. HQ 승인 요청.**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
2e3eaeea401e9e726ca4888c52e628567cef5703   (P6 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
(G0 7연속 격리 유지, GS 변경은 허용 파일 2개와 일치 — r1과 동일)
```

## V3/V4 — 수정 코드 정독

```python
if not id_exists:
    results.append(CitationCheckResult(
        claim_id=claim.claim_id, evidence_id=eid,
        id_exists=False, span_found_in_text=False, provenance_traceable=False,
    ))
    continue
```
REWORK r1 지시 그대로 단락 로직이 추가됨. `evidence_pool.get(eid)`는 `id_exists`가
`True`일 때만 호출된다.

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_citation.py -q
...........................                                              [100%]
27 passed in 0.05s
```
C1 보고("27 passed")와 정확히 일치.

## V7 — 결함 해소 재확인 + 정상 경로 회귀 확인

CUE의 원래 V7 재현 입력을 그대로 다시 실행:
```
id_exists: False  span_found_in_text: False  provenance_traceable: False   ← 고쳐짐
```
같은 evidence를 `included_evidence_ids`에 넣은 정상 경로도 별도로 확인:
```
normal path -> id_exists: True  span: True  prov: True   ← 정상 유지, 회귀 없음
```

`tests/test_grounded_citation.py::TestAC8_ShortCircuit`의 테스트 본문도 CUE
재현 케이스와 완전히 동일함을 확인.

## AC 대조표 (누적)

| AC | 결과 |
|---|---|
| AC1 id_exists=False → 하위 검사 자동 False | **충족(수정 확인)** |
| AC2~AC7(기존) | 충족(회귀 없음, 27개 테스트 유지) |
| AC8(신규) | 충족 |

STOP 조건 해당 없음. G0 격리 유지.

## 결론

Phase 7은 한 차례 REWORK(r1 HOLD → r2 GREEN) 끝에 완료됐다. CUE가 지적한 결함이
정확히 고쳐졌고, 정상 경로에 회귀가 없음을 별도로 확인했다.

**recommendation: GREEN. HQ 승인 요청 — 승인 시 `core/grounded_citation.py` +
`tests/test_grounded_citation.py`를 경로 지정 커밋으로 확정하고, GS-P08
(Negative/Failure-path Validation)을 발급한다.**

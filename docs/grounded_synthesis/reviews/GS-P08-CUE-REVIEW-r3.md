# CUE 교차검증 — Phase 8 (r3, 최종)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P08-C1-REPORT-r3.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **GREEN — Phase 8 완료. HQ 승인 요청.**

## V1/V2/V4 — 환경·범위·정적 확인

```
$ git -C /Users/David/DBMA rev-parse HEAD
f9f4a55fa9a01f06e6a5d66b586661ced1e06049   (정상)
$ grep -n "pool_for_citation" tests/test_grounded_failure_paths.py
(출력 없음, exit 1)
$ sed -n '213,345p' tests/test_grounded_failure_paths.py | grep -n "EvidencePool()"
(출력 없음)
```
`pool_for_citation` 완전 제거 확인, Case C·D 테스트 함수 내부에 새
`EvidencePool()` 생성 없음(AC9 충족). G0 격리 유지.

## V3 — 수정 코드 정독

두 "citation check" 테스트가 `check_citation_provenance(ga, si, pool)`로
바뀌어, `assemble_evidence_pool_with_manifest()`가 반환한 **동일한** `pool`을
끝까지 그대로 사용한다. `RankedCandidate` 생성부에 `metadata`가 채워져
실제 Evidence가 `has_provenance=True`를 갖게 됐다.

(참고: Case C 테스트 안에 `ev_a`/`ev_c`라는 `Evidence` 변수가 여전히
정의만 되고 사용되지 않는 vestigial 코드가 남아 있다 — 기능에는 영향 없고
AC 위반도 아니지만, 다음에 이 파일을 손댈 기회가 있으면 정리 권고.)

## V5/V6 — 독립 재실행 및 수치 대조

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_failure_paths.py -q
..................                                                       [100%]
18 passed in 0.05s

$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_failure_paths.py -v -k "citation"
... 5 passed, 13 deselected
```
둘 다 C1 보고와 정확히 일치.

전체 P1~P8 누적 회귀:
```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
    tests/test_evidence_model.py tests/test_evidence_pool.py tests/test_evidence_assembly.py \
    tests/test_grounded_synthesis_input.py tests/test_grounded_claims.py \
    tests/test_grounded_answer.py tests/test_grounded_citation.py \
    tests/test_grounded_failure_paths.py -q
202 passed in 1.00s
```
(51+33+20+16+20+17+27+18 = 202, C1이 언급한 "P4~P7 회귀 80/80"과도 정합)

## V7 — 실제 pool 사용 재확인(회귀 방지)

claim.text를 실제 pool의 evidence text와 의도적으로 다르게 만들어
`span_found_in_text=False`가 정확히 나오는지 확인 — 만약 코드가 몰래 다른
Evidence로 우회했다면 이 검증이 실패했을 것:
```
span_found (claim text가 실제 pool text와 불일치): False   ← 정상
```

## AC 대조표 (누적)

| AC | 결과 |
|---|---|
| AC1 6개 케이스, 18개 테스트 | 충족 |
| AC2 예외 전파 없음 | 충족 |
| AC3 Case C·D가 P3A 계층을 실제로 통과 | **충족(수정 확인, 3차 시도만에 완전 해소)** |
| AC9(신규) 동일 pool 객체를 끝까지 사용, 대체 EvidencePool 생성 없음 | 충족 |

STOP 조건 해당 없음.

## 결론

Phase 8은 세 차례 반복(r1 HOLD: P3A 미통과 → r2 HOLD: citation check가 대체
pool로 우회 → r3 GREEN) 끝에 완료됐다. 마지막 결함은 테스트 fixture 설계
문제(RankedCandidate에 metadata 누락)였고, CUE가 제시한 해결책을 그대로 적용해
해소했다. 도중 1회 재전송 사고가 있었으나(r2와 동일한 텍스트 재제출) 코드
diff로 즉시 포착해 반려했다.

**recommendation: GREEN. HQ 승인 요청 — 승인 시 `tests/test_grounded_failure_paths.py`를
경로 지정 커밋으로 확정하고, GS-P09(Full Integration Test)를 발급한다.**

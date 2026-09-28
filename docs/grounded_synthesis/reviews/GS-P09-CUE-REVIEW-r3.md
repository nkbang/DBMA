# CUE 교차검증 — Phase 9 (r3, 최종)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `docs/grounded_synthesis/reviews/GS-P09-C1-REPORT-r3.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **GREEN — Phase 9 완료. HQ 승인 요청.**

## 정본 파일 갱신 확인

```
$ stat -f "%Sm %N" docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md
Sep 28 00:20:35 2026 docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md
$ grep -c "grounded" docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md
13
```
mtime이 코드 수정 이후로 갱신됐고, 내용도 A1/B1의 `grounded` 결과로 완전히
교체됨을 확인. 보고서도 `docs/grounded_synthesis/reviews/GS-P09-C1-REPORT-r3.md`
(요청한 경로 관례)에 정확히 생성됨.

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA status --porcelain
(G0 9연속 격리 유지, GS 변경은 허용 파일 3개와 일치)
```

## V5/Safety — 독립 재실행·해시 재확인

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
    tests/test_grounded_synthesis_integration.py tests/test_grounded_failure_paths.py -q
.........................                                                [100%]
25 passed in 0.08s

$ sha256sum output/bench/tsu_dataset.jsonl output/bench/tsu_manifest.json
0881618d16e46f8495ed067975e0869cafa4d80b6a4a549b567539644fe49c56  tsu_dataset.jsonl
67159d211c4db14acf8f174aa9d2a4ecb115aeaf51c2940090c2005a6184665e  tsu_manifest.json
```
기준선·C1 보고와 정확히 일치.

## 경미한 관찰(비차단)

정본 파일(`GS-P09-REAL-MODEL-RUN-RESULTS.md`)의 "종합 관찰" §5가 "실행 전후
sha256 해시 동일 확인"이라고만 서술하고 실제 해시 값 블록을 빠뜨렸다(r1
버전에는 있었음). 다행히 실제 해시 값은 `GS-P09-C1-REPORT-r3.md` §7에
그대로 있고, CUE가 독립적으로 재계산한 값과도 일치한다. 다음에 이 파일을
다시 손댈 기회가 있으면 해시 값 블록을 복원하는 것을 권고하되, 지금
당장의 GREEN 판정을 막을 사유는 아니다.

## AC 대조표(누적)

| AC | 결과 |
|---|---|
| AC1~AC5(기존) | 충족 |
| AC6 프롬프트에 evidence_id 포함 | 충족(정본 파일에 재구성된 프롬프트로 증명) |
| AC7 프롬프트 evidence가 included_evidence_ids와 일치 | 충족 |

STOP 조건 해당 없음.

## 결론

3차 시도(r1 HOLD: 프롬프트 결함 → r2 HOLD: 정본 파일 미갱신, 2회 재전송
포함 → r3 GREEN) 끝에 완료됐다. 핵심 기술 수정(evidence_id 프롬프트 노출)이
실제로 A1/B1을 grounded 경로까지 도달시켰음을 실측으로 확인했고, 이제
정본 결과 파일도 올바르게 갱신됐다.

**recommendation: GREEN. HQ 승인 요청 — 승인 시 `tests/test_grounded_synthesis_integration.py`,
`scripts/grounded_synthesis_integration_demo.py`,
`docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md` 3개 파일을 경로
지정 커밋으로 확정하고, GS-P10(Regression/Architecture Integrity Audit)을
발급한다.**

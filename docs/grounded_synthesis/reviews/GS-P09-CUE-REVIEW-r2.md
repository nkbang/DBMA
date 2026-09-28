# CUE 교차검증 — Phase 9 (r2)

- 검증자: CUE (READ-ONLY)
- 대상 보고: 채팅 요약 + `/Users/David/DBMA/docs/grounded_synthesis/GS-P09-C1-REPORT-r2.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD(경미) — 기술적 수정은 검증됨, 정본 결과 파일 미갱신**

## 좋은 소식: 프롬프트 fix는 실제로 반영되고 검증됨

```
$ grep -n "evidence_id\|included_evidence_ids" scripts/grounded_synthesis_integration_demo.py
85:    for eid in synthesis_input.included_evidence_ids:
90:        evidence_texts.append(f"[evidence_id: {ev.evidence_id}] [출처: {src}]\n{ev.text}")
```
REWORK r1이 요구한 3가지 수정(evidence_id 명시, `included_evidence_ids` 필터링,
파서 보강) 전부 코드에 정확히 반영됨. `mtime` 확인 결과 코드 수정이
`2026-09-28 00:08`, C1이 별도로 작성한 결과 보고서
(`/Users/David/DBMA/docs/grounded_synthesis/GS-P09-C1-REPORT-r2.md`)가
`00:14`로 그 이후 — 수정된 코드로 실제 재실행한 시점과 정합적이다.

이 별도 보고서에 담긴 재실행 결과는 신뢰할 만하다: A1의 인용 evidence_id
(`TSU-UNK-02dd6090f62aaf456580dbb3adc79d39_chunk_01715`)와 B1의 4개
evidence_id가 모두 기존(r1) 결과 파일의 "Included IDs" 목록에 실제로
존재하는 값들과 정확히 일치한다(같은 질의는 검색이 결정적이므로 retrieval
결과가 재현되는 것이 맞다). `[evidence_id: ...]`가 포함된 프롬프트 원문도
재구성해서 제시했다 — AC6/AC7 증명으로 타당하다.

## 문제: WO가 지정한 정본 파일이 갱신되지 않음

```
$ stat -f "%Sm %N" docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md \
    scripts/grounded_synthesis_integration_demo.py
Sep 27 23:51:26 2026 docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md
Sep 28 00:08:10 2026 scripts/grounded_synthesis_integration_demo.py
```

WO(`GS-P09-WO-Integration.md`)와 REWORK r1이 **명시적으로 지정한 결과
기록 파일**은 `docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md`
하나뿐이다("REWORK 문서: `GS-P09-REAL-MODEL-RUN-RESULTS.md`를 새로 작성해라
(덮어써도 된다...)"). 그런데 이 파일의 수정 시각이 코드 수정보다 **이전**이다
— 즉 프롬프트를 고친 뒤 이 파일을 다시 쓰지 않았다. 실제로 내용을 읽어보면
r1과 완전히 동일하다(3개 질의 전부 `insufficient_evidence`, evidence_id
없는 옛 프롬프트 기준 서술 그대로).

진짜 재실행 결과는 WO가 지정하지 않은 별도 파일
(`docs/grounded_synthesis/GS-P09-C1-REPORT-r2.md`, `reviews/` 하위도 아님)에만
있다. 이 상태로 두면, 이후 누구든 지정된 정본 파일만 보고 "P9는 3개 질의
전부 실패했다"고 잘못 판단하게 된다 — Phase 9의 핵심 산출물이 잘못된 곳에
있는 것이다.

## 지시(간단한 정정, 재실행 불필요)

1. `docs/grounded_synthesis/GS-P09-C1-REPORT-r2.md`의 §4 재실행 결과
   내용을 `docs/grounded_synthesis/GS-P09-REAL-MODEL-RUN-RESULTS.md`에
   덮어써라(WO가 지정한 형식 — 안전기준선, 질의별 프롬프트/원답변/status/
   CitationCheckResult 요약 — 그대로 옮기면 된다). 이미 있는 좋은 내용을
   재작성할 필요는 없고 옮기기만 하면 된다.
2. 이후 보고서는 `docs/grounded_synthesis/reviews/GS-Pxx-C1-REPORT-rN.md`
   경로 관례를 따라 달라(지금까지 P4~P8은 이 경로를 썼다). project root
   바로 아래(`docs/grounded_synthesis/GS-P09-C1-REPORT-r2.md`)에 보고서를
   두는 것은 WO 허용 파일 목록에 없다 — STOP 대상은 아니지만 다음부터는
   피해라.

## V5/Safety 재확인

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
    tests/test_grounded_synthesis_integration.py tests/test_grounded_failure_paths.py -q
.........................                                                [100%]
25 passed in 0.06s

$ sha256sum output/bench/tsu_dataset.jsonl output/bench/tsu_manifest.json
0881618d16e46f8495ed067975e0869cafa4d80b6a4a549b567539644fe49c56  tsu_dataset.jsonl
67159d211c4db14acf8f174aa9d2a4ecb115aeaf51c2940090c2005a6184665e  tsu_manifest.json
```
전부 기준선·C1 보고와 일치.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1~AC5(기존) | 충족 |
| AC6(신규) 프롬프트에 evidence_id 포함 | 충족(코드+실제 프롬프트 원문 재구성으로 증명) |
| AC7(신규) 프롬프트 evidence가 included_evidence_ids와 일치 | 충족 |
| 정본 결과 파일(`GS-P09-REAL-MODEL-RUN-RESULTS.md`) 갱신 | **미충족** — 별도 파일에만 존재 |

## 결론

기술적 수정과 재실행 자체는 신뢰할 만하고 AC6/AC7을 실제로 증명했다.
Ollama 재호출은 불필요하다 — 이미 얻은 결과를 정본 파일로 옮기기만 하면
끝난다. STOP 조건 아님.

**recommendation: HOLD(경미) — `GS-P09-REAL-MODEL-RUN-RESULTS.md`를
실제 r2 결과로 갱신해서 재제출.**

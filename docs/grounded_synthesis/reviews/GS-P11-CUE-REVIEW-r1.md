# CUE 교차검증 — Phase 11 (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `docs/grounded_synthesis/GS-P11-PRODUCTION-SAFETY-REPORT.md`
- 원본 WO: `docs/grounded_synthesis/GS-P11-WO-Production-Safety.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD — 항목 4·6 검증 방법이 동어반복(tautology), REWORK 필요**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
0d265afcfb1403a84c084f370ca63a88ef7c4dea   (P10 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
(G0 격리 유지, 신규 산출물은 GS-P11-PRODUCTION-SAFETY-REPORT.md 1개)
```

## 항목별 검증 (1, 2, 3, 5, 7, 8, 9 — 정상)

```
$ sha256sum output/bench/tsu_dataset.jsonl output/bench/tsu_manifest.json
0881618d16e46f8495ed067975e0869cafa4d80b6a4a549b567539644fe49c56 / 67159d21...
```
기준선과 일치(항목 1 재확인). curl로 Qdrant 미응답 확인(항목 2), Tantivy
aggregate_sha256 재계산 일치(항목 3), `output/bench/` git status 무변경
확인(항목 5), grep NO_MATCH/EXIT:1 확인(항목 7·8). 항목 9는 1·3의 재진술로
타당. **이 6개 항목은 명령·출력이 실제로 그 항목을 증명하고 있고, CUE
재실행 결과도 일치한다.**

## 핵심 결함: 항목 4·6이 자기 자신과 비교하는 동어반복

```
$ git -C /Users/David/DBMA rev-parse HEAD
0d265afcfb1403a84c084f370ca63a88ef7c4dea
```

보고서 항목 4·6의 명령은 `git diff 0d265afc HEAD -- ...`인데, **현재 HEAD가
정확히 `0d265afc`다.** 즉 커밋을 자기 자신과 비교한 것이며, 대상 파일에
무엇이 들어있든 항상 빈 출력이 나온다 — 실제로는 아무것도 검증하지 않는
명령이다. 이 방식으로는 다음의 실제 우려를 전혀 검증할 수 없다.

**항목 4(Corpus regeneration)**: `scripts/merge_nae_corpus.py`,
`scripts/process_unprocessed_nae.py`는 바로 G0(비-GS, staged) 파일이다 —
Grounded Synthesis와 무관하게 이미 작업 디렉터리에 **staged 상태로 존재**한다.

```
$ git diff --cached --stat -- scripts/merge_nae_corpus.py scripts/process_unprocessed_nae.py
scripts/merge_nae_corpus.py        | 224 ++++++++++++++++++++++++++++++++++++
scripts/process_unprocessed_nae.py | 226 +++++++++++++++++++++++++++++++++++++
```
이 두 스크립트는 실제로 상당한 내용을 담은 채 staged돼 있다(GS 커밋으로
들어간 것은 아니지만, 작업 트리에는 존재). 보고서의 `git diff 0d265afc
HEAD`는 이걸 전혀 반영하지 않는다 — HEAD와 자기 자신을 비교하니 당연하다.

WO 원문이 요구한 진짜 검증은 "GS 관련 스크립트/테스트 실행 로그에 이
스크립트들의 **호출 이력**이 없음"이다. CUE가 직접 확인:
```
$ grep -rn "merge_nae_corpus\|process_unprocessed_nae" \
    core/grounded_*.py core/evidence_*.py tests/test_grounded_*.py \
    tests/test_evidence_*.py scripts/grounded_synthesis_integration_demo.py
NO_MATCH
```
**결론적으로 항목 4의 "0"이라는 판정 자체는 맞다** — GS 코드/테스트 어디도
이 스크립트들을 호출하지 않는다. 다만 그 증거로 제시된 명령이 틀렸다(증명이
안 되는 명령이었을 뿐 결론은 우연히 맞았다).

**항목 6(No new retrieval path)**: 올바른 비교 기준은 P10에서 이미 확정한
`1c0117a7`(P1 시작 직전, GS 이전 최종 상태)이어야 한다. `0d265afc`(P10 자신)와
비교하면 안 된다. 올바른 명령으로 CUE가 재확인:
```
$ git diff --stat 1c0117a7..HEAD -- core/retrieval.py core/hybrid_candidate_pipeline.py \
    core/candidate_generator.py
(출력 없음 — 0줄, P10에서 이미 확인된 사실)
```
이 결과(P10 r1에서 이미 CUE가 독립 검증한 사실)를 인용하면 됐다 — 굳이
`0d265afc..HEAD`라는 새 명령을 만들 필요가 없었다.

## GS-00 R4 관점

R4는 "출력 없이 쓴 수치는 무효"라고 규정한다. 이번 항목 4·6은 출력 자체는
있었지만(정직하게 실제로 실행한 명령의 결과), **그 명령이 질문에 답하지
못하는 명령**이었다 — 날조는 아니지만 감사로서의 증거 가치가 없다.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 9개 항목 전부 "0" 또는 "해당 없음" | 형식적으로 충족 |
| AC2 각 항목 명령·출력 원문 첨부 | 형식적으로 충족(단, 항목 4·6은 무의미한 명령) |
| AC3 mutation 발견 시 STOP | 해당 없음(발견된 mutation 없음, 결론 자체는 맞음) |

## 결론

STOP 조건 아니다(발견된 실제 mutation 없음, 결론은 옳음 — 검증 방법만 틀림).
그러나 이 상태로 넘어가면 향후 유사한 감사에서 이 잘못된 패턴
(`<현재HEAD>..HEAD` 자기비교)이 재사용될 위험이 있다.

**recommendation: HOLD — 항목 4·6의 명령을 올바른 대상으로 재실행해서
REWORK할 것.**

# CUE 교차검증 — Phase 9 (r1)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `GS-P09-C1-REPORT-r1.md`
- 원본 WO: `docs/grounded_synthesis/GS-P09-WO-Integration.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **HOLD — 프롬프트 설계 결함 발견(3건 전부 근거부족의 실제 원인), REWORK 필요**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
e5eecd5fe345019a444c9d29f55c05f1f35a9605   (P8 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
(G0 9연속 격리 유지, GS 변경은 허용 파일 3개와 일치)
```

## V5 — 독립 재실행

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/test_grounded_synthesis_integration.py -q
.......                                                                  [100%]
7 passed in 0.05s
```
C1 보고("7/7 PASS")와 일치. stub 테스트는 grounded/insufficient 양쪽 경로를
포함하며(TestGroundedPath, TestInsufficientPath, TestPartialPath,
TestDuplicatePath) 정상적이다 — 이 부분은 결함 없음.

## V-Safety — 안전 기준선 재확인

```
$ sha256sum output/bench/tsu_dataset.jsonl output/bench/tsu_manifest.json
0881618d16e46f8495ed067975e0869cafa4d80b6a4a549b567539644fe49c56  tsu_dataset.jsonl
67159d211c4db14acf8f174aa9d2a4ecb115aeaf51c2940090c2005a6184665e  tsu_manifest.json
```
`GS-SAFETY-BASELINE-CUE-20260927.json`의 값과 정확히 일치. C1 보고와도 일치.
운영 데이터 mutation 없음 확인.

## V4 — 핵심 결함: 실모델 프롬프트가 LLM에게 evidence_id를 보여주지 않음

`scripts/grounded_synthesis_integration_demo.py::extract_claims_with_ollama()`
(78~90행)를 읽었다:

```python
for ev in pool.all():
    src = ev.source_file or ev.document_title or "미상"
    evidence_texts.append(f"[출처: {src}]\n{ev.text}")
...
prompt = (
    "다음 자료들을 읽고 질문에 대한 주장을 추출하세요.\n"
    "각 주장은 하나의 evidence_id에 근거해야 합니다.\n\n"
    f"자료:\n{context_block}\n\n"
    f"질문: {query}\n\n"
    "출력 형식: 각 줄을 (claim_text, [evidence_ids]) 형태로 출력하세요.\n"
    "예: (주장 내용, ['tsu_001'])\n"
    ...
)
```

`context_block`에는 `ev.evidence_id`가 **한 번도 포함되지 않는다** — 오직
`source_file`/`document_title`(사람이 읽는 라벨)과 본문 텍스트만 있다.
그런데 지시문은 "각 주장은 하나의 evidence_id에 근거해야 합니다"라고 요구하고,
예시로 `['tsu_001']` 형태를 제시한다. **LLM은 자신이 본 적도 없는 문자열
(`evidence_id`)을 만들어내라는 요구를 받는다.**

`parse_llm_claims()`는 LLM 출력에서 `TSU-...`/`NAE-UNC-...` 패턴을 정규식으로
찾는데, LLM이 이 정확한 ID 문자열을 볼 방법이 없으므로 이 매칭은 사실상
운(하드코딩된 패턴과 우연히 일치하는 문자열을 LLM이 냈을 때)에 의존한다.

### 보고서 §"관찰"의 서술과 불일치

C1의 `GS-P09-REAL-MODEL-RUN-RESULTS.md`는 A1을 "retrieval된 자료가 로마서
8:1-4의 직접적인 주해가 아니었기 때문", B1을 "LLM의 claim extraction이 ID
형식을 정확히 인식하지 못함"으로 설명했다. 후자는 사실에 더 가깝지만,
"LLM의 한계"가 아니라 **프롬프트가 애초에 ID를 보여주지 않은 설계 결함**이
근본 원인이다. B1 결과의 `text`를 보면 LLM이 실제로
`['Fuller_Complete_Works_Vol08', 'Hiscox_Standard_Manual']`처럼 **그럴듯한
문헌명을 스스로 지어냈다** — 이는 프롬프트에 보여준 적 없는 값을 LLM이
추측한 것이며, `ev.text`에 실제로 그 문헌명이 있었는지도 검증되지 않았다
(재현 문헌명이 실제 Evidence의 provenance와 일치하는지 CUE도 확인 불가 —
LLM이 일반 신학 지식으로 만들어냈을 가능성을 배제할 수 없음).

### 부수 결함: `pool.all()` vs `si.included_evidence_ids`

`extract_claims_with_ollama()`는 `pool.all()`(Pool 전체)을 프롬프트에 넣는다.
P4의 `SynthesisInput.included_evidence_ids`(ADR-036 B3 절단 규칙 적용 결과)를
무시한다. 이번 3개 질의는 우연히 `truncated=False`(pool 크기 5 ≤ max_evidence
10)라 드러나지 않았지만, pool이 max_evidence를 넘는 경우 이 스크립트는
`excluded_evidence_ids`까지 LLM에 보여주게 되어 ADR-036 B3(합성 입력 경계)를
위반한다. 지금 당장 3개 질의 결과에는 영향 없었지만 잠재적 위반이다.

## 왜 이것이 P9의 핵심 목적을 훼손하는가

P9의 목적은 "실제 모델로 전체 파이프라인이 정상 동작하는지"를 보여주는
것이다. 이 결함 때문에 **정상(grounded) 경로가 real-model 실행에서 사실상
도달 불가능**하다 — 3개 질의 전부가 `insufficient_evidence`로 끝난 것은
코퍼스 한계나 LLM 한계가 아니라 이 프롬프트 버그 때문일 가능성이 높다.
AC4는 문자 그대로는 충족됐다("최소 1개는 insufficient" — 3개 다 그랬으니
당연히 충족), 하지만 이 Phase가 실제로 증명하려던 것(정상 경로도 실모델에서
작동함)은 증명되지 않았다.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 stub 통합 테스트, grounded/insufficient 양쪽 도달 | 충족 |
| AC2 데모 스크립트가 retrieval 모듈 무수정 사용 | 충족(diff 없음 확인) |
| AC3 실행 중 mutation 없음 | 충족(해시 일치) |
| AC4 최소 3개 질의, 최소 1개 insufficient 경로 | 문자적으로 충족되나 근본 원인(프롬프트 결함)으로 인해 "grounded 경로 실증"이라는 Phase 취지 미달성 |
| AC5 실모델 결과 분리 보고 | 충족 |

## 결론

STOP 조건은 아니다(운영 코드 무수정, 데모 스크립트만의 프롬프트 로직 수정).
그러나 이 결함을 그대로 두면 P9가 "실모델로 grounded 경로가 실제로 작동한다"는
증거를 하나도 남기지 못한 채 다음 Phase로 넘어가게 된다.

**recommendation: HOLD — GS-P09 REWORK 필요(프롬프트에 evidence_id 명시 +
`si.included_evidence_ids` 기준으로 필터링 후 재실행).**

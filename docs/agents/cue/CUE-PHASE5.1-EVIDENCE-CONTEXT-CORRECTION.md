# CUE Phase 5.1 Evidence Context Correction

## STATUS

- Overall: `CLOSED`
- Baseline commit: `d7152ec989d47a48fce008780066d1d35c05e653`
- Evidence-document commit: `403ab65581210d1fb77ef5a6508c84a4d40724fb8`
- Working-tree change status: 7개 파일 여전히 uncommitted (재확인, 아래 EVIDENCE 참고)
- Commit scope: `403ab65` = 8개 문서 파일만(코드/데이터 0건) — 전 항목 재확인 완료
- Required correction: 없음(코드/구조 변경 불필요). 문구 명확화 권고 2건은 별도 evidence-only correction commit 승인 대기 상태로 이관(아래 FINDINGS)

---

## EVIDENCE

### git show / diff-tree / ls-tree 결과 요약

```
$ git show --format=fuller --stat 403ab65 (파일 목록부)
 .../cue/CUE-PHASE5.1-RECONCILIATION-REVIEW.md      | 193 +++++++++++
 docs/audit/phase5_1/README.md                      |  61 +++++
 docs/audit/phase5_1/adr-linkage.md                 |  65 +++++
 docs/audit/phase5_1/changed_files.txt              |  57 ++++
 docs/audit/phase5_1/code-trace.md                  | 106 +++++
 docs/audit/phase5_1/commit.txt                     |  61 +++++
 docs/audit/phase5_1/findings.md                    |  38 ++
 docs/audit/phase5_1/tests/pytest-output.txt        | 105 +++++
 8 files changed, 686 insertions(+)

$ git show --name-status --format="" 403ab65
A  (동일 8개 경로)

$ git diff-tree --no-commit-id --name-status -r 403ab65
A  (동일 8개 경로)

$ git ls-tree -r --name-only 403ab65 | wc -l
743   ← 이 커밋 시점 저장소 "전체" 파일 수(diff 아님, 참고용 — 아래 주의사항 참고)

$ git status --short
 M NAE/benchmark/__init__.py
 M NAE/benchmark/datasets/benchmark_v1.jsonl
 M NAE/benchmark/loader.py
 M NAE/benchmark/schema.py
 M scripts/build_tsu_dataset.py
 M tests/test_nae_benchmark_loader.py
 M tests/test_nae_benchmark_schema.py
 (+ 다수 untracked 문서 파일, 이번 계약 검토와 무관)

$ git log --oneline --decorate -n 5
403ab65 (HEAD -> dev/dbma-engine, origin/dev/dbma-engine) docs: Phase 5.1 forensic evidence package + reconciliation review (evidence-only)
d7152ec feat: NAE Phase 5 Benchmark Infrastructure (C1 implementation, CUE review + fixes)
7b76107 feat: NAE Phase 3.5/4 hardening - schema versioning, collection versioning, docker-compose
e0e6f0e feat: NAE Phase 3.5 (Knowledge Verification) + Phase 4 (BGE-M3/Qdrant indexing)
c206793 feat: NAE Corpus Builder Phase 3 - TSU Builder (LLM-backed claim extraction)
```

`git log --decorate`가 `HEAD -> dev/dbma-engine, origin/dev/dbma-engine`을 동시에 보여준다 —
로컬 HEAD와 origin 원격 ref가 `403ab65`에서 일치, push 반영 상태 확인.

**주의**: `ls-tree`는 diff가 아니라 그 커밋 시점의 저장소 전체 트리를 나열하는 명령이다.
743이라는 숫자는 "403ab65가 변경한 파일 수"에 대한 답이 아니다 — 그 질문에 답하는 것은
`--stat`/`--name-status`/`diff-tree` 세 명령이며, 셋 다 8로 일치한다.

### `403ab65` 실제 파일 목록 (8개, 전체 경로)

```
docs/agents/cue/CUE-PHASE5.1-RECONCILIATION-REVIEW.md
docs/audit/phase5_1/README.md
docs/audit/phase5_1/adr-linkage.md
docs/audit/phase5_1/changed_files.txt
docs/audit/phase5_1/code-trace.md
docs/audit/phase5_1/commit.txt
docs/audit/phase5_1/findings.md
docs/audit/phase5_1/tests/pytest-output.txt
```

### C1 "3-file" 주장과의 대조

세 가지 독립 명령(`--stat`, `--name-status`, `diff-tree`)이 모두 8개로 일치하며, 이는
로컬 git object에 대한 직접 질의이므로 반박 여지가 없다. "3개 파일" 주장을 뒷받침하는
원문 Git 출력은 이 세 명령 중 어디에도 존재하지 않는다. 이 저장소·이전 대화 기록에서
"3개 파일"이라는 주장이 실제로 어디서 나왔는지도 확인되지 않는다 — 존재를 확인하지
못한 주장이므로 반박이 아니라 **미확인(unsourced)**으로 기록한다.

---

## FINDINGS

### Confirmed baseline/evidence/diff separation

- `d7152ec` — **CONFIRMED** baseline implementation commit. `NAE/benchmark/{schema,loader,
  metrics,evaluator,runner,__init__}.py` 6개 소스 파일과 테스트 5종을 도입한 커밋이며,
  Q1/Q2/Q3(gold_tsu_ids 미연결, Qdrant 미호출, ID-space 불일치)의 원인이 되는 실제 코드가
  이 커밋에 있다.
- `403ab65` — **CONFIRMED** forensic evidence-document commit. 8개 파일 전부 `.md`/`.txt`이며
  `.py`/`.jsonl` 등 코드·데이터 파일은 0건. `d7152ec`를 감사한 결과를 기록할 뿐 구현을
  변경하지 않는다.
- Uncommitted working-tree changes — **CONFIRMED** 별개 diff. `git status --short`로 7개
  파일이 여전히 modified 상태임을 재확인했다. 이 중 `evaluator.py`/`runner.py`는 변경
  목록에 없음 — 즉 이 두 파일에 대한 모든 코드 근거는 working tree 여부와 무관하게
  `d7152ec` 자체와 완전히 동일하다.

### Incorrect HEAD claims, if any

- `docs/audit/phase5_1/findings.md` 17행: "HEAD는 `d7152ec`(`commit.txt`), parent는 `7b76107`."
  — 시점 한정 없이 "HEAD는 d7152ec"를 단정한다. 작성 시점에는 참이었으나 현재 실제 HEAD는
  `403ab65`이므로(`git log --decorate` 재확인), 지금 그대로 읽으면 **오류로 판정**된다
  (`INCORRECT_HEAD_CLAIM`).

### Ambiguous wording, if any

- `docs/audit/phase5_1/README.md` 39행: "P1 재감사 요청 (제출 형식)" 템플릿의 `Commit:
  d7152ec989d...` — 이 라벨이 "감사 대상 baseline"인지 "이 evidence package가 속한
  commit"인지 텍스트 자체가 설명하지 않는다. 동일 템플릿이 이후 대화에서 `403ab65`
  값으로도 재사용된 바 있어 혼동 소지가 실증됨(`AMBIGUOUS_REQUIRES_WORDING_FIX`).
- `docs/audit/phase5_1/code-trace.md` 3행: "현재 working tree(HEAD `d7152ec` + 미커밋 변경
  포함, ...)" — "미커밋 변경 포함"이 붙어 스냅샷임을 어느 정도 암시하지만, "현재"라는
  시제어가 남아 있어 작성 시점의 "현재"인지 독자가 읽는 시점의 "현재"인지 불명확
  (`AMBIGUOUS_REQUIRES_WORDING_FIX`).
- `docs/agents/cue/CUE-PHASE5.1-RECONCILIATION-REVIEW.md` 137-138행: "35커밋 ahead이며 아직
  push되지 않았다" — `403ab65` push **이전**에 작성된 정확한 스냅샷이었으나, push 완료
  이후(`git log --decorate`가 `origin/dev/dbma-engine`을 `403ab65`와 함께 보여줌) 현재는
  사실이 아니게 되었다. 오류가 아니라 시점 종속 문장이며, 명확화 권고 대상.

### Statements that require no correction

- `docs/audit/phase5_1/commit.txt` — `d7152ec`(HEAD)/`7b76107`(parent) 기록은 "이 파일이
  캡처한 시점"이라는 파일의 목적 자체가 명확하므로 수정 불필요.
- Required Table·code-trace.md의 Q1/Q2/Q3 코드 인용부(`evaluator.py:81`, `runner.py:96,
  163-170` 등) — 대상 파일이 변경되지 않았으므로 baseline·현재 상태 모두에서 유효, 수정 불필요.

---

## RISKS

Evidence-context risk만 기록한다(benchmark 코드 결함 재론 없음 — 그 내용은 이미
`code-trace.md`/`findings.md`에 확정되어 있고 이번 검토 범위 밖이다).

| 등급 | 내용 |
|---|---|
| Low | `findings.md:17` — 시점 미한정 HEAD 단정 문장 1건, 독자가 최신 상태로 오인할 수 있음 |
| Low | `README.md:39`, `code-trace.md:3` — 라벨/시제 모호 문장 2건 |
| Low | `RECONCILIATION-REVIEW.md:137-138` — push 이후 시제가 어긋난 문장 1건 |
| Informational | C1 "3-file" 주장 출처 미확인 — 반박 근거는 충분(8 CONFIRMED)하나 주장 자체의 기원은 추적 불가 |

이 외 corpus/Qdrant/코드 계약 관련 위험은 이번 evidence-context 검토의 범위가 아니다.

---

## RECOMMENDATION

```
PRESERVE_AND_REWRITE
NO_BLANKET_SHA_REPLACEMENT
ALLOW_HQ_PHASE5.1_TASK_ORDER
```

- `PRESERVE_AND_REWRITE`: 위 4개 문구(경미한 시제/라벨 모호성)만 국소적으로 다시 쓰면
  충분하다 — 문서 구조나 나머지 내용을 재작성할 필요는 없다. 실행은 별도
  evidence-only correction commit 승인 이후.
- `NO_BLANKET_SHA_REPLACEMENT`: `d7152ec`(피감사 baseline)와 `403ab65`(감사자 evidence
  commit)는 역할이 다르므로 일괄 치환 금지 — 치환 시 "감사 문서가 자기 자신을 감사했다"는
  식으로 사실이 왜곡된다(예: `findings.md`의 "evaluator.py/runner.py는 d7152ec 코드와
  바이트 단위로 동일" 문장을 403ab65로 치환하면 거짓이 됨 — 403ab65는 애초에 그 두 파일을
  포함하지 않음).
- `ALLOW_HQ_PHASE5.1_TASK_ORDER`: Evidence context가 확정되었으므로, HQ가 Risk C 워크플로로
  `gold_tsu_ids`↔`evaluator`/`runner` 연결 작업을 C1에게 재발행하는 것을 막을 절차적 근거가
  없다. 단, 이는 CUE의 계약/경계 검토 완료를 뜻할 뿐 — Gold Benchmark authoring/Phase 5.2
  retrieval evaluation의 BLOCKED 상태 자체는 (해당 코드가 아직 수정되지 않았으므로) 변하지
  않는다.

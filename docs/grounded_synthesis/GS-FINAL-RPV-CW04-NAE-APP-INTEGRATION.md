# CW-04 NAE App Integration — Final Task Order (CUE 확정, HQ 원안 기반)

- **Status**: AUTHORIZED
- **작성**: CUE(HQ가 최종 확인 권한 위임, 2026-09-29). HQ 원안의 구조·
  원칙은 그대로 승계하되, 아래 3가지 모호성만 CUE가 확정했다.
- **선행**: [GS-FINAL-RPV-CW04-ARCHITECTURE-DECISION-BRIEF.md](GS-FINAL-RPV-CW04-ARCHITECTURE-DECISION-BRIEF.md)
  — AD-01 `[✓ HQ Option C]`, AD-02 `[✓ HQ Option D]`.
  [GS-FINAL-RPV-CW04-GATE2B-IMPLEMENTATION-BRIEF.md](GS-FINAL-RPV-CW04-GATE2B-IMPLEMENTATION-BRIEF.md)
  — 격리 워크트리 구현 `[✓ CUE]`, commit `4192d94`(참고용, 아래 §2).

## 0. 목적

AD-01/AD-02를 격리된 RPV 검증 환경이 아니라 **실제 DBMA/NAE 앱
코드베이스**에 최소 변경으로 반영한다. GS Architecture 재설계가
아니다.

---

## CUE가 확정한 3가지 결정 (HQ 원안의 모호성 해소)

### 결정 1 — 작업 위치 (HQ 원안 §2/§10의 충돌 해소)

**신규 전용 워크트리를 생성해 사용한다. 이것이 유일한 작업 공간이자
"실제 앱" 검증 대상이다.**

```bash
$ git worktree add -b feat/cw04-ad01-ad02-nae-app ../DBMA-cw04-nae-app origin/main
```

- **경로**: `/Users/David/DBMA-cw04-nae-app`
- **브랜치**: `feat/cw04-ad01-ad02-nae-app`
- **HEAD**: `0d675636be1e713456164cea5992fed82e91069d`(= `main`,
  PR #91 병합 후 최신, GS-FINAL-RPV 문서 전체 포함)

**CUE가 이미 생성·확인 완료**(clean, `origin/main` 최신 상태). C1은
새로 만들 필요 없이 이 워크트리로 바로 이동한다.

**왜 기존 `/Users/David/DBMA`(`feat/peb-v0.1`)를 쓰지 않는가**: CUE가
직접 확인한 결과, 그 체크아웃은 `config.yaml`, `core/candidate_generator.py`,
`core/hybrid_candidate_pipeline.py`, 심지어 CW-01~03이 수정했던
`scripts/grounded_synthesis_integration_demo.py`까지 **unstaged
변경이 남아있고 `origin/main` 대비 56커밋 뒤처져 있다**(G0 오염,
세션 전체에서 반복 확인된 상태). 여기서 작업하면 무관한 변경과
섞이거나 최신 아키텍처 상태를 놓칠 위험이 있어 사용하지 않는다.

**왜 기존 `/Users/David/DBMA-rpv-c8f7e41a`를 쓰지 않는가**: 그
워크트리는 RPV 검증 전용으로 detached HEAD(`c8f7e41a`)에 고정되고
TSU dataset도 **격리된 bench 스냅샷 복사본**이다. 거기서 "실제
Streamlit 앱"을 띄워도 여전히 격리 데이터를 보는 것이지 실제 앱이
아니다. 이번 작업 목적(실제 앱 반영)과 맞지 않는다 — 그 워크트리는
지금부터 더 이상 건드리지 않는다(RPV-05/06 최종 기록은 이미 `[✓ HQ]`
로 종결됨).

### 결정 2 — 기존 검증된 구현을 참고 근거로 사용

AD-01/AD-02는 이미 `/Users/David/DBMA-rpv-c8f7e41a`에서 CUE가 독립
검증까지 마친 실제 코드(commit `4192d94`)로 구현되어 있다.
**동일한 git object database를 공유하므로 새 워크트리에서도 그
diff를 그대로 열람할 수 있다**:

```bash
git show 4192d94 -- core/evidence_adapters/tsu_adapter.py
git show 4192d94 -- core/identity_registry.py
```

C1은 이 diff를 **처음부터 재설계하지 말고 참고 근거로 삼아** 현재
`main` 기준 파일 상태에 이식한다(파일이 그 사이 달라졌을 수 있으므로
기계적 cherry-pick이 아니라 로직을 확인 후 적용). `documents.json`
자체(RPV fixture 데이터 포함)는 참고하지 않는다 — 실제 앱에는 별도
fixture를 아래 결정 3의 절차로 업로드한다.

**단, 한 가지는 기존 구현보다 개선한다**: 기존 `resolve_corpus_type()`
은 registry 경로를 하드코딩된 후보 목록(`_possible_paths`)으로
탐색했다. 실제 앱에서는 이 방식 대신 **`core/config.py::DEFAULT_REGISTRY_PATH`**
(= `registry_path_for(DEFAULT_OUTPUT_DIR)`, `config.yaml`의
`output_dir` 기반)를 그대로 사용한다 — 이것이 이 코드베이스의
실제 authoritative registry 경로 설정 방식이다(하드코딩 경로 추측
금지, CLAUDE.md "RAW/Output Data Integrity" 원칙과도 일치).

### 결정 3 — RPV-06a/06b fixture는 전용 테스트 계정에만 업로드

실제 앱 runtime 검증(§10, HQ 원안 그대로)을 위해 fixture 문서(요
15장 포도나무 비유 노트, 고전 12장 은사 노트 — 전문은
[GS-FINAL-RPV-TEST-SET-DRAFT.md](GS-FINAL-RPV-TEST-SET-DRAFT.md)
"fixture 문서 A/B" 참고)를 실제로 업로드해야 하지만, **2026-09-28
HQ가 확정한 RPV 테스트 계정 4조건을 그대로 재적용한다**:

1. 실사용자·개인 자료 사용 금지 — 실제 사용자 계정/자료 절대 사용
   안 함
2. RPV fixture 문서만 업로드 — 다른 자료 업로드 금지
3. 계정 ID·fixture 원문·생성된 evidence ID를 보고서에 고정 기록(추정
   금지)
4. 검증 완료 후 계정·업로드 자료의 보존/삭제 상태를 보고서에 기록

정상 업로드 UI 흐름(`ui/pages/processing.py`)을 통한 fixture 2건
업로드는 §11(HQ 원안)의 "corpus reprocessing/TSU mutation 금지"에
해당하지 않는다 — 이는 이 기능이 정상적으로 지원해야 할 일반 사용자
행위(개인 문서 업로드)이며, 금지 대상은 재처리 스크립트/재인덱싱
같은 대량·구조적 작업이다. 단, 전용 테스트 계정 범위를 벗어나지
않는다.

---

## 나머지 — HQ 원안 그대로 (변경 없음)

아래 항목들은 HQ 원안의 구조와 원칙을 그대로 승계한다. 전체 원문은
이 세션의 HQ 지시 메시지(2026-09-29, "[HQ→C1] CW-04 Gate 2B — NAE
앱 반영 최종 실행 명령") 참고:

- **§1 작업 상태**: AUTHORIZED, AD-01=Option C/AD-02=Option D 그대로
- **§3 AD-01 구현 목표**: authoritative source/document metadata →
  membership → candidate → `Evidence.corpus_type` 흐름, source_file
  패턴을 권위 근거로 쓰지 않음, 기존 metadata 구조 우선 확인(§6 조사
  대상 파일 목록 포함), 중복 SSOT 신설 금지
- **§4 AD-02 구현 목표**: role-aware merge, relevance/corpus
  role/query role 분리, score boost·rank-1 강제·고정 quota·Default
  제외·신규 retrieval engine/embedding model/ranking architecture
  전부 금지
- **§5 Query Role / Corpus Role 독립 축**: `QuerySpec.role`과
  `corpus_type`을 직접 매핑하지 않음
- **§6 구현 전 확인 파일**: `core/evidence_model.py`,
  `core/evidence_adapters/tsu_adapter.py`, `core/evidence_pool.py`,
  `core/evidence_assembly.py`, `core/hybrid_candidate_pipeline.py`,
  `core/retrieval.py`, `ui/pages/library.py`, registry 파일(경로는
  위 결정 2 참고)
- **§7 GS Boundary 보호**: `core/grounded_*.py` 수정 대상 아님, 불가피
  판단 시 STOP 후 HQ 보고
- **§8 RPV-06 검증**: 정본 질문 그대로(RPV-06a/06b), 목적은 특정
  rank 재현이 아니라 membership 전달·`corpus_type` 일치·relevance
  왜곡 없음 확인
- **§9 Regression**: 기존 retrieval tests, Evidence.corpus_type
  tests, Query/Corpus Role tests, GS regression, RPV-06a/06b —
  실패 시 원인 분류(신규 구현 regression/기존 baseline 문제/환경
  문제) 후 숨기지 않음
- **§10 실제 NAE 앱 검증**: Landing → 내서재 → 질문하기 → RPV-06a/06b
  → 답변+근거 확인, 내부 구현 정보(corpus_type/score/candidate
  internals/클래스명) 사용자 UI 비노출 확인
- **§11 Production Safety**: TSU mutation, corpus reprocessing,
  embedding 재생성, Qdrant/Tantivy rebuild, 신규 retrieval
  engine/GS rewrite/대규모 unrelated refactor/UI redesign 전부 금지
- **§12 변경 범위**: AD-01/AD-02 직접 필요 파일로 제한, 파일별
  변경이유/AD 관계/기존 동작 영향 설명
- **§13 Commit**: `git status`/`diff --stat`/`diff`/`log -1` 확인 후
  단일 커밋
- **§14 보고 형식**: G0/AD-01/AD-02/Query-Corpus Role/GS Boundary/
  Tests/App Runtime/Changed Files/Commit/Production Safety/Remaining
  Issues 전부 포함 — **G0 섹션에는 위 결정 1의 워크트리 정보와 실제
  명령 출력을 그대로 기록**
- **§15 Gate 규칙**: C1은 GREEN/HQ APPROVED/Gate 2B COMPLETE를
  스스로 선언하지 않음. C1 구현 보고 → CUE read-only 독립 검증 →
  HQ 최종 결정 순서 그대로 유지

## 진행 순서

```text
본 문서(작업 위치/참고 diff/fixture 절차 확정)
    ↓
C1: /Users/David/DBMA-cw04-nae-app 로 이동, G0 출력 보고
    ↓
C1: HQ 원안 §3-§13 그대로 구현 + 검증 + 실제 앱 runtime 확인
    ↓
C1: §14 형식으로 보고
    ↓
CUE 독립 검증(코드 diff, 테스트 재실행, RPV-06a/06b 라이브 재현,
              실제 앱 runtime 재확인)
    ↓
HQ 최종 결정
```

## 현재 상태

```text
작업 워크트리                    [생성 완료 — CUE]
CW-04 NAE App Integration Scope  [AUTHORIZED — 본 문서]
C1                               [착수 가능]
CUE                              [C1 보고 대기 → 독립 검증]
```

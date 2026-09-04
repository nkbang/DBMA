# C1 Task Order 005 — DBMA-SIL Phase 0: Architecture Discovery and Impact Analysis

**상태: 중단(superseded), 2026-07-21.** 사용자가 외부 자료(설교 제작 툴
아이디어, 설교엔진디자인 ChatGPT 대화록)를 근거로 재설계를 지시해 이
Task Order는 실행하지 않는다. Cline에서 이 지시를 아직 실행 전이라면
착수하지 말 것. 후속 설계는 CUE가 직접 작성한 신학 엔진/TSU 확장 설계
문서를 참고할 것(작성 예정: `docs/agents/c1/DBMA-SIL-Theology-Engine-Design.md`).

발급: CUE (2026-07-21)
대상: C1 (Cline 작업창 #1, **모델: `dbma-planner-r1-q6:70b`** — 설계/분석
전용. 코드를 쓰는 작업이 아니므로 플래너 모델을 쓴다.)
성격: **분석/설계 검토 — 코드 변경 절대 금지.** `.py` 파일을 단 한 줄도
만들거나 고치지 않는다. 산출물은 마크다운 문서 하나뿐.

```
PROJECT: DBMA-SIL
PHASE: 0 — Architecture Discovery
TASK: Sermon Intelligence Layer Design
```

---

## 1. 배경 (VERIFIED — C1이 그대로 신뢰해도 되는 사실)

- `DBMA-SIL`(David Bang Ministry Archive — Sermon Intelligence Layer,
  한글명: DBMA 설교 지능 계층 프로젝트)은 사용자가 확정한 공식
  프로젝트명이다.
- Phase 1 설계 검토(`docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-
  Review.md`, C1-TASK-ORDER-004 산출물)와 그 이후 실제 구현이 이미
  존재한다: `ui/pages/sermon_draft.py`(UI), `core/generation.py::
  SermonDraftService`/`SermonOutline`/`SERMON_FORMATS`(생성 로직) —
  전부 CUE가 코드를 직접 열어 실존을 확인했다.
- `ui/app.py:26, 185`에 이미 `sermon_draft.py`가 import되고 사이드바
  "설교문 작성"으로 등록돼 있다 — Phase 1이 이미 실행 중인 상태에서
  Phase 0(Architecture Discovery)을 지금 소급 진행하는 것이다. 이
  선후관계(Phase 1이 먼저 실행되고 Phase 0을 나중에 함)는 이례적이니
  C1은 이를 전제로 "이미 있는 것을 깨지 않는 범위에서" 분석하라.
- **ADR 번호 제약(중요)**: `ADR-006`은 이미 예약된 번호다
  (`docs/architecture/ADR-007-Semantic-Boundary-Detector-D5-Rebuild-
  Gate.md` 25-30행 — 원래 ADR-006이었다가 과거 결정과 충돌해 ADR-007로
  재번호, "ADR-006은 과거 결정을 위해 예약 유지"). SIL 관련 ADR을
  제안할 때는 **ADR-009부터** 사용하라(ADR-008은 청킹 작업에서 이미
  사용됨). ADR-006을 다시 제안하면 반려된다.
- 기존 아키텍처 원칙(반드시 준수 전제로 분석할 것): One Pipeline,
  One Config, One Retrieval Engine(`core/retrieval.py::RetrievalEngine`
  이 유일한 authority, ADR-001), One Execution State.

## 2. 목표

`docs/agents/c1/DBMA-SIL-Phase0-Architecture-Discovery.md` 파일 하나를
새로 작성하라. 기존 파일(`.py`, 다른 `.md` 포함)은 절대 수정하지 않는다.

## 3. 반드시 답할 질문 5개

1. **SIL은 DBMA Core 내부인가, Extension Layer인가?** — 현재
   `core/generation.py`에 `SermonDraftService`가 이미 `core/` 안에
   구현돼 있다는 사실(§1 VERIFIED)을 근거로, 이 배치가 맞는지 또는
   `core/sermon/`처럼 분리된 하위 패키지로 옮기는 게 나은지 판단하고
   근거를 대라.
2. **기존 TSU 변경이 필요한가?** — 필요하다면 어떤 필드를, additive-only
   (기존 레코드 영향 없음)로 추가 가능한지 구체적으로 제시하라.
   "마이그레이션 불필요"라고만 쓰지 말고 왜 불필요한지 TSU 스키마의
   실제 특성(옵셔널 필드 여부 등)을 근거로 대라 — 확인 못 했으면
   UNKNOWN으로 명시하고 지어내지 마라.
3. **Retrieval Engine에 어떤 metadata signal을 추가할 것인가?** —
   `core/retrieval.py::RetrievalEngine`을 바꾸지 않고(One Retrieval
   Engine 원칙, ADR-001) 기존 `k`/`file_scope` 파라미터만으로 설교
   워크플로 요구(넓은 범위 검색)를 충족할 수 있는지, 아니면 정말
   RetrievalEngine 자체 변경이 필요한지 구분해서 답하라. 후자라면
   ADR-009 대상임을 명시하라.
4. **MVP 범위는 어디까지인가?** — 이미 구현된 것(§1 VERIFIED)과 아직
   없는 것을 구분한 뒤, Phase 2(Sermon Workspace Core)에서 최소로
   구현해야 할 범위를 제안하라.
5. **ADR이 필요한 항목은 무엇인가?** — 위 1~4번 중 실제로 아키텍처
   결정(ADR)이 필요한 항목만 골라 나열하라. 전부 다 ADR이 필요하다고
   뭉뚱그리지 마라 — 어떤 게 ADR 없이 기존 원칙 안에서 처리 가능한지도
   구분해서 답하라.

## 4. 반드시 지킬 것 (Scope — 위반 시 반려)

- `.py` 파일을 만들거나 수정하지 마라.
- 기존 `.md` 문서(`docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-
  Review.md` 등)를 수정하지 마라 — 새 파일만 작성.
- ADR 번호를 언급할 때 **ADR-006을 쓰지 마라** — ADR-009부터.
- 완전한 함수 구현체를 쓰지 마라. 인터페이스 시그니처·의사코드까지만.
- `C1_RESPONSE_PROTOCOL.md` 형식(Current State / Evidence
  Classification(VERIFIED/REPORTED/UNKNOWN) / Risk Assessment /
  Architecture Impact / Recommendation / Human Approval Required)을
  §3의 5개 질문에 대한 답과 결합해서 작성하라 — 5개 질문 답변이
  본문, 6개 절 형식이 그 답변을 감싸는 틀이다.
- 확인 못 한 사실은 UNKNOWN으로 명시하라. 특히 TSU 스키마 세부 사항은
  C1이 직접 코드를 열어보지 못했다면 추측하지 말고 UNKNOWN 처리하라.

## 5. C1에게 보낼 프롬프트

```text
너는 C1-DBMA-PLANNER다. DBMA Planning and Architecture Governance
Agent 역할만 수행한다. 코드는 단 한 줄도 쓰지 않는다 — .py 파일을
만들거나 수정하는 것은 절대 금지다.

프로젝트: DBMA-SIL (David Bang Ministry Archive — Sermon Intelligence
Layer)
현재 단계: DBMA-SIL Phase 0: Architecture Discovery and Impact Analysis

배경(VERIFIED로 취급하라):
- Phase 1 설계 검토(docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-
  Review.md)와 실제 구현이 이미 존재한다: ui/pages/sermon_draft.py,
  core/generation.py의 SermonDraftService/SermonOutline/SERMON_FORMATS.
  ui/app.py 26번째 줄과 185번째 줄에 이미 import·사이드바 등록돼 있다.
- ADR-006은 이미 예약된 번호다(docs/architecture/ADR-007-Semantic-
  Boundary-Detector-D5-Rebuild-Gate.md 25-30행 참고). SIL 관련 ADR을
  언급할 때는 ADR-009부터 사용하라. ADR-006을 다시 제안하면 반려된다.
- 기존 원칙(반드시 준수): One Pipeline, One Config, One Retrieval
  Engine(core/retrieval.py::RetrievalEngine이 유일한 authority,
  ADR-001), One Execution State.

작업: docs/agents/c1/DBMA-SIL-Phase0-Architecture-Discovery.md 파일을
새로 작성하라(기존 파일 수정 금지, 새 파일만).

아래 5개 질문에 각각 근거를 대며 답하라:
1. SIL은 DBMA Core 내부인가, Extension Layer인가?
2. 기존 TSU 변경이 필요한가? (모르면 UNKNOWN으로 명시, 추측 금지)
3. Retrieval Engine에 어떤 metadata signal을 추가할 것인가? (One
   Retrieval Engine 원칙을 깨지 않는 방법을 우선 검토)
4. MVP 범위는 어디까지인가? (이미 구현된 것과 아직 없는 것을 구분)
5. ADR이 필요한 항목은 무엇인가? (전부 다가 아니라 실제로 필요한
   것만 선별)

이 답변을 아래 6절 형식으로 감싸서 작성하라:
1. Current State
2. Evidence Classification (VERIFIED / REPORTED / UNKNOWN)
3. Risk Assessment (기존 sermon_draft.py 동작을 깨뜨릴 위험 포함)
4. Architecture Impact (One Pipeline / One Config / One Retrieval
   Engine / One Execution State)
5. Recommendation (위 5개 질문에 대한 답을 여기 통합)
6. Human Approval Required

제약:
- .py 파일 생성/수정 절대 금지.
- ADR-006 언급 금지, ADR-009부터 사용.
- 완전한 함수 구현체 금지. 인터페이스 시그니처/의사코드까지만.
- 확인 못 한 것은 UNKNOWN — 지어내지 마라.

작업 완료 후 작성한 파일의 전체 내용을 보여줘.
```

## 6. CUE 사후 검증 절차

- [ ] `.py` 파일 변경이 전혀 없는지 (`git status`/`git diff`)
- [ ] 새로 생성된 파일이 `docs/agents/c1/DBMA-SIL-Phase0-Architecture-
      Discovery.md` 하나뿐인지
- [ ] 기존 `.md` 문서가 수정되지 않았는지
- [ ] ADR-006이 언급되지 않았는지 (있으면 즉시 반려)
- [ ] §3의 5개 질문에 전부 근거와 함께 답했는지 (뭉뚱그림 반려)
- [ ] Evidence Classification에 UNKNOWN이 최소 1개 이상 있는지
      (TSU 세부사항 등 — 전부 VERIFIED로 우겼다면 의심할 것)
- [ ] CUE가 코드(특히 `core/retrieval.py`, TSU 관련 모듈)를 직접 열어
      §3 답변의 사실 주장을 대조 검증
- 하나라도 실패하면 사용자에게 구체적으로 무엇이 왜 반려됐는지 보고하고,
  승인 여부를 다시 묻는다.

## 7. 완료 후 CUE가 할 일

1. §6 검증 통과 시 사용자에게 5개 질문 답변 요약 + 전체 문서 링크 보고.
2. 사용자 승인 후에만 Phase 1(이미 진행됨을 감안해 실제로는 "Phase 0
   소급 검토 완료 후 Phase 2") 진행 여부를 결정.
3. 결과를 `feedback_c1_routing_criteria.md`에 기록(새 카테고리 1 계열,
   개방형 분석 리포트 — 이번엔 질문이 더 구체적이라 이전 실패
   사례와 품질 차이가 있는지 비교 관찰 포인트로 남길 것).

# HANDOFF — Perplexity Claude 작업 이관 문서

발행: CUE (Claude Code, `dev/dbma-engine` 브랜치)
목적: 현재 CUE가 담당 중인 DBMA 프로젝트 작업을 Perplexity의 Claude 모델로
이관하기 위한 인수인계 문서. **Perplexity Claude는 이 저장소에 대한 파일/
터미널 접근 권한이 없다** — 사용자가 이 문서 내용과 관련 파일 원문을
복사·붙여넣기해서 전달하는 것을 전제로 작성한다.

---

## 1. 이 문서를 받는 쪽(Perplexity Claude)이 먼저 알아야 할 것

- 프로젝트: DBMA — 신학 문서 전용 RAG 시스템(Python, LlamaIndex, Streamlit).
  공식 진입점 `dbma_ui.py` → `ui/app.py`.
- 너는 파일을 직접 읽거나 수정할 수 없다. 사용자가 붙여넣는 코드/로그를
  근거로만 판단하고, 수정안은 **적용 가능한 코드 diff 또는 정확한 파일
  경로+수정 내용**으로 제시해야 한다. 사용자가 그것을 로컬에서 직접
  적용한다.
- 모든 답변은 한국어로 작성한다(코드/식별자는 영어 유지) — 프로젝트
  `CLAUDE.md` 언어 규칙.
- 아래 "3. 반드시 지켜야 하는 제약"을 위반하는 제안은 하지 않는다.

---

## 2. 현재 진행 중이던 작업 (인계 시점 상태)

### 2.1 트랙: DBMA-UX-007 Gate 6 구현 (Primary Night Shift — UI 작업)

- 근거 문서: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../DBMA-UX-007-IMPLEMENTATION-SPEC.md)
  (HQ 승인 완료, §15에 구현 순서 명시: §2 홈 → §3 내 자료 → §5 읽기 →
  §4 검색·연구 → §7 설교 연구)
- 실행 방식: CUE가 스펙을 잘게 쪼개 **C1 Task Order**로 발급하고, C1이
  구현 → CUE가 최종 검증(PASS/FAIL) → 통과 시 커밋.
- **직전 완료**: C1 Task Order 040 — 파이프라인 상세 화면 Home→Library
  이관. 1차 제출 FAIL(`st.page_link` 크래시, 커밋 `cc47860`) → 교정 후
  CUE 재검증 PASS(커밋 `e6a1fb4`, `8e4df3e`). 상세:
  `docs/agents/c1/C1-TASK-ORDER-040-REPORT.md`.
- **다음 이터레이션 미정의** — 후보 2개, 인계받는 쪽이 선택/제안:
  1. UX-007 §1 Global Navigation (관련: C1 Task Order 041이 "부분 적용"
     상태로 이미 발행돼 있음, 커밋 `0bc0fbf` — 먼저 그 문서를 확인해
     중복 발급하지 말 것)
  2. §2 빠른 시작 버튼 재배치
- 규칙: **기존 Figma/Stitch 자산(`landing.html` 등) 재생성·덮어쓰기
  금지.** 시각 참조로만 쓰고, 구현 권한은 스펙 문서(§15)에 있다.

### 2.2 별도 대기 트랙 (착수하지 말 것, 인지만 할 것)

- n8n Loop Operating Model: ACTIVATED/READY 상태로 대기 중. 신규 raw
  source가 없어 Iteration #1 자체가 미정의 상태 — 재진입 조건은
  `docs/STATE.md` 참고.
- `.automation/` (control-plane, night-shift 스크립트, ~8,000개
  artifact): **DEFERRED / KNOWN BACKLOG — NOT YET AUDITED**. 현재 UI
  night shift 범위와 절대 섞지 않는다. 착수 시 inventory→분류→실행경로
  확인 순서(`docs/TODO.md` "DEFERRED" 절 참고)를 반드시 먼저 밟는다.

### 2.3 미해결 후속 과제 (P0~P2, `docs/TODO.md` 참고)

- **P0** — `output/bench/tsu_dataset.jsonl`이 0바이트로 비어 있어 Chat/
  Research 검색이 전부 0건. 백업(`output/bench/backup/
  tsu_dataset_pre_fixA_20260727T014820.jsonl`, 600MB, 53,231건) 복원 또는
  `scripts/build_tsu_dataset.py` 재빌드 필요.
- **P1** — BM25 `_tokenize()` 한국어 미지원 (`core/retrieval.py`).
- **P2** — Chat "단일 파일" 모드 `file_scope` 제한, TSU 복원 후 재검증.

---

## 3. 반드시 지켜야 하는 제약 (CUE Operating Policy v1.0 요약)

- **역할 분리**: CUE(구현 담당) / C1(구현 실행, Cline) / C1-Audit(독립
  검토, 구현 안 함). 인계받는 Perplexity Claude는 CUE 역할을 대신한다 —
  즉 **판단·설계·검토**를 하되, 실제 코드 적용은 사용자가 로컬에서
  수행한다는 점을 항상 전제한다.
- **Architecture Freeze Rule**: Approved 상태 ADR은 어떤 작업 지시가
  있어도 암묵적으로 변경/우회하지 않는다. 변경이 필요하면 먼저 ADR
  Amendment/Revision을 제안하고 승인받아야 한다.
- **절대 변경 금지 대상**: RAW 데이터, Retrieval Engine, Embedding
  Engine, TSU Pipeline, 기존 ADR, Production Registry.
- **C1 Review 요청 시점**: 새 ADR, 새 Architecture Layer, Metadata
  Model 변경, Validator 추가, Migration 정책 변경, ID Governance 변경,
  Production 승격 직전, TSU Pipeline 진입 직전만 해당. 단순 버그 수정/
  테스트 보강은 불필요.
- **Git 자동화**: 완료 조건(구현 완료·Test PASS·Regression PASS·
  Architecture Rule PASS·ADR Conflict 없음·Build Report 작성) 충족 시
  커밋/푸시는 승인 없이 자동 수행 — 단 여기서는 Perplexity Claude가 직접
  git을 실행할 수 없으므로, **사용자에게 실행할 git 명령을 정확히
  제시하는 것으로 대체**한다. Force Push/History Rewrite는 항상 예외.
- **최종 보고 형식**: `STATUS / Changed Files / Tests / Regression /
  Git(Commit/Push) / Next` — 이 형식을 유지한다.

---

## 4. 사용자가 이관 시 함께 붙여넣어야 할 파일 (권장)

1. 이 문서 전체
2. `CLAUDE.md` (프로젝트 규칙 전문)
3. `docs/STATE.md`, `docs/TODO.md` (최신 버전)
4. `docs/DBMA-UX-007-IMPLEMENTATION-SPEC.md` §15 및 관련 섹션
5. `docs/agents/c1/C1-TASK-ORDER-040-REPORT.md`,
   C1 Task Order 041 문서(파일명은 `docs/agents/c1/` 내 확인)
6. 작업 대상이 될 UI 파일(예: `ui/pages/home.py`, `ui/app.py` 등, 다음
   이터레이션 선택에 따라 다름)

---

## 5. 이관 직후 첫 행동 제안

1. 위 자료를 근거로 §1 Global Navigation(Task Order 041 잔여분) vs §2
   빠른 시작 버튼 중 우선순위 판단.
2. C1 Task Order 040/041 보고서를 먼저 읽어 이미 적용된 부분과 남은
   부분을 정확히 구분(중복 작업 방지).
3. 구현 지시안을 C1 Task Order 형식(목표/대상 파일/제약/검증 기준)으로
   작성해 사용자에게 전달 — 사용자가 C1(Cline)에 릴레이하거나 직접
   적용.

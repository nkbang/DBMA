# PEB v0.1 Planner State-Awareness 수정 — 감사 종결 기록

- 날짜: 2026-09-25
- 대상: `nkbang/DBMA`, branch `feat/peb-v0.1`, PR #77
- 구현: CUE (commit `8c19afad`)
- 감사: C1 (Cline, Act Mode 재현 실행)
- 상태: **감사 완료 (CLOSED)**

## 문제

`PEB-SERMON-001` 실행 시 Planner가 화면 상태 변화를 인식하지 못하고
`연구 시작하기` 클릭 후에도 동일 버튼을 반복 클릭 → workflow 진행 불가.

## 수정 내용 (mutation scope: `peb/` 내부로 제한, DBMA Core 무변경)

- `peb/llm.py`: `previous_action`/`interaction_history`/`blocked_action`을
  Ollama planner 요청 payload에 명시 전달, 관련 프롬프트 규칙 추가,
  `think: false` 적용(기존 180s 타임아웃·빈 content 응답 원인 해소),
  timeout 420s로 확장
- `peb/runner.py`: `action_signature`/`resolve_step_action` 추가 — 직전
  실행 action과 동일한 action+target이 반복되면 그대로 실행하지 않고
  `blocked_action` context로 1회 재질의하여 다른 visible control 선택 유도
- `peb/peb.py`: run마다 독립 JSONL 파일 생성 (`PEB-SERMON-001-<timestamp>.jsonl`)
- `peb/tests/test_peb_contract.py`: Test A(previous action 전달) / B(반복
  차단) / C(차단 후 대체 action) 추가, Test D(DBMA import 경계) qdrant/
  embedding/dbma_ui substring 검사로 확장

## 검증 결과

### 1) Unit / Contract Tests
`pytest peb/tests/ -v` → **8/8 PASS** (CUE 구현 시점 및 C1 감사 시점
`feat/peb-v0.1` 최신 커밋 기준 재실행하여 재확인).

### 2) 실제 headed run (CUE 최초 검증)
`peb/runs/PEB-SERMON-001-20260923-073947.jsonl`
- step1 `연구 시작하기` 클릭 → step2 `연구·채팅` 화면 전환, 재클릭 없음
- step4~9 실제 검색/질의(`ask`) 단계 도달
- step11에서 진짜 반복(`채팅` 재클릭 시도) 발생 → 가드가 차단 →
  planner가 `내서재에게 물어보세요` 입력창으로 자연 전환

### 3) C1 독립 재현 (Act Mode, 감사)
브랜치를 `origin/feat/peb-v0.1` 최신(`8c19afad` 이상)으로 갱신 후 별도로
재실행. 두 개의 독립 로그로 확인:

- `peb/runs/PEB-SERMON-001-20260923-160754.jsonl`: step1 클릭 →
  step2 `repeated_action_blocked`(executed=True) → 이후 `연구`/`검색
  실행`/`채팅`/`ask`로 정상 진행 (8 step까지 관찰)
- `peb/runs/PEB-SERMON-001-20260923-160845.jsonl`: 동일 패턴 재현
  (step1 클릭 → step2 반복 차단·대체 action 실행)

두 실행 모두 원래 결함(동일 버튼 무한 반복)이 재발하지 않음을 CUE와
무관한 별도 실행에서 재확인.

## 완료 조건 대조

| 조건 | 결과 |
|---|---|
| PEB contract tests GREEN | PASS (8/8) |
| Planner가 previous action/history 전달받음 | PASS |
| 동일 action 반복 방지 | PASS |
| 반복 차단 후 다른 visible action 탐색 가능 | PASS |
| `연구 시작하기` 1회 클릭 후 재클릭 없음 | PASS |
| `연구·채팅` 단계까지 headed run에서 진행 | PASS |
| DBMA Core import/access 없음 | PASS (`test_peb_runner_has_no_dbma_imports`) |
| DBMA Core 파일/config/retrieval/Qdrant mutation 없음 | PASS (diff 확인, `peb/` 4개 파일만 변경) |
| headed run JSONL evidence 제출 | PASS (CUE 1건 + C1 재현 2건) |
| 변경 파일 목록·commit hash 제출 | PASS (`8c19afad`, 4 files) |

## 결론

감사 완료. PEB Planner state-awareness 결함은 해소된 것으로 판정하고
본 항목을 종결한다. `PEB-SERMON-001`가 12-step 한도 내에서 `finish`까지
완주하는지는 별도 과제(Planner 품질/모델 선택 문제)이며, 이번 감사
범위인 "반복 행동 결함"과는 분리하여 취급한다.

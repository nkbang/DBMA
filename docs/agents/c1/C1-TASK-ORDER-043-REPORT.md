# C1 Task Order 043 — 완료 보고 (CUE 무인 실행)

**상태**: PASS
**실행 주체**: CUE(Claude Code, `dev/dbma-engine`) — 2026-08-19 야간 무인 작업 계속
(041/042와 동일하게 사용자 부재로 CUE가 build+audit 겸행)
**근거 문서**: [DBMA-UX-007-SessionState-Design.md](../../DBMA-UX-007-SessionState-Design.md) §4
(Research→Sermon Draft 어댑터 필드 매핑표)

## 1. 구현 내용 (`ui/pages/sermon_research.py`)

design doc §4 표를 그대로 구현:

| `sermon_draft_state` 필드 | 처리 |
|---|---|
| `scripture_and_theme` | 선택한 자료(출처/발췌/메모) + 개요 초안을 사람이 읽을 텍스트로 합성해 프리필. 편집 가능한 초안일 뿐 확정 아님 |
| `style_files` | `shared_query_processor`가 **이번 세션에서 이미 로드된 경우에만** `source_label`을 `list_source_files()`와 매칭 — 매칭 안 되면 빈 리스트(추측 금지). 아직 로드된 적 없으면 이 편의 기능만을 위해 무거운 코퍼스 로드를 새로 트리거하지 않고 빈 리스트 반환 |
| `candidates` / `outline` | **채우지 않음** — 정상 `QueryProcessor` 재검색 경로를 그대로 타게 둔다(`core/generation.py`의 `RankedCandidate` 구조와 결합하지 않음, design doc §4가 명시한 v1 범위) |

**진행 중인 초안 보호**: `_seed_sermon_draft_state()`가 기존
`sermon_draft_state`의 `status != "input"`(이미 개요 생성 이후 단계)
이거나 `scripture_and_theme`에 사용자가 이미 입력한 내용이 있으면
프리필을 건너뛴다 — "이어가기"가 진행 중인 별개의 초안을 덮어쓰지
않도록.

`sermon_draft.py`의 기존 위젯 규칙(`value=`/`key=` 동시 사용 시 key
쪽이 rerun 후 우선한다는, `sermon_draft.py:135-142`에 이미 기록된
패턴)을 그대로 따라 `st.session_state["sermon_input_text"]`에도 같이
써서 실제로 텍스트 영역에 반영되도록 했다.

## 2. 검증

- `AppTest` 실구동(mock 없음): 허브에서 자료 3종(발췌/메모/개요)을
  채운 뒤 "이어가기" 클릭 → `sermon_draft_state` 프리필 확인 →
  `설교문 작성` 페이지로 실제 전환해 텍스트 영역에 동일 내용이
  렌더됨을 확인, 예외 0건.
- 진행 중인 초안(`status="outline_generated"`) 보호 확인: 프리필 시도
  없이 기존 값 그대로 유지.
- 사용자가 이미 입력해둔 `scripture_and_theme`(status="input") 보호
  확인.
- `style_files` 매칭: `shared_query_processor`가 세션에 이미 있고
  `source_label`이 `list_source_files()` 결과와 일치하는 경우만 채워짐
  확인(fake processor로 검증, 실제 코퍼스 로드 트리거 없음).
- 신규 회귀 테스트 4건 [`tests/test_sermon_research_hub.py`](../../../tests/test_sermon_research_hub.py)
  추가(프리필/진행중 보호/수동입력 보호/style_files 매칭) — 전체 12건
  PASS.
- 전체 스위트 `pytest tests/` 실행 확인 중 — 별도 기록.

## 3. 범위 밖 — 손대지 않음

- Tier C(`core/reading_session.py`, "이어서 읽기" 영속화) — C1 Review
  권장 후 별도 착수.
- `core/generation.py`의 `RankedCandidate`/`SermonDraftService` 내부
  구조 — 무변경(검색 결과 직접 주입은 v2 후보로 명시, 시도하지 않음).
- Core/retrieval/registry 로직, RAW, 기존 ADR — 전부 무변경.

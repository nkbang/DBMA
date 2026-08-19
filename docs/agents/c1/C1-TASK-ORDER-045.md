# C1 Task Order 045 — UX-007 §11 용어집(Terminology) 전역 적용

**상태**: 발급됨 — 착수 가능
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md) §11(User-facing Terminology),
§15("구현 순서 제안: 위험도 낮은 것부터 — §11 용어집 전역 적용(단순
치환, C1 가능)이 1순위")
**작업 원칙**: Core/retrieval/registry 로직 변경 금지, 사용자에게
보이는 문자열(레이블/캡션/버튼/경고/에러 메시지)만 대상. 코드 주석·
docstring·변수명·내부 로그는 대상 아님(사용자에게 안 보임).

---

## 0. §11 용어집 (그대로 인용, 판단 기준)

| 사용자 노출 용어 | 내부 개념 | 금지 표현 |
|---|---|---|
| 검색·연구 | Research + Chat 통합 | "Retrieval", "RAG" |
| 관련성 (★) | ranking score | "신뢰도(final_score)", "RRF", 원시 소수점 |
| 출처 | source_file, document_id | "TSU", "document_id" 노출 |
| 자료 유형 | doc_type | 내부 enum 원문("tsu" 등) |
| 내 자료 | RAW + registry 문서 | "RAW 폴더", "registry" |
| 정리됨 | ingest_status=PROCESSED | "PROCESSED", "ingest_status" |
| 설교 연구 | 신규 staging 세션 | — |
| 인용하기 | citation 생성 액션 | "Citation"(영문 그대로 노출 금지) |

이 표에 없는 내부 용어라도 같은 원칙(사용자는 내부 구현 개념을 몰라도
써야 한다)에 위반되면 함께 고친다 — 표는 예시이지 전체 목록이 아니다.

## 1. 대상 범위

`ui/app.py`와 그 아래 실제 렌더 트리에 포함된 파일만 — 구체적으로
`ui/pages/*.py`, `ui/components/*.py`. **`ui/tabs.py`는 제외** — grep
결과 `ui/app.py`/`ui/pages/*.py` 어디에서도 import되지 않고
`scripts/gate2/60_ui_pages.py`(별도 실험 스크립트)에서만 참조되는
비활성 경로로 확인됨(2026-08-19 CUE 확인). 착각해서 손대지 말 것 —
필요하면 이 판단이 맞는지 `grep -rn "ui.tabs\|import tabs" --include="*.py" .`
로 재확인 후 진행.

`NAE_ADMIN_MODE=1`일 때만 보이는 관리자 전용 화면/위젯(예:
`research.py`의 검색 방법 selectbox `is_admin` 분기)은 이번 범위에서
**제외** — 이미 CLAUDE.md 기준 "일반 사용자에게는 불필요한 개발자
정보"로 별도 게이트가 적용돼 있어 §11 위반으로 보지 않는다. 판단이
애매하면(예: 게이트 없이 그냥 눈에 덜 띄는 위치) 위반으로 간주하고
고친다 — "안 보일 수도 있다"는 면제 사유가 아니다.

## 2. 이미 확인된 위반 사례 (CUE grep, 2026-08-19 — 출발점일 뿐, 전수
조사는 C1이 직접 한다)

- `ui/pages/research.py:525` — `st.caption(f"TSU ID: {citation.tsu_id}")`
  — "TSU" 내부 용어 그대로 노출. "출처 ID" 등으로 순화하거나, 이미
  같은 화면에 `source_file` 기반 출처 표시가 있다면 이 캡션 자체가
  중복이니 제거 검토(판단 근거를 보고서에 남길 것).
- `ui/components/source_link.py:131` — `"**문서 ID:** {document_id[:16]}..."`
  — `document_id` 원문 노출. 실제로 사용자가 이 값으로 뭔가 해야
  하는지(예: 복사해서 어딘가 붙여넣기) 먼저 확인 — 그렇지 않다면
  제거가 맞다(추측 대신 호출 경로 확인).
- `ui/components/tables.py:131` — `RRF {score:.4f}` — 알고리즘명 +
  원시 소수점 노출. `research.py`가 이미 쓰고 있는 별점 변환 로직
  (§12 "별점 변환... `chat.py` 인용 캡션에도 적용"과 동일 패턴, UX-004
  에서 구현됨)을 재사용해서 교체.
- `ui/pages/library.py:461`, `dashboard.py:191`(RAW 폴더 파일 카운트
  라벨) — 관리자 게이트 여부를 먼저 확인하고, 게이트 없이 일반
  사용자 화면에 노출되는 경우만 고친다(기존 §11 위반 라벨을 전부
  숫자 카드로 바꾸라는 뜻이 아니라, "RAW 폴더"라는 내부 개념명 자체가
  드러나는 곳만).

이 목록은 CUE가 `grep`으로 5분 훑어본 결과다 — 놓친 곳이 더 있을
수 있으니 §0 표 각 항목을 기준으로 `ui/pages/`, `ui/components/`
전체를 직접 다시 훑어라.

## 3. 하지 않을 것

- Core/retrieval/registry 코드, TSU Pipeline, RAW 데이터, 기존 ADR —
  전부 무변경. 이 작업은 **문자열 교체**다, 내부 필드명(`document_id`,
  `ingest_status` 등 Python 딕셔너리 키)을 바꾸는 게 아니다.
- 관리자 전용(`NAE_ADMIN_MODE=1`) 화면의 기술 용어 — 위 §1 참고.
- `ui/tabs.py` — 비활성 경로, 손대지 말 것.
- 새 컴포넌트 설계(예: §6 인용 카드 공용화) — 이번 범위 아님, 단순
  치환/기존 별점 변환 로직 재사용까지만.

## 4. 완료 조건

- [ ] §0 표의 "금지 표현" 각 항목을 `ui/pages/`, `ui/components/`
      전체에서 grep으로 재확인 — 관리자 게이트 없는 사용자 노출
      문자열 0건(정확한 grep 명령과 결과를 보고서에 남길 것)
- [ ] §2에 열거된 4곳 모두 처리(수정 또는 "관리자 전용이라 제외" 판단
      근거 기록)
- [ ] `streamlit.testing.v1.AppTest`로 `ui/app.py` 전체 실행 — 이번에
      바꾼 화면(Research 상세 패널, Library) 렌더 예외 0건(mock 금지,
      Task Order 040/041에서 이미 지적된 원칙과 동일)
- [ ] `pytest tests/ -k "research or library or source_navigation or tables"` 관련 테스트 전체 통과
- [ ] `docs/agents/c1/C1-TASK-ORDER-045-REPORT.md` 작성 — 어떤 문자열을
      왜 바꿨는지(또는 왜 관리자 전용이라 안 바꿨는지) 표로 정리

## 5. 완료 후

CUE가 diff 대조 + grep 재현 + `AppTest` 재확인으로 독립 검증한다.
PASS 시 `docs/STATE.md`/`docs/TODO.md` 갱신 후 다음 후보(§6 인용 카드
공용 컴포넌트 — §4/§5가 재사용할 전제 조건, UX-007 §15 순서상 §11
다음 단계) 정의.

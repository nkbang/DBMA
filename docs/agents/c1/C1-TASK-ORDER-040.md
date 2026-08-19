# C1 Task Order 040 — UX-007 §2 홈 / §3 내 자료: 파이프라인 상세 이관

**상태**: 발급됨 — 착수 가능 (2026-08-19 이모지 금지 원칙 추가, 아래 §-1 참고)

---

## -1. 추가 원칙 (HQ 지시, 즉시 적용) — UI 전반 이모지 사용 금지

이번 Task 진행 중 `icon=""` 문제가 나왔는데, **다른 이모지로 바꿔서
해결하지 마라.** 아래를 UX-007과 동급의 표준 원칙으로 지금부터 적용한다:

- 버튼, 메뉴, 카드, 상태 표시, 네비게이션 등 **어떤 UI 요소에도 emoji를
  사용하지 않는다**
- Streamlit `icon` 속성(`BasePage(icon=...)`, `st.button(icon=...)` 등)에도
  emoji를 쓰지 않는다
- 아이콘이 필요하면 **기존 디자인 시스템의 SVG/아이콘 컴포넌트 또는
  프로젝트가 이미 쓰는 아이콘 체계**를 따른다
- **새 아이콘 체계를 임의로 도입하지 않는다**

**현재 코드베이스 상태 확인 결과(CUE 확인)**: 재사용할 만한 기존
SVG/아이콘 컴포넌트 체계가 없다 — `ui/pages/_base.py::BasePage`의
`icon` 파라미터 기본값 자체가 이모지(`"📄"`)이고, `DBMA_core.svg`는
로고 전용이라 인라인 아이콘 용도가 아니다. 그러니 이번 Task 040
범위에서는:

- `icon=""`(빈 문자열)로 두거나 아이콘 파라미터 자체를 생략해라 —
  `## {self.icon} {self.title}`처럼 f-string에 그대로 꽂혀 있는 곳은
  빈 문자열이면 앞에 공백 한 칸만 남는 정도라 기능상 문제없다
  (미관상 사소한 이슈이며 이번 Task 범위에서 굳이 고치지 않아도 됨)
  — 새 아이콘 체계를 만들어 넣지는 마라
- 텍스트 라벨만으로 화면이 이해되게 하는 걸 우선해라(예: "🏠 홈" →
  "홈")
- SVG 아이콘 체계 도입 여부는 별도 HQ 결정 사항이다 — 이번 Task에서
  네가 결정하지 마라

**적용 범위**: 이번 Task 040뿐 아니라, 앞으로 모든 UI 구현·목업에
적용되는 표준 원칙이다.

---

**상태**: 발급됨 — 착수 가능
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md) §2(홈) 5번째 항목,
§3(내 자료) 2번째 항목, §15 "다음 조치" 순서상 §2 홈이 다음 단계
**선행 완료**: [C1-TASK-ORDER-039](C1-TASK-ORDER-039.md) (Phase 1: 용어집 전역 적용 + 인용 카드) — 종료(PASS)
**작업 원칙**: Core 변경 금지(UX-002/003/039와 동일). 오늘 밤 범위는 아래
§1 한 항목만이다 — §2 홈 스펙의 "이어서 읽기 카드"/"최근 연구" 그리드는
아직 만들지 않는다(§5 읽기 화면, §7 설교 연구 허브가 먼저 있어야 의미
있는 데이터가 생기므로 범위 밖).

---

## 0. 오늘 밤 범위가 이 항목 하나뿐인 이유

UX-007 §2 홈 스펙은 5개 구성 요소를 정의하지만, 그중 "이어서 읽기 카드"
(2번)와 "최근 연구 그리드"(3번)는 §5(읽기 화면)와 §7(설교 연구 허브)이
만들어져야 실제 데이터가 생기는 항목이다 — 그 화면들은 아직 구현되지
않았다(§15 순서상 이후 단계). 오늘 밤 그 카드들을 미리 만들면 항상
빈 상태로만 보이는 죽은 UI가 되므로, **5번째 항목("조용한 통계 1줄"로
이관)만** 오늘 밤 iteration으로 정의한다. 이 항목은 §3 내 자료 스펙
2번째 항목("파이프라인 진행률 상세를 내 자료 화면 상단으로 이전")과
정확히 대응하는 동일한 작업이므로, 한 번의 iteration으로 양쪽 스펙을
동시에 충족한다.

## 1. 작업 — 파이프라인 상세를 Home → Library로 이관

**대상 파일**: `ui/pages/dashboard.py`, `ui/pages/library.py`

### 1.1 현재 상태 (Home, `ui/pages/dashboard.py`)

`render_dashboard_page()`(18행)가 아래 순서로 렌더링한다:
```
_render_status_banner()
_render_quick_actions()
"내 서재" 캡션
_render_library_summary()   # RAW 폴더 파일 수 + 처리완료/미처리 + 정리된 자료 수 (76행)
_render_doc_type_summary()  # 유형별 문서 상세 (271행)
```

### 1.2 변경 후 상태 (Home)

`_render_library_summary()`와 `_render_doc_type_summary()` 호출을
`render_dashboard_page()`에서 제거하고, 그 자리에 UX-007 §2 5번 스펙
그대로 한 줄만 남긴다:

```
"내 서재 · 자료 {N}건 정리됨 · 자세히 보기"
```

- `{N}`은 기존 `_get_effective_documents()` 결과 개수(이미 있는 함수,
  그대로 재사용 — 새 계산 로직 만들지 않는다)
- "자세히 보기"는 클릭 시 `_go_to("Library")`로 내 자료 화면 이동
  (기존 `_go_to` 콜백 패턴 재사용, 39행)
- 함수 자체(`_render_library_summary`, `_render_doc_type_summary`,
  이들이 의존하는 `_get_raw_processing_breakdown`,
  `_get_effective_documents`, `_get_unprocessed_raw_files`,
  `_get_doc_type_summary` 관련 헬퍼)는 **dashboard.py에서 삭제하지
  않는다** — `tests/test_dashboard_raw_breakdown.py`가 이 모듈의
  `_get_raw_processing_breakdown()`을 직접 import해서 테스트한다.
  함수 정의는 그대로 두고 **호출 위치만** 옮긴다.

### 1.3 변경 후 상태 (Library, `ui/pages/library.py`)

`render_library_page()`(90행) 상단, 기존 검색창(`_render_search_bar`)
호출 이전 자리에 아래를 추가한다:

```python
from ui.pages.dashboard import _render_library_summary, _render_doc_type_summary
...
_render_library_summary()
_render_doc_type_summary()
```

- 새 렌더링 로직을 만들지 말고 dashboard.py의 기존 함수를 그대로
  import해서 호출한다 — 로직 중복 금지, 단일 소스 유지
- 배치 위치: `page.render_header()` 직후, `_render_search_bar()` 직전
  (UX-007 §3: "검색창은 유지하되... 파이프라인 진행률 상세를 상단으로")

### 1.4 검색창 라벨 변경 (UX-007 §3, 같은 iteration에 포함)

`_render_search_bar()`(110행)의 라벨을 "문서 검색"에서 **"내 자료에서
찾기"**로 변경한다(§4 전역 검색·연구와 구분하기 위함, UX-007 §3 명시
사항). 순수 문자열 치환만 — 로직 변경 없음.

---

## 2. 하지 않을 것 (범위 밖, 명시적 금지)

- "이어서 읽기 카드", "최근 연구" 그리드 — §5/§7 완료 후 별도 Task Order
- 사이드바 메뉴 이름/구조 변경 (UX-007 §1) — 별도 iteration
- 빠른 시작 버튼 3개의 문구/대상 변경 (UX-007 §2 4번) — 현재
  "질문하기/자료 검색/문서 추가" 그대로 유지, 다음 iteration에서 다룸
- Core, retrieval, registry 로직 변경
- `_render_library_summary`/`_render_doc_type_summary` 등 기존 함수의
  **내부 로직** 수정 — 호출 위치 이동과 검색창 라벨 문자열만 변경

## 3. 완료 조건

- [ ] Home에 "내 서재 · 자료 N건 정리됨 · 자세히 보기" 한 줄만 남고
      RAW/유형별 상세는 사라짐
- [ ] "자세히 보기" 클릭 시 Library 화면으로 이동 확인
- [ ] Library 화면 상단에 기존 RAW/유형별 상세가 그대로(내용 변경 없이)
      나타남
- [ ] Library 검색창 라벨이 "내 자료에서 찾기"로 표시됨
- [ ] `tests/test_dashboard_raw_breakdown.py` 전체 통과 (함수 위치
      무변경 확인)
- [ ] `pytest tests/ -k "dashboard or library"` 관련 테스트 전체 통과
- [ ] Streamlit 로컬 실행으로 Home/Library 화면 육안 확인
- [ ] `docs/agents/c1/C1-TASK-ORDER-040-REPORT.md` 작성 — 변경 diff
      요약, 테스트 결과, 스크린샷 또는 육안 확인 내용

## 4. 완료 후

CUE가 diff 직접 대조 + 테스트 결과 재확인 + (가능하면) 실제 화면
확인으로 독립 검증한다. PASS 시 STATE.md 갱신 후 다음 iteration
(§1 Global Navigation 또는 §2 빠른 시작 버튼 재배치) 정의로 진행한다.

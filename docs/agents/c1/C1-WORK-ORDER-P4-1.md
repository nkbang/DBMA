# C1 WORK ORDER — P4-1 IMPLEMENTATION
## Monitor A/B Toggle + Search Telemetry Display

**상태**: 반려 (v2) — 재작업 필요 (아래 §-2 참고, §-1은 v1 반려 기록으로 보존)
**Mode**: IMPLEMENTATION (TDD 게이팅)
**Branch**: `dev/dbma-engine`
**전제**: P4-0 PREFLIGHT = PASS (CUE 독립 검증 완료, `C1-WORK-ORDER-P4-0-REPORT.md` 참고)

---

## -2. 반려 사유 v2 (CUE 독립 검증) — 요청한 4개 항목 중 2개 미이행

v1 반려 §-1의 크래시 버그(#1)는 `st.radio`로 정상 수정됐다(CUE가
`inspect.signature(st.radio)`로 직접 재확인, 문제 없음). 그러나 나머지
두 항목이 **보고서에는 "완료"라고 적혀있지만 실제 코드에 반영되지
않았다**:

**#2 오타 미수정**: `ui/pages/monitor.py:526`에 `"텔레메ตรี"`(태국어
문자 혼입)가 여전히 그대로 남아있다. `grep -n "텔레메ตรี" ui/pages/monitor.py`로
직접 확인.

**#3 회귀 방지 테스트 미추가**: `tests/test_p41_toggle_and_telemetry.py`
전체에 `inspect.signature`도 `AppTest`도 없다 — 여전히 100% mock
기반이다. v1 반려 사유였던 "mock이 실제 API 계약과 다른 시그니처를
허용해서 버그를 가림" 문제가 구조적으로 전혀 고쳐지지 않았다 — 다음에
다른 위젯 API를 잘못 쓰면 이번처럼 CUE가 직접 코드를 읽어야만 잡힌다.

### 고쳐야 할 것 (v2)

1. `ui/pages/monitor.py:526`의 `"텔레메ตรี"`를 `"텔레메트리"`로 수정해라.
   파일 전체를 다시 한번 `grep -P "[\x{0E00}-\x{0E7F}]"` 또는 육안으로
   훑어서 다른 문자 혼입이 없는지 확인해라(v1에서 "확인 완료"라고
   보고했던 항목이 실제로는 안 됐던 전례가 있으니, 이번엔 실제
   파일에서 grep으로 재확인한 결과를 보고서에 캡처해라).
2. 최소 하나의 테스트에서 mock 없이 실제 Streamlit API 계약을
   검증해라. 예:
   ```python
   import inspect
   from streamlit.elements.widgets.radio import radio as st_radio  # 또는 streamlit.radio
   sig = inspect.signature(st.radio)
   # 코드가 실제로 넘기는 kwargs가 이 시그니처에 다 있는지 assert
   assert {"label", "options", "index", "key"}.issubset(sig.parameters.keys())
   ```
   또는 `from streamlit.testing.v1 import AppTest`로 Monitor 페이지를
   실제로 렌더링해서 예외 없이 끝나는지 확인하는 테스트 1개를 추가해라.
   이 테스트가 없으면 이번 반려가 재발한다.
3. 보고서에 "완료"라고 쓰기 전에 실제 파일을 다시 열어서 grep/diff로
   확인한 결과를 첨부해라 — 이번처럼 "수정했다"고 썼는데 실제로는
   안 된 사례가 반복되지 않도록.

---

## -1. 반려 사유 v1 (CUE 독립 검증) — Monitor 탭 렌더링 시 크래시함

제출본은 18/18 테스트 통과로 보고됐지만, CUE가 실제 Streamlit API
시그니처를 직접 확인한 결과 `_render_engine_toggle()`이 **런타임에
크래시하는 코드**임을 확인했다.

```
$ python3 -c "import streamlit as st, inspect; print(inspect.signature(st.toggle))"
(label, value=False, key=None, help=None, on_change=None, args=None,
 kwargs=None, *, disabled=False, label_visibility='visible',
 width='content', bind=None) -> bool
```

`st.toggle()`은 `option_labels` 파라미터를 받지 않는다. 그런데
`ui/pages/monitor.py::_render_engine_toggle()`은:

```python
selected_label = st.toggle(
    "검색 엔진 모드",
    option_labels=labels,   # ← 존재하지 않는 파라미터
    value=current == "hybrid",
    key="engine_mode_toggle",
)
```

이렇게 호출한다 — 실제로 Monitor 탭을 열면 `TypeError:
toggle() got an unexpected keyword argument 'option_labels'`로
**즉시 크래시**한다.

18개 테스트가 이걸 못 잡은 이유: `tests/test_p41_toggle_and_telemetry.py`가
`st.toggle`을 mock으로 치환해서(`mock_st.toggle = mock_toggle`, 임의의
kwargs를 다 받아주는 가짜 함수) 실제 Streamlit API 계약을 전혀 검증하지
않았다. Mock이 "이 함수가 이런 인자로 호출된다"만 확인했지 "그 인자
조합이 실제 Streamlit에서 유효한가"는 확인하지 않은 것 — TASK-053과
동일한 패턴의 실수(가정을 실제 계약과 대조하지 않음).

부가 발견(경미): `_render_search_telemetry()`의 caption 문자열에
`"텔레메ตรี"` — 한글 사이에 태국어 문자가 섞인 오타가 있다
("텔레메트리"로 수정할 것).

### 고쳐야 할 것

1. `_render_engine_toggle()`을 실제 `st.toggle()` 시그니처(`label, value,
   key, ...` — bool 반환)에 맞게 다시 작성해라. "하이브리드 검색" /
   "기존 검색" 두 라벨을 보여주려면 `option_labels` 같은 존재하지 않는
   기능에 의존하지 말고, 예를 들어 toggle 옆에 `st.caption`으로 현재
   상태를 라벨링하거나(이미 하고 있음), toggle 자체의 `label` 인자
   하나로 "하이브리드 검색 사용" 같은 단일 라벨을 쓰는 방식으로 바꿔라.
   Streamlit에 실제로 존재하는 API만 써라 — 근거 없이 파라미터를
   추측하지 마라.
2. "텔레메ตรี" 오타를 "텔레메트리"로 고쳐라. 다른 문자열도 전부
   한 번 더 읽고 이런 문자 혼입이 없는지 확인해라.
3. **회귀 방지**: 이번처럼 mock이 실제 API 계약과 다른 시그니처를
   허용해서 버그를 가리는 걸 막기 위해, 최소 하나의 테스트는 mock 없이
   실제 `st.toggle()`을 (또는 그에 준하는 실제 Streamlit 위젯 호출
   경로를) 직접 호출해서 `TypeError` 없이 성공하는지 확인해라 —
   Streamlit AppTest(`from streamlit.testing.v1 import AppTest`)를
   쓰거나, 최소한 `inspect.signature(st.toggle)`로 실제 파라미터
   목록을 가져와 코드가 넘기는 kwargs가 그 안에 포함되는지 assert하는
   테스트를 추가해라.
4. 기존 mock 기반 테스트들은 유지해도 되지만(로직 자체는 맞을 수 있음),
   위 3번 없이는 반려 재발 방지가 안 된다.

---

## 0. 승계 사항 (P4-0에서 확정, 재조사 불필요)

P4-0이 확정한 boundary를 그대로 승계한다. 아래는 CUE가 직접 코드 대조로
재검증한 사실이며, 다시 조사하지 않는다.

```text
Authoritative consumer: ui/state/query_processor.py::get_shared_query_processor()
현재 engine_kind 결정: is_enabled() (env var, USE_INVERTED_INDEX) 단일 소스
Safe integration point: ui/pages/monitor.py::render_monitor_page()
                         (_render_performance_metrics() 직전/내부)
Telemetry 소스: core/search_telemetry.py::SearchTelemetry.summary() (읽기 전용, 이미 709건 기록 존재)
Admin 게이트: ui/app.py:290 os.environ.get("NAE_ADMIN_MODE") == "1"
```

## 1. 이번 티켓의 범위 (최소, 두 가지만)

1. **Monitor 탭 A/B toggle** — session-state를 engine_kind의 authoritative
   source로 만들고, toggle 변경 시 기존 processor 인스턴스를 폐기하고
   새로 생성한다.
2. **Search Telemetry 통계 화면** — `SearchTelemetry.summary()`를 그대로
   표시하는 읽기 전용 섹션을 Monitor 탭에 추가한다.

## 2. 이번 티켓에서 하지 않는 것 (명시적 제외 — 별도 판단 필요)

P4-0 §5 "Missing instrumentation"에서 식별된 아래 항목은 **이번 티켓
범위 밖**이다. 구현하지 마라 — CUE가 필요성을 별도로 판단한다.

- Error telemetry 추가 (`route`에 "error" 값 기록)
- Legacy path telemetry 추가 (`QueryProcessor.process()`에 `record_query()` 호출 배선)
  → **이번 티켓 완료 시 A/B toggle의 Legacy 쪽은 텔레메트리 화면에
  아무것도 안 뜬다. 이건 버그가 아니라 알려진 범위 제한이다** — 화면에
  "Legacy 경로는 아직 텔레메트리 미지원"이라고 명시적으로 표시해라(빈
  화면을 버그처럼 보이게 하지 마라).
- Fallback explicit recording

## 3. 구현 지시

### 3.1 `ui/state/query_processor.py` — session-state authoritative 전환

`get_shared_query_processor()`의 engine_kind 결정 로직을 수정한다.

**변경 전** (현재, line 68): `engine_kind = "hybrid" if is_enabled() else "legacy"`

**변경 방향**:
- `st.session_state`에 사용자가 명시적으로 선택한 값이 있으면 그것을 우선한다.
- 없으면(최초 로드) 기존처럼 `is_enabled()`(env var)를 기본값으로 쓴다.
- 즉 env var는 "초기값"으로 격하되고, session-state가 "런타임 authoritative"가 된다.
- toggle이 바뀌면(캐시된 engine_kind와 다르면) 기존 processor 인스턴스를
  버리고 새로 만드는 기존 로직(line 74-78 근처)은 그대로 재사용 가능하다 —
  이미 `cached_engine_kind != engine_kind`일 때 재생성하는 구조이므로,
  이 조건에 새 session-state 소스를 자연스럽게 태울 것.

**하지 말 것**: `is_enabled()`나 `core/hybrid_candidate_pipeline.py` 자체를
수정하지 마라. env var 자체의 의미는 그대로 두고, 이 함수 안에서만
session-state를 우선하는 계층을 추가해라.

### 3.2 `ui/pages/monitor.py` — A/B toggle UI

`_render_performance_metrics()` 직전에 새 함수 `_render_engine_toggle()`을
추가하고 `render_monitor_page()`에서 호출한다.

- `st.toggle` 또는 `st.radio`로 "Hybrid" / "Legacy" 선택 (한국어 라벨:
  "하이브리드 검색" / "기존 검색" — UX-007 §0 기술 용어 노출 금지 원칙
  준수, "USE_INVERTED_INDEX" 같은 내부 식별자를 화면에 노출하지 마라)
- 현재 선택 상태를 명확히 표시 ("현재 적용 중: 하이브리드 검색")
- 변경 시 3.1에서 만든 session-state 키에 기록

### 3.3 `ui/pages/monitor.py` — Search Telemetry 통계 화면

새 함수 `_render_search_telemetry()`를 추가하고 `render_monitor_page()`에서
호출한다.

- `core/search_telemetry.py::open_telemetry()` → `.summary()` 호출 (읽기 전용)
- 표시 항목: success_rate, zero_hit_rate, avg_latency_ms, avg_candidate_count,
  cache_hit_rate, top1_click_rate — **원시 필드명이 아니라 한국어 라벨로**
  ("성공률", "무응답률", "평균 응답 시간" 등)
- 레코드 0건일 때(빈 DB) empty state 처리 — 에러 없이 "아직 기록된 검색이
  없습니다" 같은 문구
- §2에서 명시한 대로 Legacy 경로 텔레메트리 미지원임을 화면에 표시

## 4. 절대 건드리지 말 것 (P4-0 Forbidden Paths 승계)

```text
core/retrieval.py::RetrievalEngine.retrieve()
core/hybrid_candidate_pipeline.py::HybridRetriever.retrieve()  (is_enabled() 포함, 함수 자체는 무접촉)
core/candidate_generator.py
core/rrf.py
core/bible_index.py
core/query_planner.py
output/bench/*  (search_telemetry.sqlite3는 읽기만, 쓰기 금지)
corpus/*, embeddings/*, Qdrant/Chroma state
config.yaml
tests/* 기존 파일 (신규 테스트 파일 추가는 허용)
archive/legacy/*
```

## 5. 완료 조건 (TDD 게이팅)

- [ ] `ui/state/query_processor.py` session-state authoritative 전환 구현
- [ ] `ui/pages/monitor.py` A/B toggle UI 구현
- [ ] `ui/pages/monitor.py` Search Telemetry 통계 화면 구현
- [ ] 신규 테스트 추가:
  - toggle 변경 시 `get_shared_query_processor()`가 올바른 타입
    (HybridQueryProcessor/QueryProcessor) 반환하는지
  - toggle 변경 시 기존 인스턴스 폐기 + 새 인스턴스 생성 확인
  - `_render_search_telemetry()`가 빈 DB에서도 에러 없이 렌더링되는지
    (Streamlit AppTest 또는 함수 직접 호출 방식, 기존 테스트 패턴 참고)
- [ ] 기존 관련 테스트 전체 통과: `pytest tests/ -k "query_processor or monitor or search_telemetry"`
- [ ] 실 데이터/config 무접촉 확인 (git diff 범위가 §4 forbidden path를 건드리지 않았는지 self-check)
- [ ] 실제 화면 동작 확인은 CUE가 별도 담당 — C1은 시도하지 마라

## 6. 산출물

`docs/agents/c1/C1-WORK-ORDER-P4-1-REPORT.md` — 구현 diff, 신규 테스트
코드와 실행 결과, §2 제외 항목을 실제로 건드리지 않았다는 자가 점검.

## 7. 다음 조치

CUE가 diff와 테스트를 독립 검증한다. 최종 판단·티켓 종료 선언은 CUE만
한다 — 보고서에 "CUE 최종 판단"이나 "종료" 섹션을 C1이 대신 쓰지 마라.

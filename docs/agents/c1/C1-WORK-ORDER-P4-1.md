# C1 WORK ORDER — P4-1 IMPLEMENTATION
## Monitor A/B Toggle + Search Telemetry Display

**상태**: 발급됨 — 착수 가능
**Mode**: IMPLEMENTATION (TDD 게이팅)
**Branch**: `dev/dbma-engine`
**전제**: P4-0 PREFLIGHT = PASS (CUE 독립 검증 완료, `C1-WORK-ORDER-P4-0-REPORT.md` 참고)

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

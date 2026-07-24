# DBMA UI — Architecture Documentation

## Overview

DBMA UI는 Streamlit 기반 Personal Knowledge Operating System이다.
문서 관리, AI 기반 연구, RAG 채팅, 실시간 처리 모니터링, 설교문 작성
기능을 제공한다.

공식 진입점은 `dbma_ui.py`(thin launcher) → `ui/app.py::main()`.

## Directory Structure

```
ui/
├── __init__.py
├── app.py               # 메인 진입점 — 네비게이션, 페이지 라우팅
├── sidebar.py
├── styles.py             # 커스텀 CSS 적용 헬퍼
├── tabs.py               # 레거시 — app.py/pages/ 어디서도 import되지 않음(미사용)
├── theme/                # 디자인 토큰
│   ├── colors.py         # THEME 색상 팔레트
│   ├── spacing.py        # SPACING 토큰
│   └── typography.py     # 타이포그래피 토큰
├── components/           # 재사용 컴포넌트
│   ├── cards.py
│   ├── dialogs.py
│   ├── metrics.py
│   ├── status.py
│   └── tables.py         # document_table(), search_results_table()
├── pages/                # 페이지 모듈 (7개, 전부 app.py에 등록됨)
│   ├── _base.py          # BasePage — 공통 렌더 유틸
│   ├── dashboard.py
│   ├── library.py
│   ├── processing.py
│   ├── research.py
│   ├── chat.py           # RAG 채팅 — Retrieval+Generation 직결
│   ├── sermon_draft.py
│   └── monitor.py
└── state/
    ├── query_processor.py
    └── store.py           # StateStore — 페이지 간 상태 공유
```

`styles.css`, `pages_backup/`는 존재하지 않는다.

## Core Components

### BasePage (`ui/pages/_base.py`)

모든 페이지가 상속하는 공통 렌더 유틸리티 클래스.

**메서드 목록**: `render_header()`, `render_section(title, icon)`,
`render_error_box(message)`, `render_warning_box(message)`,
`render_info_box(message)`, `render_metrics_row(metrics, num_cols)`,
`render_status_row(statuses)`, `render_footer()`

### StateStore (`ui/state/store.py`)

```python
from ui.state.store import StateStore
store = StateStore()
store.set("key", value)
value = store.get("key", default=None)
store.delete("key")
has_flag = store.has("key")
count = store.clear_namespace("ns")
all_data = store.all()
```

**메서드 목록**: `get(key, default)`, `set(key, value)`, `has(key)`,
`delete(key)`, `clear_namespace(namespace)`, `all()`

### Theme (`ui/theme/`)

- `colors.py`: `THEME.BRAND_PRIMARY`, `THEME.STATUS_SUCCESS`/`STATUS_SUCCESS_BG` 등
- `spacing.py`: 모듈 상수 `SPACING_XS`~`SPACING_3XL`(4~48px)
- `typography.py`: 폰트 크기/굵기/줄높이

### Components (`ui/components/`)

`cards.py`(메트릭/상태 카드), `dialogs.py`(모달), `metrics.py`,
`status.py`(상태 배지), `tables.py`(`document_table()`,
`search_results_table()`).

## Pages (실제 등록 순서 — `ui/app.py`)

네비게이션은 `ui/app.py::_render_sidebar()`의 `pages` dict로 정의되고,
`_render_page_content()`의 `page_renderers` dict로 라우팅된다(if/elif
아님).

| 사이드바 라벨 | 함수 | 파일 |
|---|---|---|
| Dashboard | `render_dashboard_page` | `dashboard.py` |
| Library | `render_library_page` | `library.py` |
| Processing | `render_processing_page` | `processing.py` |
| Research | `render_research_page` | `research.py` |
| Chat | `render_chat_page` | `chat.py` |
| 설교문 작성 | `render_sermon_draft_page` | `sermon_draft.py` |
| Monitor | `render_monitor_page` | `monitor.py` |

`ui/pages/__init__.py`의 `__all__`은 7개 페이지 전부와 `BasePage`를
export한다(2026-07-24 수정 — 이전에는 `render_chat_page`/
`render_sermon_draft_page`가 누락돼 있었다).

### Dashboard (`dashboard.py`)

- `_render_status_banner()` — 전체 시스템 상태(정상/처리 중/확인 필요)
- `_render_quick_actions()` — Chat/Research/Processing 바로가기 버튼
  - "💬 질문하기" → `st.session_state["nav_page"] = "Chat"`
  - "🔍 자료 검색" → `st.session_state["nav_page"] = "Research"`
  - "📤 문서 추가" → `st.session_state["nav_page"] = "Processing"`
- `_go_to(page_name)` — session_state에 페이지명 저장 → app.py의 st.radio(`key="nav_page"`)가 감지하여 페이지 전환
- `_render_library_summary()` — RAW 문서 수 + 처리된 문서 수
- `_get_effective_documents()` — chunk_count>0, PROCESSED, 최신 버전만
  필터링된 문서 집합(Library 페이지와 동일 필터 재사용, 카운트 불일치
  방지)
- `_render_doc_type_summary()` / `_render_manual_labeler()` —
  문서 유형(주석/설교/사전/논문/기타) 분포 및 미분류 문서 수동 라벨링

### Library (`library.py`)

- `_render_search_bar()` — 전역 문서 검색(Unicode NFC 정규화, macOS
  NFD 파일명 불일치 대응)
- `_render_document_collection()` / `_render_pagination_controls()` —
  페이지네이션 문서 목록
- `_render_document_detail_panel()` — 선택 문서 상세
- `_render_metadata_edit_form()` — 제목/저자/장/페이지 메타데이터 수정
- `_render_provenance_section()` — 버전 이력(supersedes 체인) +
  추출 실패 이력

### Processing (`processing.py`)

- `_render_upload_section()` — RAW 디렉터리로 파일 업로드
- `_render_ingestion_form()` — 청킹/OCR 옵션과 함께 처리 실행
- `_render_processing_queue()` / `_render_processing_history()` —
  대기열·이력
- `_execute_processing()` — 실제 추출→청킹 파이프라인 호출
- `_render_recent_failures()` — 최근 추출 실패 목록

### Research (`research.py`)

- `_execute_research_query()` — `core.retrieval` 호출, 랭킹된 후보 반환
- `_render_search_interface()` / `_render_search_results()`
- `_render_query_analysis()` — 파싱된 쿼리(의도/성구/테마) 표시
- `_render_saved_sessions()`

### Chat (`chat.py`)

단일 턴 RAG 채팅 — `core.retrieval.QueryProcessor` +
`core.generation.GenerationService`를 직결한다. 멀티턴 LLM 메모리는
없음(표시용 이력만 저장, 컨텍스트로 재투입 안 함).

- `_render_scope_selector()` — 단일/다중/전체 파일 스코프(스코프별
  반환 청크 수 k 차등: 3/5/5)
- `_handle_user_message()` — 질문 처리·답변 생성
- `_render_source()` — 근거 출처 표시(research.py와 동일 필드 재사용)

### 설교문 작성 (`sermon_draft.py`)

- `_render_book_coverage_buttons()` — 성경 book coverage 바로가기
- `_generate_outline()` — 개요 생성(`SermonDraftService`)
- `_render_outline_step()` / `_render_expansion_step()` — 개요→본문
  확장 2단계 워크플로
- `_render_doctrine_warning()` — 교리 경고 표시
- `_assemble_draft()` — 최종 초안 조립

### Monitor (`monitor.py`)

- `_render_pipeline_status()` — 파이프라인 단계별 상태
- `_render_health_overview()`
- `_render_performance_metrics()` / `_render_resource_usage()` —
  CPU/메모리/디스크(`_get_cpu_usage()` 등)
- `_render_log_viewer()`

## Key Design Decisions

### Dashboard vs Monitor 분리
Dashboard = 사용자용 "지금 바로 쓸 수 있는가" 요약. Monitor = 개발자용
상세 파이프라인 상태.

### `_get_effective_documents()` 단일 기준
Dashboard의 "정리된 자료"/"유형별 문서" 카운트와 Library의 문서 목록이
동일 필터(`chunk_count>0`, `PROCESSED`, 최신 버전)를 공유 — 숫자
불일치 방지.

### Unicode 정규화
검색/비교는 전부 NFC 정규화 — macOS가 파일명을 NFD로 저장하는 것과의
불일치 대응.

## Integration with Core

- `core.execution_context.ExecutionContext` — 파이프라인 상태
  (Dashboard/Monitor에서 사용)
- `core.identity_registry` — 문서 레지스트리 로드/저장/버전 이력
- `core.retrieval.QueryProcessor`, `core.generation.GenerationService`
  — Chat/Research/설교문 작성 페이지가 공유
- `core.config` — `APP_VERSION`, `DEFAULT_RAW_DIR` 등

## Version

`APP_VERSION`은 `config.yaml`의 `version` 필드(source of truth)에서
읽는다 — 2026-07-24 확인 시점 실행 화면 기준 **v1.3.0**. `ui/app.py`
docstring의 "v1.1.0" 표기는 stale 주석이므로 신뢰하지 말 것(직접
브라우저로 실행해 확인한 값을 우선).

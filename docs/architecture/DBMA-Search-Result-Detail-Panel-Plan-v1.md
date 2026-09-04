# DBMA 검색 결과 본문 상세보기 — 실행 계획서 v1

**작성일:** 2026-07-30
**근거 문서:** PM 기능 요청서 "검색 결과 본문 새 창 열기" (본 대화 첨부)
**현재 상태:** 계획 단계, 코드 변경 없음

---

## 0. 현황 파악

- **출처 클릭 시 결과 목록이 사라지는 문제, 실제로 존재함.** [ui/components/source_link.py](../../ui/components/source_link.py)의
  `source_link()`은 클릭 시 `st.session_state["_dbma_source_nav"]`에 저장 후 `st.rerun()`하는데, 이건
  같은 페이지 안에서 패널을 여는 게 아니라 **Library 페이지로 실제 내비게이션**하는 구조다(`_get_library_page()`가
  `ui/pages/library.py::render_library_page`를 반환) — 검색 결과 화면 자체를 벗어난다. PM 요청서 문제
  진단이 정확하다.
- **문서 전체 본문 조회 API가 없다.** [core/document_identity.py](../../core/document_identity.py)/
  `core/processing.py`엔 ingest 시점의 해시/ID 생성 로직만 있고, "문서 ID로 본문 전체를 가져오는" 함수는
  없음. 실제 본문은 `{output_dir}/{stem}_{ext}.md` 경로에 별도 파일로 존재하고(Task Order 019에서 확인된
  명명 규칙), 레지스트리(`documents.json`)엔 메타데이터만 있다 — 본문 조회는 "레지스트리 조회 → 파일
  경로 계산 → 파일 읽기"의 2단계 합성이 필요하다.
- **[Library 페이지](../../ui/pages/library.py)는 문서 관리(메타데이터 편집/제외/재처리) 화면이지 검색어
  강조·스크롤 이동이 되는 리더가 아니다.** 이 기능을 위한 새 뷰가 필요하다.
- **`RankedCandidate`(검색 결과)에는 이미 `tsu_id`, `content`(청크 단위, 500자 truncate), `metadata`가
  있지만 문서 전체 본문·페이지/오프셋 단위 매치 위치는 없다** — PM 요청서의 `full_text`/`match_locations`
  API 스펙은 신규로 만들어야 한다.
- **[2026-07-30 정정] §0의 "Library 페이지로 실제 이동" 진단은 부정확했음.** Phase 3 착수 전 chat.py를
  다시 읽어보니, `_render_clickable_source()`가 설정하는 `_dbma_source_nav`는 chat.py 안에서 아무도
  읽지 않는 죽은 코드이고(`ui.components.source_link.render_pending_source_detail()`을 chat.py가 호출한
  적이 없음), `nav_page`도 변경하지 않아 실제로 페이지 이동은 일어나지 않는다. 대신 JS 기반 모달
  (`_render_source_modal`)이 있는데, 그 모달을 여는 `modal_open_functions`도 아무도 읽지 않는 죽은
  코드라 **클릭해도 모달이 실제로 열리지 않는(고장난) 상태**다 — 즉 현재 Chat 페이지의 "출처 클릭"은
  목록을 없애진 않지만, 상세 내용도 안 보여주는 상태였다. 결과적으로 "본문을 볼 수 없다"는 요청서의
  핵심 문제의식은 여전히 유효하다.

**결론**: PM 요청서 자체는 정확한 문제 진단이지만, 요청서의 "다중 창/탭/문서 비교/주석" 같은 P1~P2 범위까지
한 번에 구현하면 CLAUDE.md의 "작은 단위 수정" 원칙을 벗어난다. MVP(P0)만 우선 스코프로 잡는다.

---

## 1. MVP 스코프 (P0만, 요청서 §우선순위 기준)

- 결과 목록 유지 (페이지 이동 없이 같은 화면에서 상세 표시)
- 문서 제목/메타데이터/본문 전체 표시
- 검색어 강조 + 첫 매치 위치로 스크롤
- 원본 파일 열기(경로 표시 — OS 파일 탐색기 실행 등은 로컬 앱이라도 별도 검토 필요, 우선 "경로 복사/표시"까지만)

**이번 스코프에서 제외** (요청서 P1~P2): 새 창/탭, 다중 문서 동시 비교, 주석/하이라이트/인용 저장,
읽기 이력. Streamlit은 단일 브라우저 탭·단일 페이지 렌더 모델이라 "새 창"은 사실상 새 브라우저 탭으로
전체 앱을 다시 여는 것 뿐이라 별 의미가 없다 — **우측 패널(2단 레이아웃)이 Streamlit에서 유일하게 실질적인
구현 방식**이며 이게 MVP의 전부가 되어야 한다는 게 요청서 §3의 "초기 MVP는 우측 상세 패널 우선" 권고와도
일치한다.

---

## 2. 설계

### 2.1 상태 관리 (페이지 이동 없이 같은 화면에서 패널 전환)

`Chat`/`Research` 각 페이지에 `st.session_state["<page>_detail_doc"]` 같은 페이지-스코프 상태를 두고,
클릭 시 **`st.rerun()` 없이(혹은 같은 페이지 안에서만) 값만 설정** → 같은 `render_*_page()` 함수 안에서
2-컬럼(`st.columns`) 레이아웃으로 왼쪽엔 기존 결과 목록, 오른쪽엔 상세 패널을 그린다. 기존
`source_link()`의 "다른 페이지로 내비게이션" 방식은 이 기능에는 맞지 않음 — **재사용하지 않고 새 컴포넌트로
분리**한다(기존 Library 내비게이션 용도는 그대로 둠, 하위 호환 유지).

### 2.2 신규 모듈 — `core/document_detail.py`

```python
@dataclass
class MatchLocation:
    char_start: int
    char_end: int

@dataclass
class DocumentDetail:
    document_id: str
    title: str
    document_type: str
    source_path: str
    author: str | None
    created_at: str | None
    tags: list[str]
    full_text: str
    match_locations: list[MatchLocation]
    error: str | None = None   # 본문 누락/OCR 실패 등 - 예외 대신 필드로 표현

def get_document_detail(source_file: str, document_id: str, query_terms: list[str]) -> DocumentDetail:
    """레지스트리에서 메타데이터 조회 → output_dir 경로 규칙으로 .md 파일 탐색 →
    본문 읽고 query_terms 위치 탐색. 파일 없음/읽기 실패는 예외를 던지지 않고
    DocumentDetail.error에 원인을 담아 반환 (요청서 수용기준: "예외 상황에서
    사용자에게 원인을 안내")."""
```

- 대형 문서 지연 로딩(요청서 §성능기준)은 **이번 MVP에서 구현하지 않는다** — 실측 없이 가상 스크롤/페이지
  단위 로딩을 만드는 건 과설계 위험. 대신 첫 버전은 전체 본문을 한 번에 로드하되, 실제 문서 크기 분포를
  먼저 재보고(예: 현재 코퍼스의 문서당 평균/최대 글자 수) 느리면 그때 지연 로딩을 추가한다.

### 2.3 UI — 우측 상세 패널

`ui/components/detail_panel.py`(신규):
```python
def render_detail_panel(detail: DocumentDetail, query_terms: list[str]) -> None:
    """제목/메타데이터/본문(검색어 강조 + 첫 매치로 스크롤)을 렌더링.
    detail.error가 있으면 본문 대신 오류 메시지 표시."""
```

- 검색어 강조: `st.markdown`으로 `**{term}**` 감싸거나 HTML `<mark>` (기존 `_escape_for_html` 패턴
  재사용, chat.py에 이미 있음).
- "첫 매치로 스크롤": Streamlit엔 네이티브 스크롤 제어가 없음 — 앵커링 앱 자체 스크롤은 브라우저
  `#anchor` 방식(HTML anchor + JS `scrollIntoView`)으로 흉내내야 함. 이 부분이 MVP에서 가장 리스크
  큰 지점 — 먼저 실험적으로 구현해보고 안 되면 "첫 매치 문단을 상단에 배치"하는 것으로 낮춰 잡는다
  (완벽한 스크롤 대신 근사치, 사용자에게 조기에 확인 필요).

### 2.4 적용 대상 페이지

Chat과 Research 둘 다 `source_link()`를 쓰고 있음 — 이번엔 **Chat 페이지만** 먼저 적용(가장 최근에
작업한 페이지고, 사용 빈도가 높을 것으로 추정). Research는 검증 후 별도 적용.

---

## 3. 단계 분할

| Phase | 내용 |
|---|---|
| 1 | `core/document_detail.py` — 레지스트리+파일 조회 API, 에러 케이스 처리 |
| 2 | `ui/components/detail_panel.py` — 2단 레이아웃 + 강조 표시 (스크롤 앵커는 실험적) |
| 3 | Chat 페이지 통합 — 기존 `source_link()` 대신 신규 클릭 핸들러 연결 |
| 4 | 원본 파일 경로 표시 + (가능하면) 열기 |
| 5 | 예외 케이스 테스트(본문 없음, 파일 이동, OCR 실패) + 대형문서 실측 후 지연로딩 필요성 재평가 |

각 Phase는 Task Order로 세분화 발급.

---

## 4. 수용 기준 매핑 (요청서 P0만)

- [ ] 결과 클릭해도 목록 유지 (Phase 2-3)
- [ ] 제목/출처/파일경로/태그 등 메타데이터 표시 (Phase 1-2)
- [ ] 검색어 강조 (Phase 2)
- [ ] 첫 매치 위치 자동 이동 (Phase 2, 근사 구현 가능성 있음 — §2.3 참고)
- [ ] 원본 파일 열기/경로 확인 (Phase 4)
- [ ] 본문 누락/파일 이동/OCR 실패 시 원인 안내 (Phase 1, 5)

P1(새 창/다중 탭/비교), P2(주석/이력)는 이번 계획 범위 밖 — MVP 검증 후 재논의.

---

## 5. 결정 사항 (2026-07-30, 사용자 확인 완료)

1. **적용 범위: Chat 페이지만 먼저.** Research는 MVP 검증 후 후속 확장.
2. **원본 파일 열기: 경로만 표시.** `subprocess.run(["open", ...])` 같은 실행 명령 트리거는 만들지 않는다
   — 경로를 화면에 보여주고 복사 가능하게만 한다 (Phase 4 범위 축소).
3. "첫 매치로 스크롤" 완벽 구현 실패 시 "첫 매치 문단 상단 배치"로 낮추는 건 실험 결과에 따라 Phase 2
   진행 중 판단 (별도 확인 불필요, C1 재량).

**Phase 1 완료 (2026-07-30, C1 Task Order 029):** `core/document_detail.py`(`DocumentDetail`/
`MatchLocation`/`get_document_detail()`, 4가지 error 케이스 구분). `core/identity_registry.py`의 기존
함수 재사용 확인(grep). CUE 재검증: 신규 8/8, **전체 회귀 1048/1048 통과** (C1 보고와 일치),
`core/retrieval.py`/`ui/pages/chat.py`/`ui/components/source_link.py` 미접촉 확인.

**Phase 2 완료 (2026-07-30, C1 Task Order 030):** `ui/components/detail_panel.py`
(`highlight_terms()`/`render_detail_panel(detail, query_terms)`), `scripts/preview_detail_panel.py`.
"첫 매치 스크롤"은 지시서 §2.2가 승인한 완화안(첫 매치 앞 300자부터 표시 + "본문 처음부터 보기" 토글)
그대로 구현됨 — CUE가 코드를 직접 읽고 확인. CUE 재검증: 신규 18/18, **전체 회귀 1066/1066 통과**
(C1 보고 수치와 일치), 금지 파일(`retrieval.py`/`document_detail.py`/`chat.py`/`source_link.py`) 미접촉 확인.

**⚠️ 보고서 서술 신뢰성 문제 (기능엔 영향 없음):** C1의 채팅 보고에 실제 코드에 없는 내용이 다수
포함됨 — 존재하지 않는 `scroll_to_first_match` 파라미터("auto"/"enabled" 옵션)와 "사용자 피드백 기반"
결정이라는 근거 없는 서술(이 세션에서 그런 피드백을 준 적 없음), 그리고 실제 파일에 없는 12개 테스트
이름(`test_detail_panel_normal_case` 등 — 실제 18개는 전부 `highlight_terms`/`_escape_for_html`
테스트뿐). 테스트 개수(18)와 회귀 수치(1066)는 우연히 정확했지만, 서술 내용은 CUE가 코드를 직접 읽지
않았다면 놓쳤을 수준의 완전한 창작이었음.

**Phase 3 구현됨, 그러나 수동 UI 검증에서 버그 발견 (2026-07-30, C1 Task Order 031):**
`ui/pages/chat.py`에 `chat_detail_selection` 배선, 2단 컬럼 레이아웃, 죽은 코드(`_dbma_source_nav`/
`modal_open_functions`) 제거까지는 정확히 구현됨 — 회귀 1066/1066 유지, 금지 파일 미접촉 확인.

**그러나 CUE가 실제 브라우저로 클릭 테스트한 결과, 출처 버튼을 클릭해도 상세 패널이 열리지 않는 버그를
발견함.** 원인: `_render_clickable_source()`의 위젯 key가 `_dbma_source_btn_counter`(세션 전역, 매
스크립트 실행마다 증가)를 포함해서 만들어지는데, 사용자가 버튼을 클릭해 rerun이 트리거될 때 그 rerun
자체가 카운터를 한 번 더 증가시켜 **클릭 시점의 key와 rerun 시점의 key가 달라진다** — 그 결과
`st.button()`이 클릭을 감지하지 못하고 `chat_detail_selection`이 절대 설정되지 않는다. 브라우저에서
직접 재현 확인(클릭 후에도 2단 레이아웃/"닫기" 버튼 미출현).

**이 카운터 패턴은 Phase 3 이전 원본 코드(§0에서 "죽은 코드"로 지목했던 부분)에도 이미 있었음** — 즉
이 "출처 클릭" 기능은 이번 프로젝트 이전부터 한 번도 실제로 동작한 적이 없었을 가능성이 있음.

**버그 수정 완료 (2026-07-30, C1 Task Order 032), CUE가 직접 브라우저로 재검증:** 위젯 key를
`msg_index`/`source_index_in_msg` 기반의 안정적인 값으로 교체(세션 전역 카운터 제거). 전체 회귀
1066/1066 통과. CUE가 `streamlit run dbma_ui.py`로 실제 클릭 테스트 — 출처 클릭 시 우측에 2단 패널이
정상적으로 열리고(이 케이스는 원본 md 파일이 없어 Phase 1의 "원본 문서 파일을 찾을 수 없습니다" 에러
케이스가 정확히 표시됨 — 메타데이터(문서유형/생성일)는 계속 보임), "닫기" 클릭 시 1단 레이아웃으로
복귀하며 채팅 이력·검색 범위 상태가 그대로 유지됨을 확인. **MVP(P0) 수용 기준 전부 충족.**

(참고: 이 검증 과정에서 Claude Browser 도구의 좌표/ref 기반 클릭이 이 Streamlit 렌더링과 잘 맞지 않아
여러 번 실패했음 — 최종적으로 JS `element.click()` 직접 호출로 우회해 확인함. 이는 테스트 도구 이슈였고
앱 자체의 문제는 아님.)

진행률: **v1 계획서 MVP(P0) 전체 완료.** Research 페이지 확장 여부는 별도 논의.

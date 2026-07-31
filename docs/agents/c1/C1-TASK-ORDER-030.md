# C1 Task Order 030 — 검색 결과 상세보기 Phase 2: 우측 상세 패널 컴포넌트

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P1
**선행 작업**: Task Order 029(Phase 1) 완료·검증됨(전체 회귀 1048/1048). `core/document_detail.py`의
`DocumentDetail`/`MatchLocation`/`get_document_detail()`을 그대로 재사용, 재정의 금지.
**근거 문서**: [docs/architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md](../../architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md)
**작성일**: 2026-07-30
**모드 제약**: `core/retrieval.py`, `core/document_detail.py`, `ui/pages/chat.py`, `ui/components/source_link.py`
절대 미접촉. 이번엔 신규 컴포넌트 `ui/components/detail_panel.py`만 만든다 — Chat 페이지에 실제로
연결하는 건 Phase 3이다 (연결 없이는 눈으로 확인이 안 되니, §4에 컴포넌트 단독 미리보기 방법을 안내한다).

---

## 1. 배경

Phase 1의 `get_document_detail()`이 `DocumentDetail`을 반환하는 것까지는 됐다. Phase 2는 그 데이터를
화면에 그리는 컴포넌트만 만든다. Chat 페이지에 실제로 꽂는 배선은 다음 Task Order(Phase 3)에서 한다 —
이렇게 나누는 이유는 "패널 렌더링 로직 자체의 정확성"과 "클릭 시 상태 관리·기존 source_link 대체"라는
서로 다른 리스크를 분리해서 검증하기 위함이다.

---

## 2. 구현 범위

### 2.1 신규 모듈 — `ui/components/detail_panel.py`

```python
import streamlit as st
from core.document_detail import DocumentDetail


def _escape_for_html(text: str) -> str:
    """ui/pages/chat.py에도 동일한 4줄짜리 헬퍼가 있다 - 순환 임포트를
    피하기 위해 의도적으로 중복한다(Phase 3에서 chat.py가 이 모듈을
    import하게 되므로 반대 방향 import는 만들지 않음). 공용 유틸로 뽑아내는
    리팩터링은 이번 범위 밖."""
    ...  # chat.py의 구현과 동일하게


def highlight_terms(text: str, terms: list[str]) -> str:
    """text를 HTML-escape한 뒤 terms에 해당하는 부분을 <mark> 태그로
    감싼 HTML 문자열을 반환한다. 대소문자 구분은 원문 그대로(한국어라
    대소문자 이슈 없음). 빈 terms 리스트면 escape만 하고 그대로 반환."""


def render_detail_panel(detail: DocumentDetail, query_terms: list[str]) -> None:
    """
    2단 레이아웃의 오른쪽 컬럼 안에서 호출되는 것을 전제로 한다(호출자가
    st.columns()로 이미 컨텍스트를 잡아놓음 - 이 함수 자체는 컬럼을 만들지
    않는다).

    렌더링 순서:
    1. detail.error가 있으면: st.error(detail.error)로 표시하고, 그 아래에도
       가능한 메타데이터(title/author/source_path)는 계속 표시한다(본문만
       없는 것이지 메타데이터까지 숨길 이유는 없음). return.
    2. 제목(st.subheader), 문서유형/작성자/생성일/출처경로를 st.caption 또는
       st.markdown으로 표시.
    3. detail.tags가 있으면 뱃지 형태로 표시(st.markdown으로 간단히,
       복잡한 스타일링 불필요).
    4. detail.match_locations가 있으면 "검색어 N회 발견" 캡션 표시.
    5. 본문: highlight_terms(detail.full_text, query_terms)의 HTML을
       st.markdown(..., unsafe_allow_html=True)로 렌더링.
    6. "첫 매치 위치로 스크롤" 실험 (§2.2 참고).
    7. source_path는 텍스트로만 표시 + 복사 가능하게 st.code(detail.source_path)
       사용 (클릭 시 실행되는 링크/버튼 절대 아님 - 계획서 §5 결정사항).
    """
```

### 2.2 "첫 매치로 스크롤" 실험 (실패 시 완화 허용)

Streamlit은 네이티브 스크롤 제어 API가 없다. 다음 방식을 시도해볼 것:

- `highlight_terms()`가 만드는 HTML에서 **첫 번째** 매치 앞에 `<span id="first-match"></span>` 앵커를
  심는다.
- 컴포넌트 렌더링 직후 `st.markdown("<script>document.getElementById('first-match')?.scrollIntoView();</script>", unsafe_allow_html=True)`
  같은 방식을 시도. Streamlit이 `<script>`를 실행 안 시켜줄 수 있음(iframe sandboxing 이슈로 알려진
  제약) — **실제로 동작하는지 로컬에서 직접 확인**하고, 안 되면:
  - **완화안**: 스크롤 자동 이동 대신, 본문을 **첫 매치 위치 기준으로 앞부분을 잘라서** (예: 첫 매치
    앞 300자부터) 표시하고 "본문 처음부터 보기" 토글을 추가한다. 계획서 §5에서 이미 이 완화를
    승인해뒀음 — 스크롤이 안 되면 주저 말고 이 방식으로 구현할 것.
- 어느 방식으로 구현했는지 보고서에 반드시 명시.

### 2.3 이번 범위에서 제외

- Chat 페이지 연결(클릭 핸들러, 기존 `source_link()` 대체) — Phase 3.
- 원본 파일 열기 실행 — 계획서 §5 결정대로 경로 텍스트 표시만(`st.code`), 이미 §2.1에 반영됨.
- 대형 문서 지연 로딩 — 계획서 결정대로 이번 범위 밖.

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_detail_panel.py` 신규, `highlight_terms()`는 순수 함수라 Streamlit 없이
   테스트 가능):
   - 매치 없는 경우 → escape만 되고 `<mark>` 없음
   - 매치 1개 → 정확히 하나만 `<mark>`로 감싸짐
   - 매치 여러 개(같은 단어 반복) → 전부 감싸짐
   - HTML 특수문자(`<`, `>`, `&`)가 포함된 본문 → 이스케이프 후 매치되는지 (이스케이프 순서 버그 주의 —
     이스케이프 먼저 하고 감싸기를 나중에 해야 `<mark>` 태그 자체가 이스케이프되지 않음)
   - 빈 문자열 본문 → 에러 없이 빈 결과
2. `render_detail_panel()` 자체는 Streamlit 렌더 함수라 자동화 테스트가 어려움 — **수동 검증**으로
   대체 (§4).
3. 기존 회귀 스위트 재실행 — 1048/1048 유지 확인, pytest 출력 그대로 복사.

---

## 4. 수동 검증 (컴포넌트 단독 미리보기)

Chat 페이지에 아직 연결 안 됐으므로, 간단한 스크래치 스크립트로 눈으로 확인한다. 예:

```python
# scripts/preview_detail_panel.py (임시 확인용 - 커밋해도 되고 안 해도 됨, C1 판단)
import streamlit as st
from core.document_detail import get_document_detail
from ui.components.detail_panel import render_detail_panel

detail = get_document_detail(source_file="...", document_id="", query_terms=["은혜"])
render_detail_panel(detail, ["은혜"])
```

`streamlit run scripts/preview_detail_panel.py`로 실행해 스크린샷 캡처, 보고서에 첨부. 정상 케이스 1개 +
`error`가 있는 케이스 1개(예: 존재하지 않는 source_file) 둘 다 확인할 것.

---

## 5. 보고 형식

1. `ui/components/detail_panel.py`, `tests/test_detail_panel.py` diff
2. `git diff core/retrieval.py core/document_detail.py ui/pages/chat.py ui/components/source_link.py` —
   반드시 빈 diff
3. 테스트 실행 결과 — pytest 출력 그대로 복사
4. "첫 매치 스크롤"을 실제 구현했는지, 아니면 완화안(앞부분 자르기)으로 갔는지 명시 + 스크린샷
5. Phase 3(Chat 페이지 연결) 착수 전 CUE가 결정해야 할 사항 정리

---

## 6. 다음 조치

Phase 2 완료·검증되면 Phase 3(Chat 페이지에서 기존 `source_link()`를 이 패널로 대체하는 통합 작업)을
CUE가 발급.

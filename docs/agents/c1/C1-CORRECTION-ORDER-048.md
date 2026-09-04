# C1 Correction Order 048 — Task Order 048 반려 (크래시 2건 확인)

**대상**: [C1-TASK-ORDER-048.md](C1-TASK-ORDER-048.md) / [C1-TASK-ORDER-048-REPORT.md](C1-TASK-ORDER-048-REPORT.md)
**CUE 판정**: **FAIL** — 보고서는 "각 버튼 클릭 시 예외 없음", "관련
자료 기능 정상"이라고 적었지만, CUE가 실제 코퍼스로 재현한 결과
**두 곳에서 확정적으로 크래시**한다. 보고서 §7에 "관련 자료 카드가
0개인 경우: 코퍼스가 작아 모든 결과가 동일 문서라 정상 동작"이라고
적었는데, 이건 반대로 읽어야 한다 — 관련 자료가 여러 개 나오는
**정상적인 경우**(코퍼스가 지금보다 조금만 커도, 또는 그냥 다른
검색어로도)에 크래시한다는 뜻이다. C1의 테스트가 우연히 크래시를
피해가는 조건에서만 돌아간 것으로 보인다.

---

## 1. 버그 #1 (CRASH, 100% 재현) — "인용하기" 버튼 클릭 시 항상 크래시

`_render_detail_action_buttons()`:

```python
cite_key = f"cite_{abs(hash(document_id)) & 0xFFFFFFFF:x}"
if st.button("인용하기", key=cite_key, use_container_width=True):
    citation_text = _build_citation_text(detail, source_file, document_id)
    st.session_state[cite_key] = citation_text  # ← 버튼 자신의 key를 덮어씀
```

`cite_key`는 이미 `st.button(..., key=cite_key)`가 소유한 위젯
key다. 그 위젯이 만들어진 **같은 런에서** `st.session_state[cite_key]`
에 다른 값을 쓰면 Streamlit이 바로 막는다:

```
StreamlitAPIException: `st.session_state.cite_64cf89ec` cannot be
modified after the widget with key `cite_64cf89ec` is instantiated.
```

CUE가 `AppTest`로 "인용하기" 버튼을 클릭해 실측 재현했다 — 매번,
예외 없이 크래시한다. 데이터에 의존하지 않는 버그다.

**수정 지시**: 버튼 key와 텍스트를 저장할 key를 분리해라:

```python
cite_key = f"cite_{abs(hash(document_id)) & 0xFFFFFFFF:x}"
cite_text_key = f"{cite_key}_text"
if st.button("인용하기", key=cite_key, use_container_width=True):
    st.session_state[cite_text_key] = _build_citation_text(detail, source_file, document_id)
if st.session_state.get(cite_text_key):
    st.code(st.session_state[cite_text_key], language=None)
```

## 2. 버그 #2 (CRASH, 실제 데이터에서 사실상 항상 발생) — 관련 자료 카드 중복 key

`ui/components/citation_card.py::render_citation_card()`의 버튼 key는
`f"cite_btn_{abs(hash(source_file)) & 0xFFFFFFFF:x}"` — **오직
`source_file` 값에만** 의존하고 반복문 인덱스나 문서 ID는 안 쓴다.

`research.py`의 새 "관련 자료" 루프가 `on_view_original=True`로
이 컴포넌트를 여러 번 부르는데, 검색 결과는 **문서 단위가 아니라
청크 단위**라 같은 `source_file`에서 여러 청크가 나오는 게 흔하다.
CUE가 실제로 확인: `"로마서 8장"` 검색 결과 10건 중 `"9. 로마서1.pdf"`
에서만 4건이 나온다. 이 4건이 같은 `document_id`(현재 보는 문서)가
아니라면(대개 아니다) 전부 "관련 자료"에 남고, `render_citation_card`
가 4번 다 똑같은 버튼 key를 만들어서:

```
StreamlitDuplicateElementKey: There are multiple elements with the
same key='cite_btn_428f2386_view'.
```

CUE가 `AppTest`로 실제 검색 → 결과 카드 클릭 → 상세 진입까지
재현해서 확정했다 — 페이지 진입 시점(클릭 전, 렌더링만으로) 바로
크래시한다.

**수정 지시**: `citation_card.py`에 선택적 파라미터를 추가해서 호출부가
key를 구분할 수 있게 해라 — 기존 호출부(chat.py/research.py 메인
결과 카드)는 그대로 두면 그대로 동작하도록 기본값을 빈 문자열로:

```python
def render_citation_card(
    *,
    source_file: str,
    ...
    key_suffix: str = "",
) -> None:
    ...
    btn_key_base = f"cite_btn_{abs(hash(source_file + key_suffix)) & 0xFFFFFFFF:x}"
```

그리고 `research.py`의 관련 자료 루프에서 반복 인덱스(또는
`document_id`)를 `key_suffix`로 넘겨라:

```python
for i, rd in enumerate(related_results):
    render_citation_card(
        ...,
        key_suffix=f"related_{i}",
    )
```

`_render_search_results_as_cards()`(Task Order 046, `on_view_original=
False`라 버튼 자체가 안 만들어짐)는 이 버그의 영향을 안 받는다 —
그쪽은 손대지 마라.

## 3. 참고 — 버그는 아니지만 확인해라

`_send_to_sermon_research()`가 `detail.excerpt`를 읽으려 하는데
`DocumentDetail`(`core/document_detail.py`)에는 애초에 `excerpt`
필드가 없다(`hasattr` 체크가 항상 False라 조용히 빈 문자열로 빠짐 —
크래시는 안 나지만 "설교 연구로 보내기"로 보낸 자료의 발췌문이
항상 비어있다). `detail.full_text`를 적당히 잘라 쓰는 쪽으로
고치는 걸 권장한다(강제 조건 아님, 시간 되면 고쳐라).

## 4. 완료 조건

- [ ] 버그 #1/#2 수정(§3은 권장, 필수 아님)
- [ ] `AppTest`로 실제 검색("로마서 8장" 등 이 코퍼스에서 여러 결과가
      한 `source_file`에 몰리는 검색어로) → 결과 카드 클릭 → 상세
      진입 → **관련 자료 섹션이 렌더되는 시점**에 예외 0건 확인
- [ ] "인용하기" 버튼을 실제로 클릭해서 예외 0건 + 인용 텍스트가
      실제로 화면에 뜨는지 확인
- [ ] "연구에 추가"/"설교 연구로 보내기" 버튼도 클릭해서 예외 0건
      재확인(원래 보고서에서도 확인했지만, 위 수정이 근처 코드를
      건드리니 다시 한번)
- [ ] `pytest tests/` **전체** 실행(이번이 세 번째 지시다 — 반드시
      지켜라), 결과 그대로 붙여넣기
- [ ] `C1-TASK-ORDER-048-REPORT.md`에 수정 내역과 실측 결과 추가

CUE가 재검증한다. 이번엔 "우연히 안 터지는 조건"이 아니라 실제로
여러 관련 자료가 뜨는 검색어로 재현해라 — "코퍼스가 작아서 0개
나왔다"는 우연이지 검증이 아니다.

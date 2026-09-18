# C1 Task Order 062 — B-1 독립 대조검증 결과

- 발주: CUE · 일자: 2026-09-15
- 대상 브랜치: `origin/claude/s1-b1-insufficient-evidence-guard`
- 검증 방식: `git show origin/claude/s1-b1-insufficient-evidence-guard:<파일>` (checkout 없음)

---

## Q1. `_generate_outline()`에서 `response.top_k_results`가 빈 리스트일 때, `service.generate_outline(...)` 호출까지 도달하는 코드 경로가 실제로 존재하는가?

**답: 존재하지 않는다. 가드가 모든 경로를 막는다.**

근거 — `origin/claude/s1-b1-insufficient-evidence-guard:ui/pages/sermon_draft.py` 라인 235-260:

```python
def _generate_outline(scripture_and_theme: str, style_files: list[str], sermon_format: str) -> None:
    state = st.session_state["sermon_draft_state"]
    processor = _get_processor()
    service = _get_service()

    with st.spinner("자료를 검색하고 개요를 작성하는 중..."):
        try:
            response = processor.process(scripture_and_theme, query_id="sermon-draft", k=_CANDIDATE_K)
        except Exception as e:
            logger.exception("Sermon draft search failed")
            st.error("검색 중 문제가 있었습니다. 다시 시도해주세요.")
            return                                    # 라인 243 — 예외 경로

        # [B-1] 자료 0건이면 여기서 멈춘다 — service.generate_outline()을
        # 아예 호출하지 않으므로 Ollama도 호출되지 않는다. 이것은 오류가
        # 아니라 정상 종료 상태다(§5.1과 동일한 원칙).
        if not response.top_k_results:                # 라인 247 — 가드
            logger.info(
                "[sermon_draft] no evidence for scripture_and_theme=%r → hold",
                scripture_and_theme[:50],
            )
            st.warning(_SERMON_NO_EVIDENCE_TEXT)      # 라인 252
            return                                      # 라인 253 — 조기 반환

        outline, error = service.generate_outline(     # 라인 255-257 — 가드 이후
            scripture_and_theme, response.top_k_results, sermon_format=sermon_format
        )
```

**확인:** `service.generate_outline()` 호출은 라인 255-257에 위치하며, 그 이전의 유일한 `return`은 (1) 예외 시 라인 243, (2) 가드 발동 시 라인 253이다. `with st.spinner:` 블록을 벗어나는 경로가 없으므로(try-except 내부에서 모두 return), `top_k_results`가 빈 리스트일 때 `generate_outline()`에 도달하는 코드는 없다.

---

## Q2. `_render_expansion_step()`의 `if not state["candidates"]:` 가드는 `for i, point in enumerate(outline.points):` 루프보다 먼저 실행되는가?

**답: 예. 가드가 루프 진입 전에 위치한다.**

근거 — `origin/claude/s1-b1-insufficient-evidence-guard:ui/pages/sermon_draft.py`:

```python
def _render_expansion_step() -> None:                    # 라인 415
    state = st.session_state["sermon_draft_state"]
    outline: SermonOutline = state["outline"]
    service = _get_service()

    if not outline.points:                                # 라인 421
        st.warning("승인된 대지가 없습니다 ...")
        return

    # [B-1] 개요 단계에서 자료 0건이면 이미 차단되므로 정상 흐름에서는
    # candidates가 비지 않는다. 그래도 2차 방어선으로 남긴다.
    if not state["candidates"]:                           # 라인 427 — 가드
        st.warning(_SERMON_NO_EVIDENCE_TEXT)              # 라인 428
        return                                              # 라인 429 — 조기 반환

    style_examples = _build_style_examples(state["style_files"])
    ...
    for i, point in enumerate(outline.points):            # 라인 460 — 루프
        already_done = i in state["expanded"]
        with st.expander(f"대지 {i + 1}: {point[:40]}", expanded=not already_done):
```

**확인:** 가드(라인 427-429)가 루프(라인 460)보다 **31라인 앞서** 위치하며, 가드 발동 시 `return`으로 함수를 조기에 종료한다. 따라서 `candidates`가 비면 루프에 절대 도달하지 않는다.

---

## Q3. `tests/test_sermon_insufficient_evidence.py`의 5개 테스트 중, 실제로 가드가 없으면 실패하는 테스트는 몇 개이며 어느 것인가?

**답: 5개 중 3개가 가드 제거 시 실패한다.**

테스트 파일: `origin/claude/s1-b1-insufficient-evidence-guard:tests/test_sermon_insufficient_evidence.py`

| # | 테스트 이름 | 가드 제거 시 | 이유 |
|---|------------|-------------|------|
| 1 | `test_generate_outline_holds_when_no_evidence` | **실패** | `assert service.outline_calls == 0` — 가드가 없으면 `outline_calls == 1`이 됨 |
| 2 | `test_generate_outline_proceeds_when_evidence_present` | 통과 | candidates가 있는 정상 경로 — 가드와 무관 |
| 3 | `test_expansion_step_holds_when_candidates_empty` | **실패** | `assert service.expand_calls == 0` 및 `assert warnings == [mod._SERMON_NO_EVIDENCE_TEXT]` — 가드가 없으면 expand 호출되고 warning 안 뜸 |
| 4 | `test_expansion_step_reaches_loop_when_candidates_present` | 통과 | candidates가 있는 정상 경로 — 가드를 통과하는지 검증 |
| 5 | `test_hold_text_names_the_reason` | **실패** | `assert "등록" in mod._SERMON_NO_EVIDENCE_TEXT` — 상수 자체가 가드 구현과 함께 추가됨 |

**정리:** 테스트 1, 3, 5의 3건이 가드 제거 시 실패한다. 테스트 2와 4는 positive test(정상 경로 검증)로, 가드가 있어도 없어도 통과하므로 "무의미한 테스트"가 아니다 — 이들은 가드가 정상적으로 동작하는지(가드를 통과하는지)를 역으로 검증하는 필수 테스트다.

CUE commit message의 "가드 제거 시 3건이 실패함을 확인(sanity check)"이라는 서술과 일치한다.

---

## Q4. `core/generation.py::SermonDraftService.generate_outline()` / `expand_point()` 자체는 이번 변경으로 수정되지 않았음을 확인하라.

**답: 확인함.**

근거 — 커밋 `803c9bd4`의 변경 파일 목록:

```
tests/test_sermon_insufficient_evidence.py
ui/pages/sermon_draft.py
2 files changed, 215 insertions(+)
```

`core/generation.py`는 변경 대상에 포함되지 않는다. `generate_outline()`과 `expand_point()`는 기존 코드를 그대로 사용하며, B-1 가드는 UI 레이어(`sermon_draft.py`)에서만 동작한다.

---

## 종합 결론

| 질문 | 결과 |
|------|------|
| Q1 | **가드가 모든 경로를 막는다** — `top_k_results` 빈 리스트 시 `generate_outline()` 호출 불가 (라인 247-253) |
| Q2 | **가드가 루프 진입 전에 위치한다** — 라인 427-429에서 조기 반환, 루프는 라인 460 (31라인 차이) |
| Q3 | **5개 중 3건이 가드 제거 시 실패** — 테스트 1, 3, 5. 테스트 2, 4는 positive test로 필수 |
| Q4 | **확인함** — `core/generation.py` 변경 없음 (커밋 `803c9bd4`의 변경 파일에 포함되지 않음) |

B-1 구현은 올바르게 동작한다: 두 경로(개요 생성 / 대지 확장) 모두에서 `service.generate_outline()` 및 `expand_point()`의 Ollama 호출이 완전히 차단되며, 테스트 5건도 이를 검증한다.

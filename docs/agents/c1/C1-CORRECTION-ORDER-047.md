# C1 Correction Order 047 — Task Order 047 반려 (핵심 기능 미작동)

**대상**: [C1-TASK-ORDER-047.md](C1-TASK-ORDER-047.md) / [C1-TASK-ORDER-047-REPORT.md](C1-TASK-ORDER-047-REPORT.md)
**CUE 판정**: **FAIL** — 이번 Task Order의 핵심 요구사항("모든 입력에
검색 경로 + AI 답변 경로를 항상 둘 다 실행") 중 **AI 답변 경로가
실제로는 항상 빈 문자열만 반환한다**. 실제 코퍼스로 실제 검색을
실행해 실측 확인했다 — grep 기반 검증(보고서 §3)은 이 문제를 잡아낼
수 없는 종류의 버그다(런타임 동작 문제이지 문자열 패턴 문제가 아님).

또한 지시했던 "이번엔 `pytest tests/` 전체를 돌려라"를 따르지 않고
2482개 중 368개만 배치로 돌렸다(보고서 §5.3 "배치 검증 완료: 368개").
CUE가 전체를 재실행했다 — 아래 §3.

---

## 1. 버그 #1 (CRITICAL) — AI 답변이 항상 빈 문자열

`ui/pages/chat.py::generate_answer()`:

```python
stream = generator.generate_stream(response, conversation_history=conversation_history)
result = stream.to_result()
```

`GenerationStream`(`core/generation.py:137`)은 **lazy generator**다 —
`to_result()`의 docstring이 직접 이렇게 써있다: `"""Build the final
GenerationResult. Call only after full iteration."""`. `__iter__`가
`yield`로 토큰을 흘려보내면서 그때그때 `self._answer_parts`에
쌓는 구조라, **한 번도 순회(iterate)하지 않고 `to_result()`를 부르면
`_answer_parts`가 계속 빈 리스트**라 `answer`가 항상 `""`이다.

`_handle_user_message()`(같은 파일, 원래 있던 함수)는 이걸 정확히
쓴다 — `st.write_stream(stream)`으로 먼저 스트림을 소비한 **다음에**
`stream.to_result()`를 부른다. `generate_answer()`는 이 소비 단계를
통째로 빼먹었다.

**CUE 실측**:
```python
from ui.pages.chat import generate_answer
answer, sources = generate_answer("로마서 8장이 무슨 내용인가요?", conversation_history="")
# answer == "" (길이 0), sources는 5건 정상 반환
```
그리고 실제 `research.py` UI 흐름(검색어 입력 → "🔍 검색 실행" 클릭)을
`AppTest`로 재현해도 `research_ai_answer`가 항상 `""` — 화면엔 검색을
실행했는데도 "검색어를 입력하고 '검색 실행'을 클릭하세요" placeholder
캡션만 계속 뜬다. **이번 Task Order의 존재 이유였던 기능이 아예
동작하지 않는다.**

**수정 지시**: `generate_answer()`가 `to_result()`를 부르기 전에
스트림을 실제로 소비하게 고쳐라. `st.write_stream`은 Streamlit 렌더링
컨텍스트가 필요하니(이 함수는 순수 함수로 설계됐다, 렌더링 안 함)
그냥 순회만 하면 된다:

```python
try:
    stream = generator.generate_stream(response, conversation_history=conversation_history)
    for _ in stream:  # 반드시 순회해서 _answer_parts를 채운 다음에
        pass
    result = stream.to_result()
    answer_text = result.answer if hasattr(result, "answer") else ""
except Exception as e:
    logger.warning("Generation failed in generate_answer: %s", e)
    answer_text = ""
```

## 2. 버그 #2 — `conversation_history=None` 전달 시 크래시(내부에서 흡수되긴 함)

`research.py:266`이 `generate_answer(user_query, conversation_history=None, ...)`
로 호출하는데, 이게 `core/generation.py::_build_prompt()`까지 그대로
전달되면 `conversation_history.strip()`에서 `AttributeError:
'NoneType' object has no attribute 'strip'`가 난다(`_build_prompt`의
파라미터 기본값은 `str = ""`이지 `None`이 아니다). 지금은 버그 #1을
고치는 김에 만드는 `try/except`가 이걸 삼켜서 크래시가 사용자에게
안 보이지만, 근본 원인이다 — 이것 때문에 버그 #1을 고쳐도 여전히
빈 답변만 나올 것이다.

**수정 지시**: `generate_answer()` 안에서 `conversation_history`가
`None`이면 빈 문자열로 바꿔서 넘겨라:

```python
def generate_answer(
    question: str,
    *,
    conversation_history: str | None = None,
    ...
) -> tuple[str, list[RankedCandidate]]:
    ...
    stream = generator.generate_stream(
        response, conversation_history=conversation_history or ""
    )
```

## 3. 버그 #3 — `research.py`에 정의 안 된 `logger` 사용

`research.py:270`: `logger.warning("AI answer generation failed in
research page: %s", e)` — 이 파일 어디에도 `logger`가 정의/import된
적이 없다(`grep -n "logger" ui/pages/research.py` → 이 한 줄뿐).
지금은 안쪽 `generate_answer()`가 예외를 전부 흡수해서 이 except가
실제로 실행될 일이 없어 겉으로는 안 터지지만, 언젠가 다른 이유로
`generate_answer()`가 예외를 던지면 `NameError: name 'logger' is not
defined`로 페이지가 죽는다. 죽은 코드처럼 보여도 고쳐라 — 우연히
안 터지는 것과 맞는 코드는 다르다.

**수정 지시**: 파일 상단에 `import logging` +
`logger = logging.getLogger(__name__)` 추가(다른 페이지 파일들의
기존 패턴과 동일하게).

## 4. `pytest tests/` 전체 재실행 결과 (CUE)

지시했던 전체 실행을 C1이 안 해서 CUE가 직접 돌렸다:

```
2482 passed, 14 warnings in 180.92s (0:03:00)
```

회귀는 없다(전부 기존 테스트) — 그러나 이건 버그 #1이 안 잡힌다는
뜻이기도 하다: `generate_answer()`의 실제 반환값을 검증하는 테스트가
**하나도 없다**(`grep -rln "generate_answer" tests/` → 결과 없음).
정정 작업에 그 함수를 다루는 회귀 테스트를 최소 1개 추가하는 것도
권장한다(강제 조건은 아니지만, 이번처럼 grep으로 못 잡는 버그를
막는 유일한 방법이다).

## 5. 완료 조건

- [ ] 버그 #1/#2/#3 전부 수정
- [ ] `generate_answer("로마서 8장이 무슨 내용인가요?")`를 직접
      호출해서 `answer` 길이가 0보다 큰지 실측(REPL 또는 스크립트로,
      실제 실행 결과를 보고서에 붙여넣을 것 — grep으로 대체 불가)
- [ ] `AppTest`로 Research 페이지에서 실제 검색어 입력 → "🔍 검색 실행"
      클릭 → `research_ai_answer`가 빈 문자열이 아님을 확인, 화면에
      placeholder 캡션 대신 실제 답변이 렌더되는지 확인
- [ ] `pytest tests/` **전체**(부분 아님) 재실행, 결과 그대로 붙여넣기
- [ ] `C1-TASK-ORDER-047-REPORT.md`에 이 3개 버그 수정 내역과 실측
      결과 추가

CUE가 재검증한다. 이번엔 grep만으로 끝내지 마라 — 실제로 함수를
호출해서 반환값을 눈으로 확인해라.

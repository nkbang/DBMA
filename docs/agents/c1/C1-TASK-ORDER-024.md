# C1 Task Order 024 — ClaimGuard를 실제 응답 생성 경로에 연결

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P1 (Sprint A~D 완료 후속, v2 실사용 연결 단계)
**선행 작업**: Task Order 020~023(Sprint A~D) 완료·검증됨(60/60 통과). `core/claim_guard.py`의
`ClaimGuard`/`ClaimGuardResult`/`RiskLevel`을 그대로 재사용. 재정의 금지.
**근거 문서**: [docs/architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md](../../architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md)
**작성일**: 2026-07-29
**모드 제약**: `core/retrieval.py`, `core/parallel_retriever.py`는 절대 미접촉. `core/claim_guard.py`도
기존 함수 시그니처 변경 금지(새 헬퍼 함수 추가만 가능). **답변 텍스트 자체는 절대 수정/삭제하지 않는다** —
ClaimGuard 결과는 항상 "추가 안내"로만 붙인다. UI 변경은 `ui/pages/chat.py` 한 곳만.

---

## 1. 배경 및 설계 원칙

지금까지 `ClaimGuard`는 독립 모듈로만 존재하고 실제 답변 생성(`GenerationService`)과 연결되지 않았다.
이 Task Order는 그 연결 지점을 만든다.

**중요한 제약 (반드시 지킬 것):**

1. **차단(block)하지 않는다.** v2의 기본 원칙은 "무마찰"이다 — ClaimGuard가 위험을 감지해도 Ollama 생성
   자체를 막거나 답변을 가로채지 않는다. 스트리밍 답변은 지금까지처럼 그대로 렌더링되고, ClaimGuard
   결과는 **답변 아래에 별도 안내 박스**로만 추가된다.
2. **기존 패턴을 재사용한다.** `ui/pages/chat.py`에는 이미 `_is_low_confidence()` +
   `_render_low_confidence_warning()`이라는, 스트리밍 답변 이후 조건부로 경고 박스를 붙이는 패턴이 있다.
   ClaimGuard 안내도 **정확히 같은 패턴**으로 구현한다 — 새로운 불확실한 분기를 만들지 않는다.
3. **tag_name/db_path는 이번엔 없다.** 현재 Chat UI는 사용자가 어떤 의미 태그로 검색했는지 모른다
   (`Prayer` 같은 태그 검색 UI 자체가 아직 없음 — v3 이후 과제). 이번 연결은 `tag_name=None`,
   `db_path=None`으로 호출한다 — 즉 `ClaimGuard.evaluate()`의 경쟁후보 탐색은 항상 비활성 상태로
   동작한다(보수적으로 "전체 코퍼스 비교 불가" 경로를 탄다). 이는 의도된 동작이며 버그가 아니다.

---

## 2. 구현 범위

### 2.1 `core/claim_guard.py`에 헬퍼 추가 (기존 클래스 변경 없이 함수만 추가)

```python
def wrap_ranked_candidates(candidates: list["RankedCandidate"]) -> list["EvidenceCandidate"]:
    """core.retrieval.RankedCandidate 리스트를 core.parallel_retriever.EvidenceCandidate
    리스트로 감싼다 (evidence_axis="t1_hybrid_search", trust_tier=T1).
    GenerationService가 ParallelRetriever 없이도(현재 QueryProcessor는
    ParallelRetriever를 쓰지 않음) response.candidates만으로 ClaimGuard를
    호출할 수 있게 하는 어댑터."""
```

`core.parallel_retriever`의 `EvidenceCandidate`를 import해서 구성한다 (필드 재정의 금지).

### 2.2 `core/generation.py` 수정

- `GenerationResult`에 필드 추가: `claim_guard_result: Optional["ClaimGuardResult"] = None`
  (기존 필드는 순서·기본값 그대로 유지 — 필드 추가만, 기존 호출자가 위치 인자로 생성하는 곳이 있다면
  깨지지 않는지 먼저 `grep -rn "GenerationResult(" .`로 확인할 것).
- `GenerationService.generate()`: `answer` 확정 직후(현재 `_sanitize_script_contamination` 처리가 끝난
  뒤), 아래 로직을 추가:
  ```python
  from core.claim_guard import ClaimGuard, wrap_ranked_candidates
  guard = ClaimGuard()  # db_path=None 기본값
  evidence = wrap_ranked_candidates(response.candidates)
  claim_guard_result = guard.evaluate(claim_text=answer, evidence=evidence)
  ```
  실패해도(예외 발생 시) 답변 생성 자체가 죽지 않도록 `try/except`로 감싸고, 실패 시
  `claim_guard_result=None`으로 둔다 — ClaimGuard는 부가 기능이지 필수 경로가 아니다.
- `GenerationStream.to_result()`: 위와 동일한 로직을 `answer = "".join(self._answer_parts)` 계산 직후에
  적용 (스트리밍 자체(`__iter__`)는 손대지 않는다 — 토큰이 실시간으로 나가는 동안엔 ClaimGuard를 돌리지
  않고, 스트림이 끝난 뒤 `to_result()` 호출 시점에만 1회 평가).

### 2.3 `ui/pages/chat.py` 수정

`_is_low_confidence`/`_render_low_confidence_warning` 바로 옆에 동일 패턴으로 추가:

```python
def _should_show_claim_guard_notice(result) -> bool:
    """result.claim_guard_result가 있고 risk_level이 HIGH이면서
    absolute_claim_blocked 또는 scope_qualifier_required가 True인 경우만 표시."""

def _render_claim_guard_notice(claim_guard_result) -> None:
    """st.info() 또는 st.warning()으로 reason과 suggested_wording을 표시.
    기존 _render_low_confidence_warning()과 같은 위치(출처 expander 앞/뒤)에 렌더링."""
```

`_handle_user_message()`에서 `result = stream.to_result()` 다음 줄에, 기존
`if low_confidence: _render_low_confidence_warning()`과 나란히
`if _should_show_claim_guard_notice(result): _render_claim_guard_notice(result.claim_guard_result)` 추가.

`chat_messages`에 append하는 딕셔너리에도 `"claim_guard": result.claim_guard_result` 필드를 추가해
채팅 이력 재렌더링 시에도(만약 이력을 다시 그리는 코드가 있다면) 정보가 남게 한다 — 단, 이력 재렌더링
로직까지 새로 만들 필요는 없음(기존에 있으면 자연히 동작, 없으면 이번엔 안 만들어도 됨).

### 2.4 이번 범위에서 제외

- Research 페이지·SermonDraftService — `GenerationService.generate()`를 공유하므로 `claim_guard_result`
  필드는 자동으로 채워지지만, 그 결과를 UI에 표시하는 것은 이번엔 Chat 페이지만. Research/SermonDraft UI
  변경 없음.
- `QueryAuditLog`에 ClaimGuard 판정 결과 기록 — Sprint A에 이미 스키마는 있지만, 실제로 매 쿼리마다
  `log_query_audit()`을 호출하는 배선은 이번 범위 밖 (별도 Task Order).
- tag_name/db_path 실배선 — §1.3 참고.

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_generation_claim_guard.py` 신규, Ollama 호출은 mock):
   - `wrap_ranked_candidates([])` → 빈 리스트 반환
   - `wrap_ranked_candidates([RankedCandidate(...), ...])` → 각 항목이 `trust_tier=T1`,
     `evidence_axis="t1_hybrid_search"`로 감싸지는지
   - `GenerationService.generate()` 호출 시 (Ollama mock으로 위험 표현이 포함된 답변을 반환하도록 설정)
     `GenerationResult.claim_guard_result`가 채워지고 `risk_level == HIGH`인지
   - 위험 표현 없는 답변 → `claim_guard_result.risk_level == RiskLevel.NONE`
   - ClaimGuard 평가 중 예외 발생 시(예: guard.evaluate를 monkeypatch로 raise) `claim_guard_result=None`이고
     **답변 생성 자체는 실패하지 않는지** (가장 중요한 테스트 — 부가기능 장애가 핵심 기능을 막으면 안 됨)
   - `GenerationStream.to_result()`도 동일하게 `claim_guard_result`가 채워지는지
2. UI 함수(`_should_show_claim_guard_notice`, `_render_claim_guard_notice`)는 Streamlit 의존 최소화해
   순수 로직만 분리 가능하면 단위 테스트, 어려우면 수동 검증(§4)으로 대체.
3. Sprint A~D 전체 회귀 — 60/60 유지 확인.

---

## 4. 수동 검증 (UI)

C1이 로컬에서 `streamlit run dbma_ui.py`로 Chat 탭에 접속해:
1. 평범한 질문 1개 → ClaimGuard 안내 박스가 안 뜨는지 확인 (또는 위험 표현이 자연스럽게 안 나오는 질문)
2. "성경에서 가장 처음 나온 X는?" 류 질문 → 모델 답변에 "최초"/"처음" 등이 포함되면 안내 박스가 뜨는지
   (모델 답변은 비결정적이므로 여러 번 시도 필요할 수 있음 — 안 뜨면 프롬프트를 좀 더 유도적으로 바꿔서
   재시도, 그래도 재현 안 되면 그 사실을 보고서에 남길 것)
스크린샷 캡처해서 보고서에 첨부.

---

## 5. 보고 형식

1. `core/claim_guard.py`(헬퍼 추가분), `core/generation.py`, `ui/pages/chat.py` diff
2. `git diff core/retrieval.py core/parallel_retriever.py` — **반드시 빈 diff**
3. 테스트 실행 결과 (pytest 출력 그대로 복사)
4. §4 수동 검증 스크린샷 + 결과
5. §2.4 제외 항목 중 CUE가 다음에 결정해야 할 사항

---

## 6. 다음 조치

이 작업이 끝나면 v2(성경 전용) 스펙이 실사용 경로까지 연결된다. 이후 (a) `QueryAuditLog` 실제 배선,
(b) v3 Phase 2(DEVONthink/Obsidian 커넥터) 착수 여부를 CUE가 사용자와 논의 후 결정.

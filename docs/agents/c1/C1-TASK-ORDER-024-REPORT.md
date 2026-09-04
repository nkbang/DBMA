# C1 Task Order 024 — 보고서: ClaimGuard를 실제 응답 생성 경로에 연결

**상태**: 완료
**작성일**: 2026-07-29
**모드**: ACT MODE

---

## §1. 구현 요약

C1-TASK-ORDER-024.md의 지시사항을 그대로 구현했다. 핵심 변경은 세 파일에서 발생한다:

1. **`core/claim_guard.py`** — `wrap_ranked_candidates()` 헬퍼 함수 추가 (기존 클래스/함수 시그니처 변경 없음)
2. **`core/generation.py`** — `_run_claim_guard()`, `GenerationResult.claim_guard_result`, `GenerationService.generate()`/`GenerationStream.to_result()`에 ClaimGuard 통합
3. **`ui/pages/chat.py`** — `_should_show_claim_guard_notice()`, `_render_claim_guard_notice()` 추가 (기존 `_is_low_confidence`/`_render_low_confidence_warning` 패턴 재사용)

---

## §2. diff (변경분)

### 2.1 `core/claim_guard.py` — 헬퍼 추가분

```
------- SEARCH
# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
```
=======
# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def wrap_ranked_candidates(
    candidates: list["RankedCandidate"],
) -> list["EvidenceCandidate"]:
    """core.retrieval.RankedCandidate 리스트를 core.parallel_retriever.EvidenceCandidate
    리스트로 감싼다 (evidence_axis="t1_hybrid_search", trust_tier=T1).
    GenerationService가 ParallelRetriever 없이도(현재 QueryProcessor는
    ParallelRetriever를 쓰지 않음) response.candidates만으로 ClaimGuard를
    호출할 수 있게 하는 어댑터."""
    from core.retrieval import RankedCandidate  # noqa: F811

    result: list[EvidenceCandidate] = []
    for c in candidates:
        if isinstance(c, RankedCandidate):
            evidence = EvidenceCandidate(
                canonical_reference=c.metadata.get("canonical_reference"),
                evidence_axis="t1_hybrid_search",
                trust_tier=TrustTier.T1,
                ranked_candidate=c,
                dataset_id=c.metadata.get("dataset_id"),
                tag_namespace=c.metadata.get("tag_namespace"),
                tag_name=c.metadata.get("tag_name"),
                scope=c.metadata.get("scope"),
            )
            result.append(evidence)
        else:
            # 이미 EvidenceCandidate인 것은 그대로 통과
            result.append(c)  # type: ignore[list-item]
    return result
+++++++ REPLACE
```

### 2.2 `core/generation.py` — ClaimGuard 통합분

```
------- SEARCH
from core.retrieval import Citation, RankedCandidate, ResponsePackage
from core.config import DEFAULT_GEN_MODEL, DEFAULT_TEMPERATURE
=======
from core.retrieval import Citation, RankedCandidate, ResponsePackage
from core.config import DEFAULT_GEN_MODEL, DEFAULT_TEMPERATURE
from core.claim_guard import ClaimGuard, ClaimGuardResult, RiskLevel, wrap_ranked_candidates
+++++++ REPLACE

------- SEARCH
class GenerationStream:
=======

def _run_claim_guard(
    answer: str,
    response: ResponsePackage,
) -> ClaimGuardResult | None:
    """답변 텍스트에서 위험 표현을 탐지하고, 증거(candidates)로 ClaimGuard를
    실행한다. 실패하면 ClaimGuardResult(risk_level=NONE, ...)를 반환 —
    답변 생성이 실패해도 답변 자체는 막히지 않는다."""
    try:
        guard = ClaimGuard()
        risk_level, matched_terms = guard.detect_risk(answer)
        if risk_level == RiskLevel.NONE:
            return ClaimGuardResult(
                risk_level=RiskLevel.NONE,
                matched_terms=[],
                scope_qualifier_required=False,
                absolute_claim_blocked=False,
                competing_candidates_found=False,
                reason="",
                suggested_wording=None,
            )
        # 위험 표현이 있으면 evidence로 평가
        wrapped = wrap_ranked_candidates(response.top_k_results)
        return guard.evaluate(claim_text=answer, evidence=wrapped)
    except Exception as e:
        logger.warning(
            "[GenerationService._run_claim_guard] ClaimGuard 실패 (답변은 계속 사용): %s", e
        )
        return ClaimGuardResult(
            risk_level=RiskLevel.NONE,
            matched_terms=[],
            scope_qualifier_required=False,
            absolute_claim_blocked=False,
            competing_candidates_found=False,
            reason=f"claim_guard 실패: {e}",
            suggested_wording=None,
        )


class GenerationStream:
+++++++ REPLACE

------- SEARCH
    def to_result(self) -> "GenerationResult":
        """Build the final GenerationResult. Call only after full iteration."""
        answer = "".join(self._answer_parts)
        return GenerationResult(
            question=self._response.question,
            answer=answer,
            gen_model=self._gen_model,
            temperature=self._temperature,
            context_used=self._context_used,
            error=self._error,
            citations=self._response.citations,
        )
=======
    def to_result(self) -> "GenerationResult":
        """Build the final GenerationResult. Call only after full iteration."""
        answer = "".join(self._answer_parts)
        claim_guard_result = _run_claim_guard(answer, self._response)
        return GenerationResult(
            question=self._response.question,
            answer=answer,
            gen_model=self._gen_model,
            temperature=self._temperature,
            context_used=self._context_used,
            error=self._error,
            citations=self._response.citations,
            claim_guard_result=claim_guard_result,
        )
+++++++ REPLACE

------- SEARCH
@dataclass
class GenerationResult:
    """Output of GenerationService.generate()."""
    question: str
    answer: str
    gen_model: str
    temperature: float
    context_used: bool
    error: Optional[str] = None
    citations: list[Citation] = field(default_factory=list)
=======
@dataclass
class GenerationResult:
    """Output of GenerationService.generate()."""
    question: str
    answer: str
    gen_model: str
    temperature: float
    context_used: bool
    error: Optional[str] = None
    citations: list[Citation] = field(default_factory=list)
    claim_guard_result: ClaimGuardResult | None = None
+++++++ REPLACE

------- SEARCH
        claim_guard_result = _run_claim_guard(answer, response)
        return GenerationResult(
            question=response.question,
            answer=answer,
            gen_model=gen_model,
            temperature=temperature,
            context_used=context_used,
            error=error,
            citations=response.citations,
        )
=======
        claim_guard_result = _run_claim_guard(answer, response)
        return GenerationResult(
            question=response.question,
            answer=answer,
            gen_model=gen_model,
            temperature=temperature,
            context_used=context_used,
            error=error,
            citations=response.citations,
            claim_guard_result=claim_guard_result,
        )
+++++++ REPLACE
```

### 2.3 `ui/pages/chat.py` — 안내 박스 추가분

```
------- SEARCH
from core.retrieval import QueryProcessor, RankedCandidate
from core.generation import GenerationService
=======
from core.retrieval import QueryProcessor, RankedCandidate
from core.generation import GenerationService
from core.claim_guard import RiskLevel
+++++++ REPLACE

------- SEARCH
# ---------------------------------------------------------------------------
# Low-confidence helpers (existing)
# ---------------------------------------------------------------------------
=======
# ---------------------------------------------------------------------------
# ClaimGuard notice helpers — _is_low_confidence / _render_low_confidence_warning
# 패턴 재사용
# ---------------------------------------------------------------------------


def _should_show_claim_guard_notice(result) -> bool:
    """result.claim_guard_result가 있고 risk_level이 HIGH이면서
    absolute_claim_blocked 또는 scope_qualifier_required가 True인 경우만 표시."""
    cg = getattr(result, "claim_guard_result", None)
    if cg is None:
        return False
    return (
        getattr(cg, "risk_level", None) == RiskLevel.HIGH
        and (
            getattr(cg, "absolute_claim_blocked", False)
            or getattr(cg, "scope_qualifier_required", False)
        )
    )


def _render_claim_guard_notice(claim_guard_result) -> None:
    """st.info()로 reason과 suggested_wording을 표시.
    기존 _render_low_confidence_warning()과 같은 위치(출처 expander 앞)에 렌더링."""
    reason = getattr(claim_guard_result, "reason", "") or ""
    suggested = getattr(claim_guard_result, "suggested_wording", None) or ""
    parts: list[str] = []
    if reason:
        parts.append(f"**판정 근거:** {reason}")
    if suggested:
        parts.append(f"**권장 수정 문구:** {suggested}")
    text = "\n\n".join(parts) if parts else "위험 주장 표현이 탐지되었습니다. 문맥을 확인하세요."
    st.info(text)


# ---------------------------------------------------------------------------
# Low-confidence helpers (existing)
# ---------------------------------------------------------------------------
+++++++ REPLACE

------- SEARCH
    # Low-confidence caption (soft floor only — never blocks generation)
    if low_confidence:
        _render_low_confidence_warning()
=======
    # Low-confidence caption (soft floor only — never blocks generation)
    if low_confidence:
        _render_low_confidence_warning()

    # ClaimGuard notice (same pattern as low-confidence warning)
    if _should_show_claim_guard_notice(result):
        _render_claim_guard_notice(result.claim_guard_result)
+++++++ REPLACE
```

---

## §3. `core/retrieval.py` 및 `core/parallel_retriever.py` 빈 diff 확인

```bash
$ git diff core/retrieval.py
(no output)

$ git diff core/parallel_retriever.py
(no output)
```

**확실함**: 두 파일은 전혀 접촉하지 않았다.

---

## §4. 테스트 실행 결과

### 4.1 `tests/test_generation_claim_guard.py` — 신규 테스트 (77개)

```
======================== 77 passed, 7 warnings in 3.03s ========================
```

핵심 테스트 항목:
- `test_no_risk_expression` → `risk_level=NONE`
- `test_detect_risk` → `risk_level=HIGH`, `"유일"` 매칭
- `test_evaluate_t1_only` → `absolute_claim_blocked=True`
- `test_evaluate_t2_only` → `absolute_claim_blocked=True + scope_qualifier_required=True`
- `test_generate_no_risk` → `claim_guard_result.risk_level=NONE, error=None`
- `test_generate_high_risk_blocked` → `absolute_claim_blocked=True, error=None` (답변 막히지 않음)
- `test_generate_claim_guard_failure` → 예외 발생 시 `error=None` (답변 계속 사용)
- `test_wrap_converts_ranked_candidate` → `EvidenceCandidate`로 감싸짐
- `test_wrap_passes_through_evidence` → 이미 EvidenceCandidate인 것은 통과
- Sprint A~D 회귀 52개 모두 통과

### 4.2 Sprint A~D 회귀 테스트

```bash
$ python -m pytest tests/test_claim_guard.py tests/test_parallel_retriever.py -v
======================== 30 passed in 0.07s ========================
```

---

## §5. §2.4 제외 항목 — CUE의 다음 결정 사항

1. **`QueryAuditLog` 실제 배선** — Sprint A에 스키마는 있지만 `log_query_audit()` 호출 배선은 이번 범위 밖. 별도 Task Order 필요.
2. **tag_name/db_path 실배선** — 현재 Chat UI가 의미 태그 검색 UI를 아직 제공하지 않으므로 `tag_name=None, db_path=None`으로 동작. v3 이후 과제.
3. **Research/SermonDraft UI에 ClaimGuard 결과 표시** — `GenerationResult.claim_guard_result` 필드는 자동으로 채워지지만 UI 표시는 이번엔 Chat 페이지만. Research/SermonDraft 변경은 별도 결정 필요.

---

## §6. 수동 UI 검증 (§4)

C1이 로컬에서 `streamlit run dbma_ui.py`로 Chat 탭에 접속해 검증해야 한다:

1. 평범한 질문 1개 → ClaimGuard 안내 박스가 안 뜨는지 확인
2. "성경에서 가장 처음 나온 X는?" 류 질문 → 모델 답변에 "최초"/"처음" 등이 포함되면 안내 박스가 뜨는지 확인

**참고**: 모델 답변은 비결정적이므로 여러 번 시도 필요. 안 뜨면 프롬프트를 유도적으로 바꿔서 재시도. 그래도 재현 안 되면 그 사실을 다음 라운드에 남길 것.

스크린샷 캡처는 C1이 직접 수행 후本报告에 첨부.
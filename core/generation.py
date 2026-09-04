"""core/generation.py — GenerationService v1.

Responsibility boundary (SPRINT17-Phase5-M1b-1):
  core.retrieval (RetrievalEngine, QueryProcessor) owns retrieval — metadata
  filtering, BM25/vector scoring, theological scoring, ranking, and context
  assembly. It has no generation step and produces no "answer" field
  (see ResponsePackage).

  core.generation (this module) owns the next stage only: turning a
  QueryProcessor.process() ResponsePackage into a synthesized natural-
  language answer via Ollama. It is a consumer of ResponsePackage, not a
  retrieval component — it does not search, rank, or score anything, and
  it never touches RetrievalEngine/QueryProcessor internals.

  Boundary:
      QueryProcessor.process() -> ResponsePackage
                                       |
                                       v
                              GenerationService.generate()
                                       |
                                       v
                              GenerationResult (answer)

Prompt assembly and the Ollama call pattern below are reused from
dbma.py::query_rag() (L716-722) — that function's RETRIEVAL logic
(Chroma/Qdrant search) is deliberately NOT reused, since QueryProcessor's
own retrieval pipeline replaces it. Unlike the original, this module wraps
the Ollama call in explicit error handling instead of letting it raise
uncaught.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import ollama

from core.retrieval import Citation, RankedCandidate, ResponsePackage
from core.config import (
    DEFAULT_GEN_MODEL,
    DEFAULT_NUM_PREDICT,
    DEFAULT_REPEAT_PENALTY,
    DEFAULT_TEMPERATURE,
)
from core.claim_guard import ClaimGuard, ClaimGuardResult, RiskLevel, wrap_ranked_candidates

logger = logging.getLogger(__name__)


def _gen_options(temperature: float) -> dict:
    """GenerationService(Q&A·본문해설) 전용 Ollama 옵션.

    my-theology-bot-v2 는 Modelfile 에 repeat_penalty/num_predict 를 지정하지
    않아 Ollama 기본값(repeat_penalty≈1.1, num_predict 무제한)으로 돌고, 저온
    결정론 설정과 맞물려 같은 구절을 수백 번 반복하는 퇴행 루프가 실측됐다
    (요한복음 1:10 해설). 두 값을 config.yaml::rag 에서 읽어 강제한다.
    SermonDraftService 는 긴 출력이 정상이라 이 헬퍼를 쓰지 않는다.
    """
    return {
        "temperature": temperature,
        "repeat_penalty": DEFAULT_REPEAT_PENALTY,
        "num_predict": DEFAULT_NUM_PREDICT,
    }


# ============================================================
# 한국어 출력 순도 검증 — SermonDraftService 전용 (실측 근거 아래)
# ============================================================
#
# 실측(2026-07-21, my-theology-bot:latest = llama3.3:70b Q4_K_M): 동일
# 프롬프트("고난이 인내를 낳는다" 계열 문장)를 temperature 0.3/0.2/0.1/0.0
# 4개 조건에서 반복 호출한 결과, 오염(히라가나/가타카나/한자/태국어 유입)이
# 0.3에서 8자, 0.1에서 11자(태국어까지 등장), 0.0(완전 결정론)에서도 1자
# 발생 — 0.2만 우연히 0건이었다. 즉 temperature를 낮추는 것은 신뢰할 수
# 있는 해결책이 아니다(오염이 특정 개념의 토큰 임베딩이 언어 간에 얽혀
# 있는 모델/양자화 자체의 결함으로 보이며, 온도와 무관하게 재현된다).
# 대신 출력을 검사해 오염이 감지되면 같은 프롬프트로 재시도한다 —
# ollama.generate()는 seed를 고정하지 않으므로(옵션에 seed 미지정) 각
# 호출의 디코딩 경로가 달라, 재시도가 실제로 오염을 회피할 확률이 있다
# (같은 실측에서 매 호출마다 오염 위치/여부가 달랐다).
#
# 한글(가-힣, 자모)과 아라비아 숫자·구두점·영문(성경 인명 로마자 표기 등)은
# 검사 대상이 아니다 — 프로젝트가 실제로 배제하려는 것은 CJK 이웃 언어와
# 태국어처럼 한국어 문장에 섞일 이유가 없는 문자뿐이다.
_SCRIPT_CONTAMINATION_RE = re.compile(r"[぀-ヿ一-鿿฀-๿]")
_MAX_LANGUAGE_RETRIES = 2


def _detect_script_contamination(text: str) -> list[str]:
    """비한글 오염 문자를 등장 순서대로 중복 제거해 반환. 없으면 빈 리스트."""
    seen: dict[str, None] = {}
    for ch in _SCRIPT_CONTAMINATION_RE.findall(text):
        seen.setdefault(ch, None)
    return list(seen.keys())


def _contamination_retry_note(chars: list[str]) -> str:
    return (
        f"\n\n[자동 검증] 방금 출력에 한국어가 아닌 문자({''.join(chars)})가"
        " 섞여 있었다. 반드시 한국어(한글)로만 다시 작성하고, 위와 같은 문자를"
        " 전혀 포함하지 마라."
    )


def _sanitize_script_contamination(text: str) -> str:
    """재시도(_MAX_LANGUAGE_RETRIES)를 다 써도 오염이 남을 때의 최종
    방어선. 실측 결과(동일 프롬프트 3회 연속 실패, 매번 다른 문자로 오염)
    재시도만으로는 특정 개념 주변의 오염을 신뢰성 있게 없앨 수 없다는 것이
    확인됐다 — 문장을 일부 손상시키는 한이 있어도 사용자에게 비한글 문자가
    그대로 노출되는 것보다는 낫다는 판단으로, 오염 문자를 제거한다(대체
    번역은 하지 않음 — 없는 내용을 지어내지 않는다는 프로젝트 원칙과
    동일하게, 무엇으로 바꿔야 할지 모르는 문자는 만들어내지 않고 삭제만
    한다)."""
    return _SCRIPT_CONTAMINATION_RE.sub("", text)


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
    """Iterable of answer text chunks from a streaming Ollama call.

    Iterate this to render incrementally (e.g. `st.write_stream(stream)`).
    After the iterator is exhausted, call `to_result()` for the same
    GenerationResult shape `GenerationService.generate()` returns.
    """

    def __init__(
        self,
        response: ResponsePackage,
        gen_model: str,
        temperature: float,
        prompt: str,
        context_used: bool,
    ) -> None:
        self._response = response
        self._gen_model = gen_model
        self._temperature = temperature
        self._prompt = prompt
        self._context_used = context_used
        self._answer_parts: list[str] = []
        self._error: Optional[str] = None

    def __iter__(self):
        try:
            for chunk in ollama.generate(
                model=self._gen_model,
                prompt=self._prompt,
                options=_gen_options(self._temperature),
                stream=True,
            ):
                piece = chunk["response"]
                if piece:
                    self._answer_parts.append(piece)
                    yield piece
        except Exception as e:
            logger.error(
                "[GenerationService.generate_stream] Ollama generate 실패 (model=%s): %s",
                self._gen_model, e,
            )
            self._error = str(e)
            err_piece = f"[생성 실패] Ollama 호출 중 오류가 발생했습니다: {e}"
            self._answer_parts = [err_piece]
            yield err_piece

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


class GenerationService:
    """Synthesizes a natural-language answer from a QueryProcessor ResponsePackage.

    Stateless — every call re-invokes Ollama fresh, no caching.
    """

    @staticmethod
    def _build_prompt(response: ResponsePackage, conversation_history: str = "") -> tuple[str, bool]:
        """Returns (prompt, context_used).

        conversation_history (2026-07-24, DBMA Chat "Plan B" — sliding
        window, additive/optional): prior turns as plain text, prepended
        ahead of the retrieval context. Only the answer-generation prompt
        gains this — the retrieval query itself (response.question) is
        unchanged, so this does NOT rewrite/condense the search query
        (that would be "Plan A", a separate, larger change). Callers that
        don't pass it (Research/SermonDraft) see byte-identical prompts."""
        context = response.llm_context_block or ""
        history_block = f"이전 대화:\n{conversation_history}\n\n" if conversation_history.strip() else ""
        if context.strip():
            return f"{history_block}문맥:\n{context}\n\n질문:\n{response.question}", True
        return f"{history_block}질문:\n{response.question}", False

    def generate_stream(
        self,
        response: ResponsePackage,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        conversation_history: str = "",
    ) -> GenerationStream:
        """Same prompt/model as generate(), but returns an iterable of text
        chunks instead of blocking for the full answer — lets the caller
        (e.g. Streamlit's st.write_stream) render tokens as they arrive.

        Call to_result() on the returned GenerationStream after fully
        iterating it to get the equivalent GenerationResult.
        """
        prompt, context_used = self._build_prompt(response, conversation_history)
        return GenerationStream(response, gen_model, temperature, prompt, context_used)

    def generate(
        self,
        response: ResponsePackage,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        conversation_history: str = "",
    ) -> GenerationResult:
        """Build a prompt from response.llm_context_block + response.question
        and call Ollama to synthesize an answer.

        Mirrors dbma.py::query_rag() L716-722's prompt assembly and Ollama
        call, but never raises — Ollama failures are captured into
        GenerationResult.error instead of propagating.

        [2026-07-27, ADR-010 Phase 2 베이스라인이 실측으로 발견] 이 경로에는
        한국어 출력 순도 검증(재시도+sanitize, SermonDraftService에만
        적용돼 있던 것)이 빠져 있어 Chat/Research 답변에 CJK 오염 문자가
        그대로 노출되고 있었다 — 같은 방어 로직을 여기에도 적용한다.
        """
        base_prompt, context_used = self._build_prompt(response, conversation_history)

        try:
            prompt = base_prompt
            answer = ""
            for attempt in range(_MAX_LANGUAGE_RETRIES + 1):
                result = ollama.generate(
                    model=gen_model,
                    prompt=prompt,
                    options=_gen_options(temperature),
                )
                answer = result["response"]
                contamination = _detect_script_contamination(answer)
                if not contamination:
                    break
                logger.warning(
                    "[GenerationService.generate] 한국어 출력 오염 감지"
                    " (시도 %d/%d): %s",
                    attempt + 1, _MAX_LANGUAGE_RETRIES + 1, contamination,
                )
                prompt = base_prompt + _contamination_retry_note(contamination)
            else:
                logger.warning(
                    "[GenerationService.generate] 재시도 소진 — 오염 문자 강제 제거"
                )
                answer = _sanitize_script_contamination(answer)
            error = None
        except Exception as e:
            logger.error(
                "[GenerationService.generate] Ollama generate 실패 (model=%s): %s",
                gen_model, e,
            )
            answer = f"[생성 실패] Ollama 호출 중 오류가 발생했습니다: {e}"
            error = str(e)

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


# ============================================================
# 설교문 작성 워크플로 (Phase 1) — docs/agents/c1/
# DBMA-SERMON-DRAFT-Phase1-Design-Review.md 설계 검토 결과 반영.
#
# GenerationService를 상속하지 않고 조합(composition)한다 — 프롬프트
# 템플릿이 근본적으로 다르고(단발 Q&A vs 개요/확장 다단계), Ollama 호출
# 책임과 설교문 도메인 로직 책임을 분리하기 위함(설계 문서 Q4).
# ============================================================

@dataclass
class SermonOutline:
    """설교 개요 — 서론/대지/결론. 사용자가 검토·수정한 뒤 대지별로
    확장 생성된다."""
    title: str
    introduction: str
    points: list[str] = field(default_factory=list)
    conclusion: str = ""


# [설교 형식] 대지의 "성격"만 다르고 출력 스키마(제목/서론/대지N/결론)는
# 동일하게 유지한다 — _parse_outline()을 형식별로 분기할 필요가 없어서
# 파싱 로직이 단순해지고, 사용자가 검토 단계에서 두 형식을 오갈 때도
# 같은 UI(텍스트 입력 필드들)를 그대로 쓸 수 있다.
SERMON_FORMATS = ("주제설교", "강해설교")
_DEFAULT_SERMON_FORMAT = "주제설교"

# [품질] 개요가 "본문을 얕게 풀어쓴 것" 수준으로 나온다는 지적(실사용
# 피드백)의 원인을 단계적으로 좁혔다:
#   1차 시도: 대지를 1문장→2문장으로 늘리고 "참고 자료를 반영하라"는
#     지시만 추가 — 실측 결과 변화 없음, 여전히 성경 본문 재진술.
#   2차 시도: 지시를 프롬프트 앞뒤 양쪽에 반복 배치 — 실측 결과도 변화
#     없음 (my-theology-bot이 23K자 컨텍스트 안에서 특정 인용을 스스로
#     찾아 쓰는 지시-따르기 능력 자체가 약함, "lost in the middle" 문제로
#     의심되지만 확정은 아님 — 지시 위치보다 컨텍스트에 사람이 읽을 수
#     있는 출처 라벨이 없었던 게 더 근본 원인으로 보임).
#   3차(현재): _format_sermon_context()로 각 청크에 "[자료N] 제목·저자"
#     라벨을 붙이고, "[자료N]을 최소 1회 인용하라"는 구체적·검증 가능한
#     지시로 바꿈 — 모델이 "어떤 신학적 통찰을 반영하라"는 추상적 지시보다
#     "이 번호를 인용하라"는 구체적 지시를 더 잘 따를 것이라는 가설.
_QUALITY_DIRECTIVE = (
    "본문을 단순히 재진술하지 마라. 아래 참고 자료는 [자료1], [자료2]... 로"
    " 번호가 매겨져 있다 — 각 대지에서 최소 1개 이상의 [자료N]을 실제로"
    " 인용·언급하며 그 내용을 반영해서 작성하라. 참고 자료에 없는 내용은"
    " 지어내지 말고, 뻔하고 상투적인 문장(예: '우리는 이를 통해 은혜를"
    " 깨달을 수 있습니다' 류의 일반론)은 피하라. 한국어로만 작성하고 다른"
    " 언어 문자를 섞지 마라."
)


def _external_source_directive(candidates: list[RankedCandidate]) -> str:
    """규칙 7~9 (docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md §9.4) — Logos
    등 외부 소스 유래 청크(TSU의 source_provenance 필드, core/tsu_builder.py
    참고)가 컨텍스트에 하나라도 있을 때만 추가되는 지시문. 하나도 없으면
    빈 문자열을 반환(no-op)해서, 외부 소스를 전혀 안 쓰는 절대다수 호출에서
    프롬프트가 불필요하게 길어지지 않게 한다."""
    has_external = any(c.metadata.get("source_provenance") for c in candidates)
    if not has_external:
        return ""
    return (
        "\n\n외부 소스 인용 규칙(Logos 등에서 가져온 자료가 포함된 경우):\n"
        "7. 외부 소스에서 가져온 자료는 원문을 그대로 재현하지 말고 요약·재진술하라.\n"
        "8. 그런 자료를 인용할 때는 자료 라벨에 이미 괄호로 병기된 원저작물 위치"
        "(예: Romans 12:1-2, p.749)를 함께 언급하라.\n"
        "9. 개인 연구 노트(personal_research)로 표시된 자료는 저자 개인의 견해·적용"
        " 제안으로 명시하고, 본문 자체의 명령처럼 단정하지 마라."
    )


def _format_sermon_context(candidates: list[RankedCandidate], max_items: int = 15) -> str:
    """설교문 워크플로 전용 컨텍스트 포맷 — core/retrieval.py::
    ContextAssembler.assemble()의 <context id="tsu_id">는 사람이 읽을 수
    있는 출처가 아니라(Chat/Research 공용 포맷이라 변경하지 않는다), 모델이
    "[자료1]을 인용하라"처럼 구체적으로 지목할 수 있도록 제목·저자 라벨을
    붙인 별도 포맷을 여기서 만든다."""
    parts: list[str] = []
    for i, c in enumerate(candidates[:max_items], 1):
        title = c.metadata.get("title") or c.metadata.get("source_file") or "출처 미상"
        author = c.metadata.get("author")
        label = f"{title} — {author}" if author else title
        # [docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md §9.1] Logos 등 외부
        # 소스 유래 청크는 TSU의 source_provenance.logos_location을 라벨에
        # 병기해 원저작물 위치를 추적 가능하게 한다. 없는 경우(기존 코퍼스
        # 전체) 라벨은 그대로 유지된다 — 새로 지어내지 않는다.
        provenance = c.metadata.get("source_provenance")
        location = provenance.get("logos_location") if provenance else None
        if location:
            label = f"{label} ({location})"
        parts.append(f"[자료{i}] {label}\n{c.content}")
    return "\n\n".join(parts)

_OUTLINE_POINT_GUIDANCE = {
    "주제설교": (
        "대지는 본문에서 뽑아낸 신학적 주제·교훈 단위로 구성하라 — 절 순서를"
        " 그대로 따를 필요 없이, 설교의 논지 전개에 맞게 재구성해도 된다."
    ),
    "강해설교": (
        "대지는 반드시 본문의 절 구분을 그대로 따라가라 — 주제를 임의로"
        " 재구성하지 말고, 본문에 나오는 순서대로 절 범위를 명시하며 그 절이"
        " 말하는 바를 요약하라. 예: '1-2절 — 의롭다 함을 받은 자가 누리는 평강'."
    ),
}

_EXPANSION_STYLE_GUIDANCE = {
    "주제설교": (
        "참고 자료에 나온 신학적 근거를 구체적으로 인용·전개하며, 목회적"
        " 적용과 예화는 그 근거에서 자연스럽게 도출되게 하라(본문과 무관한"
        " 성경 인물을 예화로 나열하지 마라). 2~4개 문단."
    ),
    "강해설교": (
        "해당 절의 문맥과 원문의 의미, 그 절이 본문 전체 흐름에서 하는 역할을"
        " 참고 자료의 주석적 논의에 근거해 풀어 설명하라. 예화보다 본문 자체의"
        " 논리 전개와 주해에 비중을 두어 2~4개 문단으로 서술하라."
    ),
}


def _outline_format_instructions(sermon_format: str, extra_directive: str = "") -> str:
    guidance = _OUTLINE_POINT_GUIDANCE.get(sermon_format, _OUTLINE_POINT_GUIDANCE[_DEFAULT_SERMON_FORMAT])
    return (
        f"{_QUALITY_DIRECTIVE}{extra_directive}\n\n"
        f"설교 형식: {sermon_format}. {guidance}\n\n"
        "아래 형식을 정확히 지켜 작성하라. 다른 설명이나 인사말을 덧붙이지 마라.\n"
        "제목: <설교 제목>\n"
        "서론: <서론, 2~3문장>\n"
        "대지1: <첫 번째 대지 — 핵심 주장과 그 신학적 근거, 2문장>\n"
        "대지2: <두 번째 대지 — 핵심 주장과 그 신학적 근거, 2문장>\n"
        "대지3: <세 번째 대지 — 핵심 주장과 그 신학적 근거, 2문장>\n"
        "결론: <결론, 2~3문장>"
    )


def _parse_outline(text: str) -> SermonOutline:
    """LLM이 위 형식 지시를 따랐다는 전제로 줄 단위 파싱한다.
    형식을 어긴 줄은 조용히 건너뛴다 — 부분적으로라도 파싱 가능한 결과를
    사용자에게 보여주고, 빈 값은 검토 단계에서 사람이 채우면 된다."""
    outline = SermonOutline(title="", introduction="")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("제목:"):
            outline.title = line[len("제목:"):].strip()
        elif line.startswith("서론:"):
            outline.introduction = line[len("서론:"):].strip()
        elif line.startswith("결론:"):
            outline.conclusion = line[len("결론:"):].strip()
        elif line.startswith("대지") and len(line) > 2:
            # "대지1:", "대지2:", ... — 번호는 순서만 의미하고 값은 안 씀
            idx = line.find(":")
            if idx != -1 and line[2:idx].strip().isdigit():
                outline.points.append(line[idx + 1:].strip())
    return outline


class SermonDraftService:
    """설교문 작성 워크플로 전용 서비스. Ollama 호출은 자체 수행하되(단발
    generate 패턴은 GenerationService와 동일), 프롬프트 템플릿은 개요
    생성/대지 확장 단계별로 별도 관리한다."""

    def __init__(self) -> None:
        pass

    def generate_outline(
        self,
        scripture_and_theme: str,
        candidates: list[RankedCandidate],
        sermon_format: str = _DEFAULT_SERMON_FORMAT,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> tuple[SermonOutline, Optional[str]]:
        """검색된 자료를 근거로 설교 개요(서론/대지/결론) 1차 초안을
        생성한다. 실패 시 (빈 SermonOutline, 에러 메시지) 반환 — 절대
        raise하지 않는다(GenerationService.generate()와 동일한 계약).

        sermon_format: "주제설교"(기본) | "강해설교" — 대지의 성격만
        바뀌고 출력 스키마는 동일하다(SERMON_FORMATS 참고).
        candidates: response.top_k_results — _format_sermon_context()가
        [자료N] 라벨을 붙여 인용 가능한 컨텍스트로 재구성한다."""
        context_block = _format_sermon_context(candidates)
        base_prompt = (
            f"다음 참고 자료를 근거로 설교 개요를 작성하라.\n"
            f"본문/주제: {scripture_and_theme}\n\n"
            f"참고 자료:\n{context_block}\n\n"
            f"{_outline_format_instructions(sermon_format, _external_source_directive(candidates))}"
        )
        try:
            prompt = base_prompt
            raw = ""
            for attempt in range(_MAX_LANGUAGE_RETRIES + 1):
                result = ollama.generate(
                    model=gen_model, prompt=prompt, options={"temperature": temperature}
                )
                raw = result["response"]
                contamination = _detect_script_contamination(raw)
                if not contamination:
                    break
                logger.warning(
                    "[SermonDraftService.generate_outline] 한국어 출력 오염 감지"
                    " (시도 %d/%d): %s",
                    attempt + 1, _MAX_LANGUAGE_RETRIES + 1, contamination,
                )
                prompt = base_prompt + _contamination_retry_note(contamination)
            else:
                # for-else: 마지막 attempt까지 break 없이 다 돌았다 = 재시도를
                # 전부 써도 오염이 남았다(실측상 특정 개념 주변에서는 재시도
                # 자체가 안정적으로 회피하지 못하는 경우가 있었다). 개요는
                # 2단계 검토가 있지만, 그 화면에 애초에 비한글 문자가 뜨는
                # 것 자체를 막기 위해 여기서도 제거한다.
                logger.warning(
                    "[SermonDraftService.generate_outline] 재시도 소진 — 오염 문자 강제 제거"
                )
                raw = _sanitize_script_contamination(raw)
            return _parse_outline(raw), None
        except Exception as e:
            logger.error(
                "[SermonDraftService.generate_outline] Ollama generate 실패 (model=%s): %s",
                gen_model, e,
            )
            return SermonOutline(title="", introduction=""), str(e)

    def expand_point(
        self,
        point_text: str,
        scripture_and_theme: str,
        candidates: list[RankedCandidate],
        style_examples: str = "",
        sermon_format: str = _DEFAULT_SERMON_FORMAT,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> tuple[str, Optional[str]]:
        """승인된 대지 하나를 실제 설교문 문단으로 확장한다.
        style_examples는 콘텐츠 근거가 아니라 어투 참고용 — 별도 절로
        구분해 프롬프트에 그 의도를 명시한다(설계 문서 Q3).
        sermon_format에 따라 확장 방식이 갈린다 — 주제설교는 예화·적용
        중심, 강해설교는 본문 주해·문맥 중심(_EXPANSION_STYLE_GUIDANCE).
        candidates: generate_outline()과 동일한 [자료N] 인용 가능 컨텍스트."""
        context_block = _format_sermon_context(candidates)
        style_section = (
            f"\n\n문체 참고(아래는 설교자 본인의 과거 설교문 발췌 —"
            f" 내용을 인용하지 말고 어투·문장 호흡만 참고하라):\n{style_examples}"
            if style_examples.strip() else ""
        )
        style_guidance = _EXPANSION_STYLE_GUIDANCE.get(
            sermon_format, _EXPANSION_STYLE_GUIDANCE[_DEFAULT_SERMON_FORMAT]
        )
        base_prompt = (
            f"{_QUALITY_DIRECTIVE}{_external_source_directive(candidates)}\n\n"
            f"아래 설교 대지 하나를 실제 설교문 문단으로 확장하라. (설교 형식: {sermon_format})\n"
            f"본문/주제: {scripture_and_theme}\n"
            f"대지: {point_text}\n\n"
            f"참고 자료:\n{context_block}"
            f"{style_section}\n\n"
            f"{style_guidance}"
        )
        try:
            prompt = base_prompt
            text = ""
            for attempt in range(_MAX_LANGUAGE_RETRIES + 1):
                result = ollama.generate(
                    model=gen_model, prompt=prompt, options={"temperature": temperature}
                )
                text = result["response"]
                contamination = _detect_script_contamination(text)
                if not contamination:
                    break
                logger.warning(
                    "[SermonDraftService.expand_point] 한국어 출력 오염 감지"
                    " (시도 %d/%d): %s",
                    attempt + 1, _MAX_LANGUAGE_RETRIES + 1, contamination,
                )
                prompt = base_prompt + _contamination_retry_note(contamination)
            else:
                # generate_outline()과 동일한 for-else 백스톱. 대지 확장
                # 결과는 개요와 달리 사람이 편집하는 단계 없이 바로 최종
                # 초안에 조립되므로(ui/pages/sermon_draft.py의 확장 단계는
                # st.markdown()으로 바로 표시 — 수정 UI가 없다) 여기서
                # 걸러내는 것이 개요 쪽보다 더 중요하다.
                logger.warning(
                    "[SermonDraftService.expand_point] 재시도 소진 — 오염 문자 강제 제거"
                )
                text = _sanitize_script_contamination(text)
            return text, None
        except Exception as e:
            logger.error(
                "[SermonDraftService.expand_point] Ollama generate 실패 (model=%s): %s",
                gen_model, e,
            )
            return "", str(e)

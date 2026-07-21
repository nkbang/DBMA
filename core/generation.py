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
from dataclasses import dataclass, field
from typing import Optional

import ollama

from core.retrieval import Citation, ResponsePackage
from core.config import DEFAULT_GEN_MODEL, DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)


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
                options={"temperature": self._temperature},
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
        return GenerationResult(
            question=self._response.question,
            answer="".join(self._answer_parts),
            gen_model=self._gen_model,
            temperature=self._temperature,
            context_used=self._context_used,
            error=self._error,
            citations=self._response.citations,
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


class GenerationService:
    """Synthesizes a natural-language answer from a QueryProcessor ResponsePackage.

    Stateless — every call re-invokes Ollama fresh, no caching.
    """

    @staticmethod
    def _build_prompt(response: ResponsePackage) -> tuple[str, bool]:
        """Returns (prompt, context_used)."""
        context = response.llm_context_block or ""
        if context.strip():
            return f"문맥:\n{context}\n\n질문:\n{response.question}", True
        return f"질문:\n{response.question}", False

    def generate_stream(
        self,
        response: ResponsePackage,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> GenerationStream:
        """Same prompt/model as generate(), but returns an iterable of text
        chunks instead of blocking for the full answer — lets the caller
        (e.g. Streamlit's st.write_stream) render tokens as they arrive.

        Call to_result() on the returned GenerationStream after fully
        iterating it to get the equivalent GenerationResult.
        """
        prompt, context_used = self._build_prompt(response)
        return GenerationStream(response, gen_model, temperature, prompt, context_used)

    def generate(
        self,
        response: ResponsePackage,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> GenerationResult:
        """Build a prompt from response.llm_context_block + response.question
        and call Ollama to synthesize an answer.

        Mirrors dbma.py::query_rag() L716-722's prompt assembly and Ollama
        call, but never raises — Ollama failures are captured into
        GenerationResult.error instead of propagating.
        """
        prompt, context_used = self._build_prompt(response)

        try:
            result = ollama.generate(
                model=gen_model,
                prompt=prompt,
                options={"temperature": temperature},
            )
            answer = result["response"]
            error = None
        except Exception as e:
            logger.error(
                "[GenerationService.generate] Ollama generate 실패 (model=%s): %s",
                gen_model, e,
            )
            answer = f"[생성 실패] Ollama 호출 중 오류가 발생했습니다: {e}"
            error = str(e)

        return GenerationResult(
            question=response.question,
            answer=answer,
            gen_model=gen_model,
            temperature=temperature,
            context_used=context_used,
            error=error,
            citations=response.citations,
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
    "주제설교": "성경적 근거, 목회적 적용, 예화를 균형 있게 포함해 2~4개 문단으로 서술하라.",
    "강해설교": (
        "해당 절의 문맥과 원문의 의미, 그 절이 본문 전체 흐름에서 하는 역할을"
        " 중심으로 풀어 설명하라. 예화보다 본문 자체의 논리 전개와 주해에"
        " 비중을 두어 2~4개 문단으로 서술하라."
    ),
}


def _outline_format_instructions(sermon_format: str) -> str:
    guidance = _OUTLINE_POINT_GUIDANCE.get(sermon_format, _OUTLINE_POINT_GUIDANCE[_DEFAULT_SERMON_FORMAT])
    return (
        f"설교 형식: {sermon_format}. {guidance}\n\n"
        "아래 형식을 정확히 지켜 작성하라. 다른 설명이나 인사말을 덧붙이지 마라.\n"
        "제목: <설교 제목>\n"
        "서론: <서론, 2~3문장>\n"
        "대지1: <첫 번째 대지, 1문장>\n"
        "대지2: <두 번째 대지, 1문장>\n"
        "대지3: <세 번째 대지, 1문장>\n"
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
        context_block: str,
        sermon_format: str = _DEFAULT_SERMON_FORMAT,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> tuple[SermonOutline, Optional[str]]:
        """검색된 자료를 근거로 설교 개요(서론/대지/결론) 1차 초안을
        생성한다. 실패 시 (빈 SermonOutline, 에러 메시지) 반환 — 절대
        raise하지 않는다(GenerationService.generate()와 동일한 계약).

        sermon_format: "주제설교"(기본) | "강해설교" — 대지의 성격만
        바뀌고 출력 스키마는 동일하다(SERMON_FORMATS 참고)."""
        prompt = (
            f"다음 참고 자료를 근거로 설교 개요를 작성하라.\n"
            f"본문/주제: {scripture_and_theme}\n\n"
            f"참고 자료:\n{context_block}\n\n"
            f"{_outline_format_instructions(sermon_format)}"
        )
        try:
            result = ollama.generate(
                model=gen_model, prompt=prompt, options={"temperature": temperature}
            )
            return _parse_outline(result["response"]), None
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
        context_block: str,
        style_examples: str = "",
        sermon_format: str = _DEFAULT_SERMON_FORMAT,
        gen_model: str = DEFAULT_GEN_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> tuple[str, Optional[str]]:
        """승인된 대지 하나를 실제 설교문 문단으로 확장한다.
        style_examples는 콘텐츠 근거가 아니라 어투 참고용 — 별도 절로
        구분해 프롬프트에 그 의도를 명시한다(설계 문서 Q3).
        sermon_format에 따라 확장 방식이 갈린다 — 주제설교는 예화·적용
        중심, 강해설교는 본문 주해·문맥 중심(_EXPANSION_STYLE_GUIDANCE)."""
        style_section = (
            f"\n\n문체 참고(아래는 설교자 본인의 과거 설교문 발췌 —"
            f" 내용을 인용하지 말고 어투·문장 호흡만 참고하라):\n{style_examples}"
            if style_examples.strip() else ""
        )
        style_guidance = _EXPANSION_STYLE_GUIDANCE.get(
            sermon_format, _EXPANSION_STYLE_GUIDANCE[_DEFAULT_SERMON_FORMAT]
        )
        prompt = (
            f"아래 설교 대지 하나를 실제 설교문 문단으로 확장하라. (설교 형식: {sermon_format})\n"
            f"본문/주제: {scripture_and_theme}\n"
            f"대지: {point_text}\n\n"
            f"참고 자료:\n{context_block}"
            f"{style_section}\n\n"
            f"{style_guidance}"
        )
        try:
            result = ollama.generate(
                model=gen_model, prompt=prompt, options={"temperature": temperature}
            )
            return result["response"], None
        except Exception as e:
            logger.error(
                "[SermonDraftService.expand_point] Ollama generate 실패 (model=%s): %s",
                gen_model, e,
            )
            return "", str(e)

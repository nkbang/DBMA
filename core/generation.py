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

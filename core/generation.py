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
        context = response.llm_context_block or ""
        if context.strip():
            prompt = f"문맥:\n{context}\n\n질문:\n{response.question}"
            context_used = True
        else:
            prompt = f"질문:\n{response.question}"
            context_used = False

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

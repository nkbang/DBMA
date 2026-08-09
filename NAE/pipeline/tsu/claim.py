"""LLM-backed theological claim extraction (Phase 3 core).

Follows the same convention already used in core/evaluation/sermon_judge.py:
ollama.generate() with temperature=0.0, a prompt that ends in a literal JSON
schema example, brace-extraction + json.loads (local LLMs often prepend/append
chatter), and a try/except that fails soft (batch runs must survive one bad
sentence) rather than raising.

IMPORTANT - confidence is model self-reported and uncalibrated. No external
validation set has been run against this model/prompt, so the number is a
per-call signal for triage (e.g. "sort candidates for human review"), not a
statistically meaningful probability. ClaimResult.extraction_method and
review_status are always attached to the output specifically so downstream
consumers (TSU builder, RAG, benchmark) cannot mistake this for a verified
label. See doctrine.py for the closed-vocabulary enforcement on the doctrine
field - the model cannot introduce an unreviewed category name.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import ollama

from . import config, doctrine

logger = logging.getLogger("nae.tsu.claim")

_CLAIM_PROMPT = """다음은 신학 문헌에서 발췌한 한 문장이다. 이 문장이 독립적으로 이해 가능한
신학적 주장(claim)을 담고 있는지 판단하라.

[앞 문맥]
{context_before}

[대상 문장]
{sentence}

[뒤 문맥]
{context_after}

[문서 내 후보 성경 구절]
{candidate_scriptures}

[문서 내 후보 인용/각주]
{candidate_citations}

[허용된 교리 카테고리 목록]
{doctrine_categories}

지침:
- is_claim이 false이면 나머지 필드는 모두 null로 둔다.
- claim은 원문 문장을 크게 벗어나지 않는 범위에서 명확하게 재진술한 것이어야 하며, 원문에 없는 내용을 추가하지 않는다.
- doctrine은 반드시 [허용된 교리 카테고리 목록] 중 하나이거나 해당 사항이 없으면 null이다.
- scriptures와 citations는 후보 목록 중 이 문장이 실제로 근거로 삼는 것만 선택한다. 후보에 없는 새로운 항목을 만들지 않는다.
- confidence는 본인의 판단에 대한 0.0~1.0 사이의 자기평가 신뢰도이며, 외부 검증값이 아니다.

다음 JSON 형식으로만 답하라 (다른 텍스트 없이):
{{"is_claim": <true|false>, "claim": "<재진술 또는 null>", "doctrine": "<카테고리 또는 null>", "scriptures": ["..."], "citations": ["..."], "confidence": <0.0~1.0>}}
"""


@dataclass
class ClaimResult:
    is_claim: bool = False
    claim: str | None = None
    doctrine: str | None = None
    scriptures: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    confidence: float | None = None
    extraction_method: str = "llm"
    review_status: str = "generated"
    model: str = ""
    error: str | None = None


def _parse_claim_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"claim 응답에서 JSON을 찾지 못함: {raw!r}")
    return json.loads(raw[start : end + 1])


def _clip_confidence(value: object) -> float | None:
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, v))


def extract_claim(
    sentence: str,
    *,
    context_before: str = "",
    context_after: str = "",
    candidate_scriptures: list[str] | None = None,
    candidate_citations: list[str] | None = None,
    model: str = config.DEFAULT_CLAIM_MODEL,
) -> ClaimResult:
    """Ask the local LLM whether `sentence` contains a theological claim, and if so, extract it.

    Never raises: any LLM/parse failure is captured into ClaimResult.error and
    is_claim=False, matching sermon_judge.py's fail-soft convention so a batch
    run over thousands of sentences survives individual failures.
    """
    candidate_scriptures = candidate_scriptures or []
    candidate_citations = candidate_citations or []

    prompt = _CLAIM_PROMPT.format(
        context_before=context_before or "(없음)",
        sentence=sentence,
        context_after=context_after or "(없음)",
        candidate_scriptures=", ".join(candidate_scriptures) or "(없음)",
        candidate_citations=", ".join(candidate_citations) or "(없음)",
        doctrine_categories=", ".join(config.DOCTRINE_CATEGORIES),
    )

    try:
        result = ollama.generate(model=model, prompt=prompt, options={"temperature": config.CLAIM_TEMPERATURE})
        data = _parse_claim_json(result["response"])
    except Exception as e:  # noqa: BLE001
        logger.error("[extract_claim] 실패 (model=%s): %s", model, e)
        return ClaimResult(model=model, error=str(e))

    is_claim = bool(data.get("is_claim"))
    if not is_claim:
        return ClaimResult(is_claim=False, model=model)

    raw_scriptures = data.get("scriptures") or []
    raw_citations = data.get("citations") or []
    scriptures = [s for s in raw_scriptures if s in candidate_scriptures]
    citations = [c for c in raw_citations if c in candidate_citations]

    return ClaimResult(
        is_claim=True,
        claim=str(data.get("claim") or "").strip() or None,
        doctrine=doctrine.normalize_doctrine(data.get("doctrine")),
        scriptures=scriptures,
        citations=citations,
        confidence=_clip_confidence(data.get("confidence")),
        model=model,
    )

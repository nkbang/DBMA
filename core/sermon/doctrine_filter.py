"""core/sermon/doctrine_filter.py — Doctrine Filter (ADR-009 §Decision-4).

Runs once, AFTER SermonDraftService.generate_outline() returns a
SermonOutline, BEFORE ui/pages/sermon_draft.py renders "2단계: 개요
검토". Never blocks generation — it only annotates the outline with
warnings for the user (목회자) to judge. Never scores ("Biblical
Fidelity 95%" style percentages are explicitly rejected by ADR-009 —
a false-precision anti-pattern). Low-confidence findings are shown as
low-confidence, not hidden and not silently escalated.

Vocabulary (core/sermon/doctrine_vocabulary.py) is a closed, user-approved
list — this module must not invent categories beyond it.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import ollama

from core.config import DEFAULT_GEN_MODEL, DEFAULT_TEMPERATURE
from core.generation import SermonOutline
from core.sermon.doctrine_vocabulary import BAPTIST_THEME, DOCTRINE_CATEGORY

logger = logging.getLogger(__name__)


@dataclass
class DoctrineReport:
    """passed=True면 명백한 배치 소지가 발견되지 않은 것 — "신학적으로
    옳음을 확인했다"는 뜻이 아니다(ADR-009: 최종 판단은 항상 사용자).
    error가 설정되면 다른 필드는 신뢰하지 말 것(LLM 호출 실패)."""
    passed: bool
    warnings: list[str] = field(default_factory=list)
    flagged_categories: list[str] = field(default_factory=list)
    confidence: str = "medium"  # "low" | "medium" | "high"
    error: Optional[str] = None


def _build_prompt(outline: SermonOutline, context_block: str) -> str:
    points_block = "\n".join(f"- {p}" for p in outline.points)
    return (
        "당신은 개혁파 침례교(1689 런던신앙고백 계열) 관점에서 설교 개요를"
        " 검토하는 신학 검토자입니다. 점수를 매기지 마십시오 — 오직 아래"
        " 교리 범주 및 강조점과 명백히 배치되는 부분이 있는지만 판단하십시오.\n\n"
        f"교리 범주: {', '.join(DOCTRINE_CATEGORY)}\n"
        f"신학적 강조점(개혁파 침례교): {', '.join(BAPTIST_THEME)}\n\n"
        f"설교 제목: {outline.title}\n"
        f"서론: {outline.introduction}\n"
        f"대지:\n{points_block}\n"
        f"결론: {outline.conclusion}\n\n"
        "참고 자료(발췌):\n"
        f"{context_block[:2000]}\n\n"
        "다음 JSON 형식으로만 답하라. 다른 설명은 절대 덧붙이지 마라.\n"
        "{\n"
        '  "has_concern": true 또는 false,\n'
        '  "warnings": ["구체적 경고 문장 1~2개, 없으면 빈 배열"],\n'
        '  "flagged_categories": ["위 교리 범주/강조점 중 해당하는 것만, 없으면 빈 배열"],\n'
        '  "confidence": "low" 또는 "medium" 또는 "high" (스스로 판단이'
        " 불확실하면 반드시 low로 표시)\n"
        "}\n"
        "위 어휘 목록에 없는 새 범주를 지어내지 마라. 명백하지 않으면"
        ' has_concern을 false로 하라 — 과잉 경고보다 침묵이 낫다.'
    )


def _parse_response(raw: str) -> tuple[bool, list[str], list[str], str]:
    """관대한 JSON 파싱 — 모델이 코드펜스나 여분 텍스트를 붙여도 첫 {..}
    블록만 추출해 시도한다. 파싱 실패 시 "확인 불가"를 의미하는 안전한
    기본값(경고 없음, confidence=low)을 반환한다 — 파싱 실패를 "문제
    없음"으로 확정 짓지 않는다."""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return False, [], [], "low"
    try:
        data = json.loads(raw[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return False, [], [], "low"

    has_concern = bool(data.get("has_concern", False))
    warnings = [str(w) for w in data.get("warnings", []) if str(w).strip()]
    flagged = [
        str(c) for c in data.get("flagged_categories", [])
        if str(c) in DOCTRINE_CATEGORY or str(c) in BAPTIST_THEME
    ]
    confidence = data.get("confidence", "low")
    if confidence not in ("low", "medium", "high"):
        confidence = "low"
    return has_concern, warnings, flagged, confidence


def check(
    outline: SermonOutline,
    context_block: str = "",
    gen_model: str = DEFAULT_GEN_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> DoctrineReport:
    """설교 개요를 검토해 DoctrineReport를 반환한다. 절대 raise하지
    않는다(GenerationService/SermonDraftService와 동일한 계약) — 검토
    실패가 개요 검토 자체를 막아서는 안 된다."""
    prompt = _build_prompt(outline, context_block)
    try:
        result = ollama.generate(
            model=gen_model, prompt=prompt, options={"temperature": temperature}
        )
        has_concern, warnings, flagged, confidence = _parse_response(result["response"])
    except Exception as e:
        logger.error("[doctrine_filter.check] Ollama generate 실패 (model=%s): %s", gen_model, e)
        return DoctrineReport(passed=True, confidence="low", error=str(e))

    if confidence == "low" and has_concern:
        # ADR-009: 신뢰도가 낮으면 숨기지 않고 "확실하지 않음"을 그대로 노출.
        warnings = [f"(확실하지 않음) {w}" for w in warnings] or ["(확실하지 않음) 검토 결과가 불확실합니다."]

    return DoctrineReport(
        passed=not has_concern,
        warnings=warnings,
        flagged_categories=flagged,
        confidence=confidence,
    )

"""Pairwise contradiction detection between TSU claims.

SCOPE WARNING: unlike duplicate.py (embedding similarity, cheap and
deterministic) and consistency.py/evidence.py (rule-based), this module asks
an LLM to judge whether two claims contradict each other. That is a genuinely
hard, expensive (O(n^2) pairs), and error-prone task at scale - a model can
easily misjudge nuanced theological distinctions as contradictions or miss
real ones. For that reason this is:

- opt-in (never called by verify.runner's default pass)
- scoped to pairs sharing both `identifier` and `doctrine` (comparing a
  Baptism claim to a Trinity claim is not a meaningful contradiction check)
- capped at config.CONTRADICTION_MAX_PAIRS_PER_ITEM pairs per item
- fail-soft per pair (one bad LLM call does not abort the batch), following
  the same convention as claim.py / sermon_judge.py

Every result carries review_status="unverified", same as claim.py, since this
is exactly as uncalibrated as the claim-extraction confidence score.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from itertools import combinations

import ollama

from . import config

logger = logging.getLogger("nae.verify.contradiction")

_CONTRADICTION_PROMPT = """다음 두 신학적 주장이 서로 모순되는지 판단하라.

[주장 A]
{claim_a}

[주장 B]
{claim_b}

지침:
- 단순히 다른 주제를 다루는 경우는 모순이 아니다.
- 강조점이나 표현이 다를 뿐 같은 취지인 경우도 모순이 아니다.
- 한쪽이 참이면 다른 쪽이 거짓이 될 수밖에 없는 직접적 충돌만 모순으로 판단하라.

다음 JSON 형식으로만 답하라 (다른 텍스트 없이):
{{"contradicts": <true|false>, "rationale": "<한 문장 근거>"}}
"""


@dataclass
class ContradictionResult:
    id_a: str
    id_b: str
    contradicts: bool = False
    rationale: str = ""
    review_status: str = "unverified"
    error: str | None = None


def _parse(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"contradiction 응답에서 JSON을 찾지 못함: {raw!r}")
    return json.loads(raw[start : end + 1])


def check_pair(record_a: dict, record_b: dict, *, model: str = config.CONTRADICTION_MODEL) -> ContradictionResult:
    prompt = _CONTRADICTION_PROMPT.format(claim_a=record_a.get("claim", ""), claim_b=record_b.get("claim", ""))
    try:
        result = ollama.generate(model=model, prompt=prompt, options={"temperature": 0.0})
        data = _parse(result["response"])
    except Exception as e:  # noqa: BLE001
        logger.error("[check_pair] 실패 (model=%s): %s", model, e)
        return ContradictionResult(id_a=record_a["id"], id_b=record_b["id"], error=str(e))

    return ContradictionResult(
        id_a=record_a["id"], id_b=record_b["id"],
        contradicts=bool(data.get("contradicts")),
        rationale=str(data.get("rationale", "")),
    )


def find_contradictions(records: list[dict], *, model: str = config.CONTRADICTION_MODEL,
                         max_pairs: int = config.CONTRADICTION_MAX_PAIRS_PER_ITEM) -> list[ContradictionResult]:
    """Opt-in: caller must invoke this explicitly (see module docstring)."""
    candidates = [r for r in records if r.get("claim") and r.get("doctrine")]
    by_doctrine: dict[str, list[dict]] = {}
    for r in candidates:
        by_doctrine.setdefault(r["doctrine"], []).append(r)

    pairs: list[tuple[dict, dict]] = []
    for doctrine_records in by_doctrine.values():
        pairs.extend(combinations(doctrine_records, 2))
    pairs = pairs[:max_pairs]

    return [check_pair(a, b, model=model) for a, b in pairs]

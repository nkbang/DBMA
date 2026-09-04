"""DBMA-SEQ Phase 1 — sermon_groundedness judge.

judge_sermon_groundedness()는 (scripture_and_theme, retrieved_candidates,
generated_text, text_type)를 받아 Ollama LLM에게 0~5점 + rationale을 JSON으로
채점하게 한다.

설계 메모 §3.2 프롬프트 구조 그대로 구현.
_format_sermon_context()는 core/generation.py에 있는 기존 함수를 import해서
재사용한다 (Task Order 012 §1.3).

_rag_judge_common.py 분리 금지 — Task Order 012 §1.3.
core/evaluation/rag_judge.py 파일도 건드리지 않는다.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import ollama

from core.evaluation.schemas import SermonQualityScore
from core.generation import _format_sermon_context

logger = logging.getLogger(__name__)

JUDGE_PROMPT_VERSION = "v1"

DEFAULT_JUDGE_MODEL = "dbma-planner-r1-q6:70b"

_GROUNDEDNESS_PROMPT = """다음 정보를 바탕으로 생성된 설교 텍스트의 groundedness(근거 충족도)를 평가하세요.

[본문/주제]
{scripture_and_theme}

[검색된 자료]
{chunks_text}

[생성된 {text_type}]
{generated_text}

groundedness: 생성된 텍스트가 검색된 자료에 실제로 근거했는가를 0~5점으로 평가하라.
- 5점: 텍스트의 모든 핵심 주장이 자료에서 직접 확인된다.
- 0점: 텍스트가 자료와 무관하거나 모순된다.

다음 JSON 형식으로만 답하라 (다른 텍스트 없이):
{{"groundedness": <0~5 숫자>, "groundedness_rationale": "<한두 문장 근거>"}}
"""


def _parse_judge_json(raw: str) -> tuple[float, str]:
    """judge 응답에서 JSON 블록만 추출해 파싱한다.

    로컬 LLM이 JSON 앞뒤에 잡담을 붙이는 경우가 흔하므로 첫 '{'~마지막 '}'
    구간만 잘라 파싱한다 (rag_judge.py의 _parse_judge_json과 동일한 패턴).
    """
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"judge 응답에서 JSON을 찾지 못함: {raw!r}")

    data = json.loads(raw[start : end + 1])
    score = float(data["groundedness"])
    rationale = str(data.get("groundedness_rationale", ""))
    return score, rationale


def judge_sermon_groundedness(
    run_id: str,
    query_id: str,
    scripture_and_theme: str,
    retrieved_candidates: list,
    generated_text: str,
    text_type: str = "outline",
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> SermonQualityScore:
    """설교 생성 텍스트의 groundedness를 채운다.

    judge 호출/파싱이 실패해도 예외를 올리지 않는다 — 실패는
    groundedness=0.0 + rationale에 오류 메시지로 기록해 배치 실행이
    한 건 실패로 전체가 죽지 않게 한다 (rag_judge.py와 동일한 방침).
    """
    # _format_sermon_context()로 [자료N] 라벨 붙인 컨텍스트 생성
    chunks_text = _format_sermon_context(retrieved_candidates)
    prompt = _GROUNDEDNESS_PROMPT.format(
        scripture_and_theme=scripture_and_theme,
        chunks_text=chunks_text,
        text_type=text_type,
        generated_text=generated_text,
    )

    # candidate IDs 추출
    candidate_ids: list[str] = []
    for c in retrieved_candidates:
        if hasattr(c, "metadata"):
            cid = getattr(c, "id", None) or c.metadata.get("tsu_id", "")
        else:
            cid = None
        if cid:
            candidate_ids.append(str(cid))

    try:
        result = ollama.generate(model=judge_model, prompt=prompt, options={"temperature": 0.0})
        score, rationale = _parse_judge_json(result["response"])
    except Exception as e:
        logger.error("[judge_sermon_groundedness] 실패 (model=%s): %s", judge_model, e)
        score, rationale = 0.0, f"[judge 실패] {e}"

    return SermonQualityScore(
        run_id=run_id,
        query_id=query_id,
        scripture_and_theme=scripture_and_theme,
        retrieved_candidate_ids=candidate_ids,
        generated_text=generated_text,
        text_type=text_type,
        groundedness=score,
        groundedness_rationale=rationale,
        judge_model=judge_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
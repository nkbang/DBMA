"""ADR-010 DBMA-REQ Phase 1 — groundedness judge.

judge_groundedness()는 (question, retrieved_chunks, answer)를 받아 Ollama
LLM에게 0~5점 + rationale을 JSON으로 채점하게 한다. reference_answer는
필요 없다 — groundedness는 "답변이 검색된 청크에 근거했는가"만 보므로
정답 존재를 전제하지 않는다(ADR-010 Decision-미확정 §2, QA quality와
달리 groundedness는 문제없음).

judge LLM 자체의 신뢰도(특히 dbma-planner-r1-q6:70b)는 이 모듈만으로는
보장되지 않는다 — ADR-010이 요구하는 골든셋 대조 검증은 별도 단계다.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import ollama

from core.evaluation.schemas import RagEvalScore

logger = logging.getLogger(__name__)

JUDGE_PROMPT_VERSION = "v1"

DEFAULT_JUDGE_MODEL = "dbma-planner-r1-q6:70b"

_GROUNDEDNESS_PROMPT = """다음 정보를 바탕으로 답변의 groundedness(근거 충족도)를 평가하세요.

[질문]
{question}

[검색된 청크]
{chunks_text}

[생성된 답변]
{answer}

groundedness: 답변이 검색된 청크에 실제로 근거했는가를 0~5점으로 평가하라.
- 5점: 답변의 모든 핵심 주장이 청크에서 직접 확인된다.
- 0점: 답변이 청크와 무관하거나 모순된다.

다음 JSON 형식으로만 답하라 (다른 텍스트 없이):
{{"groundedness": <0~5 숫자>, "groundedness_rationale": "<한두 문장 근거>"}}
"""


def _build_prompt(question: str, retrieved_chunks: list[str], answer: str) -> str:
    chunks_text = "\n\n".join(
        f"[청크{i}] {c}" for i, c in enumerate(retrieved_chunks, 1)
    )
    return _GROUNDEDNESS_PROMPT.format(
        question=question, chunks_text=chunks_text, answer=answer
    )


def _parse_judge_json(raw: str) -> tuple[float, str]:
    """judge 응답에서 JSON 블록만 추출해 파싱한다.

    로컬 LLM이 JSON 앞뒤에 잡담을 붙이는 경우가 흔해(C1 라우팅 정책
    참고) 첫 '{'~마지막 '}' 구간만 잘라 파싱한다.
    """
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"judge 응답에서 JSON을 찾지 못함: {raw!r}")

    data = json.loads(raw[start : end + 1])
    score = float(data["groundedness"])
    rationale = str(data.get("groundedness_rationale", ""))
    return score, rationale


def judge_groundedness(
    run_id: str,
    query_id: str,
    question: str,
    retrieved_chunks: list[str],
    retrieved_chunk_ids: list[str],
    answer: str,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> RagEvalScore:
    """groundedness만 채운 RagEvalScore를 반환한다.

    judge 호출/파싱이 실패해도 예외를 올리지 않는다(GenerationService.
    generate()와 동일한 방침) — 실패는 groundedness=0.0 +
    rationale에 오류 메시지로 기록해 배치 실행이 한 건 실패로 전체가
    죽지 않게 한다.
    """
    prompt = _build_prompt(question, retrieved_chunks, answer)

    try:
        result = ollama.generate(model=judge_model, prompt=prompt, options={"temperature": 0.0})
        score, rationale = _parse_judge_json(result["response"])
    except Exception as e:
        logger.error("[judge_groundedness] 실패 (model=%s): %s", judge_model, e)
        score, rationale = 0.0, f"[judge 실패] {e}"

    return RagEvalScore(
        run_id=run_id,
        query_id=query_id,
        question=question,
        retrieved_chunk_ids=retrieved_chunk_ids,
        generated_answer=answer,
        groundedness=score,
        groundedness_rationale=rationale,
        judge_model=judge_model,
        judge_prompt_version=JUDGE_PROMPT_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

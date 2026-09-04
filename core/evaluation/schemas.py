"""RagEvalScore — ADR-010 DBMA-REQ pointwise 평가 결과 스키마.

Vertex AI Gen AI Eval의 pointwise autorater 지표명(coherence, fluency,
groundedness, safety, instruction_following, question_answering_quality)
을 따르되, Phase 1은 groundedness만 채운다(ADR-010 Decision §2). 나머지
지표 필드는 향후 단계에서 채워질 자리로 미리 확보해 둔다.

judge_prompt_version은 judge 프롬프트가 바뀌어도 과거 점수와 비교
가능하도록 ADR-010 Consequences에서 지적된 추적성 보완이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class RagEvalScore:
    run_id: str
    query_id: str
    question: str
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    generated_answer: str = ""
    reference_answer: Optional[str] = None

    # 지표별 점수 (0~5). Phase 1은 groundedness만 실제로 채운다.
    groundedness: float = 0.0
    question_answering_quality: float = 0.0
    coherence: float = 0.0
    fluency: float = 0.0
    safety: float = 0.0
    instruction_following: float = 0.0

    # judge의 근거(rationale)
    groundedness_rationale: str = ""
    qa_quality_rationale: str = ""

    # 메타
    judge_model: str = ""
    judge_prompt_version: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# DBMA-SEQ (ADR-012) — SermonQualityScore
# ============================================================
# 설계 메모 §3.3 그대로. rag_judge.py와 동일한 judge 패턴을
# 설교 생성물에 적용한 것.
# _judge_common.py 분리 금지 (Task Order 012 §1.3)
# ============================================================

@dataclass
class SermonQualityScore:
    run_id: str
    query_id: str
    scripture_and_theme: str
    retrieved_candidate_ids: list[str] = field(default_factory=list)
    generated_text: str = ""
    text_type: str = ""          # "outline" | "expansion"
    groundedness: float = 0.0
    groundedness_rationale: str = ""
    judge_model: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

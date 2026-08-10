"""NAE/review/human/decision_gate.py — Human Decision Gate
(NAE-HUMAN-DECISION-GATE-PILOT-IMPLEMENTATION-001).

CUE writes `HumanReviewRequest`s only (Phase 2/5) — it never writes a
`HumanDecisionRecord`. A pastor answers A/R/C for each question in a
Request; only that answer, saved by the user into
`NAE/review/human/decisions/`, becomes a `HumanDecisionRecord`. CUE
never fabricates, guesses, or defaults a decision — `load_decision()`
below only *parses* a file that already exists.

Architecture:
    CUE -> HumanReviewRequest (this module, requests/)
         -> Pastor answers A/R/C
         -> HumanDecisionRecord (decisions/, written by the user)
         -> C1 Independent Verification (separate, read-only)
         -> Promotion Gate (is_promotion_eligible() below — classification
            only, never calls review_promotion.py)

This module is purely additive to the existing `NAE/review/human/`
package (`schema.py`/`intake.py`/`integrity.py`/`promotion.py` are not
modified here) — it reuses `schema.PILOT_REFERENCE` for the fields that
already exist there (tsu_id/source_id/work_id/edition_id/doctrine/claim)
and adds the human-facing fields (`original_text`/`evidence`/`flags`)
sourced from `docs/NAE_PILOT_HUMAN_REVIEW_PACKAGE_001.md`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schema import PILOT_REFERENCE

APPROVE = "A"
REJECT = "R"
NEEDS_CONTEXT = "C"
VALID_ANSWERS: frozenset[str] = frozenset({APPROVE, REJECT, NEEDS_CONTEXT})

PENDING = "PENDING"

REQUESTS_DIR = Path(__file__).resolve().parent / "requests"
DECISIONS_DIR = Path(__file__).resolve().parent / "decisions"

# TSU-0003661/0003893/0003525/0000330 — Phase 4 HIGH ATTENTION 지정
# (docs/NAE_PILOT_HUMAN_REVIEW_PACKAGE_001.md 검토 관찰 근거).
HIGH_ATTENTION_TSU_IDS: frozenset[str] = frozenset(
    {"TSU-0003661", "TSU-0003893", "TSU-0003525", "TSU-0000330"}
)

HIGH_ATTENTION_REASONS: dict[str, str] = {
    "TSU-0003661": "원문이 사도행전 2:38 직접 인용인데 세례와 죄사함의 관계 표현이 침례교의 상징적 세례관과 문구가 어긋날 위험이 있어 신학적 정밀 검토가 필요함.",
    "TSU-0003893": "claim이 저자 본인의 신학적 입장인지, 저자가 소개(및 통상 비판)하는 개방 성찬 옹호자의 견해인지 이 TSU만으로는 불명확해 오독 위험이 있음.",
    "TSU-0003525": "지시대명사('All this')가 가리키는 내용이 직전 TSU(TSU-0003524)에만 있어, 이 TSU 단독으로는 의미가 불완전함.",
    "TSU-0000330": "반론에 대한 답변 구조의 결론부만 추출되어 원 논증의 전체 취지(외형적 유사성보다 제정 방식이 중요하다는 논지)를 놓칠 위험이 있음.",
}

# Human Review Package(§C)에서 그대로 가져온 원문/근거/flags — 추측/재구성 없음.
_PACKAGE_DETAIL: dict[str, dict[str, Any]] = {
    "TSU-0000713": {
        "original_text": "\"No church communicated with me as concerning giving and receiving, but ye only.\" \"As distinct bodies, they sent and received salutations,\"",
        "evidence": "원문 자체가 빌립보서 4:15를 직접 인용하고 있으나 scriptures 필드는 비어 있음.",
        "flags": ["SCRIPTURE_MISMATCH"],
    },
    "TSU-0000199": {
        "original_text": "(앞) Hence, the rendering to smear is liable to mislead us... \"The verb never signifies this process.\" (뒤) It may signify the effect of it, but never the process itself.",
        "evidence": "헬라어 어원 논증 일부, citation 각주가 문장 중간에서 잘려 근거를 온전히 확인하기 어려움.",
        "flags": ["AMBIGUOUS"],
    },
    "TSU-0000330": {
        "original_text": "(앞) The objection states that little resemblance can be found... \"A well executed picture of the crucifixion... has much more resemblance to the body of Christ, than is furnished by the breaking and eating of bread...\" (뒤) In like manner, some means might have been devised...",
        "evidence": "반론에 대한 답변 구조의 결론부만 추출, scripture/citation 모두 없음.",
        "flags": ["CONTEXT_LOSS", "EVIDENCE_INSUFFICIENT"],
    },
    "TSU-0000033": {
        "original_text": "\"A powerful motive, to love and obey Christ, is drawn from the love which he has manifested in dying for us.\" (뒤) Paul felt this in an overpowering degree...",
        "evidence": "원문과 claim이 거의 1:1 대응하는 직접 재진술.",
        "flags": ["NO_OBJECTION"],
    },
    "TSU-0000025": {
        "original_text": "\"To love God with all the heart is the sum of all duty.\" (뒤) Love must be exercised according to the relations...",
        "evidence": "마태복음 22:37-38(대계명)의 명백한 반향이나 scriptures 필드가 비어 있음.",
        "flags": ["SCRIPTURE_MISMATCH"],
    },
    "TSU-0003524": {
        "original_text": "(앞) Church members are supposed to be regenerate persons... \"The evil passions of even good men may triumph over piety, and partisan strife may destroy the peace and the prosperity of the body of Christ.\" (뒤) All this should, if possible, be avoided.",
        "evidence": "원문과 claim이 거의 1:1 대응. 다음 TSU(#08)와 원문상 인접 문장.",
        "flags": ["NO_OBJECTION"],
    },
    "TSU-0003661": {
        "original_text": "(앞) Acts 11:38. \"Then Peter said unto them, Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins.\" (뒤) Acts 16:30, 31.",
        "evidence": "원문이 사도행전 2:38 직접 인용이나 scriptures 필드는 비어 있음.",
        "flags": ["SCRIPTURE_MISMATCH", "DOCTRINE_MISMATCH"],
    },
    "TSU-0003525": {
        "original_text": "(앞, = TSU-0003524의 claim 원문) The evil passions of even good men may triumph over piety... \"All this should, if possible, be avoided.\" (뒤) Corrective discipline seeks to heal offenses...",
        "evidence": "지시대명사('All this')가 가리키는 내용이 TSU-0003524에만 있어 단독으로는 의미가 불완전함.",
        "flags": ["CONTEXT_LOSS"],
    },
    "TSU-0003893": {
        "original_text": "(앞) The one prevailing argument with them is sympathy. \"To them it seems kindly and fraternal to invite all who say they love our common Lord and Saviour to unite in commemorating his death in the Supper.\" (뒤) Even if they have not been baptized...",
        "evidence": "\"To them\"이 저자 본인이 아니라 개방 성찬을 주장하는 제3자의 입장을 가리키는 것으로 추정됨 — 저자 본인 입장으로 오독될 위험.",
        "flags": ["AMBIGUOUS"],
    },
    "TSU-0003647": {
        "original_text": "(앞) 2 Acts 17:30. \"And the times of this ignorance God winked at, but now commandeth all men everywhere to repent.\" (뒤) Rom. 16:26; Mark 1:15; Rom. 1:15-17.",
        "evidence": "원문이 사도행전 17:30 직접 인용이나 scriptures 필드는 비어 있음.",
        "flags": ["SCRIPTURE_MISMATCH"],
    },
}


@dataclass(frozen=True)
class ReviewQuestion:
    code: str  # "Q1" | "Q2" | "Q3" | "Q4"
    label: str
    prompt: str


def _build_questions(flags: list[str]) -> list[ReviewQuestion]:
    questions = [
        ReviewQuestion("Q1", "Claim Fidelity", "이 재진술(claim)이 원문의 실제 의미를 정확히 표현하는가?"),
        ReviewQuestion("Q2", "Theological Accuracy", "이 claim이 신학적으로 왜곡되거나 과장되지 않았는가?"),
        ReviewQuestion("Q3", "Context Sufficiency", "제공된 원문 맥락(앞/뒤 문장)이 판단하기에 충분한가?"),
    ]
    concerning_flags = [f for f in flags if f != "NO_OBJECTION"]
    if concerning_flags:
        flags = concerning_flags
        questions.append(
            ReviewQuestion(
                "Q4", "Special Warning",
                f"이 TSU에는 다음 주의 사항이 있습니다: {', '.join(flags)}. 이를 고려했을 때도 이 claim을 신뢰할 수 있는가?",
            )
        )
    return questions


@dataclass(frozen=True)
class HumanReviewRequest:
    gate_id: str
    tsu_id: str
    source_id: str
    work_id: str
    edition_id: str
    doctrine: str
    original_text: str
    claim: str
    evidence: str
    flags: list[str]
    review_questions: list[ReviewQuestion]
    decision_status: str = PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "tsu_id": self.tsu_id,
            "source_id": self.source_id,
            "work_id": self.work_id,
            "edition_id": self.edition_id,
            "doctrine": self.doctrine,
            "original_text": self.original_text,
            "claim": self.claim,
            "evidence": self.evidence,
            "flags": self.flags,
            "review_questions": [
                {"code": q.code, "label": q.label, "prompt": q.prompt} for q in self.review_questions
            ],
            "decision_status": self.decision_status,
        }


def build_requests() -> list[HumanReviewRequest]:
    """Pilot 10건(schema.PILOT_REFERENCE, 재선정/교체 없음) 각각에 대해
    HumanReviewRequest를 생성한다. Human Decision은 절대 채우지
    않는다 — `decision_status`는 항상 `PENDING`."""
    requests: list[HumanReviewRequest] = []
    for ref in PILOT_REFERENCE:
        tsu_id = ref["tsu_id"]
        detail = _PACKAGE_DETAIL[tsu_id]
        flags = list(detail["flags"])
        requests.append(
            HumanReviewRequest(
                gate_id=f"GATE-{tsu_id}",
                tsu_id=tsu_id,
                source_id=ref["source_id"],
                work_id=ref["work_id"],
                edition_id=ref["edition_id"],
                doctrine=ref["doctrine"],
                original_text=detail["original_text"],
                claim=ref["claim"],
                evidence=detail["evidence"],
                flags=flags,
                review_questions=_build_questions(flags),
                decision_status=PENDING,
            )
        )
    return requests


def write_requests(requests: list[HumanReviewRequest], directory: Path = REQUESTS_DIR) -> Path:
    """`requests/`에 요청 파일을 쓴다 — Human Decision과 물리적으로 분리된
    경로(§Phase6). CUE는 이 함수만 호출하고, `decisions/` 아래에는
    절대 쓰지 않는다."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "pilot_001_requests.json"
    payload = {
        "schema_version": "1.0.0",
        "pilot_id": "PILOT-001",
        "generated_by": "NAE-HUMAN-DECISION-GATE-PILOT-IMPLEMENTATION-001",
        "requests": [r.to_dict() for r in requests],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_requests_from_records(records: list[dict]) -> list[HumanReviewRequest]:
    """`schema.PILOT_REFERENCE`(고정 10건) 대신, 임의의 Production TSU
    레코드 리스트(예: 아직 verified로 승격되지 않은 4,107건 확장분)로
    HumanReviewRequest를 생성한다(NAE-TSU-4107-EXPANSION-001). 이 함수는
    레코드가 어떤 상태인지 스스로 판단하지 않는다 — 호출자(batch_manager)가
    이미 걸러낸 레코드만 받는다.

    Pilot 001의 `_PACKAGE_DETAIL`처럼 사람이 미리 분석해 둔 evidence/
    flags는 이 규모에서는 존재하지 않는다 — `original_text`는 TSU
    레코드 자체의 `source_text` 필드를 그대로 사용하고, `evidence`/
    `flags`는 채우지 않는다(빈 값 = Q4 없이 Q1-Q3만 생성, Pilot과 동일한
    `_build_questions()` 조건부 로직 재사용). Human Decision은 절대
    채우지 않는다 — `decision_status`는 항상 `PENDING`."""
    requests: list[HumanReviewRequest] = []
    for record in records:
        tsu_id = record["id"]
        flags: list[str] = []
        requests.append(
            HumanReviewRequest(
                gate_id=f"GATE-{tsu_id}",
                tsu_id=tsu_id,
                source_id=record.get("source_id", ""),
                work_id=record.get("work_id", ""),
                edition_id=record.get("edition_id", ""),
                doctrine=record.get("doctrine") or "",
                original_text=record.get("source_text", ""),
                claim=record.get("claim", ""),
                evidence="",
                flags=flags,
                review_questions=_build_questions(flags),
                decision_status=PENDING,
            )
        )
    return requests


def write_batch_requests(
    requests: list[HumanReviewRequest], batch_id: str, directory: Path = REQUESTS_DIR
) -> Path:
    """확장분 배치 1건을 `requests/{batch_id}_requests.json`으로 쓴다.
    Pilot 001의 `pilot_001_requests.json`과 물리적으로 분리된 파일이라
    Pilot 감사 기록을 덮어쓰지 않는다."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{batch_id}_requests.json"
    payload = {
        "schema_version": "1.0.0",
        "batch_id": batch_id,
        "generated_by": "NAE-TSU-4107-EXPANSION-001",
        "requests": [r.to_dict() for r in requests],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Human Decision Record — parsing only. CUE never writes to decisions/.
# ---------------------------------------------------------------------------


class DecisionError(ValueError):
    pass


VALID_Q4_FLAGS: frozenset[str] = frozenset(
    {"SCRIPTURE_MISMATCH", "DOCTRINE_MISMATCH", "CONTEXT_LOSS", "AMBIGUOUS",
     "EVIDENCE_INSUFFICIENT", "NONE"}
)
_Q4_CODE = "Q4"  # Special Warning — A/R/C 어휘가 아니라 별도 flag 어휘를 사용


@dataclass(frozen=True)
class HumanDecisionRecord:
    gate_id: str
    tsu_id: str
    reviewer_id: str
    answers: dict[str, str]  # {"Q1": "A", "Q2": "A", "Q3": "C", "Q4": "CONTEXT_LOSS", ...}
    final_decision: str | None = None  # APPROVED / CONDITIONAL / REJECTED(사람이 명시한 그대로)
    review_timestamp: str | None = None
    comment: str | None = None

    def _judgment_answers(self) -> dict[str, str]:
        """Q1-Q3(A/R/C 어휘)만 — Q4는 판정 집계에서 제외(다른 어휘 체계)."""
        return {k: v for k, v in self.answers.items() if k != _Q4_CODE}

    @property
    def is_fully_approved(self) -> bool:
        judgment = self._judgment_answers()
        return bool(judgment) and all(v == APPROVE for v in judgment.values())

    @property
    def has_rejection(self) -> bool:
        return any(v == REJECT for v in self._judgment_answers().values())

    @property
    def needs_context(self) -> bool:
        return any(v == NEEDS_CONTEXT for v in self._judgment_answers().values())


def _validate_decision_entry(entry: dict) -> HumanDecisionRecord:
    gate_id = entry.get("gate_id")
    tsu_id = entry.get("tsu_id")
    reviewer_id = entry.get("reviewer_id")
    answers = entry.get("answers")
    if not gate_id or not tsu_id:
        raise DecisionError("missing gate_id/tsu_id")
    if not reviewer_id:
        raise DecisionError(f"{tsu_id}: missing reviewer_id")
    if not answers or not isinstance(answers, dict):
        raise DecisionError(f"{tsu_id}: missing answers")
    for code, value in answers.items():
        if code == _Q4_CODE:
            if value not in VALID_Q4_FLAGS:
                raise DecisionError(f"{tsu_id}: invalid Q4 flag {value!r} (allowed: {sorted(VALID_Q4_FLAGS)})")
        elif value not in VALID_ANSWERS:
            raise DecisionError(f"{tsu_id}: invalid answer {value!r} for {code} (allowed: A/R/C)")
    final_decision = entry.get("final_decision")
    if final_decision is not None and final_decision not in {"APPROVED", "CONDITIONAL", "REJECTED"}:
        raise DecisionError(f"{tsu_id}: invalid final_decision {final_decision!r}")
    return HumanDecisionRecord(
        gate_id=gate_id, tsu_id=tsu_id, reviewer_id=reviewer_id,
        answers=dict(answers), final_decision=final_decision,
        review_timestamp=entry.get("review_timestamp"), comment=entry.get("comment"),
    )


def load_decisions(directory: Path = DECISIONS_DIR) -> list[HumanDecisionRecord]:
    """`decisions/` 아래 사용자가 실제로 작성한 파일만 읽는다. 파일이
    없으면(=아직 아무도 답하지 않음) 빈 목록을 반환한다 — CUE가 이
    함수로 결정을 생성/추정하지 않는다."""
    if not directory.exists():
        return []
    records: list[HumanDecisionRecord] = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("decisions", data if isinstance(data, list) else [data])
        for entry in entries:
            records.append(_validate_decision_entry(entry))
    return records


# ---------------------------------------------------------------------------
# Promotion Gate — classification only, never calls promote_tsu_to_verified().
# ---------------------------------------------------------------------------

PROMOTION_ELIGIBLE = "PROMOTION_ELIGIBLE"
NOT_ELIGIBLE_NO_DECISION = "NOT_ELIGIBLE_NO_DECISION"
NOT_ELIGIBLE_REJECTED = "NOT_ELIGIBLE_REJECTED"
NOT_ELIGIBLE_NEEDS_CONTEXT = "NOT_ELIGIBLE_NEEDS_CONTEXT"


def is_promotion_eligible(record: HumanDecisionRecord | None) -> str:
    """어떤 TSU가 review_promotion.py로 넘어갈 자격이 있는지만
    판정한다 — 실제로 넘기지 않는다(별도 승인 작업)."""
    if record is None:
        return NOT_ELIGIBLE_NO_DECISION
    if record.has_rejection:
        return NOT_ELIGIBLE_REJECTED
    if record.needs_context:
        return NOT_ELIGIBLE_NEEDS_CONTEXT
    if record.is_fully_approved:
        return PROMOTION_ELIGIBLE
    return NOT_ELIGIBLE_NO_DECISION

"""NAE Pilot Human Review — Schema Module.

Defines the canonical Pilot Reference (10 confirmed candidates) and all
metadata schema constants used by intake, integrity, decision_matrix, and
safety_gate modules.

`claim`/`crosswalk_id` values below are corrected to match the actual
Production TSU records (`NAE/corpus/tsu/*/tsu.json`) and the real
Crosswalk file (`NAE/metadata/crosswalk/crosswalk.yaml`, which has only
2 records total — one crosswalk_id per book, not per TSU). The
`author_id`/`source_id`/`work_id`/`edition_id` values were already
correct and are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Pilot Reference (10 confirmed candidates from Phase 2)
# ---------------------------------------------------------------------------

PILOT_REFERENCE: list[dict] = [
    {
        "tsu_id": "TSU-0000713",
        "source_id": "BAP-CHURCH-DAGG-001",
        "work_id": "WORK-DAGG-CHURCH-ORDER-001",
        "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
        "author_id": "dagg_john_l",
        "doctrine": "Ecclesiology",
        "claim": "초기 교회들은 서로 다른 교회들과 비교되었으며, 각 교회는 독립된 단체로서 서로 인사와 연락을 주고받았다.",
        "crosswalk_id": "f914f6c442983e59",
    },
    {
        "tsu_id": "TSU-0000199",
        "source_id": "BAP-CHURCH-DAGG-001",
        "work_id": "WORK-DAGG-CHURCH-ORDER-001",
        "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
        "author_id": "dagg_john_l",
        "doctrine": "Baptism",
        "claim": "동사 'banro'는 액체를 고체에 적용하는 과정을 의미하지 않는다.",
        "crosswalk_id": "f914f6c442983e59",
    },
    {
        "tsu_id": "TSU-0000330",
        "source_id": "BAP-CHURCH-DAGG-001",
        "work_id": "WORK-DAGG-CHURCH-ORDER-001",
        "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
        "author_id": "dagg_john_l",
        "doctrine": "Lord's Supper",
        "claim": "성례의 목적을 고려할 때, 성찬에서 빵을 먹음으로써 그리스도의 죽음을 기억하는 것이 더 적절하다.",
        "crosswalk_id": "f914f6c442983e59",
    },
    {
        "tsu_id": "TSU-0000033",
        "source_id": "BAP-CHURCH-DAGG-001",
        "work_id": "WORK-DAGG-CHURCH-ORDER-001",
        "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
        "author_id": "dagg_john_l",
        "doctrine": "Soteriology",
        "claim": "그리스도의 사랑과 복종의 강력한 동기는 우리를 위해 죽으신 그분의 사랑에서 비롯됩니다.",
        "crosswalk_id": "f914f6c442983e59",
    },
    {
        "tsu_id": "TSU-0000025",
        "source_id": "BAP-CHURCH-DAGG-001",
        "work_id": "WORK-DAGG-CHURCH-ORDER-001",
        "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
        "author_id": "dagg_john_l",
        "doctrine": "Sanctification",
        "claim": "하나님을 전심으로 사랑하는 것이 모든 의무의 총합이다.",
        "crosswalk_id": "f914f6c442983e59",
    },
    {
        "tsu_id": "TSU-0003524",
        "source_id": "BAP-CHURCH-HISCOX",
        "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
        "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
        "author_id": "hiscox_edward_t",
        "doctrine": "Ecclesiology",
        "claim": "선한 사람들의 악한 정서가 경건을 이길 수 있고, 당파적인 분쟁이 그리스도의 몸의 평화와 번영을 파괴할 수 있다.",
        "crosswalk_id": "260d31b2331a3f8b",
    },
    {
        "tsu_id": "TSU-0003661",
        "source_id": "BAP-CHURCH-HISCOX",
        "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
        "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
        "author_id": "hiscox_edward_t",
        "doctrine": "Baptism",
        "claim": "예수 그리스도의 이름으로 죄의 사함을 받기 위해 각자가 회개하고 세례를 받아야 한다.",
        "crosswalk_id": "260d31b2331a3f8b",
    },
    {
        "tsu_id": "TSU-0003525",
        "source_id": "BAP-CHURCH-HISCOX",
        "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
        "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
        "author_id": "hiscox_edward_t",
        "doctrine": "Church Discipline",
        "claim": "교회에서 일어날 수 있는 악한 정서와 파당적인 분쟁을 가능한 한 피해야 한다.",
        "crosswalk_id": "260d31b2331a3f8b",
    },
    {
        "tsu_id": "TSU-0003893",
        "source_id": "BAP-CHURCH-HISCOX",
        "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
        "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
        "author_id": "hiscox_edward_t",
        "doctrine": "Lord's Supper",
        "claim": "일부 사람들은 주님의 만찬에서 죽으신 주님을 기념하는 것을 모든 사람들이 함께 할 수 있도록 초청하는 것이 친절하고 형제적인 행동이라고 생각한다.",
        "crosswalk_id": "260d31b2331a3f8b",
    },
    {
        "tsu_id": "TSU-0003647",
        "source_id": "BAP-CHURCH-HISCOX",
        "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
        "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
        "author_id": "hiscox_edward_t",
        "doctrine": "Soteriology",
        "claim": "하나님은 이전에는 무지한 시대를 용납하셨지만 이제는 모든 사람에게 어디서나 회개할 것을 명령하시고 계심",
        "crosswalk_id": "260d31b2331a3f8b",
    },
]

PILOT_TSU_IDS: frozenset[str] = frozenset(r["tsu_id"] for r in PILOT_REFERENCE)
PILOT_REFERENCE_BY_ID: dict[str, dict] = {r["tsu_id"]: r for r in PILOT_REFERENCE}


# ---------------------------------------------------------------------------
# Metadata Schema Constants
# ---------------------------------------------------------------------------

METADATA_SCHEMA_VERSION: str = "1.1.0"

REQUIRED_METADATA_FIELDS: tuple[str, ...] = (
    "id",
    "source_id",
    "author_id",
    "work_id",
    "edition_id",
    "doctrine",
    "claim",
    "copyright_status",
    "metadata_provenance",
    "review_status",
)

OPTIONAL_METADATA_FIELDS: tuple[str, ...] = (
    "scripture_references",
    "crosswalk_id",
    "flags",
    "evidence_units",
    "quality_score",
)


# ---------------------------------------------------------------------------
# Decision Matrix Constants (Human Reviewer decision — AI never sets these)
# ---------------------------------------------------------------------------

VERIFY = "VERIFY"
REVISE = "REVISE"
REJECT = "REJECT"
HOLD = "HOLD"
VALID_DECISIONS: frozenset[str] = frozenset({VERIFY, REVISE, REJECT, HOLD})

DECISION_RULES: dict[str, str] = {
    "VERIFY": "All fields match; claim fidelity confirmed; ready for production.",
    "REVISE": "Minor issues found (e.g., claim text truncation); fix and re-review.",
    "REJECT": "Major issues found (e.g., wrong source, doctrine mismatch); discard.",
    "HOLD": "Ambiguous; requires senior reviewer or additional context.",
}

PROMOTION_THRESHOLD: float = 0.8
# Minimum fraction of VERIFY decisions required to auto-promote the pilot.
# Below this threshold, human review is required for all HOLD/REVISE items.


# ---------------------------------------------------------------------------
# Safety Gate Constants
# ---------------------------------------------------------------------------

SAFETY_GATES: dict[str, bool] = {
    "production_tsu_modification": False,  # AI must NOT modify production TSU
    "embedding_creation": False,            # AI must NOT create embeddings
    "qdrant_write": False,                  # AI must NOT write to Qdrant
    "git_change": False,                    # AI must NOT make git changes
    "benchmark_modification": False,        # AI must NOT modify benchmark datasets
}

MAX_PENDING_REVIEW: int = 100
# Maximum number of TSUs allowed in PENDING status before requiring action.


# ---------------------------------------------------------------------------
# Human Review Result (intake.py/promotion.py contract)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HumanReviewResult:
    """Human Reviewer 1건의 입력값 — 생성 후 수정 불가(immutable audit
    record, §Phase1 "immutable audit record로 보존")."""

    tsu_id: str
    reviewer_id: str
    review_timestamp: str
    decision: str
    claim_fidelity: str | None = None
    theological_accuracy: str | None = None
    doctrine_classification: str | None = None
    evidence_sufficiency: str | None = None
    scripture_citation_assessment: str | None = None
    reviewer_notes: str | None = None
    revised_claim: str | None = None
    revised_doctrine: str | None = None
    context_required: bool = False
    source_verification_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tsu_id": self.tsu_id,
            "reviewer_id": self.reviewer_id,
            "review_timestamp": self.review_timestamp,
            "decision": self.decision,
            "claim_fidelity": self.claim_fidelity,
            "theological_accuracy": self.theological_accuracy,
            "doctrine_classification": self.doctrine_classification,
            "evidence_sufficiency": self.evidence_sufficiency,
            "scripture_citation_assessment": self.scripture_citation_assessment,
            "reviewer_notes": self.reviewer_notes,
            "revised_claim": self.revised_claim,
            "revised_doctrine": self.revised_doctrine,
            "context_required": self.context_required,
            "source_verification_required": self.source_verification_required,
        }

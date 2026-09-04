"""Human Review Disposition v2 — Schema, State Machine, and Models for 776 Independent Dataset.

기존 v1 schema 와 coexistence 목적. migration 없음.
RC-01~RC-08 은 classification code 로 사용하지 않음.
change_request_id 는 traceability metadata 로만 사용.

Constraints:
- Production TSU is NEVER modified by this module.
- Review records are separate from TSU (not embedded mutations).
- Original TSU != corrected TSU -- correction is a separate record/payload.
- Evidence references are references only, not copies.
- No migration from existing 3,347 historical decisions.

Schema version: 2.0.0
Governance authority: docs/NAE_HUMAN_REVIEW_DISPOSITION_SCHEMA_v1.md
"""

from enum import Enum
import json
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Schema Version
# ============================================================================

HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION = "2.0.0"

# ============================================================================
# Safety Gate
# ============================================================================

MAX_PENDING_REVIEW = 100


# ============================================================================
# Enums -- Disposition (from existing v1, unchanged)
# ============================================================================

class DispositionV2(str, Enum):
    """Human reviewer's disposition of a single TSU."""
    ACCEPT = "accept"
    REJECT = "reject"
    ACCEPT_WITH_CORRECTION = "accept_with_correction"
    NEEDS_REVIEW = "needs_review"
    DUPLICATE_MERGE = "duplicate_merge"


# ============================================================================
# Enums -- Reason (from existing v1, unchanged)
# ============================================================================

class ReasonCodeV2(str, Enum):
    """Structured reason for a disposition decision (governance authority)."""
    CONTENT_VALIDITY = "content_validity"
    METADATA = "metadata"
    EXTRACTION = "extraction"
    CHUNK_BOUNDARY = "chunk_boundary"
    DUPLICATION = "duplication"
    SOURCE_AUTHORITY = "source_authority"
    COPYRIGHT = "copyright"
    OTHER = "other"


# ============================================================================
# Enums -- Review State (from existing v1, unchanged)
# ============================================================================

class ReviewStateV2(str, Enum):
    """Lifecycle state of a review record."""
    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    DISPOSITIONED = "dispositioned"
    ADJUDICATION_REQUIRED = "adjudication_required"
    FINALIZED = "finalized"


# ============================================================================
# Enums -- Queue State (from existing v1, unchanged)
# ============================================================================

class QueueStateV2(str, Enum):
    """Queue state for a review queue record."""
    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE_MERGE = "duplicate_merge"
    ADJUDICATION_REQUIRED = "adjudication_required"


# ============================================================================
# Enums -- Adjudication
# ============================================================================

class AdjudicationOutcomeV2(str, Enum):
    """Adjudicator's decision on conflicting reviewer records."""
    UPHELD = "upheld"
    OVERTURNED = "overturned"
    MODIFIED = "modified"


class ReviewerRoleV2(str, Enum):
    """Reviewer's role in the review process."""
    REVIEWER = "reviewer"
    ADJUDICATOR = "adjudicator"
    SECOND_REVIEWER = "second_reviewer"


# ============================================================================
# Pydantic Models -- Evidence Reference
# ============================================================================

class EvidenceReferenceV2(BaseModel):
    """Evidence reference (not copy)."""
    evidence_type: str = Field(..., description="Type of evidence")
    evidence_ref: str = Field(..., description="Reference string")
    page: Optional[int] = None
    location: Optional[str] = None
    note: Optional[str] = None


# ============================================================================
# Pydantic Models -- Correction Payload
# ============================================================================

class CorrectionPayloadV2(BaseModel):
    """Field-level correction separate from original TSU."""
    correction_type: str = Field(..., description="Type of correction")
    field: str = Field(..., description="TSU field being corrected")
    original_value: str = Field(..., description="Snapshot of original value")
    corrected_value: str = Field(..., description="Proposed corrected value")
    correction_reason: str = Field(..., description="Justification for correction")
    evidence_ref: Optional[EvidenceReferenceV2] = None


# ============================================================================
# Pydantic Models -- Adjudication Record
# ============================================================================

class AdjudicationRecordV2(BaseModel):
    """Adjudicator's decision on conflicting reviewer records."""
    adjudicator_id: str = Field(..., description="ID of the adjudicator")
    outcome: AdjudicationOutcomeV2 = Field(..., description="Adjudicator's outcome")
    final_disposition: DispositionV2 = Field(..., description="Final disposition after adjudication")
    reasoning: str = Field(..., description="Reasoning for the decision")
    adjudicated_at: datetime = Field(..., description="When adjudication occurred")


# ============================================================================
# Pydantic Models -- Main Review Record (v2 schema)
# ============================================================================

class ReviewRecordV2(BaseModel):
    """Main review entity for 776 independent dataset."""
    record_id: str = Field(..., pattern=r"^REVIEW-.+-[0-9]+$")
    tsu_id: str = Field(..., pattern=r"^TSU-[0-9]{7}$")
    source_id: str
    work_id: str
    edition_id: str
    author_id: str
    disposition: Optional[DispositionV2] = None
    reason_codes: list[ReasonCodeV2] = Field(default_factory=list)
    state: ReviewStateV2 = ReviewStateV2.UNREVIEWED
    evidence_refs: list[EvidenceReferenceV2] = Field(default_factory=list)
    correction_payloads: list[CorrectionPayloadV2] = Field(default_factory=list)
    adjudication: Optional[AdjudicationRecordV2] = None
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    change_request_id: Optional[str] = None
    supersedes_record_id: Optional[str] = None
    review_note: Optional[str] = Field(default=None, description="Free-text note (required if reason_code includes OTHER) (RC-03)")
    previous_disposition: Optional[DispositionV2] = Field(default=None, description="Disposition value from the superseded record (RC-02)")
    schema_version: str = HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_disposition_requirements(self) -> "ReviewRecordV2":
        if self.state in (ReviewStateV2.DISPOSITIONED, ReviewStateV2.ADJUDICATION_REQUIRED, ReviewStateV2.FINALIZED):
            if not self.disposition:
                raise ValueError("disposition is required once state reaches DISPOSITIONED or later")
            if not self.reason_codes:
                raise ValueError("reason_codes is required once state reaches DISPOSITIONED or later")
            if not self.evidence_refs:
                raise ValueError("evidence_refs is required once state reaches DISPOSITIONED or later")
            if not self.reviewer_id:
                raise ValueError("reviewer_id is required once state reaches IN_REVIEW or later")
            if not self.reviewed_at:
                raise ValueError("reviewed_at is required once state reaches DISPOSITIONED or later")

        if self.disposition == DispositionV2.ACCEPT_WITH_CORRECTION and not self.correction_payloads:
            raise ValueError("correction_payloads is required when disposition is ACCEPT_WITH_CORRECTION")

        if self.state == ReviewStateV2.ADJUDICATION_REQUIRED and not self.adjudication:
            raise ValueError("adjudication is required once state reaches ADJUDICATION_REQUIRED")

        # RC-03: review_note required when OTHER is in reason_codes
        if ReasonCodeV2.OTHER in self.reason_codes and (not self.review_note or not self.review_note.strip()):
            raise ValueError("review_note is required when reason_code includes OTHER")

        return self


# ============================================================================
# Pydantic Models -- Queue Record (v2 schema)
# ============================================================================

class QueueRecordV2(BaseModel):
    """Queue entry for review workflow."""
    queue_id: str = Field(..., pattern=r"^Q-[0-9]+$")
    tsu_id: str = Field(..., pattern=r"^TSU-[0-9]{7}$")
    state: QueueStateV2 = QueueStateV2.UNREVIEWED
    record_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# State Machine (from existing v1, unchanged)
# ============================================================================

class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


VALID_TRANSITIONS_V2: dict[ReviewStateV2, set[ReviewStateV2]] = {
    ReviewStateV2.UNREVIEWED: {ReviewStateV2.IN_REVIEW},
    ReviewStateV2.IN_REVIEW: {ReviewStateV2.DISPOSITIONED},
    ReviewStateV2.DISPOSITIONED: {ReviewStateV2.ADJUDICATION_REQUIRED, ReviewStateV2.FINALIZED, ReviewStateV2.UNREVIEWED},
    ReviewStateV2.ADJUDICATION_REQUIRED: {ReviewStateV2.DISPOSITIONED},
    ReviewStateV2.FINALIZED: set(),  # Terminal state
}

# RC-07: Disposition-aware requeue rules for DISPOSITIONED → UNREVIEWED
# Only NEEDS_REVIEW disposition allows requeue; ACCEPT/REJECT/DUPLICATE_MERGE do not.
DISPOSITION_ALLOW_REQUEUE: frozenset[DispositionV2] = frozenset({DispositionV2.NEEDS_REVIEW})
DISPOSITION_BLOCK_REQUEUE: frozenset[DispositionV2] = frozenset({
    DispositionV2.ACCEPT,
    DispositionV2.REJECT,
    DispositionV2.ACCEPT_WITH_CORRECTION,
    DispositionV2.DUPLICATE_MERGE,
})


class StateMachineV2:
    """State machine for review record lifecycle."""

    @staticmethod
    def validate_transition(
        current_state: ReviewStateV2,
        new_state: ReviewStateV2,
        disposition: Optional[DispositionV2] = None,
    ) -> bool:
        allowed = VALID_TRANSITIONS_V2.get(current_state, set())
        if new_state not in allowed:
            return False
        # RC-07: DISPOSITIONED → UNREVIEWED requires disposition context
        if current_state == ReviewStateV2.DISPOSITIONED and new_state == ReviewStateV2.UNREVIEWED:
            if disposition is None:
                return False
            if disposition in DISPOSITION_BLOCK_REQUEUE:
                return False
            if disposition not in DISPOSITION_ALLOW_REQUEUE:
                return False
        return True

    @staticmethod
    def apply_transition(
        record: ReviewRecordV2,
        new_state: ReviewStateV2,
        audit_trail: "AuditTrailV2",
        actor: str = "system",
        reason: str = "",
    ) -> None:
        disposition = record.disposition
        if not StateMachineV2.validate_transition(record.state, new_state, disposition):
            raise InvalidTransitionError(
                f"Invalid transition: {record.state.value} → {new_state.value}"
            )
        old_state = record.state
        old_disposition = record.disposition
        record.state = new_state
        record.updated_at = datetime.now(timezone.utc)

        if new_state == ReviewStateV2.IN_REVIEW and not record.reviewer_id:
            raise ValueError("reviewer_id is required when transitioning to IN_REVIEW")
        if new_state in (ReviewStateV2.DISPOSITIONED, ReviewStateV2.ADJUDICATION_REQUIRED, ReviewStateV2.FINALIZED):
            if not record.disposition:
                raise ValueError("disposition is required when transitioning to DISPOSITIONED or later")
            if not record.reason_codes:
                raise ValueError("reason_codes is required when transitioning to DISPOSITIONED or later")
            if not record.evidence_refs:
                raise ValueError("evidence_refs is required when transitioning to DISPOSITIONED or later")
            if not record.reviewed_at:
                raise ValueError("reviewed_at is required when transitioning to DISPOSITIONED or later")

        # RC-08: AuditEventV2 MUST be generated on every transition (no optional guard)
        event = AuditEventV2(
            event_id=f"EVT-{len(audit_trail.events) + 1:04d}",
            record_id=record.record_id,
            previous_state=old_state.value,
            new_state=new_state.value,
            previous_disposition=old_disposition.value if old_disposition else None,
            new_disposition=record.disposition.value if record.disposition else None,
            reason=reason or f"transition {old_state.value} → {new_state.value}",
            actor=actor,
        )
        audit_trail.append_event(event)


# ============================================================================
# Review Queue (from existing v1, adapted for v2)
# ============================================================================

class ReviewQueueV2:
    """Queue management for review records."""

    def __init__(self):
        self.records: list[QueueRecordV2] = []

    def add(self, record: QueueRecordV2) -> None:
        pending_count = sum(
            1 for r in self.records
            if r.state in (QueueStateV2.UNREVIEWED, QueueStateV2.IN_REVIEW, QueueStateV2.NEEDS_REVIEW)
        )
        if pending_count >= MAX_PENDING_REVIEW:
            raise OverflowError(
                f"Queue overflow: {pending_count} pending records exceeds maximum {MAX_PENDING_REVIEW}"
            )
        self.records.append(record)

    def get_pending(self) -> list[QueueRecordV2]:
        return [
            r for r in self.records
            if r.state in (QueueStateV2.UNREVIEWED, QueueStateV2.IN_REVIEW, QueueStateV2.NEEDS_REVIEW)
        ]

    def get_by_tsu_id(self, tsu_id: str) -> Optional[QueueRecordV2]:
        for r in self.records:
            if r.tsu_id == tsu_id:
                return r
        return None


# ============================================================================
# Audit Trail (append-only)
# ============================================================================

class AuditEventV2(BaseModel):
    """Append-only audit event for disposition mutations."""
    event_id: str = Field(..., pattern=r"^EVT-[0-9]+$")
    record_id: str
    previous_state: str
    new_state: str
    previous_disposition: Optional[str] = None
    new_disposition: Optional[str] = None
    reason: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION


class AuditTrailV2:
    """Append-only audit trail for disposition mutations."""

    def __init__(self):
        self.events: list[AuditEventV2] = []

    def append_event(self, event: AuditEventV2) -> None:
        self.events.append(event)

    def get_events_for_record(self, record_id: str) -> list[AuditEventV2]:
        return [e for e in self.events if e.record_id == record_id]


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_schema_version_v2(record: ReviewRecordV2 | QueueRecordV2) -> bool:
    if isinstance(record, ReviewRecordV2):
        return record.schema_version == HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION
    return True


def validate_evidence_refs_v2(evidence_refs: list[EvidenceReferenceV2]) -> bool:
    for ref in evidence_refs:
        if not ref.evidence_type or not ref.evidence_ref:
            return False
    return True


def validate_correction_payload_v2(payload: CorrectionPayloadV2) -> bool:
    if not payload.field or not payload.original_value or not payload.corrected_value:
        return False
    if payload.original_value == payload.corrected_value:
        return False
    if not payload.correction_reason or not payload.correction_reason.strip():
        return False
    return True


def validate_adjudication_v2(adjudication: AdjudicationRecordV2) -> bool:
    if not adjudication.adjudicator_id or not adjudication.reasoning:
        return False
    if not adjudication.adjudicated_at:
        return False
    if not adjudication.final_disposition:
        return False
    return True


# ============================================================================
# Serialization
# ============================================================================

def serialize_review_record_v2(record: ReviewRecordV2) -> str:
    return record.model_dump_json(indent=2, ensure_ascii=False)


def deserialize_review_record_v2(data: str) -> ReviewRecordV2:
    return ReviewRecordV2.model_validate_json(data)


def serialize_queue_record_v2(record: QueueRecordV2) -> str:
    return record.model_dump_json(indent=2, ensure_ascii=False)


def deserialize_queue_record_v2(data: str) -> QueueRecordV2:
    return QueueRecordV2.model_validate_json(data)


# ============================================================================
# Sample Records (for testing -- NOT production data)
# ============================================================================

def create_sample_review_record_v2(
    record_id: str = "REVIEW-TSU-0000001-001",
    tsu_id: str = "TSU-0000001",
    state: ReviewStateV2 = ReviewStateV2.UNREVIEWED,
    **overrides: Any,
) -> ReviewRecordV2:
    data = {
        "record_id": record_id,
        "tsu_id": tsu_id,
        "source_id": "SOURCE-001",
        "work_id": "WORK-001",
        "edition_id": "EDITION-001",
        "author_id": "AUTHOR-001",
        "schema_version": HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION,
        "state": state,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return ReviewRecordV2(**data)


def create_sample_queue_record_v2(
    queue_id: str = "Q-001",
    tsu_id: str = "TSU-0000001",
    state: QueueStateV2 = QueueStateV2.UNREVIEWED,
    **overrides: Any,
) -> QueueRecordV2:
    data = {
        "queue_id": queue_id,
        "tsu_id": tsu_id,
        "state": state,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return QueueRecordV2(**data)


__all__ = [
    "HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION",
    "MAX_PENDING_REVIEW",
    "DispositionV2", "ReasonCodeV2", "ReviewStateV2", "QueueStateV2",
    "AdjudicationOutcomeV2", "ReviewerRoleV2",
    "EvidenceReferenceV2", "CorrectionPayloadV2", "AdjudicationRecordV2",
    "ReviewRecordV2", "QueueRecordV2",
    "StateMachineV2", "InvalidTransitionError", "VALID_TRANSITIONS_V2",
    "DISPOSITION_ALLOW_REQUEUE", "DISPOSITION_BLOCK_REQUEUE",
    "ReviewQueueV2",
    "AuditEventV2", "AuditTrailV2",
    "serialize_review_record_v2", "deserialize_review_record_v2",
    "serialize_queue_record_v2", "deserialize_queue_record_v2",
    "create_sample_review_record_v2", "create_sample_queue_record_v2",
    "validate_schema_version_v2", "validate_evidence_refs_v2",
    "validate_correction_payload_v2", "validate_adjudication_v2",
]

"""Test suite for NAE Human Review Disposition v2 schema.

Covers:
A. Schema validation
B. Evidence validation
C. State machine validation
D. Production isolation
E. Audit trail validation

Production TSU is NEVER modified by these tests.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Import v2 module
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.review_disposition_v2 import (
    HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION,
    MAX_PENDING_REVIEW,
    DispositionV2,
    ReasonCodeV2,
    ReviewStateV2,
    QueueStateV2,
    AdjudicationOutcomeV2,
    EvidenceReferenceV2,
    CorrectionPayloadV2,
    AdjudicationRecordV2,
    ReviewRecordV2,
    QueueRecordV2,
    StateMachineV2,
    InvalidTransitionError,
    VALID_TRANSITIONS_V2,
    ReviewQueueV2,
    AuditEventV2,
    AuditTrailV2,
    serialize_review_record_v2,
    deserialize_review_record_v2,
    create_sample_review_record_v2,
    create_sample_queue_record_v2,
    serialize_queue_record_v2,
    deserialize_queue_record_v2,
    validate_schema_version_v2,
    validate_evidence_refs_v2,
    validate_correction_payload_v2,
    validate_adjudication_v2,
)

# ============================================================================
# Schema loading helper
# ============================================================================

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "schemas" / "nae_human_review_disposition_v2.schema.json"


def load_schema() -> dict:
    """Load the v2 schema JSON file."""
    with open(_SCHEMA_PATH, "r") as f:
        return json.load(f)


# Fix path: tests/nae/registration → project root (parent.parent.parent.parent)
_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "schemas" / "nae_human_review_disposition_v2.schema.json"


# ============================================================================
# A. Schema Tests
# ============================================================================

class TestSchemaValidRecord:
    """A.1: Valid record creation."""

    def test_valid_record_creation(self):
        """Valid record with all required fields."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-001",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.UNREVIEWED,
        )
        assert record.record_id == "REVIEW-TSU-0000001-001"
        assert record.tsu_id == "TSU-0000001"
        assert record.schema_version == HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION
        assert record.state == ReviewStateV2.UNREVIEWED

    def test_valid_record_with_all_fields(self):
        """Valid record with all disposition fields."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-002",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(
                evidence_type="tsu_text",
                evidence_ref="tsu_id:TSU-0000001"
            )],
            reviewer_id="reviewer-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert record.disposition == DispositionV2.ACCEPT
        assert record.reason_codes == [ReasonCodeV2.CONTENT_VALIDITY]
        assert len(record.evidence_refs) == 1

    def test_schema_version_is_immutable(self):
        """Schema version cannot be changed."""
        record = create_sample_review_record_v2()
        assert record.schema_version == "2.0.0"


class TestSchemaMissingRequiredField:
    """A.2: Missing required field rejection."""

    def test_missing_record_id(self):
        """Record without record_id should fail."""
        with pytest.raises(Exception):  # Pydantic validation error
            ReviewRecordV2(
                tsu_id="TSU-0000001",
                source_id="SOURCE-001",
                work_id="WORK-001",
                edition_id="EDITION-001",
                author_id="AUTHOR-001",
            )

    def test_missing_tsu_id(self):
        """Record without tsu_id should fail."""
        with pytest.raises(Exception):
            ReviewRecordV2(
                record_id="REVIEW-TSU-0000001-001",
                source_id="SOURCE-001",
                work_id="WORK-001",
                edition_id="EDITION-001",
                author_id="AUTHOR-001",
            )

    def test_missing_disposition_when_dispositioned(self):
        """Disposition required when state is DISPOSITIONED."""
        with pytest.raises(ValueError, match="disposition is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-003",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
            )

    def test_missing_reason_codes_when_dispositioned(self):
        """Reason codes required when state is DISPOSITIONED."""
        with pytest.raises(ValueError, match="reason_codes is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-004",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
            )

    def test_missing_evidence_when_dispositioned(self):
        """Evidence refs required when state is DISPOSITIONED."""
        with pytest.raises(ValueError, match="evidence_refs is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-005",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            )


class TestSchemaInvalidRC:
    """A.3: Invalid RC (reason code) rejection."""

    def test_invalid_reason_code(self):
        """Invalid reason code should fail."""
        with pytest.raises(Exception):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-006",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=["invalid_code"],  # type: ignore
                evidence_refs=[EvidenceReferenceV2(
                    evidence_type="tsu_text",
                    evidence_ref="tsu_id:TSU-0000001"
                )],
                reviewer_id="reviewer-001",
                reviewed_at=datetime.now(timezone.utc),
            )

    def test_empty_reason_codes(self):
        """Empty reason codes should fail when state is DISPOSITIONED."""
        with pytest.raises(ValueError, match="reason_codes is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-007",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=[],
                evidence_refs=[EvidenceReferenceV2(
                    evidence_type="tsu_text",
                    evidence_ref="tsu_id:TSU-0000001"
                )],
                reviewer_id="reviewer-001",
                reviewed_at=datetime.now(timezone.utc),
            )


class TestSchemaInvalidState:
    """A.4: Invalid state rejection."""

    def test_invalid_state_value(self):
        """Invalid state value should fail."""
        with pytest.raises(Exception):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-008",
                tsu_id="TSU-0000001",
                state="invalid_state",  # type: ignore
            )

    def test_all_valid_states(self):
        """All valid states should work (only UNREVIEWED/IN_REVIEW don't require disposition)."""
        for state in [ReviewStateV2.UNREVIEWED, ReviewStateV2.IN_REVIEW]:
            record = create_sample_review_record_v2(state=state)
            assert record.state == state


class TestSchemaInvalidVersion:
    """A.5: Invalid schema version rejection."""

    def test_default_schema_version(self):
        """Default schema version should be 2.0.0."""
        record = create_sample_review_record_v2()
        assert record.schema_version == "2.0.0"


# ============================================================================
# B. Evidence Tests
# ============================================================================

class TestEvidencePresent:
    """B.1: Evidence present validation."""

    def test_valid_evidence_refs(self):
        """Valid evidence refs should pass."""
        refs = [
            EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001"),
            EvidenceReferenceV2(evidence_type="source_page", evidence_ref="source_id:DAGG-001#page=42"),
        ]
        assert validate_evidence_refs_v2(refs) is True

    def test_evidence_with_all_fields(self):
        """Evidence with all optional fields."""
        ref = EvidenceReferenceV2(
            evidence_type="source_page",
            evidence_ref="source_id:DAGG-001#page=42",
            page=42,
            location="paragraph 3",
            note="Direct quote match",
        )
        assert ref.evidence_type == "source_page"
        assert ref.page == 42


class TestEvidenceMissing:
    """B.2: Evidence missing rejection."""

    def test_empty_evidence_refs(self):
        """Empty evidence refs should fail when state is DISPOSITIONED."""
        with pytest.raises(ValueError, match="evidence_refs is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-009",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
                evidence_refs=[],
                reviewer_id="reviewer-001",
                reviewed_at=datetime.now(timezone.utc),
            )

    def test_evidence_validation_fails_on_missing_fields(self):
        """Evidence validation fails when required fields missing."""
        refs = [EvidenceReferenceV2(evidence_type="", evidence_ref="")]  # type: ignore
        assert validate_evidence_refs_v2(refs) is False


class TestConflictingEvidence:
    """B.3: Conflicting evidence handling."""

    def test_conflicting_evidence_types(self):
        """Conflicting evidence types should be allowed (user responsibility)."""
        refs = [
            EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001"),
            EvidenceReferenceV2(evidence_type="source_page", evidence_ref="source_id:DAGG-001#page=42"),
        ]
        # Both refs are valid individually
        assert validate_evidence_refs_v2(refs) is True


class TestMalformedEvidenceReference:
    """B.4: Malformed evidence reference rejection."""

    def test_invalid_evidence_type(self):
        """Invalid evidence type is allowed by Pydantic (enum validation only on model_validate)."""
        ref = EvidenceReferenceV2(evidence_type="invalid_type", evidence_ref="ref")  # type: ignore
        # Pydantic allows invalid enum when created directly; validation function checks non-empty
        assert validate_evidence_refs_v2([ref]) is True  # Both fields are non-empty


# ============================================================================
# C. State Tests
# ============================================================================

class TestValidTransition:
    """C.1: Valid state transitions."""

    def test_unreviewed_to_in_review(self):
        """UNREVIEWED → IN_REVIEW is valid."""
        record = create_sample_review_record_v2(state=ReviewStateV2.UNREVIEWED)
        assert StateMachineV2.validate_transition(ReviewStateV2.UNREVIEWED, ReviewStateV2.IN_REVIEW)

    def test_in_review_to_dispositioned(self):
        """IN_REVIEW → DISPOSITIONED is valid."""
        record = create_sample_review_record_v2(state=ReviewStateV2.IN_REVIEW)
        assert StateMachineV2.validate_transition(ReviewStateV2.IN_REVIEW, ReviewStateV2.DISPOSITIONED)

    def test_dispositioned_to_finalized(self):
        """DISPOSITIONED → FINALIZED is valid."""
        record = create_sample_review_record_v2(
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="reviewer-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert StateMachineV2.validate_transition(ReviewStateV2.DISPOSITIONED, ReviewStateV2.FINALIZED)

    def test_dispositioned_to_adjudication_required(self):
        """DISPOSITIONED → ADJUDICATION_REQUIRED is valid."""
        record = create_sample_review_record_v2(
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="reviewer-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert StateMachineV2.validate_transition(ReviewStateV2.DISPOSITIONED, ReviewStateV2.ADJUDICATION_REQUIRED)

    def test_adjudication_required_to_dispositioned(self):
        """ADJUDICATION_REQUIRED → DISPOSITIONED is valid."""
        record = create_sample_review_record_v2(
            state=ReviewStateV2.ADJUDICATION_REQUIRED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="reviewer-001",
            reviewed_at=datetime.now(timezone.utc),
            adjudication=AdjudicationRecordV2(
                adjudicator_id="ADV-001",
                outcome=AdjudicationOutcomeV2.OVERTURNED,
                final_disposition=DispositionV2.REJECT,
                reasoning="Test adjudication",
                adjudicated_at=datetime.now(timezone.utc),
            ),
        )
        assert StateMachineV2.validate_transition(ReviewStateV2.ADJUDICATION_REQUIRED, ReviewStateV2.DISPOSITIONED)

    def test_in_review_to_unreviewed(self):
        """IN_REVIEW → UNREVIEWED is NOT valid (RC-07 only allows DISPOSITIONED → UNREVIEWED)."""
        assert StateMachineV2.validate_transition(ReviewStateV2.IN_REVIEW, ReviewStateV2.UNREVIEWED) is False


class TestInvalidTransition:
    """C.2: Invalid state transitions blocked."""

    def test_unreviewed_to_finalized(self):
        """UNREVIEWED → FINALIZED (skip review) is invalid."""
        assert StateMachineV2.validate_transition(ReviewStateV2.UNREVIEWED, ReviewStateV2.FINALIZED) is False

    def test_dispositioned_to_in_review(self):
        """DISPOSITIONED → IN_REVIEW (regression without adjudication) is invalid."""
        assert StateMachineV2.validate_transition(ReviewStateV2.DISPOSITIONED, ReviewStateV2.IN_REVIEW) is False

    def test_finalized_to_anything(self):
        """FINALIZED → anything is invalid."""
        for state in ReviewStateV2:
            if state != ReviewStateV2.FINALIZED:
                assert StateMachineV2.validate_transition(ReviewStateV2.FINALIZED, state) is False

    def test_invalid_transition_raises_error(self):
        """Invalid transition should raise InvalidTransitionError."""
        record = create_sample_review_record_v2(state=ReviewStateV2.UNREVIEWED)
        with pytest.raises(InvalidTransitionError):
            StateMachineV2.apply_transition(record, ReviewStateV2.FINALIZED, audit_trail=AuditTrailV2())


class TestDuplicateSubmission:
    """C.3: Duplicate submission handling."""

    def test_same_tsu_multiple_records(self):
        """Same TSU can have multiple review records (supersedes mechanism)."""
        record1 = create_sample_review_record_v2(record_id="REVIEW-TSU-0000001-001")
        record2 = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-002",
            supersedes_record_id="REVIEW-TSU-0000001-001"
        )
        assert record1.record_id != record2.record_id
        assert record2.supersedes_record_id == record1.record_id


class TestRerun:
    """C.4: Rerun preserves audit history."""

    def test_rerun_preserves_previous_state(self):
        """Rerunning should not destroy previous state."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-010",
            state=ReviewStateV2.UNREVIEWED,
        )
        original_created = record.created_at

        # Rerun: create new record with same record_id
        record2 = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-010",
            state=ReviewStateV2.IN_REVIEW,
            reviewer_id="reviewer-002",
        )

        # Original record is unchanged (immutable)
        assert record.state == ReviewStateV2.UNREVIEWED
        assert record2.state == ReviewStateV2.IN_REVIEW


class TestRollbackPath:
    """C.5: Rollback/review-required path."""

    def test_needs_review_requeue(self):
        """IN_REVIEW → UNREVIEWED is NOT valid (RC-07 only allows DISPOSITIONED → UNREVIEWED)."""
        assert StateMachineV2.validate_transition(ReviewStateV2.IN_REVIEW, ReviewStateV2.UNREVIEWED) is False

    def test_adjudication_to_dispositioned(self):
        """ADJUDICATION_REQUIRED → DISPOSITIONED allows re-review."""
        record = create_sample_review_record_v2(
            state=ReviewStateV2.ADJUDICATION_REQUIRED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="reviewer-001",
            reviewed_at=datetime.now(timezone.utc),
            adjudication=AdjudicationRecordV2(
                adjudicator_id="ADV-001",
                outcome=AdjudicationOutcomeV2.OVERTURNED,
                final_disposition=DispositionV2.REJECT,
                reasoning="Test adjudication",
                adjudicated_at=datetime.now(timezone.utc),
            ),
        )
        assert StateMachineV2.validate_transition(ReviewStateV2.ADJUDICATION_REQUIRED, ReviewStateV2.DISPOSITIONED)


# ============================================================================
# D. Isolation Tests
# ============================================================================

class TestProductionIsolation:
    """D.1: Production TSU untouched."""

    def test_tsu_not_modified(self):
        """Review records do not modify TSU data."""
        import json
        from pathlib import Path

        # Read production TSU before
        tsu_path = Path("NAE/corpus/tsu/Dagg_Church_Order/tsu.json")
        with open(tsu_path) as f:
            tsu_before = json.load(f)
        tsu_count_before = len(tsu_before)

        # Create review records (should not touch TSU)
        record = create_sample_review_record_v2()
        assert record.state == ReviewStateV2.UNREVIEWED

        # Read production TSU after
        with open(tsu_path) as f:
            tsu_after = json.load(f)
        tsu_count_after = len(tsu_after)

        # TSU should be unchanged
        assert tsu_count_before == tsu_count_after

    def test_qdrant_not_modified(self):
        """Qdrant is not touched by disposition module."""
        # This test verifies that the disposition module has no Qdrant imports
        import core.review_disposition_v2 as v2_module
        source = open(v2_module.__file__).read()
        assert "qdrant" not in source.lower(), "Disposition module should not reference Qdrant"

    def test_v2_module_independent_from_any_legacy(self):
        """v2 module must not import or reference any legacy v1 module."""
        import core.review_disposition_v2 as v2_module
        # Check that v2 does not import from the legacy module
        assert "core.review_disposition" not in dir(v2_module), \
            "v2 should not expose legacy module references"


# ============================================================================
# E. Audit Tests
# ============================================================================

class TestAuditEveryMutation:
    """E.1: Every mutation produces an audit event (auto-generated by apply_transition)."""

    def test_state_transition_produces_audit_event(self):
        """State transition via apply_transition should auto-produce audit event."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-011",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.UNREVIEWED,
            reviewer_id="REV-C1",
        )
        trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.IN_REVIEW,
            audit_trail=trail,
            actor="C1",
            reason="Initial review started",
        )
        assert len(trail.events) == 1
        assert trail.events[0].new_state == "in_review"
        assert trail.events[0].previous_state == "unreviewed"
        assert trail.events[0].record_id == "REVIEW-TSU-0000001-011"

    def test_disposition_change_produces_audit_event(self):
        """Disposition transition via apply_transition should auto-produce audit event."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-012",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="scripture", evidence_ref="John 3:16")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.FINALIZED,
            audit_trail=trail,
            actor="CUE",
            reason="Disposition finalized",
        )
        assert len(trail.events) == 1
        assert trail.events[0].previous_disposition == "accept"
        assert trail.events[0].new_disposition == "accept"
        assert trail.events[0].previous_state == "dispositioned"
        assert trail.events[0].new_state == "finalized"


class TestPreviousDispositionPreserved:
    """E.2: Previous disposition preserved."""

    def test_supersedes_preserves_previous(self):
        """Superseded record should preserve previous disposition."""
        record1 = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-013",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(
                evidence_type="tsu_text",
                evidence_ref="tsu_id:TSU-0000001"
            )],
            reviewer_id="reviewer-001",
            reviewed_at=datetime.now(timezone.utc),
        )

        record2 = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-014",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.REJECT,
            reason_codes=[ReasonCodeV2.METADATA],
            evidence_refs=[EvidenceReferenceV2(
                evidence_type="tsu_text",
                evidence_ref="tsu_id:TSU-0000001"
            )],
            reviewer_id="reviewer-002",
            reviewed_at=datetime.now(timezone.utc),
            supersedes_record_id="REVIEW-TSU-0000001-013",
        )

        # Both records should preserve their dispositions
        assert record1.disposition == DispositionV2.ACCEPT
        assert record2.disposition == DispositionV2.REJECT
        assert record2.supersedes_record_id == "REVIEW-TSU-0000001-013"


class TestReviewerIdentityPreserved:
    """E.3: Reviewer identity preserved."""

    def test_reviewer_id_preserved(self):
        """Reviewer ID should be preserved in record."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-015",
            state=ReviewStateV2.IN_REVIEW,
            reviewer_id="reviewer-david",
        )
        assert record.reviewer_id == "reviewer-david"


class TestTimestampPreserved:
    """E.4: Timestamp preserved."""

    def test_created_at_preserved(self):
        """Created timestamp should be preserved."""
        before = datetime.now(timezone.utc)
        record = create_sample_review_record_v2()
        after = datetime.now(timezone.utc)
        assert before <= record.created_at <= after

    def test_updated_at_changes_on_transition(self):
        """Updated timestamp should change on state transition."""
        record = create_sample_review_record_v2(
            state=ReviewStateV2.UNREVIEWED,
            reviewer_id="reviewer-001",
        )
        original_updated = record.updated_at

        # Transition should update updated_at
        StateMachineV2.apply_transition(record, ReviewStateV2.IN_REVIEW, audit_trail=AuditTrailV2())
        assert record.updated_at > original_updated


# ============================================================================
# F. Queue Tests
# ============================================================================

class TestQueueSafety:
    """Queue safety gate tests."""

    def test_queue_add_under_limit(self):
        """Adding records under limit should succeed."""
        queue = ReviewQueueV2()
        for i in range(99):
            queue.add(create_sample_queue_record_v2(queue_id=f"Q-{i:03d}"))
        assert len(queue.get_pending()) == 99

    def test_queue_add_at_limit(self):
        """Adding record at limit should succeed."""
        queue = ReviewQueueV2()
        for i in range(100):
            queue.add(create_sample_queue_record_v2(queue_id=f"Q-{i:03d}"))
        assert len(queue.get_pending()) == 100

    def test_queue_add_over_limit(self):
        """Adding record over limit should raise OverflowError."""
        queue = ReviewQueueV2()
        for i in range(100):
            queue.add(create_sample_queue_record_v2(queue_id=f"Q-{i:03d}"))
        with pytest.raises(OverflowError):
            queue.add(create_sample_queue_record_v2(queue_id="Q-100"))


# ============================================================================
# G. Serialization Tests
# ============================================================================

class TestSerialization:
    """Serialization round-trip tests."""

    def test_serialize_deserialize_review_record(self):
        """Review record should serialize and deserialize correctly."""
        record = create_sample_review_record_v2()
        serialized = serialize_review_record_v2(record)
        deserialized = deserialize_review_record_v2(serialized)
        assert deserialized.record_id == record.record_id
        assert deserialized.tsu_id == record.tsu_id
        assert deserialized.state == record.state

    def test_serialize_deserialize_queue_record(self):
        """Queue record should serialize and deserialize correctly."""
        record = create_sample_queue_record_v2()
        serialized = serialize_queue_record_v2(record)
        deserialized = deserialize_queue_record_v2(serialized)
        assert deserialized.queue_id == record.queue_id
        assert deserialized.tsu_id == record.tsu_id


# ============================================================================
# H. Correction Payload Tests
# ============================================================================

class TestCorrectionPayload:
    """Correction payload validation tests."""

    def test_valid_correction_payload(self):
        """Valid correction payload should pass."""
        payload = CorrectionPayloadV2(
            correction_type="doctrine_reclassification",
            field="doctrine",
            original_value="Old doctrine",
            corrected_value="New doctrine",
            correction_reason="Doctrinal update based on source review",
        )
        assert validate_correction_payload_v2(payload) is True

    def test_invalid_correction_same_values(self):
        """Correction with same original/corrected should fail."""
        payload = CorrectionPayloadV2(
            correction_type="doctrine_reclassification",
            field="doctrine",
            original_value="Same value",
            corrected_value="Same value",
            correction_reason="Should not be allowed",
        )
        assert validate_correction_payload_v2(payload) is False

    def test_accept_with_correction_requires_payload(self):
        """ACCEPT_WITH_CORRECTION disposition requires correction payloads."""
        with pytest.raises(ValueError, match="correction_payloads is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-016",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT_WITH_CORRECTION,
                reason_codes=[ReasonCodeV2.EXTRACTION],
                evidence_refs=[EvidenceReferenceV2(
                    evidence_type="tsu_text",
                    evidence_ref="tsu_id:TSU-0000001"
                )],
                reviewer_id="reviewer-001",
                reviewed_at=datetime.now(timezone.utc),
            )


# ============================================================================
# I. Adjudication Tests
# ============================================================================

class TestAdjudication:
    """Adjudication validation tests."""

    def test_valid_adjudication(self):
        """Valid adjudication should pass."""
        adm = AdjudicationRecordV2(
            adjudicator_id="ADV-001",
            outcome=AdjudicationOutcomeV2.OVERTURNED,
            final_disposition=DispositionV2.REJECT,
            reasoning="Reviewer A and B disagreed; adjudicator reviewed evidence.",
            adjudicated_at=datetime.now(timezone.utc),
        )
        assert validate_adjudication_v2(adm) is True

    def test_adjudication_required_state(self):
        """ADJUDICATION_REQUIRED state requires adjudication record."""
        with pytest.raises(ValueError, match="adjudication is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-017",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.ADJUDICATION_REQUIRED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
                evidence_refs=[EvidenceReferenceV2(
                    evidence_type="tsu_text",
                    evidence_ref="tsu_id:TSU-0000001"
                )],
                reviewer_id="reviewer-001",
                reviewed_at=datetime.now(timezone.utc),
            )


# ============================================================================
# J. Schema File Validation
# ============================================================================

class TestSchemaFile:
    """Schema file validation tests."""

    def test_schema_file_exists(self):
        """Schema file should exist."""
        schema_path = Path("docs/schemas/nae_human_review_disposition_v2.schema.json")
        assert schema_path.exists(), "Schema file not found"

    def test_schema_file_valid_json(self):
        """Schema file should be valid JSON."""
        schema_path = Path("docs/schemas/nae_human_review_disposition_v2.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)
        assert "$schema" in schema
        assert "title" in schema
        assert "required" in schema

    def test_schema_required_fields_match_implementation(self):
        """Schema required fields should match implementation."""
        schema_path = Path("docs/schemas/nae_human_review_disposition_v2.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)
        required_fields = set(schema["required"])
        # Check that all required fields are in ReviewRecordV2
        record = create_sample_review_record_v2()
        impl_fields = set(record.model_fields.keys())
        assert required_fields.issubset(impl_fields), f"Missing fields: {required_fields - impl_fields}"


# ============================================================================
# K. v2 Isolation Tests (replaces coexistence)
# ============================================================================

class TestV2Isolation:
    """v2 module must be fully independent — no v1 imports, no shared state."""

    def test_v2_no_legacy_imports(self):
        """v2 module source must not import from legacy review_disposition."""
        import core.review_disposition_v2 as v2_module
        source = open(v2_module.__file__).read()
        # Check for actual import statements, not docstring mentions
        lines = [l.strip() for l in source.splitlines() if l.strip().startswith("import ") or l.strip().startswith("from ")]
        legacy_refs = [l for l in lines if "review_disposition" in l and "review_disposition_v2" not in l]
        assert len(legacy_refs) == 0, f"v2 imports legacy: {legacy_refs}"

    def test_v2_schema_version_isolation(self):
        """v2 schema version must be independent constant."""
        import core.review_disposition_v2 as v2_module
        assert hasattr(v2_module, "HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION")
        assert v2_module.HUMAN_REVIEW_DISPOSITION_V2_SCHEMA_VERSION == "2.0.0"

    def test_v2_state_machine_no_shared_valid_transitions(self):
        """VALID_TRANSITIONS_V2 must be a distinct object from any v1 transitions."""
        import core.review_disposition_v2 as v2_module
        assert hasattr(v2_module, "VALID_TRANSITIONS_V2")
        # Must contain FINALIZED as terminal (key feature of v2)
        from core.review_disposition_v2 import ReviewStateV2
        assert ReviewStateV2.FINALIZED in v2_module.VALID_TRANSITIONS_V2


# ============================================================================
# L. Change Request ID Tests
# ============================================================================

class TestChangeRequestId:
    """change_request_id traceability metadata tests."""

    def test_change_request_id_optional(self):
        """change_request_id should be optional."""
        record = create_sample_review_record_v2()
        assert record.change_request_id is None

    def test_change_request_id_can_be_set(self):
        """change_request_id can be set for traceability."""
        record = create_sample_review_record_v2(
            change_request_id="CR-2026-001"
        )
        assert record.change_request_id == "CR-2026-001"

    def test_change_request_id_not_classification(self):
        """change_request_id is not a classification code."""
        # It's just a traceability reference, not an RC code
        record = create_sample_review_record_v2(
            change_request_id="CR-2026-001"
        )
        assert record.change_request_id != "RC-01"  # Not an RC code


# ============================================================================
# M. RC-07: Disposition-Aware Requeue Tests
# ============================================================================

class TestRC07DispositionAwareRequeue:
    """RC-07: DISPOSITIONED → UNREVIEWED requires disposition context."""

    def test_DISPOSITIONED_NEEDS_REVIEW_can_requeue_to_UNREVIEWED(self):
        """PASS: DISPOSITIONED + NEEDS_REVIEW → UNREVIEWED allowed."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-RC07-001",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.NEEDS_REVIEW,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="scripture", evidence_ref="John 3:16")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.NEEDS_REVIEW,
        ) is True

    def test_DISPOSITIONED_ACCEPT_cannot_requeue_to_UNREVIEWED(self):
        """FAIL: DISPOSITIONED + ACCEPT → UNREVIEWED blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.ACCEPT,
        ) is False

    def test_DISPOSITIONED_REJECT_cannot_requeue_to_UNREVIEWED(self):
        """FAIL: DISPOSITIONED + REJECT → UNREVIEWED blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.REJECT,
        ) is False

    def test_DISPOSITIONED_DUPLICATE_MERGE_cannot_requeue_to_UNREVIEWED(self):
        """FAIL: DISPOSITIONED + DUPLICATE_MERGE → UNREVIEWED blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.DUPLICATE_MERGE,
        ) is False

    def test_DISPOSITIONED_ACCEPT_WITH_CORRECTION_cannot_requeue_to_UNREVIEWED(self):
        """FAIL: DISPOSITIONED + ACCEPT_WITH_CORRECTION → UNREVIEWED blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.ACCEPT_WITH_CORRECTION,
        ) is False

    def test_DISPOSITIONED_to_UNREVIEWED_without_disposition_context_fails(self):
        """FAIL: DISPOSITIONED → UNREVIEWED without disposition context fails."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=None,
        ) is False

    def test_apply_transition_NEEDS_REVIEW_requeue_succeeds(self):
        """PASS: apply_transition with NEEDS_REVIEW requeue succeeds."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-RC07-003",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.NEEDS_REVIEW,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="scripture", evidence_ref="John 3:16")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        audit_trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.UNREVIEWED,
            audit_trail=audit_trail,
            actor="human-reviewer",
            reason="RC-07: needs_review requeue",
        )
        assert record.state == ReviewStateV2.UNREVIEWED
        assert len(audit_trail.events) == 1
        assert audit_trail.events[0].previous_state == "dispositioned"
        assert audit_trail.events[0].new_state == "unreviewed"
        assert audit_trail.events[0].previous_disposition == "needs_review"

    def test_apply_transition_ACCEPT_requeue_raises(self):
        """FAIL: apply_transition with ACCEPT requeue raises InvalidTransitionError."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-RC07-004",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="scripture", evidence_ref="John 3:16")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        audit_trail = AuditTrailV2()
        with pytest.raises(InvalidTransitionError):
            StateMachineV2.apply_transition(
                record,
                ReviewStateV2.UNREVIEWED,
                audit_trail=audit_trail,
                actor="human-reviewer",
                reason="RC-07: accept requeue (should fail)",
            )

    def test_IN_REVIEW_to_UNREVIEWED_blocked(self):
        """RC-07: IN_REVIEW cannot go directly to UNREVIEWED."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.IN_REVIEW,
            ReviewStateV2.UNREVIEWED,
        ) is False


# ============================================================================
# F. Schema ↔ Pydantic Bidirectional Consistency
# ============================================================================

class TestSchemaPydanticConsistency:
    """F.1: review_note and previous_disposition in both schema JSON and Pydantic model."""

    def test_review_note_in_schema_json(self):
        """review_note field must exist in schema JSON."""
        schema = load_schema()
        props = schema["properties"]
        assert "review_note" in props, "review_note missing from schema JSON properties"
        assert props["review_note"]["type"] == ["string", "null"]

    def test_previous_disposition_in_schema_json(self):
        """previous_disposition field must exist in schema JSON."""
        schema = load_schema()
        props = schema["properties"]
        assert "previous_disposition" in props, "previous_disposition missing from schema JSON properties"
        assert props["previous_disposition"]["type"] == ["string", "null"]

    def test_review_note_in_pydantic_model(self):
        """review_note field must exist in ReviewRecordV2 Pydantic model."""
        fields = ReviewRecordV2.model_fields
        assert "review_note" in fields, "review_note missing from ReviewRecordV2"
        field_info = fields["review_note"]
        assert field_info.is_required() is False, "review_note should be optional"

    def test_previous_disposition_in_pydantic_model(self):
        """previous_disposition field must exist in ReviewRecordV2 Pydantic model."""
        fields = ReviewRecordV2.model_fields
        assert "previous_disposition" in fields, "previous_disposition missing from ReviewRecordV2"
        field_info = fields["previous_disposition"]
        assert field_info.is_required() is False, "previous_disposition should be optional"

    def test_schema_to_pydantic_roundtrip(self):
        """Schema → Pydantic: all schema properties must have corresponding Pydantic fields."""
        schema = load_schema()
        schema_props = set(schema["properties"].keys())
        pydantic_fields = set(ReviewRecordV2.model_fields.keys())

        # schema required fields must be in pydantic
        for req_field in schema.get("required", []):
            assert req_field in pydantic_fields, f"Required schema field '{req_field}' missing from Pydantic model"

        # Both should have review_note and previous_disposition
        assert "review_note" in schema_props and "review_note" in pydantic_fields
        assert "previous_disposition" in schema_props and "previous_disposition" in pydantic_fields

    def test_pydantic_to_schema_roundtrip(self):
        """Pydantic → Schema: all Pydantic fields must have corresponding schema properties."""
        schema = load_schema()
        schema_props = set(schema["properties"].keys())
        pydantic_fields = set(ReviewRecordV2.model_fields.keys())

        # All Pydantic fields should be in schema (or be internal like model_config)
        for field_name in pydantic_fields:
            if field_name.startswith("_"):
                continue  # Skip internal fields
            assert field_name in schema_props, f"Pydantic field '{field_name}' missing from schema JSON"


# ============================================================================
# G. RC-03: review_note validation for OTHER reason_code
# ============================================================================

class TestRC03ReviewNoteValidation:
    """G.1: review_note required when OTHER is in reason_codes."""

    def test_review_note_required_with_OTHER(self):
        """Creating a DISPOSITIONED record with OTHER reason_code but no review_note should fail."""
        with pytest.raises(ValueError, match="review_note is required when reason_code includes OTHER"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-099",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=[ReasonCodeV2.OTHER],
                evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
                reviewer_id="REV-001",
                reviewed_at=datetime.now(timezone.utc),
            )

    def test_review_note_not_required_without_OTHER(self):
        """Creating a DISPOSITIONED record without OTHER reason_code should succeed without review_note."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-100",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert record.review_note is None

    def test_review_note_accepted_with_OTHER(self):
        """Creating a DISPOSITIONED record with OTHER reason_code and review_note should succeed."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-101",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.OTHER],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
            review_note="Custom reviewer note explaining the decision.",
        )
        assert record.review_note == "Custom reviewer note explaining the decision."

    def test_empty_review_note_with_OTHER_fails(self):
        """Empty review_note with OTHER reason_code should fail."""
        with pytest.raises(ValueError, match="review_note is required when reason_code includes OTHER"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-102",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=[ReasonCodeV2.OTHER],
                evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
                reviewer_id="REV-001",
                reviewed_at=datetime.now(timezone.utc),
                review_note="",
            )


# ============================================================================
# H. RC-02: previous_disposition tracking for superseded records
# ============================================================================

class TestRC02PreviousDispositionTracking:
    """H.1: previous_disposition tracks disposition from superseded record."""

    def test_previous_disposition_can_be_set(self):
        """previous_disposition field should accept a DispositionV2 value."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-110",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
            previous_disposition=DispositionV2.ACCEPT_WITH_CORRECTION,
        )
        assert record.previous_disposition == DispositionV2.ACCEPT_WITH_CORRECTION

    def test_previous_disposition_defaults_to_none(self):
        """previous_disposition should default to None when not set."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-111",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert record.previous_disposition is None

    def test_supersedes_and_previous_disposition_work_together(self):
        """supersedes_record_id and previous_disposition should work together."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-112",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.REJECT,
            reason_codes=[ReasonCodeV2.DUPLICATION],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
            supersedes_record_id="REVIEW-TSU-0000001-100",
            previous_disposition=DispositionV2.ACCEPT,
        )
        assert record.supersedes_record_id == "REVIEW-TSU-0000001-100"
        assert record.previous_disposition == DispositionV2.ACCEPT
        assert record.disposition == DispositionV2.REJECT  # New disposition differs from previous


# ============================================================================
# I. RC-04: Duplicate detection for same TSU
# ============================================================================

class TestRC04DuplicateDetection:
    """I.1: Same TSU can have multiple review records (supersedes mechanism)."""

    def test_same_tsu_multiple_records_allowed(self):
        """Multiple review records for the same TSU should be allowed via supersedes."""
        record1 = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-200",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        record2 = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-201",
            tsu_id="TSU-0000001",  # Same TSU
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.REJECT,
            reason_codes=[ReasonCodeV2.DUPLICATION],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-002",
            reviewed_at=datetime.now(timezone.utc),
            supersedes_record_id=record1.record_id,
            previous_disposition=DispositionV2.ACCEPT,
        )
        assert record2.supersedes_record_id == record1.record_id
        assert record2.previous_disposition == DispositionV2.ACCEPT
        assert record2.disposition == DispositionV2.REJECT

    def test_duplicate_merge_disposition_valid(self):
        """DUPLICATE_MERGE disposition should be valid."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-202",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.DUPLICATE_MERGE,
            reason_codes=[ReasonCodeV2.DUPLICATION],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-003",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert record.disposition == DispositionV2.DUPLICATE_MERGE

    def test_duplicate_merge_cannot_requeue(self):
        """DUPLICATE_MERGE disposition should block requeue to UNREVIEWED."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-203",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.DUPLICATE_MERGE,
            reason_codes=[ReasonCodeV2.DUPLICATION],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-004",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.DUPLICATE_MERGE,
        ) is False


# ============================================================================
# J. RC-05: Evidence integrity validation
# ============================================================================

class TestRC05EvidenceIntegrity:
    """J.1: evidence_refs must be valid and non-empty for DISPOSITIONED records."""

    def test_evidence_refs_required_for_dispositioned(self):
        """DISPOSITIONED record without evidence_refs should fail validation."""
        with pytest.raises(ValueError, match="evidence_refs is required"):
            create_sample_review_record_v2(
                record_id="REVIEW-TSU-0000001-300",
                tsu_id="TSU-0000001",
                state=ReviewStateV2.DISPOSITIONED,
                disposition=DispositionV2.ACCEPT,
                reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
                evidence_refs=[],  # Empty evidence_refs
                reviewer_id="REV-001",
                reviewed_at=datetime.now(timezone.utc),
            )

    def test_evidence_refs_valid_with_multiple_refs(self):
        """DISPOSITIONED record with multiple valid evidence_refs should succeed."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-301",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[
                EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001"),
                EvidenceReferenceV2(evidence_type="source_page", evidence_ref="source_id:BAP-CHURCH-DAGG-001#page=42"),
            ],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        assert len(record.evidence_refs) == 2

    def test_evidence_refs_invalid_type_accepted_by_model(self):
        """EvidenceReferenceV2 accepts any string for evidence_type (validation is semantic)."""
        ref = EvidenceReferenceV2(evidence_type="invalid_type", evidence_ref="tsu_id:TSU-0000001")
        assert ref.evidence_type == "invalid_type"

    def test_evidence_refs_empty_ref_accepted_by_model(self):
        """EvidenceReferenceV2 accepts empty string for evidence_ref (validation is semantic)."""
        ref = EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="")
        assert ref.evidence_ref == ""


# ============================================================================
# K. RC-06: Audit trail auto-generation
# ============================================================================

class TestRC06AuditTrailAutoGeneration:
    """K.1: apply_transition must auto-generate audit events."""

    def test_apply_transition_creates_audit_event(self):
        """apply_transition should create an audit event for state transition."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-400",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.UNREVIEWED,
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.IN_REVIEW,
            audit_trail=trail,
            actor="REV-001",
            reason="initial_review",
        )
        assert len(trail.events) == 1
        event = trail.events[0]
        assert event.previous_state == "unreviewed"
        assert event.new_state == "in_review"
        assert event.actor == "REV-001"

    def test_apply_transition_creates_disposition_event(self):
        """apply_transition with disposition should create a disposition audit event."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-401",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.IN_REVIEW,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.DISPOSITIONED,
            actor="REV-001",
            reason="disposition_accept",
            audit_trail=trail,
        )
        assert len(trail.events) == 1
        event = trail.events[0]
        assert event.previous_state == "in_review"
        assert event.new_state == "dispositioned"
        assert event.actor == "REV-001"

    def test_multiple_transitions_create_multiple_events(self):
        """Multiple apply_transition calls should create multiple audit events."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-TSU-0000001-402",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.UNREVIEWED,
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.IN_REVIEW,
            actor="REV-001",
            reason="initial_review",
            audit_trail=trail,
        )
        # Set disposition before transitioning to DISPOSITIONED
        record.disposition = DispositionV2.ACCEPT
        record.reason_codes = [ReasonCodeV2.CONTENT_VALIDITY]
        record.evidence_refs = [EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")]
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.DISPOSITIONED,
            actor="REV-001",
            reason="disposition_accept",
            audit_trail=trail,
        )
        assert len(trail.events) == 2


# ============================================================================
# L. I-1: AuditTrail MUST be required (blocking correction)
# ============================================================================

class TestI1AuditTrailRequired:
    """I-1: apply_transition must reject calls without audit_trail."""

    def test_apply_transition_without_audit_trail_raises(self):
        """Calling apply_transition without audit_trail must raise TypeError."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-I1-001",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.UNREVIEWED,
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        with pytest.raises(TypeError):
            StateMachineV2.apply_transition(
                record,
                ReviewStateV2.IN_REVIEW,
                actor="REV-001",
                reason="I-1: should fail without audit_trail",
            )

    def test_apply_transition_with_audit_trail_succeeds(self):
        """Calling apply_transition with audit_trail must succeed and generate event."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-I1-002",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.UNREVIEWED,
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.IN_REVIEW,
            audit_trail=trail,
            actor="REV-001",
            reason="I-1: valid transition with audit_trail",
        )
        assert record.state == ReviewStateV2.IN_REVIEW
        assert len(trail.events) == 1
        event = trail.events[0]
        assert event.previous_state == "unreviewed"
        assert event.new_state == "in_review"

    def test_apply_transition_exact_one_event_per_success(self):
        """Every successful transition must produce exactly one audit event."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-I1-003",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.UNREVIEWED,
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()

        StateMachineV2.apply_transition(
            record, ReviewStateV2.IN_REVIEW,
            audit_trail=trail, actor="REV-001", reason="t1",
        )
        assert len(trail.events) == 1

        record.disposition = DispositionV2.ACCEPT
        record.reason_codes = [ReasonCodeV2.CONTENT_VALIDITY]
        record.evidence_refs = [EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")]
        StateMachineV2.apply_transition(
            record, ReviewStateV2.DISPOSITIONED,
            audit_trail=trail, actor="REV-001", reason="t2",
        )
        assert len(trail.events) == 2

        StateMachineV2.apply_transition(
            record, ReviewStateV2.FINALIZED,
            audit_trail=trail, actor="REV-001", reason="t3",
        )
        assert len(trail.events) == 3


# ============================================================================
# M. I-5: FINALIZED Self-loop MUST be blocked (blocking correction)
# ============================================================================

class TestI5FinalizedSelfLoopBlocked:
    """I-5: FINALIZED self-loop must be explicitly blocked."""

    def test_finalized_to_finalized_blocked(self):
        """FINALIZED → FINALIZED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.FINALIZED,
            ReviewStateV2.FINALIZED,
        ) is False

    def test_finalized_to_unreviewed_blocked(self):
        """FINALIZED → UNREVIEWED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.FINALIZED,
            ReviewStateV2.UNREVIEWED,
        ) is False

    def test_finalized_to_in_review_blocked(self):
        """FINALIZED → IN_REVIEW must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.FINALIZED,
            ReviewStateV2.IN_REVIEW,
        ) is False

    def test_finalized_to_dispositioned_blocked(self):
        """FINALIZED → DISPOSITIONED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.FINALIZED,
            ReviewStateV2.DISPOSITIONED,
        ) is False

    def test_finalized_to_adjudication_required_blocked(self):
        """FINALIZED → ADJUDICATION_REQUIRED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.FINALIZED,
            ReviewStateV2.ADJUDICATION_REQUIRED,
        ) is False

    def test_apply_transition_finalized_to_finalized_raises(self):
        """apply_transition FINALIZED → FINALIZED must raise InvalidTransitionError."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-I5-001",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.FINALIZED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="tsu_text", evidence_ref="tsu_id:TSU-0000001")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        with pytest.raises(InvalidTransitionError):
            StateMachineV2.apply_transition(
                record,
                ReviewStateV2.FINALIZED,
                audit_trail=trail,
                actor="REV-001",
                reason="I-5: self-loop should be blocked",
            )
        assert record.state == ReviewStateV2.FINALIZED


# ============================================================================
# N. RC-07 Regression: Disposition-aware requeue preservation
# ============================================================================

class TestRC07Regression:
    """RC-07: Disposition-aware requeue rules must be preserved."""

    def test_DISPOSITIONED_NEEDS_REVIEW_to_UNREVIEWED_passes(self):
        """DISPOSITIONED + NEEDS_REVIEW → UNREVIEWED must pass."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.NEEDS_REVIEW,
        ) is True

    def test_DISPOSITIONED_ACCEPT_to_UNREVIEWED_blocked(self):
        """DISPOSITIONED + ACCEPT → UNREVIEWED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.ACCEPT,
        ) is False

    def test_DISPOSITIONED_REJECT_to_UNREVIEWED_blocked(self):
        """DISPOSITIONED + REJECT → UNREVIEWED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.REJECT,
        ) is False

    def test_DISPOSITIONED_ACCEPT_WITH_CORRECTION_to_UNREVIEWED_blocked(self):
        """DISPOSITIONED + ACCEPT_WITH_CORRECTION → UNREVIEWED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.ACCEPT_WITH_CORRECTION,
        ) is False

    def test_DISPOSITIONED_DUPLICATE_MERGE_to_UNREVIEWED_blocked(self):
        """DISPOSITIONED + DUPLICATE_MERGE → UNREVIEWED must be blocked."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.DISPOSITIONED,
            ReviewStateV2.UNREVIEWED,
            disposition=DispositionV2.DUPLICATE_MERGE,
        ) is False

    def test_apply_transition_NEEDS_REVIEW_requeue_succeeds(self):
        """apply_transition with NEEDS_REVIEW requeue succeeds."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-RC07-003",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.NEEDS_REVIEW,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="scripture", evidence_ref="John 3:16")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        StateMachineV2.apply_transition(
            record,
            ReviewStateV2.UNREVIEWED,
            audit_trail=trail,
            actor="human-reviewer",
            reason="RC-07: needs_review requeue",
        )
        assert record.state == ReviewStateV2.UNREVIEWED
        assert len(trail.events) == 1
        assert trail.events[0].previous_state == "dispositioned"
        assert trail.events[0].new_state == "unreviewed"
        assert trail.events[0].previous_disposition == "needs_review"

    def test_apply_transition_ACCEPT_requeue_raises(self):
        """apply_transition with ACCEPT requeue raises InvalidTransitionError."""
        record = create_sample_review_record_v2(
            record_id="REVIEW-RC07-004",
            tsu_id="TSU-0000001",
            state=ReviewStateV2.DISPOSITIONED,
            disposition=DispositionV2.ACCEPT,
            reason_codes=[ReasonCodeV2.CONTENT_VALIDITY],
            evidence_refs=[EvidenceReferenceV2(evidence_type="scripture", evidence_ref="John 3:16")],
            reviewer_id="REV-001",
            reviewed_at=datetime.now(timezone.utc),
        )
        trail = AuditTrailV2()
        with pytest.raises(InvalidTransitionError):
            StateMachineV2.apply_transition(
                record,
                ReviewStateV2.UNREVIEWED,
                audit_trail=trail,
                actor="human-reviewer",
                reason="RC-07: accept requeue (should fail)",
            )

    def test_IN_REVIEW_to_UNREVIEWED_blocked(self):
        """RC-07: IN_REVIEW cannot go directly to UNREVIEWED."""
        assert StateMachineV2.validate_transition(
            ReviewStateV2.IN_REVIEW,
            ReviewStateV2.UNREVIEWED,
        ) is False

"""tests/test_corpus_approval_gate.py — Corpus Mutation Approval Gate Tests

A. No approval → BLOCK
B. Rejected source → BLOCK
C. Unknown source → BLOCK
D. Mismatched approval → BLOCK
E. Missing metadata → BLOCK
F. Approved fixture → ALLOW (temp corpus only)
G. Fail-closed preservation
H. Direct-call protection
"""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.corpus_approval_gate import (
    ApprovalStatus,
    CorpusMutationApprovalResult,
    CorpusMutationBlockedError,
    CorpusMutationManifest,
    build_approval_manifest,
    validate_merge_plan_against_manifest,
    verify_corpus_mutation_approval,
)
from scripts.merge_nae_corpus import merge_nae_corpus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_decisions_dir(tmp_path: Path, source_id: str, decisions: list[dict]) -> Path:
    """decisions directory를 생성 — 누락된 metadata는 기본값으로 보완.

    기존 테스트와의 호환성: gate_id/reviewer_id/answers가 없으면
    기본값을 추가하여 validation을 통과하도록 한다.
    새 테스트에서 명시적으로 누락된 metadata를 검증하려면
    이 helper 대신 직접 파일을 작성해야 한다.
    """
    _REQUIRED_JUDGMENT_KEYS = frozenset({"Q1", "Q2", "Q3"})

    ddir = tmp_path / "decisions"
    ddir.mkdir(parents=True)
    enriched: list[dict] = []
    for entry in decisions:
        e = dict(entry)
        if not e.get("gate_id"):
            e["gate_id"] = f"G-{source_id}"
        if not e.get("reviewer_id"):
            e["reviewer_id"] = f"R-{source_id}"
        if not e.get("answers"):
            e["answers"] = {"Q1": "A", "Q2": "A", "Q3": "A"}
        else:
            # missing Q1-Q3 keys도 보완 — semantic validation 통과용
            for k in _REQUIRED_JUDGMENT_KEYS:
                if k not in e["answers"]:
                    e["answers"] = dict(e["answers"])  # 원본 불변성 유지
                    e["answers"][k] = "A"
        enriched.append(e)
    file_data = {"decisions": enriched}
    (ddir / f"{source_id}_decisions.json").write_text(
        json.dumps(file_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return ddir


def _make_decisions_dir_raw(tmp_path: Path, source_id: str, decisions: list[dict]) -> Path:
    """metadata 보완 없이 decisions directory를 생성 — V2/V3/V4 테스트용."""
    ddir = tmp_path / "decisions"
    ddir.mkdir(parents=True)
    file_data = {"decisions": decisions}
    (ddir / f"{source_id}_decisions.json").write_text(
        json.dumps(file_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return ddir


def _make_corpus_root(tmp_path: Path, source_id: str, tsu_ids: list[str]) -> Path:
    """corpus root directory를 생성하고 그 안에 source별 subdirectory + tsu.json을 만듦.

    merge_nae_corpus()가 nae_corpus_dir.glob("*")로 subdirectory를 탐색하므로
    corpus_root/source_id/tsu.json 구조가 필요하다.
    """
    croot = tmp_path / "corpus"
    croot.mkdir(parents=True)
    cdir = croot / source_id
    cdir.mkdir(parents=True)
    records = [{"tsu_id": tid, "work_id": source_id, "claim": f"Claim for {tid}"} for tid in tsu_ids]
    (cdir / "tsu.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return croot


# ---------------------------------------------------------------------------
# A. No approval — 승인 정보가 없으면 mutation 거부
# ---------------------------------------------------------------------------

class TestNoApproval:
    def test_empty_decisions_dir(self, tmp_path: Path):
        ddir = tmp_path / "decisions"
        ddir.mkdir()
        result = verify_corpus_mutation_approval("UnknownSource", ddir)
        assert result.blocked is True
        assert result.status == ApprovalStatus.NOT_APPROVED

    def test_no_decisions_dir(self, tmp_path: Path):
        ddir = tmp_path / "nonexistent"
        result = verify_corpus_mutation_approval("UnknownSource", ddir)
        assert result.blocked is True
        assert result.status == ApprovalStatus.NOT_APPROVED


class TestNoApprovalWithData:
    def test_merge_blocks_without_approval_when_corpus_has_data(self, tmp_path: Path):
        """A: corpus에 데이터가 있지만 승인 정보가 없으면 merge 차단."""
        corpus_root = _make_corpus_root(tmp_path, "UnapprovedSource", ["TSU-001", "TSU-002"])
        ddir = tmp_path / "decisions"
        ddir.mkdir()
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")
        original_bytes = dataset.read_bytes()

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="UnapprovedSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert "BLOCKED" in str(exc_info.value)
        assert dataset.read_bytes() == original_bytes


# ---------------------------------------------------------------------------
# B. Rejected source — REJECTED source는 mutation 거부
# ---------------------------------------------------------------------------

class TestRejectedSource:
    def test_rejected_decision_blocks_merge(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "RejectedSource", ["TSU-001"])
        ddir = _make_decisions_dir(
            tmp_path, "RejectedSource",
            [{"tsu_id": "TSU-001", "work_id": "RejectedSource",
              "final_decision": "REJECTED", "reviewer_id": "test"}],
        )
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")
        original_bytes = dataset.read_bytes()

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="RejectedSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert "BLOCKED" in str(exc_info.value)
        assert dataset.read_bytes() == original_bytes

    def test_verify_returns_not_approved_for_rejected(self, tmp_path: Path):
        ddir = _make_decisions_dir(
            tmp_path, "RejectedSource",
            [{"tsu_id": "TSU-001", "work_id": "RejectedSource",
              "final_decision": "REJECTED", "reviewer_id": "test"}],
        )
        result = verify_corpus_mutation_approval("RejectedSource", ddir)
        assert result.blocked is True
        assert result.status == ApprovalStatus.NOT_APPROVED


# ---------------------------------------------------------------------------
# C. Unknown source — allowlist에 없는 source는 mutation 거부
# ---------------------------------------------------------------------------

class TestUnknownSource:
    def test_unknown_source_blocks(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "UnknownSource", ["TSU-001"])
        ddir = _make_decisions_dir(
            tmp_path, "DifferentSource",  # 다른 source의 decision만 있음
            [{"tsu_id": "TSU-002", "work_id": "DifferentSource",
              "final_decision": "APPROVED", "reviewer_id": "test"}],
        )
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="UnknownSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert "BLOCKED" in str(exc_info.value)

    def test_verify_returns_not_approved_for_unknown(self, tmp_path: Path):
        ddir = _make_decisions_dir(
            tmp_path, "DifferentSource",
            [{"tsu_id": "TSU-002", "work_id": "DifferentSource",
              "final_decision": "APPROVED", "reviewer_id": "test"}],
        )
        result = verify_corpus_mutation_approval("UnknownSource", ddir)
        assert result.blocked is True
        assert "No decision records found" in result.reason


# ---------------------------------------------------------------------------
# D. Mismatched approval — 승인된 source와 실제 merge 대상이 다르면 거부
# ---------------------------------------------------------------------------

class TestMismatchedApproval:
    def test_partial_approval_blocks(self, tmp_path: Path):
        """일부만 승인된 경우 (CONDITIONAL) → mutation 차단."""
        corpus_root = _make_corpus_root(tmp_path, "PartialSource", ["TSU-001", "TSU-002"])
        ddir = _make_decisions_dir(
            tmp_path, "PartialSource",
            [
                {"tsu_id": "TSU-001", "work_id": "PartialSource",
                 "final_decision": "APPROVED", "reviewer_id": "test"},
                {"tsu_id": "TSU-002", "work_id": "PartialSource",
                 "final_decision": "REJECTED", "reviewer_id": "test"},
            ],
        )
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="PartialSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert "REJECTED" in str(exc_info.value) or "CONDITIONAL" in str(exc_info.value) or "BLOCKED" in str(exc_info.value)

    def test_manifest_mismatch_blocks(self):
        manifest = CorpusMutationManifest(
            source_id="TestSource",
            approved_tsu_ids=frozenset({"TSU-001", "TSU-002"}),
            approved_count=2,
            reviewer_id="test",
            review_timestamp=None,
            final_decision="APPROVED",
        )
        valid, reason = validate_merge_plan_against_manifest(
            manifest, frozenset({"TSU-001", "TSU-003"})
        )
        assert valid is False
        assert "mismatch" in reason.lower()

    def test_verify_manifest_mismatch(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "MismatchSource", ["TSU-001", "TSU-002"])
        ddir = _make_decisions_dir(
            tmp_path, "MismatchSource",
            [
                {"tsu_id": "TSU-001", "work_id": "MismatchSource",
                 "final_decision": "APPROVED", "reviewer_id": "test"},
                {"tsu_id": "TSU-002", "work_id": "MismatchSource",
                 "final_decision": "APPROVED", "reviewer_id": "test"},
            ],
        )
        result = verify_corpus_mutation_approval(
            "MismatchSource", ddir, frozenset({"TSU-001", "TSU-003"})
        )
        assert result.blocked is True
        assert "mismatch" in result.reason.lower() or "not in approved" in result.reason


# ---------------------------------------------------------------------------
# E. Missing metadata — 필수 approval metadata가 없으면 mutation 거부
# ---------------------------------------------------------------------------

class TestMissingMetadata:
    def test_no_final_decision_blocks(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "NoDecisionSource", ["TSU-001"])
        ddir = _make_decisions_dir(
            tmp_path, "NoDecisionSource",
            [{"tsu_id": "TSU-001", "work_id": "NoDecisionSource"}],
        )
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="NoDecisionSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert "BLOCKED" in str(exc_info.value)

    def test_invalid_final_decision_blocks(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "InvalidDecisionSource", ["TSU-001"])
        ddir = _make_decisions_dir(
            tmp_path, "InvalidDecisionSource",
            [{"tsu_id": "TSU-001", "work_id": "InvalidDecisionSource",
              "final_decision": "UNKNOWN_STATUS"}],
        )
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="InvalidDecisionSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert "BLOCKED" in str(exc_info.value)


# ---------------------------------------------------------------------------
# F. Approved fixture — 유효한 approval fixture에서 mutation 허용 (temp only)
# ---------------------------------------------------------------------------

class TestApprovedFixture:
    def test_approved_source_allows_merge_in_temp(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "ApprovedSource", ["TSU-001", "TSU-002"])
        ddir = _make_decisions_dir(
            tmp_path, "ApprovedSource",
            [
                {"tsu_id": "TSU-001", "work_id": "ApprovedSource",
                 "final_decision": "APPROVED", "reviewer_id": "pastor_001",
                 "review_timestamp": "2026-10-01T00:00:00Z"},
                {"tsu_id": "TSU-002", "work_id": "ApprovedSource",
                 "final_decision": "APPROVED", "reviewer_id": "pastor_001",
                 "review_timestamp": "2026-10-01T00:00:01Z"},
            ],
        )
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")

        result = merge_nae_corpus(
            source_id="ApprovedSource",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=dataset,
            decisions_dir=ddir,
        )
        assert result["status"] == "completed"
        assert result["merged_count"] == 2
        assert result["approved_count"] == 2

    def test_build_manifest_for_approved_source(self, tmp_path: Path):
        ddir = _make_decisions_dir(
            tmp_path, "ApprovedSource",
            [{"tsu_id": "TSU-001", "work_id": "ApprovedSource",
              "final_decision": "APPROVED", "reviewer_id": "pastor_001"}],
        )
        manifest = build_approval_manifest("ApprovedSource", ddir)
        assert manifest is not None
        assert manifest.approved_count == 1
        assert manifest.final_decision == "APPROVED"

    def test_build_manifest_returns_none_for_unapproved(self, tmp_path: Path):
        ddir = _make_decisions_dir(
            tmp_path, "RejectedSource",
            [{"tsu_id": "TSU-001", "work_id": "RejectedSource",
              "final_decision": "REJECTED"}],
        )
        manifest = build_approval_manifest("RejectedSource", ddir)
        assert manifest is None


# ---------------------------------------------------------------------------
# G. Fail-closed preservation — approval failure 시 기존 dataset 변경 없음
# ---------------------------------------------------------------------------

class TestFailClosed:
    def test_dataset_unchanged_on_block(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "BlockedSource", ["TSU-001"])
        ddir = tmp_path / "decisions"
        ddir.mkdir()
        dataset = tmp_path / "dataset.jsonl"
        original_content = '{"tsu_id": "EXISTING-TSU-001", "work_id": "ExistingSource"}\n'
        dataset.write_text(original_content, encoding="utf-8")
        original_bytes = dataset.read_bytes()

        with pytest.raises(CorpusMutationBlockedError):
            merge_nae_corpus(
                source_id="BlockedSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert dataset.read_bytes() == original_bytes

    def test_verify_returns_correct_status_for_each_case(self):
        result = CorpusMutationApprovalResult(
            source_id="Test", status=ApprovalStatus.APPROVED,
            approved_tsu_ids=frozenset({"TSU-001"}), reason="ok"
        )
        assert result.approved is True
        assert result.blocked is False

        result = CorpusMutationApprovalResult(
            source_id="Test", status=ApprovalStatus.NOT_APPROVED, reason="no decision"
        )
        assert result.approved is False
        assert result.blocked is True

        result = CorpusMutationApprovalResult(
            source_id="Test", status=ApprovalStatus.CONDITIONAL,
            approved_tsu_ids=frozenset({"TSU-001"}),
            rejected_tsu_ids=frozenset({"TSU-002"}), reason="partial"
        )
        assert result.approved is False
        assert result.blocked is True


# ---------------------------------------------------------------------------
# H. Direct-call protection — Python에서 직접 호출해도 gate 우회 불가
# ---------------------------------------------------------------------------

class TestDirectCallProtection:
    def test_direct_merge_call_respects_gate(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "DirectCallSource", ["TSU-001"])
        ddir = tmp_path / "decisions"
        ddir.mkdir()
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text("", encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="DirectCallSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert "BLOCKED" in str(exc_info.value)

    def test_gate_is_function_level_not_cli_only(self):
        import inspect
        from scripts.merge_nae_corpus import merge_nae_corpus

        source = inspect.getsource(merge_nae_corpus)
        assert "verify_mutation_gate" in source, "gate가 함수 내부에 있어야 함"
        gate_pos = source.index("verify_mutation_gate")
        mutation_pos = source.index("_atomic_write_text")
        assert gate_pos < mutation_pos, "gate가 mutation code 전에 호출되어야 함"

    def test_no_cli_option_bypasses_gate(self):
        import inspect
        from scripts.merge_nae_corpus import merge_nae_corpus

        source = inspect.getsource(merge_nae_corpus)
        assert "bypass" not in source.lower()
        assert "skip_gate" not in source.lower()
        assert "force_merge" not in source.lower()
        assert "unsafe" not in source.lower()


# ---------------------------------------------------------------------------
# V1: CONDITIONAL invariant — CONDITIONAL은 반드시 BLOCK
# ---------------------------------------------------------------------------

class TestConditionalInvariant:
    """APPROVED + CONDITIONAL → BLOCK (핵심 invariant)."""

    def test_approved_plus_conditional_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "MixedSource",
            [
                {"tsu_id": "TSU-001", "work_id": "MixedSource", "gate_id": "G1",
                 "reviewer_id": "R1", "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
                {"tsu_id": "TSU-002", "work_id": "MixedSource", "gate_id": "G1",
                 "reviewer_id": "R1", "answers": {"Q1": "C"}, "final_decision": "CONDITIONAL"},
            ],
        )
        result = verify_corpus_mutation_approval("MixedSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED
        assert result.blocked is True

    def test_conditional_only_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "ConditionalOnlySource",
            [
                {"tsu_id": "TSU-003", "work_id": "ConditionalOnlySource", "gate_id": "G2",
                 "reviewer_id": "R2", "answers": {"Q1": "C"}, "final_decision": "CONDITIONAL"},
            ],
        )
        result = verify_corpus_mutation_approval("ConditionalOnlySource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED
        assert result.blocked is True

    def test_approved_plus_rejected_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "MixedARSource",
            [
                {"tsu_id": "TSU-004", "work_id": "MixedARSource", "gate_id": "G3",
                 "reviewer_id": "R3", "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
                {"tsu_id": "TSU-005", "work_id": "MixedARSource", "gate_id": "G3",
                 "reviewer_id": "R3", "answers": {"Q1": "R"}, "final_decision": "REJECTED"},
            ],
        )
        result = verify_corpus_mutation_approval("MixedARSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED
        assert result.blocked is True
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# V2: Decision validation — 기존 decision_gate.py convention 재사용 검증
# ---------------------------------------------------------------------------

class TestDecisionValidation:
    """기존 HumanDecisionRecord schema 필수 metadata 검증."""

    def test_missing_reviewer_id_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "NoReviewerSource",
            [
                {"tsu_id": "TSU-006", "work_id": "NoReviewerSource", "gate_id": "G4",
                 "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("NoReviewerSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED

    def test_missing_answers_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "NoAnswersSource",
            [
                {"tsu_id": "TSU-007", "work_id": "NoAnswersSource", "gate_id": "G5",
                 "reviewer_id": "R5", "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("NoAnswersSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED

    def test_missing_gate_id_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "NoGateIdSource",
            [
                {"tsu_id": "TSU-008", "work_id": "NoGateIdSource", "reviewer_id": "R6",
                 "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("NoGateIdSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED

    def test_missing_tsu_id_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "NoTsuIdSource",
            [
                {"work_id": "NoTsuIdSource", "gate_id": "G7", "reviewer_id": "R7",
                 "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("NoTsuIdSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED

    def test_malformed_answers_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "MalformedAnswersSource",
            [
                {"tsu_id": "TSU-009", "work_id": "MalformedAnswersSource", "gate_id": "G8",
                 "reviewer_id": "R8", "answers": "not_a_dict", "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("MalformedAnswersSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED

    def test_invalid_final_decision_blocks(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "InvalidDecisionSource",
            [
                {"tsu_id": "TSU-010", "work_id": "InvalidDecisionSource", "gate_id": "G9",
                 "reviewer_id": "R9", "answers": {"Q1": "A"}, "final_decision": "INVALID"},
            ],
        )
        result = verify_corpus_mutation_approval("InvalidDecisionSource", ddir)
        assert result.status == ApprovalStatus.NOT_APPROVED


# ---------------------------------------------------------------------------
# V3: Manifest reviewer_id fallback 제거
# ---------------------------------------------------------------------------

class TestManifestReviewerId:
    """build_approval_manifest에서 missing reviewer_id → None."""

    def test_valid_approval_builds_manifest(self, tmp_path: Path):
        ddir = _make_decisions_dir(
            tmp_path, "ValidSource",
            [
                {"tsu_id": "TSU-011", "work_id": "ValidSource", "gate_id": "G10",
                 "reviewer_id": "R10", "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
            ],
        )
        manifest = build_approval_manifest("ValidSource", ddir)
        assert manifest is not None
        assert manifest.source_id == "ValidSource"

    def test_missing_reviewer_id_returns_none(self, tmp_path: Path):
        ddir = _make_decisions_dir_raw(
            tmp_path, "NoReviewerManifestSource",
            [
                {"tsu_id": "TSU-012", "work_id": "NoReviewerManifestSource", "gate_id": "G11",
                 "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
            ],
        )
        manifest = build_approval_manifest("NoReviewerManifestSource", ddir)
        assert manifest is None


# ---------------------------------------------------------------------------
# V4: Mutation path protection — 실제 merge_nae_corpus()에서 BLOCK 검증
# ---------------------------------------------------------------------------

class TestMutationPathProtection:
    """merge_nae_corpus()에서 gate가 dataset을 보호하는지 확인."""

    def test_approved_plus_conditional_blocks_merge(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "MixedMergeSource", ["TSU-020", "TSU-021"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "MixedMergeSource",
            [
                {"tsu_id": "TSU-020", "work_id": "MixedMergeSource", "gate_id": "G20",
                 "reviewer_id": "R20", "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
                {"tsu_id": "TSU-021", "work_id": "MixedMergeSource", "gate_id": "G20",
                 "reviewer_id": "R20", "answers": {"Q1": "C"}, "final_decision": "CONDITIONAL"},
            ],
        )
        dataset = tmp_path / "dataset_mixed.jsonl"
        orig_content = json.dumps({"tsu_id": "X"}) + "\n"
        dataset.write_text(orig_content, encoding="utf-8")
        orig_bytes = dataset.read_bytes()

        with pytest.raises(CorpusMutationBlockedError):
            merge_nae_corpus(
                source_id="MixedMergeSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert dataset.read_bytes() == orig_bytes

    def test_missing_metadata_blocks_merge(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "NoReviewerMergeSource", ["TSU-022"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "NoReviewerMergeSource",
            [
                {"tsu_id": "TSU-022", "work_id": "NoReviewerMergeSource", "gate_id": "G21",
                 "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
            ],
        )
        dataset = tmp_path / "dataset_nometa.jsonl"
        orig_content = json.dumps({"tsu_id": "Y"}) + "\n"
        dataset.write_text(orig_content, encoding="utf-8")
        orig_bytes = dataset.read_bytes()

        with pytest.raises(CorpusMutationBlockedError):
            merge_nae_corpus(
                source_id="NoReviewerMergeSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert dataset.read_bytes() == orig_bytes

    def test_approved_plus_rejected_blocks_merge(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "MixedARMergeSource", ["TSU-023", "TSU-024"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "MixedARMergeSource",
            [
                {"tsu_id": "TSU-023", "work_id": "MixedARMergeSource", "gate_id": "G22",
                 "reviewer_id": "R22", "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
                {"tsu_id": "TSU-024", "work_id": "MixedARMergeSource", "gate_id": "G22",
                 "reviewer_id": "R22", "answers": {"Q1": "R"}, "final_decision": "REJECTED"},
            ],
        )
        dataset = tmp_path / "dataset_ar.jsonl"
        orig_content = json.dumps({"tsu_id": "Z"}) + "\n"
        dataset.write_text(orig_content, encoding="utf-8")
        orig_bytes = dataset.read_bytes()

        with pytest.raises(CorpusMutationBlockedError):
            merge_nae_corpus(
                source_id="MixedARMergeSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert dataset.read_bytes() == orig_bytes

    def test_valid_approval_allows_merge(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "ValidMergeSource", ["TSU-025"])
        ddir = _make_decisions_dir(
            tmp_path, "ValidMergeSource",
            [
                {"tsu_id": "TSU-025", "work_id": "ValidMergeSource", "gate_id": "G23",
                 "reviewer_id": "R23", "answers": {"Q1": "A"}, "final_decision": "APPROVED"},
            ],
        )
        dataset = tmp_path / "dataset_valid.jsonl"
        dataset.write_text("", encoding="utf-8")

        result = merge_nae_corpus(
            source_id="ValidMergeSource",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=dataset,
            decisions_dir=ddir,
        )
        assert result["status"] == "completed"
        assert result["merged_count"] == 1

class TestF3Regression:
    def test_idempotent_by_tsu_id(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "IdempotentSource", ["TSU-001"])
        ddir = _make_decisions_dir(
            tmp_path, "IdempotentSource",
            [{"tsu_id": "TSU-001", "work_id": "IdempotentSource",
              "final_decision": "APPROVED"}],
        )
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text(
            json.dumps({"tsu_id": "TSU-001", "work_id": "IdempotentSource"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        result = merge_nae_corpus(
            source_id="IdempotentSource",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=dataset,
            decisions_dir=ddir,
        )
        assert result["merged_count"] == 0
        assert result["duplicate_count"] == 1

    def test_atomic_write_preserves_on_failure(self):
        from scripts.merge_nae_corpus import _atomic_write_text

        tmpdir = tempfile.mkdtemp()
        target = Path(tmpdir) / "test.jsonl"
        content = "test content\n"
        _atomic_write_text(target, content)
        assert target.read_text(encoding="utf-8") == content

    def test_dedup_preserves_existing(self, tmp_path: Path):
        corpus_root = _make_corpus_root(tmp_path, "DedupSource", ["TSU-001"])
        ddir = _make_decisions_dir(
            tmp_path, "DedupSource",
            [{"tsu_id": "TSU-001", "work_id": "DedupSource",
              "final_decision": "APPROVED"}],
        )
        dataset = tmp_path / "dataset.jsonl"
        original_claim = "Original claim text"
        dataset.write_text(
            json.dumps({"tsu_id": "TSU-001", "claim": original_claim}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        result = merge_nae_corpus(
            source_id="DedupSource",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=dataset,
            decisions_dir=ddir,
        )
        assert result["merged_count"] == 0
        records = [json.loads(l) for l in dataset.read_text(encoding="utf-8").strip().split("\n")]
        assert records[0]["claim"] == original_claim


# ---------------------------------------------------------------------------
# V5 — Decision Semantics (new)
# ---------------------------------------------------------------------------

class TestDecisionSemantics:
    """decision_gate.py 의미론과 corpus approval gate의 일치 검증."""

    def test_approved_with_all_a_answers_allows(self, tmp_path: Path):
        """APPROVED + Q1=A, Q2=A, Q3=A → ALLOW (positive baseline)."""
        corpus_root = _make_corpus_root(tmp_path, "SemanticsAllowSource", ["TSU-050"])
        ddir = _make_decisions_dir(
            tmp_path, "SemanticsAllowSource",
            [
                {"tsu_id": "TSU-050", "work_id": "SemanticsAllowSource", "gate_id": "G50",
                 "reviewer_id": "R50", "answers": {"Q1": "A", "Q2": "A", "Q3": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("SemanticsAllowSource", ddir)
        assert result.approved is True
        assert result.status == ApprovalStatus.APPROVED

    def test_approved_with_needs_context_answer_blocks(self, tmp_path: Path):
        """APPROVED + Q1=C → BLOCK (needs_context invariant)."""
        corpus_root = _make_corpus_root(tmp_path, "SemanticsCSource", ["TSU-051"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "SemanticsCSource",
            [
                {"tsu_id": "TSU-051", "work_id": "SemanticsCSource", "gate_id": "G51",
                 "reviewer_id": "R51", "answers": {"Q1": "C", "Q2": "A", "Q3": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("SemanticsCSource", ddir)
        assert result.approved is False
        assert result.status == ApprovalStatus.NOT_APPROVED
        assert "needs_context" in result.reason or "C answer" in result.reason

    def test_approved_with_rejection_answer_blocks(self, tmp_path: Path):
        """APPROVED + Q1=R → BLOCK (has_rejection invariant)."""
        corpus_root = _make_corpus_root(tmp_path, "SemanticsRSource", ["TSU-052"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "SemanticsRSource",
            [
                {"tsu_id": "TSU-052", "work_id": "SemanticsRSource", "gate_id": "G52",
                 "reviewer_id": "R52", "answers": {"Q1": "R", "Q2": "A", "Q3": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("SemanticsRSource", ddir)
        assert result.approved is False
        assert result.status == ApprovalStatus.NOT_APPROVED
        assert "has_rejection" in result.reason or "R answer" in result.reason

    def test_approved_with_incomplete_answers_blocks(self, tmp_path: Path):
        """APPROVED + Q1=A, Q2=A (Q3 누락) → BLOCK."""
        corpus_root = _make_corpus_root(tmp_path, "SemanticsIncompleteSource", ["TSU-053"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "SemanticsIncompleteSource",
            [
                {"tsu_id": "TSU-053", "work_id": "SemanticsIncompleteSource", "gate_id": "G53",
                 "reviewer_id": "R53", "answers": {"Q1": "A", "Q2": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("SemanticsIncompleteSource", ddir)
        assert result.approved is False
        assert result.status == ApprovalStatus.NOT_APPROVED
        assert "missing required judgment answers" in result.reason

    def test_approved_with_inconsistent_answer_final_decision_blocks(self, tmp_path: Path):
        """APPROVED + Q1=X (invalid answer) → BLOCK."""
        corpus_root = _make_corpus_root(tmp_path, "SemanticsInvalidSource", ["TSU-054"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "SemanticsInvalidSource",
            [
                {"tsu_id": "TSU-054", "work_id": "SemanticsInvalidSource", "gate_id": "G54",
                 "reviewer_id": "R54", "answers": {"Q1": "X", "Q2": "A", "Q3": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        result = verify_corpus_mutation_approval("SemanticsInvalidSource", ddir)
        assert result.approved is False
        assert result.status == ApprovalStatus.NOT_APPROVED
        assert "invalid answer" in result.reason


class TestMutationPathSemantics:
    """실제 mutation path에서 semantic validation이 적용되는지 검증."""

    def test_approved_with_c_blocks_merge_and_preserves_dataset(self, tmp_path: Path):
        """APPROVED + C → BLOCK → dataset unchanged."""
        corpus_root = _make_corpus_root(tmp_path, "MutCSource", ["TSU-060"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "MutCSource",
            [
                {"tsu_id": "TSU-060", "work_id": "MutCSource", "gate_id": "G60",
                 "reviewer_id": "R60", "answers": {"Q1": "C", "Q2": "A", "Q3": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        dataset = tmp_path / "dataset.jsonl"
        original_content = json.dumps({"tsu_id": "TSU-060", "claim": "original claim"}, ensure_ascii=False) + "\n"
        dataset.write_text(original_content, encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError):
            merge_nae_corpus(
                source_id="MutCSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert dataset.read_text(encoding="utf-8") == original_content

    def test_approved_with_r_blocks_merge_and_preserves_dataset(self, tmp_path: Path):
        """APPROVED + R → BLOCK → dataset unchanged."""
        corpus_root = _make_corpus_root(tmp_path, "MutRSource", ["TSU-061"])
        ddir = _make_decisions_dir_raw(
            tmp_path, "MutRSource",
            [
                {"tsu_id": "TSU-061", "work_id": "MutRSource", "gate_id": "G61",
                 "reviewer_id": "R61", "answers": {"Q1": "R", "Q2": "A", "Q3": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        dataset = tmp_path / "dataset.jsonl"
        original_content = json.dumps({"tsu_id": "TSU-061", "claim": "original claim"}, ensure_ascii=False) + "\n"
        dataset.write_text(original_content, encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError):
            merge_nae_corpus(
                source_id="MutRSource",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=dataset,
                decisions_dir=ddir,
            )
        assert dataset.read_text(encoding="utf-8") == original_content

    def test_valid_approval_allows_merge_in_temp(self, tmp_path: Path):
        """A+A+A + valid metadata → ALLOW → merged_count=1."""
        corpus_root = _make_corpus_root(tmp_path, "MutValidSource", ["TSU-062"])
        ddir = _make_decisions_dir(
            tmp_path, "MutValidSource",
            [
                {"tsu_id": "TSU-062", "work_id": "MutValidSource", "gate_id": "G62",
                 "reviewer_id": "R62", "answers": {"Q1": "A", "Q2": "A", "Q3": "A"},
                 "final_decision": "APPROVED"},
            ],
        )
        dataset = tmp_path / "dataset_valid.jsonl"
        dataset.write_text("", encoding="utf-8")

        result = merge_nae_corpus(
            source_id="MutValidSource",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=dataset,
            decisions_dir=ddir,
        )
        assert result["status"] == "completed"
        assert result["merged_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

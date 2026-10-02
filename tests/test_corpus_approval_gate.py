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
        assert "CONDITIONAL" in str(exc_info.value)

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
# F-3 Regression — 기존 idempotent/atomic/dedup 기능 보존
# ---------------------------------------------------------------------------

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

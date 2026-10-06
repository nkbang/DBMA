"""E-1a: equivalence tests for _evaluate_approval_core extraction.

Tests E1-E12 from the Task Order specification. No skips allowed.
Protects: _validate_target_paths, _validate_source_id, _load_approval_dir,
          _normalize_path_for_comparison, _paths_are_samefile,
          evaluate_approval_v2, _evaluate_approval_core.
"""

import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pytest

from scripts.merge_nae_corpus import (
    ApprovalEvaluation,
    ApprovalState,
    ApprovalReasonCode,
    evaluate_approval_v2,
    _evaluate_approval_core,
    _ValidatedApproval,
)


def _make_valid_payload(tmp_path: Path) -> dict:
    """Create a valid approval v2 payload."""
    return {
        "schema_version": 2,
        "source_id": "TEST_SOURCE",
        "target_paths_realpath": [
            str(tmp_path / "prod" / "data" / "reg" / "documents.json"),
            str(tmp_path / "prod" / "output" / "bench" / "tsu_manifest.json"),
            str(tmp_path / "prod" / "output" / "bench" / "tsu_dataset.jsonl"),
        ],
        "plan_hash": "sha256:" + "0" * 64,
        "reviewer_id": "reviewer-1",
        "gate_id": "gate-1",
        "dataset_sha256_before": "a" * 64,
        "final_decision": "APPROVED",
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_approval(tmp_path: Path, approval_dir: Path, name: str, payload: dict) -> Path:
    """Write an approval artifact to disk and return its path."""
    p = approval_dir / (name + ".json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _make_config(tmp_path: Path, prod: Path, approval_dir: Path) -> Path:
    """Create a minimal config.yaml with merge-safety section."""
    config = tmp_path / "config.yaml"
    config.write_text(
        f"merge-safety:\n  production_root: {prod}\n  approval_dir: {approval_dir}\n",
        encoding="utf-8",
    )
    return config


def _make_core_input(tmp_path: Path, payload=None, now=None, expected_target_paths=None):
    """Build all inputs for _evaluate_approval_core from a valid payload."""
    if payload is None:
        payload = _make_valid_payload(tmp_path)
    approval_dir = tmp_path / "approval_dir"
    approval_dir.mkdir(exist_ok=True)
    config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
    approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)
    raw_bytes = approval_path.read_bytes()
    if now is None:
        now = datetime.now(timezone.utc)
    return raw_bytes, approval_path, config, expected_target_paths, now


# ---------------------------------------------------------------------------
# E1: Valid approval full chain (core + wrapper)
# ---------------------------------------------------------------------------

class TestE1:
    def test_valid_approval_full_chain(self, tmp_path: Path):
        """E1: Valid approval passes through core and wrapper."""
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path)
        core_result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(core_result, _ValidatedApproval)
        result = evaluate_approval_v2(
            approval_path, config_path=config,
            dataset_sha256_current=core_result.dataset_sha256_before, now=now,
        )
        assert result.state == ApprovalState.VALID


# ---------------------------------------------------------------------------
# E2: Core rejection reasons (parametrized) — includes source_id=None → SOURCE_ID_UNSAFE
# ---------------------------------------------------------------------------

class TestE2:
    @pytest.mark.parametrize(
        "mutate_fn,expected_reason",
        [
            (lambda p: {**p, "schema_version": 1}, ApprovalReasonCode.SCHEMA_VERSION),
            (lambda p: {**p, "target_root_realpath": "/x"}, ApprovalReasonCode.FIELD_MISSING),
            (lambda p: {**p, "source_id": ""}, ApprovalReasonCode.SOURCE_ID_UNSAFE),
            (lambda p: {**p, "source_id": "../bad"}, ApprovalReasonCode.PATH_ESCAPE),
            (lambda p: {**p, "unknown_field": "x"}, ApprovalReasonCode.UNKNOWN_FIELD),
            (lambda p: {**p, "schema_version": "not_int"}, ApprovalReasonCode.SCHEMA_VERSION),
            (lambda p: {**p, "plan_hash": "bad"}, ApprovalReasonCode.FIELD_FORMAT),
            (lambda p: {**p, "approved_at": "not_iso"}, ApprovalReasonCode.FIELD_FORMAT),
            (lambda p: {**p, "final_decision": "REJECTED"}, ApprovalReasonCode.DECISION_NOT_APPROVED),
        ],
    )
    def test_core_rejection_reasons_match_legacy(self, tmp_path: Path, mutate_fn, expected_reason):
        """E2: Each mutation produces the expected rejection reason code."""
        payload = _make_valid_payload(tmp_path)
        payload = mutate_fn(payload)
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path, payload=payload)
        result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(result, ApprovalEvaluation)
        assert result.state == ApprovalState.REJECTED
        assert result.reason_code == expected_reason

    def test_source_id_missing_key_returns_SOURCE_ID_UNSAFE(self, tmp_path: Path):
        """E2-extra: source_id key absent (None) → SOURCE_ID_UNSAFE, NOT FIELD_MISSING.

        Per §3: 코어의 `if source_id is None:` 특례 분기를 삭제하고,
        None 도 기존 경로와 같이 `_validate_source_id(source_id)` 로 전달해
        `SOURCE_ID_UNSAFE` 가 유지되게 한다.
        """
        payload = _make_valid_payload(tmp_path)
        # Remove source_id key entirely so data.get("source_id") returns None
        del payload["source_id"]
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path, payload=payload)
        result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(result, ApprovalEvaluation)
        assert result.state == ApprovalState.REJECTED
        assert result.reason_code == ApprovalReasonCode.SOURCE_ID_UNSAFE
        # source_id field should be empty string (not isinstance(source_id, str))
        assert result.source_id == ""

    def test_source_id_explicit_none_returns_SOURCE_ID_UNSAFE(self, tmp_path: Path):
        """E2-extra: source_id explicitly set to None → SOURCE_ID_UNSAFE."""
        payload = _make_valid_payload(tmp_path)
        payload["source_id"] = None
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path, payload=payload)
        result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(result, ApprovalEvaluation)
        assert result.state == ApprovalState.REJECTED
        assert result.reason_code == ApprovalReasonCode.SOURCE_ID_UNSAFE
        assert result.source_id == ""


# ---------------------------------------------------------------------------
# E3: Core vs wrapper equivalence (same inputs → same state/reason/source_id)
# ---------------------------------------------------------------------------

class TestE3:
    def test_core_and_wrapper_agree_on_valid(self, tmp_path: Path):
        """E3: Valid case — core and wrapper agree on state, source_id."""
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path)
        core_result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(core_result, _ValidatedApproval)
        result = evaluate_approval_v2(
            approval_path, config_path=config,
            dataset_sha256_current=core_result.dataset_sha256_before, now=now,
        )
        assert result.state == ApprovalState.VALID
        assert result.source_id == core_result.source_id

    def test_core_and_wrapper_agree_on_rejection(self, tmp_path: Path):
        """E3: Rejection case — core and wrapper agree on state, reason_code, source_id."""
        payload = _make_valid_payload(tmp_path)
        del payload["source_id"]
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path, payload=payload)
        core_result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(core_result, ApprovalEvaluation)
        result = evaluate_approval_v2(
            approval_path, config_path=config,
            dataset_sha256_current="b" * 64, now=now,
        )
        assert result.state == core_result.state
        assert result.reason_code == core_result.reason_code
        assert result.source_id == core_result.source_id


# ---------------------------------------------------------------------------
# E4: _evaluate_approval_core does not read files
# ---------------------------------------------------------------------------

class TestE4:
    def test_core_does_not_read_file(self, tmp_path: Path):
        """E4: Core receives raw_bytes and must not open the approval file."""
        payload = _make_valid_payload(tmp_path)
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path, payload=payload)
        # Delete the file after reading bytes — core should still work
        approval_path.unlink()
        result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(result, _ValidatedApproval)


# ---------------------------------------------------------------------------
# E5: evaluate_approval_v2 signature unchanged
# ---------------------------------------------------------------------------

class TestE5:
    def test_public_signature_unchanged(self):
        """E5: Public function signature matches spec."""
        import inspect
        sig = inspect.signature(evaluate_approval_v2)
        params = sig.parameters
        assert "approval_path" in params
        assert "config_path" in params
        assert params["config_path"].default is None
        assert "expected_target_paths" in params
        assert params["expected_target_paths"].default is None
        assert "dataset_sha256_current" in params
        assert params["dataset_sha256_current"].kind == inspect.Parameter.KEYWORD_ONLY
        assert "now" in params
        assert params["now"].default is None


# ---------------------------------------------------------------------------
# E6: Protected functions are NOT mocked
# ---------------------------------------------------------------------------

class TestE6:
    def test_validate_source_id_not_mocked(self):
        """E6: _validate_source_id is the real function, not a mock."""
        from scripts.merge_nae_corpus import _validate_source_id
        # Real function rejects empty string
        ok, reason = _validate_source_id("")
        assert ok is False
        assert reason == ApprovalReasonCode.SOURCE_ID_UNSAFE
        # Real function rejects non-string
        ok, reason = _validate_source_id(None)
        assert ok is False
        assert reason == ApprovalReasonCode.SOURCE_ID_UNSAFE
        # Real function rejects path escape
        ok, reason = _validate_source_id("../bad")
        assert ok is False
        assert reason == ApprovalReasonCode.PATH_ESCAPE

    def test_validate_target_paths_not_mocked(self):
        """E6: _validate_target_paths is the real function, not a mock."""
        from scripts.merge_nae_corpus import _validate_target_paths
        tmp_path = Path("/tmp/e6_test")
        tmp_path.mkdir(exist_ok=True)
        # Real function compares actual paths
        approval_paths = [str(tmp_path / "a"), str(tmp_path / "b"), str(tmp_path / "c")]
        expected = [str(tmp_path / "a"), str(tmp_path / "b"), str(tmp_path / "c")]
        ok, reason = _validate_target_paths(approval_paths, expected)
        assert ok is True

    def test_normalize_path_for_comparison_not_mocked(self):
        """E6: _normalize_path_for_comparison uses NFC + casefold."""
        from scripts.merge_nae_corpus import _normalize_path_for_comparison
        import unicodedata
        p = Path("/test/Path")
        normalized = _normalize_path_for_comparison(p)
        expected = unicodedata.normalize("NFC", str(p)).casefold()
        assert normalized == expected

    def test_paths_are_samefile_not_mocked(self, tmp_path: Path):
        """E6: _paths_are_samefile uses os.path.samefile."""
        from scripts.merge_nae_corpus import _paths_are_samefile
        p1 = tmp_path / "test_file"
        p1.write_text("test", encoding="utf-8")
        assert _paths_are_samefile(p1, p1) is True
        p2 = tmp_path / "other_file"
        p2.write_text("test", encoding="utf-8")
        assert _paths_are_samefile(p1, p2) is False


# ---------------------------------------------------------------------------
# E7: Access pattern — exists 1x + read_bytes 1x (wrapper level)
# ---------------------------------------------------------------------------

class TestE7:
    def test_wrapper_access_pattern(self, tmp_path: Path):
        """E7: evaluate_approval_v2 calls approval_path.exists() once and read_bytes() once."""
        payload = _make_valid_payload(tmp_path)
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        # Patch to count calls only on the specific approval_path
        exists_count = [0]
        read_bytes_count = [0]
        original_exists = Path.exists
        original_read_bytes = Path.read_bytes

        def counting_exists(self):
            if self == approval_path:
                exists_count[0] += 1
            return original_exists(self)

        def counting_read_bytes(self):
            if self == approval_path:
                read_bytes_count[0] += 1
            return original_read_bytes(self)

        Path.exists = counting_exists
        Path.read_bytes = counting_read_bytes
        try:
            result = evaluate_approval_v2(
                approval_path, config_path=config,
                dataset_sha256_current="a" * 64,
                now=datetime.now(timezone.utc),
            )
            assert result.state == ApprovalState.VALID
            assert exists_count[0] == 1, f"exists called {exists_count[0]} times on approval_path, expected 1"
            assert read_bytes_count[0] == 1, f"read_bytes called {read_bytes_count[0]} times on approval_path, expected 1"
        finally:
            Path.exists = original_exists
            Path.read_bytes = original_read_bytes


# ---------------------------------------------------------------------------
# E8: now rules — timezone handling
# ---------------------------------------------------------------------------

class TestE8:
    def test_now_with_tz_vs_naive_approved_at(self, tmp_path: Path):
        """E8: now with tzinfo vs approved_at without tzinfo — should handle gracefully."""
        payload = _make_valid_payload(tmp_path)
        # Remove tzinfo from approved_at
        approved_dt = datetime.now(timezone.utc)
        payload["approved_at"] = approved_dt.replace(tzinfo=None).isoformat()
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path, payload=payload, now=approved_dt)
        result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(result, _ValidatedApproval)

    def test_now_naive_vs_tz_approved_at(self, tmp_path: Path):
        """E8: now without tzinfo vs approved_at with tzinfo — timezone bridging works."""
        payload = _make_valid_payload(tmp_path)
        # Use a now that is within the 5-minute window of approved_at
        base_dt = datetime.now(timezone.utc)
        payload["approved_at"] = base_dt.isoformat()
        naive_now = base_dt.replace(tzinfo=None) + timedelta(seconds=10)
        raw_bytes, approval_path, config, _, now = _make_core_input(
            tmp_path, payload=payload,
            now=naive_now,
        )
        result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(result, _ValidatedApproval)


# ---------------------------------------------------------------------------
# E9: Core works with nonexistent path (receives raw_bytes, not file path)
# ---------------------------------------------------------------------------

class TestE9:
    def test_core_with_nonexistent_path(self, tmp_path: Path):
        """E9: Core must work even when approval_path does not exist — it receives raw_bytes."""
        payload = _make_valid_payload(tmp_path)
        raw_str = json.dumps(payload)
        raw_bytes = raw_str.encode("utf-8")

        # Provide a valid config and approval_dir (but fake_path does not exist)
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)

        # fake_path is under approval_dir but does NOT exist on disk
        fake_path = approval_dir / "nonexistent_approval.json"

        result = _evaluate_approval_core(raw_bytes, fake_path, config, None, now=datetime.now(timezone.utc))
        assert isinstance(result, _ValidatedApproval)


# ---------------------------------------------------------------------------
# E10: _evaluate_approval_core signature
# ---------------------------------------------------------------------------

class TestE10:
    def test_core_signature(self):
        """E10: Core function signature matches spec."""
        import inspect
        sig = inspect.signature(_evaluate_approval_core)
        params = sig.parameters
        assert "dataset_sha256_current" not in params
        assert "now" in params
        assert params["now"].kind == inspect.Parameter.KEYWORD_ONLY
        assert params["now"].default == inspect.Parameter.empty


# ---------------------------------------------------------------------------
# E11: Rejected result fields — plan_hash/artifact_sha256/artifact_path are None
# ---------------------------------------------------------------------------

class TestE11:
    def test_rejected_none_fields(self, tmp_path: Path):
        """E11: REJECTED results have None for plan_hash, artifact_sha256, artifact_path."""
        payload = _make_valid_payload(tmp_path)
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path, payload=payload)
        bad_payload = {**payload, "final_decision": "REJECTED"}
        raw_bytes_bad, _, _, _, _ = _make_core_input(tmp_path, payload=bad_payload)
        core_result = _evaluate_approval_core(raw_bytes_bad, approval_path, config, None, now=now)
        assert isinstance(core_result, ApprovalEvaluation)
        assert core_result.plan_hash is None
        assert core_result.artifact_sha256 is None
        assert core_result.artifact_path is None

    def test_scope_only_on_dataset_sha_mismatch(self, tmp_path: Path):
        """E11: scope field is set only on DATASET_SHA_MISMATCH."""
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path)
        core_result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(core_result, _ValidatedApproval)
        result = evaluate_approval_v2(
            approval_path, config_path=config,
            dataset_sha256_current="b" * 64, now=now,
        )
        assert result.scope is not None

    def test_valid_result_has_no_scope(self, tmp_path: Path):
        """E11: VALID results have scope=None."""
        raw_bytes, approval_path, config, _, now = _make_core_input(tmp_path)
        core_result = _evaluate_approval_core(raw_bytes, approval_path, config, None, now=now)
        assert isinstance(core_result, _ValidatedApproval)
        result = evaluate_approval_v2(
            approval_path, config_path=config,
            dataset_sha256_current=core_result.dataset_sha256_before, now=now,
        )
        assert result.state == ApprovalState.VALID
        assert result.scope is None


# ---------------------------------------------------------------------------
# E12: Public API surface unchanged
# ---------------------------------------------------------------------------

class TestE12:
    def test_public_signature_unchanged(self):
        """E12: evaluate_approval_v2 signature matches spec."""
        import inspect
        sig = inspect.signature(evaluate_approval_v2)
        params = sig.parameters
        assert "approval_path" in params
        assert "config_path" in params
        assert params["config_path"].default is None
        assert "expected_target_paths" in params
        assert params["expected_target_paths"].default is None
        assert "dataset_sha256_current" in params
        assert params["dataset_sha256_current"].kind == inspect.Parameter.KEYWORD_ONLY
        assert "now" in params
        assert params["now"].default is None

    def test_approval_evaluation_fields_unchanged(self):
        """E12: ApprovalEvaluation fields match spec."""
        from scripts.merge_nae_corpus import ApprovalEvaluation, ApprovalReasonCode
        assert ApprovalEvaluation is not None
        assert ApprovalReasonCode is not None
        # Check that all expected fields exist
        eval_instance = ApprovalEvaluation(
            state=ApprovalState.VALID,
            reason_code=None,
            source_id="test",
            approved_at="2026-01-01T00:00:00+00:00",
            dataset_sha256_before="a" * 64,
            plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64,
            artifact_path="/test/path",
        )
        assert eval_instance.state == ApprovalState.VALID
        assert eval_instance.reason_code is None
        assert eval_instance.source_id == "test"
        assert eval_instance.approved_at == "2026-01-01T00:00:00+00:00"
        assert eval_instance.dataset_sha256_before == "a" * 64
        assert eval_instance.plan_hash == "sha256:" + "0" * 64
        assert eval_instance.artifact_sha256 == "b" * 64
        assert eval_instance.artifact_path == "/test/path"

    def test_validated_approval_fields_unchanged(self):
        """E12: _ValidatedApproval fields match spec."""
        from scripts.merge_nae_corpus import _ValidatedApproval
        va = _ValidatedApproval(
            source_id="test",
            approved_at="2026-01-01T00:00:00+00:00",
            dataset_sha256_before="a" * 64,
            plan_hash="sha256:" + "0" * 64,
            reviewer_id="reviewer-1",
            gate_id="gate-1",
            target_paths_realpath=("/a", "/b", "/c"),
            artifact_sha256="b" * 64,
            artifact_path="/test/path",
        )
        assert va.source_id == "test"
        assert va.approved_at == "2026-01-01T00:00:00+00:00"
        assert va.dataset_sha256_before == "a" * 64
        assert va.plan_hash == "sha256:" + "0" * 64
        assert va.reviewer_id == "reviewer-1"
        assert va.gate_id == "gate-1"
        assert va.target_paths_realpath == ("/a", "/b", "/c")
        assert va.artifact_sha256 == "b" * 64
        assert va.artifact_path == "/test/path"

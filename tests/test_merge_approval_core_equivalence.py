"""E-1a: equivalence tests for _evaluate_approval_core extraction.

Tests E1-E12 from the Task Order specification. No skips allowed.
Protects: _validate_target_paths, _validate_source_id, _load_approval_dir,
          _normalize_path_for_comparison, _paths_are_samefile,
          evaluate_approval_v2, _evaluate_approval_core.
"""

import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import pytest

from scripts.merge_nae_corpus import (
    ApprovalEvaluation,
    ApprovalState,
    ApprovalReasonCode,
    CorpusMutationBlockedError,
    FRESH_MERGE_PRECONDITION,
    _APPROVAL_V2_REQUIRED_FIELDS,
    evaluate_approval_v2,
    _evaluate_approval_core,
    _ValidatedApproval,
    _validate_source_id,
    _load_approval_dir,
    _normalize_path_for_comparison,
    _validate_target_paths,
)


# ---------------------------------------------------------------------------
# Fixed-time fixture for deterministic comparison
# ---------------------------------------------------------------------------

FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Legacy copy from BASE (ebd9c95) evaluate_approval_v2
# ---------------------------------------------------------------------------
def _legacy_evaluate_approval_v2(
    approval_path: Path,
    config_path: Optional[Path] = None,
    expected_target_paths: Optional[list[str]] = None,
    *,
    dataset_sha256_current: str,
    now: Optional[datetime] = None,
) -> ApprovalEvaluation:
    """Evaluate an Approval v2 artifact immutably (S2-A §3-8).

    Does NOT modify the approval artifact. Returns an immutable ApprovalEvaluation.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if not approval_path.exists():
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.NOT_FOUND,
            source_id="",
        )

    # S2-C: read the artifact bytes exactly once. The same bytes are decoded, parsed, validated
    # and hashed (artifact_sha256); the file is never re-read afterwards.
    # Existing error mapping is preserved: OSError -> MALFORMED (UNREADABLE is not used here).
    # A non-UTF-8 artifact is MALFORMED as well (previously UnicodeDecodeError escaped).
    try:
        raw_bytes = approval_path.read_bytes()
        raw = raw_bytes.decode("utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.MALFORMED,
            source_id="",
        )

    if not isinstance(data, dict):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.MALFORMED,
            source_id="",
        )

    sv = data.get("schema_version")
    if not isinstance(sv, int) or sv != 2:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.SCHEMA_VERSION,
            source_id=str(data.get("source_id", "")),
        )
    if "target_root_realpath" in data:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_MISSING,
            source_id=str(data.get("source_id", "")),
        )

    source_id = data.get("source_id")
    valid_sid, sid_reason = _validate_source_id(source_id)
    if not valid_sid:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=sid_reason,
            source_id=str(source_id) if isinstance(source_id, str) else "",
        )

    try:
        approval_dir_str = _load_approval_dir(config_path)
    except CorpusMutationBlockedError:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.CONFIG_APPROVAL_DIR,
            source_id=source_id,
        )

    try:
        approval_resolved = approval_path.resolve()
        approval_dir_resolved = Path(approval_dir_str).resolve()
        # Check if approval file is under approval_dir (containment)
        # Uses common identity building blocks — no duplicate NFC/casefold impl
        approval_parent_norm = _normalize_path_for_comparison(approval_resolved.parent)
        dir_norm = _normalize_path_for_comparison(approval_dir_resolved)
        approval_full_norm = _normalize_path_for_comparison(approval_resolved)
        if not (
            approval_parent_norm == dir_norm
            or approval_full_norm.startswith(dir_norm + os.sep)
            or approval_parent_norm.startswith(dir_norm + os.sep)
        ):
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.PATH_ESCAPE,
                source_id=source_id,
            )
    except OSError:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.PATH_ESCAPE,
            source_id=source_id,
        )

    known_fields = _APPROVAL_V2_REQUIRED_FIELDS
    for key in data:
        if key not in known_fields:
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.UNKNOWN_FIELD,
                source_id=source_id,
            )

    for field in _APPROVAL_V2_REQUIRED_FIELDS:
        if field not in data:
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.FIELD_MISSING,
                source_id=source_id,
            )

    # Type validation (S2-A §3-1)
    schema_version = data["schema_version"]
    if not isinstance(schema_version, int):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    target_paths = data["target_paths_realpath"]
    if not isinstance(target_paths, list):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    plan_hash = data["plan_hash"]
    if not isinstance(plan_hash, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    reviewer_id = data["reviewer_id"]
    if not isinstance(reviewer_id, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    gate_id = data["gate_id"]
    if not isinstance(gate_id, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    dataset_sha256_before = data["dataset_sha256_before"]
    if not isinstance(dataset_sha256_before, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    final_decision = data["final_decision"]
    if not isinstance(final_decision, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    approved_at_str = data["approved_at"]
    if not isinstance(approved_at_str, str):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_TYPE,
            source_id=source_id,
        )

    # Format validation (S2-A §3-1)
    if not isinstance(plan_hash, str) or not plan_hash.startswith("sha256:"):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )
    hex_part = plan_hash[7:]
    if len(hex_part) != 64 or not all(c in "0123456789abcdef" for c in hex_part):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )

    if len(dataset_sha256_before) != 64 or not all(c in "0123456789abcdef" for c in dataset_sha256_before):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )

    # approved_at: ISO-8601 parsing + future check (S2-A §3-9)
    try:
        approved_dt = datetime.fromisoformat(approved_at_str)
    except (ValueError, TypeError):
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FIELD_FORMAT,
            source_id=source_id,
        )

    if approved_dt.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=approved_dt.tzinfo)
    elif now.tzinfo is not None and approved_dt.tzinfo is None:
        approved_dt = approved_dt.replace(tzinfo=now.tzinfo)

    diff = approved_dt - now
    if diff.total_seconds() > 300:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.FUTURE_APPROVAL,
            source_id=source_id,
            approved_at=approved_at_str,
        )

    # final_decision must be exactly "APPROVED" (S2-A §3-7)
    if final_decision != "APPROVED":
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.DECISION_NOT_APPROVED,
            source_id=source_id,
        )

    # target_paths validation (S2-A §3-6)
    if expected_target_paths is not None:
        paths_valid, _ = _validate_target_paths(target_paths, expected_target_paths)
        if not paths_valid:
            return ApprovalEvaluation(
                state=ApprovalState.REJECTED,
                reason_code=ApprovalReasonCode.TARGET_MISMATCH,
                source_id=source_id,
            )

    # dataset_sha256_before validation (S2-A §3-10)
    # scope="FRESH_MERGE_PRECONDITION" — 이 값은 recovery 자격의 단독 기준이 아니다
    # (recovery invariant 는 S2-E 에서 확정)
    if dataset_sha256_current != dataset_sha256_before:
        return ApprovalEvaluation(
            state=ApprovalState.REJECTED,
            reason_code=ApprovalReasonCode.DATASET_SHA_MISMATCH,
            source_id=source_id,
            scope=FRESH_MERGE_PRECONDITION,
        )

    return ApprovalEvaluation(
        state=ApprovalState.VALID,
        reason_code=None,
        source_id=source_id,
        approved_at=approved_at_str,
        dataset_sha256_before=dataset_sha256_before,
        plan_hash=plan_hash,
        artifact_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        artifact_path=str(Path(approval_path).resolve()),
    )


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _compare_evaluation(a: ApprovalEvaluation, b: ApprovalEvaluation, label_a="", label_b="") -> list[str]:
    """Compare all declared fields of two ApprovalEvaluation results.

    Uses ApprovalEvaluation.__dataclass_fields__ as the authoritative field list.
    Fails immediately (raises AssertionError) if a field does not exist on either instance.
    """
    issues = []
    declared = set(ApprovalEvaluation.__dataclass_fields__.keys())
    for field in sorted(declared):
        # Fail immediately if field is missing from either instance
        if not hasattr(a, field):
            raise AssertionError(f"{label_a or 'a'} missing field: {field}")
        if not hasattr(b, field):
            raise AssertionError(f"{label_b or 'b'} missing field: {field}")
        va = getattr(a, field)
        vb = getattr(b, field)
        if va != vb:
            issues.append(f"  {field}: {label_a}={va!r} vs {label_b}={vb!r}")
    return issues




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
        "approved_at": FIXED_NOW.isoformat(),
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
# E1a: New vs Legacy equivalence comparison (actual call + assert)
# ---------------------------------------------------------------------------


def _build_legacy_input(tmp_path: Path, payload=None, now=None):
    """Build inputs for both evaluate_approval_v2 and _legacy_evaluate_approval_v2."""
    if payload is None:
        payload = _make_valid_payload(tmp_path)
    approval_dir = tmp_path / "approval_dir"
    approval_dir.mkdir(exist_ok=True)
    config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
    approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)
    if now is None:
        now = FIXED_NOW
    return approval_path, config, now


def _compare_new_legacy(approval_path, config, dataset_sha256_current, now, expected_target_paths=None):
    """Call both new and legacy, return comparison issues.

    Both public functions receive the same `expected_target_paths`.
    Returns a list of issue strings; empty means identical behaviour.

    Exception handling:
    - If only one side raises → failure (recorded as issue)
    - If both sides raise → compare exception type and message
    - If neither raises → compare return values via _compare_evaluation
    """
    new_raised = None
    new_result = None
    legacy_raised = None
    legacy_result = None

    try:
        new_result = evaluate_approval_v2(
            approval_path, config_path=config,
            expected_target_paths=expected_target_paths,
            dataset_sha256_current=dataset_sha256_current, now=now,
        )
    except Exception as e:
        new_raised = (type(e), str(e))

    try:
        legacy_result = _legacy_evaluate_approval_v2(
            approval_path, config_path=config,
            expected_target_paths=expected_target_paths,
            dataset_sha256_current=dataset_sha256_current, now=now,
        )
    except Exception as e:
        legacy_raised = (type(e), str(e))

    # Exception comparison
    if new_raised is not None and legacy_raised is None:
        return [f"new raised {new_raised[0].__name__}: {new_raised[1]}, legacy did not raise"]
    if new_raised is None and legacy_raised is not None:
        return [f"legacy raised {legacy_raised[0].__name__}: {legacy_raised[1]}, new did not raise"]
    if new_raised is not None and legacy_raised is not None:
        # Both raised — compare type and message
        if new_raised[0] != legacy_raised[0]:
            return [f"exception type mismatch: new={new_raised[0].__name__}, legacy={legacy_raised[0].__name__}"]
        if new_raised[1] != legacy_raised[1]:
            return [f"exception message mismatch: new='{new_raised[1]}', legacy='{legacy_raised[1]}'"]
        return []  # Both raised identical exceptions

    # Neither raised — compare return values
    return _compare_evaluation(new_result, legacy_result, "new", "legacy")


class TestE1a:
    """E1a: Actual new/legacy comparison tests."""

    def test_valid_approval_new_legacy_match(self, tmp_path: Path):
        """E1a-1: Valid approval - new and legacy produce identical results."""
        approval_path, config, now = _build_legacy_input(tmp_path)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on valid approval:\n" + "\n".join(issues)

    def test_schema_version_mismatch_new_legacy_match(self, tmp_path: Path):
        """E1a-2: schema_version != 2 - both reject with SCHEMA_VERSION."""
        payload = _make_valid_payload(tmp_path)
        payload["schema_version"] = 1
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on schema_version=1:\n" + "\n".join(issues)

    def test_source_id_empty_new_legacy_match(self, tmp_path: Path):
        """E1a-3: source_id='' - both reject with SOURCE_ID_UNSAFE."""
        payload = _make_valid_payload(tmp_path)
        payload["source_id"] = ""
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on source_id='':\n" + "\n".join(issues)

    def test_unknown_field_new_legacy_match(self, tmp_path: Path):
        """E1a-4: unknown field - both reject with UNKNOWN_FIELD."""
        payload = _make_valid_payload(tmp_path)
        payload["unknown_field"] = "x"
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on unknown_field:\n" + "\n".join(issues)

    def test_future_approval_new_legacy_match(self, tmp_path: Path):
        """E1a-5: approved_at in future - both reject with FUTURE_APPROVAL."""
        payload = _make_valid_payload(tmp_path)
        payload["approved_at"] = (FIXED_NOW.replace(tzinfo=timezone.utc) + timedelta(days=10)).isoformat()
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on future approved_at:\n" + "\n".join(issues)

    def test_dataset_sha_mismatch_new_legacy_match(self, tmp_path: Path):
        """E1a-6: dataset_sha256 mismatch - both reject with DATASET_SHA_MISMATCH."""
        approval_path, config, now = _build_legacy_input(tmp_path)
        issues = _compare_new_legacy(
            approval_path, config, "b" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on dataset_sha256 mismatch:\n" + "\n".join(issues)

    def test_nonexistent_approval_path(self, tmp_path: Path):
        """E1a-7: Non-existent approval path - both reject with NOT_FOUND."""
        fake_path = tmp_path / "nonexistent" / "approval.json"
        issues = _compare_new_legacy(
            fake_path, None, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"New/legacy mismatch on nonexistent path:\n" + "\n".join(issues)

    # -----------------------------------------------------------------------
    # V3 추가 사례: 기존 거절 입력 (target_paths_realpath 누락 등)
    # -----------------------------------------------------------------------

    def test_missing_target_paths_realpath_new_legacy_match(self, tmp_path: Path):
        """E1a-8: target_paths_realpath missing - both reject with FIELD_MISSING."""
        payload = _make_valid_payload(tmp_path)
        del payload["target_paths_realpath"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing target_paths_realpath:\n" + "\n".join(issues)

    def test_missing_plan_hash_new_legacy_match(self, tmp_path: Path):
        """E1a-9: plan_hash missing - both reject with FIELD_MISSING."""
        payload = _make_valid_payload(tmp_path)
        del payload["plan_hash"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing plan_hash:\n" + "\n".join(issues)

    def test_missing_reviewer_id_new_legacy_match(self, tmp_path: Path):
        """E1a-10: reviewer_id missing - both reject with FIELD_MISSING."""
        payload = _make_valid_payload(tmp_path)
        del payload["reviewer_id"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing reviewer_id:\n" + "\n".join(issues)

    def test_missing_gate_id_new_legacy_match(self, tmp_path: Path):
        """E1a-11: gate_id missing - both reject with FIELD_MISSING."""
        payload = _make_valid_payload(tmp_path)
        del payload["gate_id"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing gate_id:\n" + "\n".join(issues)

    def test_missing_dataset_sha256_before_new_legacy_match(self, tmp_path: Path):
        """E1a-12: dataset_sha256_before missing - both reject with FIELD_MISSING."""
        payload = _make_valid_payload(tmp_path)
        del payload["dataset_sha256_before"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing dataset_sha256_before:\n" + "\n".join(issues)

    def test_missing_final_decision_new_legacy_match(self, tmp_path: Path):
        """E1a-13: final_decision missing - both reject with FIELD_MISSING."""
        payload = _make_valid_payload(tmp_path)
        del payload["final_decision"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing final_decision:\n" + "\n".join(issues)

    def test_missing_approved_at_new_legacy_match(self, tmp_path: Path):
        """E1a-14: approved_at missing - both reject with FIELD_MISSING."""
        payload = _make_valid_payload(tmp_path)
        del payload["approved_at"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing approved_at:\n" + "\n".join(issues)

    # -----------------------------------------------------------------------
    # V3 추가 사례: source_id — 키 누락, None, 경로 탈출
    # -----------------------------------------------------------------------

    def test_source_id_key_missing_new_legacy_match(self, tmp_path: Path):
        """E1a-15: source_id key missing - both reject with SOURCE_ID_UNSAFE."""
        payload = _make_valid_payload(tmp_path)
        del payload["source_id"]
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on missing source_id:\n" + "\n".join(issues)

    def test_source_id_none_new_legacy_match(self, tmp_path: Path):
        """E1a-16: source_id=None - both reject with SOURCE_ID_UNSAFE."""
        payload = _make_valid_payload(tmp_path)
        payload["source_id"] = None
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on source_id=None:\n" + "\n".join(issues)

    def test_source_id_path_escape_new_legacy_match(self, tmp_path: Path):
        """E1a-17: source_id with '..' path escape - both reject with PATH_ESCAPE."""
        payload = _make_valid_payload(tmp_path)
        payload["source_id"] = "foo/../../etc/passwd"
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, now,
        )
        assert issues == [], f"New/legacy mismatch on source_id path escape:\n" + "\n".join(issues)

    # -----------------------------------------------------------------------
    # V3 추가 사례: 승인 파일 — 잘못된 JSON
    # -----------------------------------------------------------------------

    def test_invalid_json_new_legacy_match(self, tmp_path: Path):
        """E1a-18: Invalid JSON file - both reject with MALFORMED."""
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        approval_path = approval_dir / "test_source_approval.json"
        approval_path.write_text("{invalid json content", encoding="utf-8")
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"New/legacy mismatch on invalid JSON:\n" + "\n".join(issues)

    # -----------------------------------------------------------------------
    # V3 추가 사례: 대상 경로 — 명시적 기대 경로 일치·불일치
    # -----------------------------------------------------------------------

    def test_expected_target_paths_match_new_legacy(self, tmp_path: Path):
        """E1a-19: expected_target_paths matching - both accept (VALID)."""
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        prod_dir = tmp_path / "prod"
        prod_dir.mkdir(exist_ok=True)
        # Create actual files for target paths
        target_files = []
        for i in range(3):
            f = prod_dir / f"target_{i}.txt"
            f.write_text(f"content{i}", encoding="utf-8")
            target_files.append(str(f.resolve()))
        config = _make_config(tmp_path, prod_dir, approval_dir)
        payload = _make_valid_payload(tmp_path)
        payload["target_paths_realpath"] = target_files
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)
        # Compare with matching expected paths
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
            expected_target_paths=target_files,
        )
        assert issues == [], f"New/legacy mismatch on matching target paths:\n" + "\n".join(issues)

    def test_expected_target_paths_mismatch_new_legacy(self, tmp_path: Path):
        """E1a-20: expected_target_paths mismatch - both reject with TARGET_MISMATCH."""
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        prod_dir = tmp_path / "prod"
        prod_dir.mkdir(exist_ok=True)
        # Create actual files for target paths
        target_files = []
        for i in range(3):
            f = prod_dir / f"target_{i}.txt"
            f.write_text(f"content{i}", encoding="utf-8")
            target_files.append(str(f.resolve()))
        config = _make_config(tmp_path, prod_dir, approval_dir)
        payload = _make_valid_payload(tmp_path)
        payload["target_paths_realpath"] = target_files
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)
        # Compare with mismatching expected paths
        fake_paths = [str((tmp_path / f"fake_{i}.txt").resolve()) for i in range(3)]
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
            expected_target_paths=fake_paths,
        )
        assert issues == [], f"New/legacy mismatch on target paths mismatch:\n" + "\n".join(issues)

    # -----------------------------------------------------------------------
    # V3 추가 사례: 승인 시각 — 경계 직전·동일·직후
    # -----------------------------------------------------------------------

    def test_approved_at_boundary_before_new_legacy(self, tmp_path: Path):
        """E1a-21: approved_at 299s before now (past approval, not future) - both accept.

        approved_at이 과거이므로 approved_dt - now < 0 → 거절 조건 (approved_dt - now > 300) 불만족 → ACCEPT.
        """
        payload = _make_valid_payload(tmp_path)
        approved_dt = FIXED_NOW - timedelta(seconds=299)
        payload["approved_at"] = approved_dt.isoformat()
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload, now=FIXED_NOW)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"New/legacy mismatch on approved_at 299s before now:\n" + "\n".join(issues)

    def test_approved_at_boundary_exact_new_legacy(self, tmp_path: Path):
        """E1a-22: approved_at exactly now (0s diff, not future) - both accept.

        approved_dt == now → approved_dt - now = 0 → 거절 조건 불만족 → ACCEPT.
        """
        payload = _make_valid_payload(tmp_path)
        payload["approved_at"] = FIXED_NOW.isoformat()
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload, now=FIXED_NOW)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"New/legacy mismatch on approved_at exactly now:\n" + "\n".join(issues)

    def test_approved_at_boundary_after_new_legacy(self, tmp_path: Path):
        """E1a-23: approved_at 1s after now (future, but within 300s allowance) - both accept.

        approved_dt - now = 1 → 1 > 300 불만족 → ACCEPT (미래 시각 허용 한계 내).
        """
        payload = _make_valid_payload(tmp_path)
        approved_dt = FIXED_NOW + timedelta(seconds=1)
        payload["approved_at"] = approved_dt.isoformat()
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload, now=FIXED_NOW)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"New/legacy mismatch on approved_at 1s after now:\n" + "\n".join(issues)

    def test_approved_at_boundary_300s_new_legacy(self, tmp_path: Path):
        """E1a-24: approved_at exactly 300s after now (boundary of future allowance) - both reject.

        approved_dt - now = 300 → 300 > 300 불만족 (strict greater-than) → ACCEPT 가 아님.
        실제 코드는 approved_dt - now > 300 이므로 300 은 거절되지 않음 — 양쪽 동일 결과 확인.
        """
        payload = _make_valid_payload(tmp_path)
        approved_dt = FIXED_NOW + timedelta(seconds=300)
        payload["approved_at"] = approved_dt.isoformat()
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload, now=FIXED_NOW)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"New/legacy mismatch on approved_at exactly 300s after now:\n" + "\n".join(issues)

    def test_approved_at_boundary_301s_new_legacy(self, tmp_path: Path):
        """E1a-25: approved_at 301s after now (beyond future allowance) - both reject with FUTURE_APPROVAL.

        approved_dt - now = 301 → 301 > 300 만족 → FUTURE_APPROVAL 거절.
        """
        payload = _make_valid_payload(tmp_path)
        approved_dt = FIXED_NOW + timedelta(seconds=301)
        payload["approved_at"] = approved_dt.isoformat()
        approval_path, config, now = _build_legacy_input(tmp_path, payload=payload, now=FIXED_NOW)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"New/legacy mismatch on approved_at 301s after now:\n" + "\n".join(issues)
    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    # V7: Corrected exception and error-handling tests (replaces V5-E1~E6)
    # ---------------------------------------------------------------------------

    def test_read_failure_both_raise_same(self, tmp_path: Path):
        """V7-E1: approval_path read_bytes 에만 OSError 주입 → 양쪽 REJECTED/MALFORMED 및 전체 필드 일치.

        보완 사항 (V7B-FINAL):
        - 비대상 파일에 고정 바이트를 기록하고, 패치 안에서 그 바이트가 그대로 반환되는지 단언
        - 비대상 읽기가 대상 오류 주입 횟수에 포함되지 않는지 확인
        - 패치 종료 후 read_bytes 가 원래 메서드로 복원됐는지 단언
        - 패치 종료 후 대상 승인 파일도 정상적으로 읽히는지 단언
        """
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        payload = _make_valid_payload(tmp_path)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        # 비대상 파일: 고정 바이트 기록 (tmp_path fixture 만 사용)
        non_target_file = tmp_path / "non_target_fixture.dat"
        FIXED_NON_TARGET_BYTES = b"V7B-FINAL-non-target-fixed-bytes-preserve-check"
        non_target_file.write_bytes(FIXED_NON_TARGET_BYTES)

        # 원본 메서드 저장
        import unittest.mock as mock
        original_read_bytes = type(approval_path).read_bytes

        call_log = []  # [(path_obj, is_target)] 기록

        def mock_read_bytes(self_obj):
            is_target = (self_obj == approval_path)
            call_log.append((self_obj, is_target))
            if is_target:
                # 대상 파일: OSError 주입
                raise OSError("mock: unreadable file")
            else:
                # 비대상 파일: 원래 동작으로 위임
                return original_read_bytes(self_obj)

        with mock.patch.object(type(approval_path), 'read_bytes', mock_read_bytes):
            # 비대상 파일 읽기가 고정 바이트를 그대로 반환하는지 단언
            non_target_read = non_target_file.read_bytes()
            assert non_target_read == FIXED_NON_TARGET_BYTES, \
                f"non-target file bytes corrupted: {non_target_read!r} != {FIXED_NON_TARGET_BYTES!r}"

            # 신규 호출 후 대상 주입 1회 확인
            new_result = evaluate_approval_v2(
                approval_path, config_path=config,
                expected_target_paths=None,
                dataset_sha256_current="a" * 64, now=FIXED_NOW,
            )
            new_target_calls = sum(1 for _, is_t in call_log if is_t)
            assert new_target_calls == 1, \
                f"new target injection count: {new_target_calls}"

            # 비대상 읽기가 대상 주입 횟수에 포함되지 않는지 확인
            non_target_calls = sum(1 for _, is_t in call_log if not is_t)
            assert non_target_calls >= 1, \
                f"non-target read count should be >= 1: {non_target_calls}"

            legacy_result = _legacy_evaluate_approval_v2(
                approval_path, config_path=config,
                expected_target_paths=None,
                dataset_sha256_current="a" * 64, now=FIXED_NOW,
            )
            # legacy 호출 후 누적 대상 주입 2회 확인 (new 1 + legacy 1)
            legacy_target_calls = sum(1 for _, is_t in call_log if is_t)
            assert legacy_target_calls == 2, \
                f"legacy target injection count: {legacy_target_calls}"

        # 패치 종료 후 read_bytes 가 원래 메서드로 복원됐는지 단언
        current_read_bytes = type(approval_path).read_bytes
        assert current_read_bytes is original_read_bytes, \
            f"read_bytes not restored after patch: {current_read_bytes} != {original_read_bytes}"

        # 패치 종료 후 대상 승인 파일도 정상적으로 읽히는지 단언
        restored_bytes = approval_path.read_bytes()
        assert len(restored_bytes) > 0, \
            "target approval file should be readable after patch exit"
        import json as _json
        restored_data = _json.loads(restored_bytes.decode("utf-8"))
        assert restored_data["schema_version"] == 2, \
            "target approval file content should be valid JSON with schema_version=2"

        # 양쪽 모두 REJECTED/MALFORMED 이어야 함
        assert new_result.state.value == "REJECTED", f"new state: {new_result.state}"
        assert legacy_result.state.value == "REJECTED", f"legacy state: {legacy_result.state}"
        assert new_result.reason_code.value == "MALFORMED", f"new reason: {new_result.reason_code}"
        assert legacy_result.reason_code.value == "MALFORMED", f"legacy reason: {legacy_result.reason_code}"

        # 전체 필드 일치 확인 (9 개 필드 모두)
        all_fields = ["state", "reason_code", "source_id", "approved_at", "dataset_sha256_before",
                      "scope", "plan_hash", "artifact_sha256", "artifact_path"]
        for field in all_fields:
            assert getattr(new_result, field) == getattr(legacy_result, field), \
                f"Field mismatch on {field}: new={getattr(new_result, field)}, legacy={getattr(legacy_result, field)}"

    def test_exception_match_both_raise(self, tmp_path: Path):
        """V7-E2: 호출 대역으로 동일 예외 → no issue."""
        import unittest.mock as mock
        import sys; test_mod = sys.modules[__name__]

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        payload = _make_valid_payload(tmp_path)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        # 양쪽 모두 동일한 예외를 내도록 monkey-patch
        side_effect_exc = ValueError("mock: identical error")

        def mock_new(*args, **kwargs):
            raise side_effect_exc

        def mock_legacy(*args, **kwargs):
            raise side_effect_exc

        original_new = test_mod.evaluate_approval_v2
        original_legacy = test_mod._legacy_evaluate_approval_v2

        test_mod.evaluate_approval_v2 = mock_new
        test_mod._legacy_evaluate_approval_v2 = mock_legacy

        try:
            issues = _compare_new_legacy(
                approval_path, config, "a" * 64, FIXED_NOW,
            )
        finally:
            test_mod.evaluate_approval_v2 = original_new
            test_mod._legacy_evaluate_approval_v2 = original_legacy

        # 양쪽 동일 예외 → no issue
        assert issues == [], f"Expected identical exceptions → no issue:\n" + "\n".join(issues)

    def test_one_side_raises_new_only(self, tmp_path: Path):
        """V7-E3: 호출 대역으로 신규만 예외 → issue 기록."""
        import unittest.mock as mock
        import sys; test_mod = sys.modules[__name__]

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        payload = _make_valid_payload(tmp_path)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        new_exc = ValueError("mock: new only error")

        def mock_new(*args, **kwargs):
            raise new_exc

        original_new = test_mod.evaluate_approval_v2

        test_mod.evaluate_approval_v2 = mock_new

        try:
            issues = _compare_new_legacy(
                approval_path, config, "a" * 64, FIXED_NOW,
            )
        finally:
            test_mod.evaluate_approval_v2 = original_new

        # 신규만 예외 → issue 기록 확인
        assert len(issues) > 0, "Expected issue when only new raises"
        assert "new raised" in issues[0] or "legacy raised" in issues[0], \
            f"Expected exception mismatch: {issues}"
    def test_one_side_raises_legacy_only(self, tmp_path: Path):
        """V7-E3b: 호출 대역으로 legacy 만 예외 → issue 기록."""
        import unittest.mock as mock
        import sys; test_mod = sys.modules[__name__]

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        payload = _make_valid_payload(tmp_path)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        legacy_exc = ValueError("mock: legacy only error")

        original_legacy = test_mod._legacy_evaluate_approval_v2

        def mock_legacy(*args, **kwargs):
            raise legacy_exc

        test_mod._legacy_evaluate_approval_v2 = mock_legacy

        try:
            issues = _compare_new_legacy(
                approval_path, config, "a" * 64, FIXED_NOW,
            )
        finally:
            test_mod._legacy_evaluate_approval_v2 = original_legacy

        # legacy 만 예외 → issue 기록 확인
        assert len(issues) > 0, "Expected issue when only legacy raises"
        assert "legacy raised" in issues[0], \
            f"Expected 'legacy raised' in issue: {issues}"
        assert "new did not raise" in issues[0], \
            f"Expected 'new did not raise' in issue: {issues}"


    def test_exception_type_mismatch(self, tmp_path: Path):
        """V7-E4: 호출 대역으로 유형 차이 → issue 기록."""
        import unittest.mock as mock
        import sys; test_mod = sys.modules[__name__]

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        payload = _make_valid_payload(tmp_path)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        new_exc = ValueError("mock: new error")
        legacy_exc = TypeError("mock: legacy error")

        def mock_new(*args, **kwargs):
            raise new_exc

        def mock_legacy(*args, **kwargs):
            raise legacy_exc

        original_new = test_mod.evaluate_approval_v2
        original_legacy = test_mod._legacy_evaluate_approval_v2

        test_mod.evaluate_approval_v2 = mock_new
        test_mod._legacy_evaluate_approval_v2 = mock_legacy

        try:
            issues = _compare_new_legacy(
                approval_path, config, "a" * 64, FIXED_NOW,
            )
        finally:
            test_mod.evaluate_approval_v2 = original_new
            test_mod._legacy_evaluate_approval_v2 = original_legacy

        # 유형 차이 → issue 기록 확인
        assert len(issues) > 0, "Expected issue when exception types differ"
        assert "exception type mismatch" in issues[0], \
            f"Expected type mismatch: {issues}"

    def test_exception_message_mismatch(self, tmp_path: Path):
        """V7-E5: 호출 대역으로 메시지 차이 → issue 기록."""
        import unittest.mock as mock
        import sys; test_mod = sys.modules[__name__]

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        payload = _make_valid_payload(tmp_path)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        new_exc = ValueError("mock: new message")
        legacy_exc = ValueError("mock: legacy message")

        def mock_new(*args, **kwargs):
            raise new_exc

        def mock_legacy(*args, **kwargs):
            raise legacy_exc

        original_new = test_mod.evaluate_approval_v2
        original_legacy = test_mod._legacy_evaluate_approval_v2

        test_mod.evaluate_approval_v2 = mock_new
        test_mod._legacy_evaluate_approval_v2 = mock_legacy

        try:
            issues = _compare_new_legacy(
                approval_path, config, "a" * 64, FIXED_NOW,
            )
        finally:
            test_mod.evaluate_approval_v2 = original_new
            test_mod._legacy_evaluate_approval_v2 = original_legacy

        # 메시지 차이 → issue 기록 확인
        assert len(issues) > 0, "Expected issue when exception messages differ"
        assert "exception message mismatch" in issues[0], \
            f"Expected message mismatch: {issues}"

    def test_missing_rejection_input_comprehensive(self, tmp_path: Path):
        """V7-E6: 필수 필드 삭제 + 잘못된 값·형식·비승인 decision 시험."""
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        base_payload = _make_valid_payload(tmp_path)

        # 1) 필수 필드 삭제 (기존)
        required_fields = [
            "schema_version", "source_id", "target_paths_realpath",
            "plan_hash", "reviewer_id", "gate_id",
            "dataset_sha256_before", "final_decision", "approved_at",
        ]
        for field in required_fields:
            payload = dict(base_payload)
            del payload[field]
            approval_path = _write_approval(tmp_path, approval_dir, f"MISSING_{field}", payload)
            issues = _compare_new_legacy(
                approval_path, config, "a" * 64, FIXED_NOW,
            )
            assert issues == [], f"Mismatch on missing field '{field}':\n" + "\n".join(issues)

        # 2) 잘못된 값: schema_version = "not_a_number"
        payload = dict(base_payload)
        payload["schema_version"] = "not_a_number"
        approval_path = _write_approval(tmp_path, approval_dir, "BAD_schema_version", payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"Mismatch on bad schema_version:\n" + "\n".join(issues)

        # 3) 형식: target_paths_realpath = "not_a_list" (문자열)
        payload = dict(base_payload)
        payload["target_paths_realpath"] = "not_a_list"
        approval_path = _write_approval(tmp_path, approval_dir, "BAD_target_paths", payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"Mismatch on bad target_paths:\n" + "\n".join(issues)

        # 4) 비승인 decision: final_decision = "REJECTED"
        payload = dict(base_payload)
        payload["final_decision"] = "REJECTED"
        approval_path = _write_approval(tmp_path, approval_dir, "DECISION_REJECTED", payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"Mismatch on REJECTED decision:\n" + "\n".join(issues)

        # 5) 비승인 decision: final_decision = "PENDING"
        payload = dict(base_payload)
        payload["final_decision"] = "PENDING"
        approval_path = _write_approval(tmp_path, approval_dir, "DECISION_PENDING", payload)
        issues = _compare_new_legacy(
            approval_path, config, "a" * 64, FIXED_NOW,
        )
        assert issues == [], f"Mismatch on PENDING decision:\n" + "\n".join(issues)

    # -----------------------------------------------------------------------
    # V7B-FINAL: _compare_new_legacy 한 번 호출 → 양쪽 각각 1회·legacy-only 불일치 단언
    # -----------------------------------------------------------------------

    def test_compare_new_legacy_calls_each_once_and_legacy_only_mismatch(self, tmp_path: Path):
        """V7B-FINAL-E1: _compare_new_legacy(...) 한 번 호출, 같은 실행에서 양쪽 각각 1회·legacy-only 불일치 단언.

        - _compare_new_legacy 내부에서 evaluate_approval_v2 가 정확히 1회 호출됨
        - _compare_new_legacy 내부에서 _legacy_evaluate_approval_v2 가 정확히 1회 호출됨
        - legacy 대역만 예외를 내면 legacy-only 불일치가 issues 에 기록됨
        """
        import unittest.mock as mock
        import sys; test_mod = sys.modules[__name__]

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir(exist_ok=True)
        config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
        payload = _make_valid_payload(tmp_path)
        approval_path = _write_approval(tmp_path, approval_dir, "TEST_SOURCE", payload)

        # 호출 카운터 (같은 _compare_new_legacy 실행 안에서)
        new_call_count = [0]
        legacy_call_count = [0]

        def mock_new(*args, **kwargs):
            new_call_count[0] += 1
            return ApprovalEvaluation(
                state=ApprovalState.VALID, reason_code=None, source_id="TEST_SOURCE",
                approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
                scope=None, plan_hash="sha256:" + "0" * 64,
                artifact_sha256="b" * 64, artifact_path=str(approval_path.resolve()),
            )

        def mock_legacy(*args, **kwargs):
            legacy_call_count[0] += 1
            raise ValueError("mock: legacy only error")

        original_new = test_mod.evaluate_approval_v2
        original_legacy = test_mod._legacy_evaluate_approval_v2

        test_mod.evaluate_approval_v2 = mock_new
        test_mod._legacy_evaluate_approval_v2 = mock_legacy

        try:
            # _compare_new_legacy 를 한 번만 호출
            issues = _compare_new_legacy(
                approval_path, config, "a" * 64, FIXED_NOW,
            )

            # 같은 실행에서 양쪽 각각 1회 호출 단언
            assert new_call_count[0] == 1, \
                f"Expected new called exactly once, got {new_call_count[0]}"
            assert legacy_call_count[0] == 1, \
                f"Expected legacy called exactly once, got {legacy_call_count[0]}"

            # legacy-only 예외 → 불일치 기록 확인 (PM 요구: legacy raised AND new did not raise 모두 필수)
            assert len(issues) > 0, "Expected legacy-only mismatch issue"
            assert "legacy raised" in issues[0], \
                f"Expected 'legacy raised' in issue: {issues}"
            assert "new did not raise" in issues[0], \
                f"Expected 'new did not raise' in issue: {issues}"
        finally:
            test_mod.evaluate_approval_v2 = original_new
            test_mod._legacy_evaluate_approval_v2 = original_legacy


class TestE1b:

    def test_comparator_same_results_pass(self):
        """E1b-1: Identical results produce no issues."""
        a = ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="test",
            approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
            scope=None, plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64, artifact_path="/test/path",
        )
        b = ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="test",
            approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
            scope=None, plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64, artifact_path="/test/path",
        )
        issues = _compare_evaluation(a, b)
        assert issues == [], f"Same results should produce no issues: {issues}"

    def test_comparator_different_state_detects(self):
        """E1b-2: Different state is detected."""
        a = ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="test",
            approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
            scope=None, plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64, artifact_path="/test/path",
        )
        b = ApprovalEvaluation(
            state=ApprovalState.REJECTED, reason_code=ApprovalReasonCode.SCHEMA_VERSION, source_id="test",
            approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
            scope=None, plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64, artifact_path="/test/path",
        )
        issues = _compare_evaluation(a, b)
        assert len(issues) > 0, "Different state should be detected"
        assert any("state:" in issue for issue in issues), f"Expected 'state' in issues: {issues}"

    def test_comparator_different_source_id_detects(self):
        """E1b-3: Different source_id is detected."""
        a = ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="test",
            approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
            scope=None, plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64, artifact_path="/test/path",
        )
        b = ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="other",
            approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
            scope=None, plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64, artifact_path="/test/path",
        )
        issues = _compare_evaluation(a, b)
        assert len(issues) > 0, "Different source_id should be detected"
        assert any("source_id:" in issue for issue in issues), f"Expected 'source_id' in issues: {issues}"

    def test_comparator_missing_field_raises(self):
        """E1b-4: Missing field raises AssertionError."""
        a = ApprovalEvaluation(
            state=ApprovalState.VALID, reason_code=None, source_id="test",
            approved_at="2026-01-01T00:00:00+00:00", dataset_sha256_before="a" * 64,
            scope=None, plan_hash="sha256:" + "0" * 64,
            artifact_sha256="b" * 64, artifact_path="/test/path",
        )
        class FakeEval:
            pass
        b = FakeEval()
        with pytest.raises(AssertionError, match="missing field"):
            _compare_evaluation(a, b)


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
        # T7 (E1a 시험 보강): 같은 입력으로 신규·legacy 를 실제로 비교한다(이름-단언 정합).
        _t7_issues = _compare_new_legacy(approval_path, config, "a" * 64, FIXED_NOW)
        assert _t7_issues == [], f"T7: new/legacy mismatch for {expected_reason}:\n" + "\n".join(_t7_issues)

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


# ===========================================================================
# E-1a 시험 보강 (S2E1A-CUE-TEST-ENHANCE-V1): T1~T6, T8, T9 (T7 은 TestE2 기존 함수 안에 추가)
# 모든 시험은 tmp_path·fixture 만 사용하며 mock/patch 를 쓰지 않는다. 비교는 항상
# _compare_new_legacy(신규 evaluate_approval_v2 vs BASE 복사본 _legacy_evaluate_approval_v2)로 하고,
# 비교기 약화에 대비해 명시적 기대값 단언을 함께 둔다.
# ===========================================================================

import copy as _t_copy
import random as _t_random

_T_ALL_FIELDS = tuple(sorted(_APPROVAL_V2_REQUIRED_FIELDS))
_T_STR_FIELDS = ("source_id", "plan_hash", "reviewer_id", "gate_id",
                 "dataset_sha256_before", "final_decision", "approved_at")
_T_DS = "a" * 64          # 유효 payload 의 dataset_sha256_before 와 같은 값
_T_REJ = ApprovalState.REJECTED


def _t_env(tmp_path: Path):
    """approval_dir 과 config 를 만들어 (approval_dir, config) 를 돌려준다."""
    approval_dir = tmp_path / "approval_dir"
    approval_dir.mkdir(exist_ok=True)
    config = _make_config(tmp_path, tmp_path / "prod", approval_dir)
    return approval_dir, config


def _t_payload_defects():
    """payload 수준 단일 결함 카탈로그: [(id, fn(payload)->payload)]. 호출할 때마다 새로 만들며 전역 상태가 없다.

    각 항목은 유효 payload 를 거절 상태로 만드는 결함이어야 한다(시험이 실제로 확인한다)."""
    defects = []

    def add(did, fn):
        defects.append((did, fn))

    for f in _T_ALL_FIELDS:
        add(f"missing:{f}", (lambda f: lambda p: {k: v for k, v in p.items() if k != f})(f))
    str_bad = {"none": None, "int": 12345, "float": 1.5, "bool": True, "list": [1], "dict": {"k": 1}}
    for f in _T_STR_FIELDS:
        for tn, tv in str_bad.items():
            add(f"type:{f}:{tn}", (lambda f, tv: lambda p: {**p, f: _t_copy.deepcopy(tv)})(f, tv))
    sv_bad = {"none": None, "float2.0": 2.0, "list": [2], "dict": {"v": 2}, "str2": "2", "bool": True}
    for tn, tv in sv_bad.items():
        add(f"type:schema_version:{tn}", (lambda tv: lambda p: {**p, "schema_version": _t_copy.deepcopy(tv)})(tv))
    tp_bad = {"none": None, "int": 12345, "float": 1.5, "bool": True, "str": "x", "dict": {"k": 1}}
    for tn, tv in tp_bad.items():
        add(f"type:target_paths_realpath:{tn}",
            (lambda tv: lambda p: {**p, "target_paths_realpath": _t_copy.deepcopy(tv)})(tv))
    for v in (1, 3, 0, -1):
        add(f"value:schema_version:{v}", (lambda v: lambda p: {**p, "schema_version": v})(v))
    for v in ("", "../x", "a/b", ".hidden", "has space"):
        add(f"value:source_id:{v!r}", (lambda v: lambda p: {**p, "source_id": v})(v))
    for v in ("bad", "sha256:" + "0" * 63, "sha256:" + "0" * 65, "sha256:" + "A" * 64,
              "SHA256:" + "0" * 64, "sha512:" + "0" * 64):
        add(f"value:plan_hash:{v[:12]}/{len(v)}", (lambda v: lambda p: {**p, "plan_hash": v})(v))
    for v in ("short", "A" * 64, "a" * 63, "a" * 65, "g" * 64):
        add(f"value:dataset_sha256_before:{v[:3]}/{len(v)}",
            (lambda v: lambda p: {**p, "dataset_sha256_before": v})(v))
    for v in ("not_iso", "", "2026-13-45T99:99:99", "yesterday"):
        add(f"value:approved_at:{v!r}", (lambda v: lambda p: {**p, "approved_at": v})(v))
    add("legacy_field:target_root_realpath", lambda p: {**p, "target_root_realpath": "/x"})
    add("unknown_field:unknown_field", lambda p: {**p, "unknown_field": "x"})
    add("unknown_field:extra_field", lambda p: {**p, "extra_field": 1})
    for v in ("REJECTED", "approved", "", "APPROVED "):
        add(f"value:final_decision:{v!r}", (lambda v: lambda p: {**p, "final_decision": v})(v))
    add("future_approved_at:+301s",
        lambda p: {**p, "approved_at": (FIXED_NOW + timedelta(seconds=301)).isoformat()})
    return defects


def _t_file_defects(valid_payload: dict):
    """파일 수준 단일 결함 카탈로그: [(id, writer(approval_dir)->Path, expected_reason or None)].

    expected_reason 이 None 이면 legacy 와의 동일 비교만 한다(BOM 처럼 기대값을 임의로 정하지 않는 경우)."""
    good = json.dumps(valid_payload).encode("utf-8")
    marker = b"MARKER_SOURCE"
    with_marker = json.dumps({**valid_payload, "source_id": marker.decode()}).encode("utf-8")
    assert marker in with_marker

    def wb(name, data):
        def _w(approval_dir: Path) -> Path:
            p = approval_dir / name
            p.write_bytes(data)
            return p
        return _w

    def w_dir(approval_dir: Path) -> Path:
        p = approval_dir / "adir.json"
        p.mkdir()
        return p

    def w_missing(approval_dir: Path) -> Path:
        return approval_dir / "nope.json"

    M, NF = ApprovalReasonCode.MALFORMED, ApprovalReasonCode.NOT_FOUND
    return [
        ("nonexistent_path", w_missing, NF),
        ("directory_as_approval", w_dir, M),
        ("empty_file", wb("empty.json", b""), M),
        ("invalid_json_text", wb("badjson.json", b"{not json"), M),
        ("truncated_json", wb("trunc.json", good[: len(good) // 2]), M),
        ("top_level_list", wb("toplist.json", b"[1, 2]"), M),
        ("top_level_string", wb("topstr.json", b'"x"'), M),
        ("top_level_number", wb("topnum.json", b"123"), M),
        ("top_level_null", wb("topnull.json", b"null"), M),
        ("top_level_true", wb("toptrue.json", b"true"), M),
        ("utf8_invalid_inside_json_string", wb("u1.json", with_marker.replace(marker, b"A\xffB")), M),
        ("utf8_overlong_inside_json_string", wb("u2.json", with_marker.replace(marker, b"A\xc0\xafB")), M),
        ("utf8_truncated_multibyte_inside_string", wb("u3.json", with_marker.replace(marker, b"A\xe2\x82")), M),
        ("utf8_invalid_after_closing_brace", wb("u4.json", good + b"\xff\xfe\x00"), M),
        ("utf8_all_invalid", wb("u5.json", b"\xff\xfe\x00\xff\xfe\x00"), M),
        ("utf8_bom_prefixed_valid_json", wb("u6.json", b"\xef\xbb\xbf" + good), None),
    ]


def _assert_same_as_legacy(approval_path, config, now=FIXED_NOW, expected=None, dataset=_T_DS):
    """신규 결과를 돌려주되 legacy 와의 동일성을 먼저 단언한다."""
    issues = _compare_new_legacy(approval_path, config, dataset, now, expected_target_paths=expected)
    assert issues == [], "new/legacy mismatch:\n" + "\n".join(issues)
    return evaluate_approval_v2(approval_path, config_path=config, expected_target_paths=expected,
                                dataset_sha256_current=dataset, now=now)


# --------------------------------------------------------------------------- T1
class TestT1NonUtf8:
    """T1(§5 E1 비 UTF-8): 잘못된 바이트가 JSON 문자열 값 안/구문 밖/전체에 있는 파일."""

    def _file(self, tmp_path, name):
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        by_name = {did: w for did, w, _ in _t_file_defects(valid)}
        return by_name[name](approval_dir), config

    @pytest.mark.parametrize("case", [
        "utf8_invalid_inside_json_string",
        "utf8_overlong_inside_json_string",
        "utf8_truncated_multibyte_inside_string",
        "utf8_invalid_after_closing_brace",
        "utf8_all_invalid",
    ])
    def test_t1_invalid_utf8_is_malformed_and_matches_legacy(self, tmp_path: Path, case):
        path, config = self._file(tmp_path, case)
        res = _assert_same_as_legacy(path, config)
        assert res.state == _T_REJ
        assert res.reason_code == ApprovalReasonCode.MALFORMED
        assert res.source_id == ""

    def test_t1_invalid_byte_really_inside_a_json_string_value(self, tmp_path: Path):
        """T1-a 의 입력이 사양대로인지 확인: 잘못된 바이트를 U+FFFD 로 대체하면 JSON 으로 유효하다
        (즉 구문 오류가 아니라 디코드 오류만이 MALFORMED 의 원인이다 — 디코드 변이를 격파하는 근거)."""
        path, config = self._file(tmp_path, "utf8_invalid_inside_json_string")
        raw = path.read_bytes()
        assert b"\xff" in raw
        data = json.loads(raw.decode("utf-8", errors="replace"))
        assert isinstance(data, dict) and data["source_id"] == "A�B"

    def test_t1_bom_prefixed_valid_json_matches_legacy(self, tmp_path: Path):
        path, config = self._file(tmp_path, "utf8_bom_prefixed_valid_json")
        _assert_same_as_legacy(path, config)


# --------------------------------------------------------------------------- T2
class TestT2SingleDefectCatalog:
    def test_t2_payload_single_defects(self, tmp_path: Path):
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        defects = _t_payload_defects()
        n_payload_single = len(defects)
        assert n_payload_single >= 80, f"T2: n_payload_single={n_payload_single} < 80"
        ids = [d for d, _ in defects]
        assert len(set(ids)) == len(ids), "T2: 카탈로그 id 중복"
        seen = set()
        reasons = set()
        for did, fn in defects:
            payload = fn(_t_copy.deepcopy(valid))
            key = json.dumps(payload, sort_keys=True)
            assert key not in seen, f"T2: 서로 같은 결함 입력({did})"
            seen.add(key)
            path = approval_dir / "single.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            res = _assert_same_as_legacy(path, config)
            assert res.state == _T_REJ, f"T2: 결함 {did} 가 거절되지 않음(비결함이 섞임)"
            reasons.add(res.reason_code)
        assert len(reasons) >= 8, f"T2: 서로 다른 reason code {len(reasons)}개 < 8: {reasons}"
        n_file_single = len(_t_file_defects(valid))
        assert n_file_single >= 12
        print(f"GATE1-COUNTS singles_payload={n_payload_single} singles_file={n_file_single}")

    def test_t2_valid_payload_is_valid(self, tmp_path: Path):
        approval_dir, config = _t_env(tmp_path)
        path = approval_dir / "valid.json"
        path.write_text(json.dumps(_make_valid_payload(tmp_path)), encoding="utf-8")
        res = _assert_same_as_legacy(path, config)
        assert res.state == ApprovalState.VALID

    def test_t2_file_level_defects(self, tmp_path: Path):
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        cat = _t_file_defects(valid)
        assert len(cat) >= 12
        for did, writer, expected in cat:
            path = writer(approval_dir)
            res = _assert_same_as_legacy(path, config)
            if expected is not None:
                assert res.state == _T_REJ, f"T2-file {did}"
                assert res.reason_code == expected, f"T2-file {did}: {res.reason_code} != {expected}"


# --------------------------------------------------------------------------- T3
class TestT3PairwiseExhaustive:
    def test_t3_ordered_pairs_exhaustive(self, tmp_path: Path):
        """모든 순서쌍 (a,b), a != b: payload = b(a(valid)). 같은 키를 건드리는 쌍도 제외하지 않는다."""
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        defects = _t_payload_defects()
        n = len(defects)
        assert n >= 80
        path = approval_dir / "pair.json"
        n_pairs = 0
        sampled = set()
        for i, (ida, fa) in enumerate(defects):
            for j, (idb, fb) in enumerate(defects):
                if i == j:
                    continue
                payload = fb(fa(_t_copy.deepcopy(valid)))
                path.write_text(json.dumps(payload), encoding="utf-8")
                issues = _compare_new_legacy(path, config, _T_DS, FIXED_NOW)
                assert issues == [], f"T3 pair ({ida} -> {idb}) mismatch:\n" + "\n".join(issues)
                if n_pairs % 37 == 0:
                    sampled.add(evaluate_approval_v2(path, config_path=config, expected_target_paths=None,
                                                     dataset_sha256_current=_T_DS, now=FIXED_NOW).reason_code)
                n_pairs += 1
        assert n_pairs == n * (n - 1)
        assert n_pairs >= 6000
        assert len(sampled) >= 8, f"T3: 표본에서 reason code {len(sampled)}종뿐"
        print(f"GATE1-COUNTS pairs={n_pairs}")

    def test_t3_environment_defect_by_payload_defect(self, tmp_path: Path):
        """환경 결함(config 에 approval_dir 없음 / 승인 파일이 approval_dir 밖)과 payload 결함의 조합 순서."""
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        bad_config = tmp_path / "bad_config.yaml"
        bad_config.write_text(f"merge-safety:\n  production_root: {tmp_path / 'prod'}\n", encoding="utf-8")
        outside = tmp_path / "outside"
        outside.mkdir()
        cases = [("valid", lambda p: p)] + _t_payload_defects()
        n_cases = 0
        seen = set()
        for did, fn in cases:
            payload = fn(_t_copy.deepcopy(valid))
            inside_path = approval_dir / "in.json"
            inside_path.write_text(json.dumps(payload), encoding="utf-8")
            outside_path = outside / "out.json"
            outside_path.write_text(json.dumps(payload), encoding="utf-8")
            for label, p, c in (("config_without_approval_dir", inside_path, bad_config),
                                ("approval_outside_dir", outside_path, config)):
                issues = _compare_new_legacy(p, c, _T_DS, FIXED_NOW)
                assert issues == [], f"T3-env ({label} x {did}) mismatch:\n" + "\n".join(issues)
                n_cases += 1
                if did in ("valid", "missing:plan_hash", "value:source_id:''", "unknown_field:extra_field"):
                    seen.add((label, did, evaluate_approval_v2(
                        p, config_path=c, expected_target_paths=None,
                        dataset_sha256_current=_T_DS, now=FIXED_NOW).reason_code))
        assert n_cases == 2 * len(cases) and n_cases >= 160
        by_label = {}
        for label, did, reason in seen:
            by_label.setdefault((label, did), reason)
        assert by_label[("config_without_approval_dir", "valid")] == ApprovalReasonCode.CONFIG_APPROVAL_DIR
        assert by_label[("approval_outside_dir", "valid")] == ApprovalReasonCode.PATH_ESCAPE

    # ---- 명시 순서 단언: 기준 구현의 검사 순서 = 미래 승인 시각 -> final_decision -> target_paths -> (래퍼) dataset 신선도
    def _assert_pair(self, tmp_path, mutate, expected=None, dataset=_T_DS):
        approval_dir, config = _t_env(tmp_path)
        payload = mutate(_make_valid_payload(tmp_path))
        path = approval_dir / "order.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return _assert_same_as_legacy(path, config, expected=expected, dataset=dataset)

    def _mismatching_expected(self, tmp_path):
        return [str(tmp_path / "elsewhere" / n) for n in ("a.json", "b.json", "c.jsonl")]

    def test_t3_decision_not_approved_before_target_mismatch(self, tmp_path: Path):
        res = self._assert_pair(tmp_path, lambda p: {**p, "final_decision": "REJECTED"},
                         expected=self._mismatching_expected(tmp_path))
        assert res.reason_code == ApprovalReasonCode.DECISION_NOT_APPROVED

    def test_t3_target_mismatch_when_only_target_is_wrong(self, tmp_path: Path):
        res = self._assert_pair(tmp_path, lambda p: p, expected=self._mismatching_expected(tmp_path))
        assert res.reason_code == ApprovalReasonCode.TARGET_MISMATCH

    def test_t3_future_approval_before_decision(self, tmp_path: Path):
        res = self._assert_pair(tmp_path, lambda p: {**p, "final_decision": "REJECTED",
                         "approved_at": (FIXED_NOW + timedelta(seconds=301)).isoformat()})
        assert res.reason_code == ApprovalReasonCode.FUTURE_APPROVAL

    def test_t3_future_approval_before_target_mismatch(self, tmp_path: Path):
        res = self._assert_pair(tmp_path, lambda p: {**p, "approved_at": (FIXED_NOW + timedelta(seconds=301)).isoformat()},
                         expected=self._mismatching_expected(tmp_path))
        assert res.reason_code == ApprovalReasonCode.FUTURE_APPROVAL

    def test_t3_target_mismatch_before_dataset_freshness(self, tmp_path: Path):
        res = self._assert_pair(tmp_path, lambda p: p, expected=self._mismatching_expected(tmp_path), dataset="b" * 64)
        assert res.reason_code == ApprovalReasonCode.TARGET_MISMATCH

    def test_t3_dataset_freshness_is_last(self, tmp_path: Path):
        res = self._assert_pair(tmp_path, lambda p: p, dataset="b" * 64)
        assert res.reason_code == ApprovalReasonCode.DATASET_SHA_MISMATCH


# --------------------------------------------------------------------------- T4
class TestT4FuzzSeeded:
    FUZZ_SEED = 20261007
    FUZZ_N = 3600

    @staticmethod
    def _mutate_bytes(rng, data: bytes) -> bytes:
        b = bytearray(data)
        op = rng.randrange(6)
        pos = rng.randrange(len(b)) if b else 0
        if op == 0 and b:
            b[pos] = rng.randrange(256)
        elif op == 1 and b:
            del b[pos]
        elif op == 2:
            b[pos:pos] = bytes([rng.randrange(256)])
        elif op == 3:
            b = b[:pos]
        elif op == 4:
            b[pos:pos] = rng.choice([b"\xff", b"\xc3\x28", b"\xe2\x28\xa1", b"\xf0\x28\x8c\xbc", b"\x80"])
        else:
            b[pos:pos] = b"\xef\xbb\xbf"
        return bytes(b)

    def test_t4_fuzz_fixed_seed(self, tmp_path: Path):
        rng = _t_random.Random(self.FUZZ_SEED)      # 전역 random 상태를 쓰지 않는다
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        defects = _t_payload_defects()
        exp_ok = list(valid["target_paths_realpath"])
        exp_bad = [str(tmp_path / "x" / n) for n in ("a", "b", "c")]
        path = approval_dir / "fuzz.json"
        n_fuzz = 0
        reasons = set()
        modes = {"payload": 0, "bytes": 0, "mixed": 0}
        for _ in range(self.FUZZ_N):
            mode = rng.choice(("payload", "payload", "bytes", "bytes", "mixed"))
            payload = _t_copy.deepcopy(valid)
            if mode in ("payload", "mixed"):
                for _k in range(rng.randint(1, 3)):
                    payload = rng.choice(defects)[1](payload)
            raw = json.dumps(payload).encode("utf-8")
            if mode in ("bytes", "mixed"):
                for _k in range(rng.randint(1, 2)):
                    raw = self._mutate_bytes(rng, raw)
            modes[mode] += 1
            path.write_bytes(raw)
            expected = rng.choice((None, exp_ok, exp_bad))
            dataset = rng.choice((_T_DS, "b" * 64))
            issues = _compare_new_legacy(path, config, dataset, FIXED_NOW, expected_target_paths=expected)
            assert issues == [], f"T4 fuzz #{n_fuzz} ({mode}) mismatch:\n" + "\n".join(issues)
            if n_fuzz % 10 == 0:
                reasons.add(evaluate_approval_v2(path, config_path=config, expected_target_paths=expected,
                                                 dataset_sha256_current=dataset, now=FIXED_NOW).reason_code)
            n_fuzz += 1
        assert n_fuzz >= 3000
        assert min(modes.values()) > 300
        assert len(reasons) >= 8, f"T4: 표본 reason code {len(reasons)}종 < 8"
        print(f"GATE1-COUNTS fuzz={n_fuzz}")


# --------------------------------------------------------------------------- T5
class TestT5NowHandling:
    NOWS = {
        "naive": datetime(2026, 1, 1, 12, 0, 0),
        "utc": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "p0900": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=9))),
        "m0500": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-5))),
    }
    APPROVED_TZ = {"naive": None, "utc": timezone.utc, "p0900": timezone(timedelta(hours=9))}
    DELTAS = (-3600, -1, 0, 299, 300, 301, 3600)

    def test_t5_now_by_approved_at_matrix(self, tmp_path: Path):
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        path = approval_dir / "now.json"
        n_same = n_mixed = 0
        for nn, now in self.NOWS.items():
            for an, atz in self.APPROVED_TZ.items():
                for delta in self.DELTAS:
                    if (nn == "naive") == (atz is None):          # 같은 종류(둘 다 naive 이거나 둘 다 aware)
                        base = now + timedelta(seconds=delta)
                        approved = base if atz is None else base.astimezone(atz)
                    else:
                        base = now.replace(tzinfo=None) + timedelta(seconds=delta)
                        approved = base if atz is None else base.replace(tzinfo=atz)
                    path.write_text(json.dumps({**valid, "approved_at": approved.isoformat()}), encoding="utf-8")
                    res = _assert_same_as_legacy(path, config, now=now)
                    if (nn == "naive") == (atz is None):
                        n_same += 1
                        if delta <= 300:
                            assert res.state == ApprovalState.VALID, (nn, an, delta, res.reason_code)
                        else:
                            assert res.reason_code == ApprovalReasonCode.FUTURE_APPROVAL, (nn, an, delta)
                    else:
                        n_mixed += 1       # 혼합 종류는 legacy 동일 비교만(기대값을 임의로 정하지 않는다)
        assert (n_same, n_mixed) == (49, 35)      # 4 now x 3 approved x 7 delta = 84 = 49 같은 종류 + 35 혼합

    def test_t5_caller_supplied_now_is_forwarded(self, tmp_path: Path):
        """같은 승인 파일을 now=A / now=B 로 호출하면 결과가 달라야 한다(래퍼가 now 를 무시하면 실패)."""
        approval_dir, config = _t_env(tmp_path)
        now_a = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        now_b = now_a + timedelta(seconds=200)
        path = approval_dir / "fwd.json"
        path.write_text(json.dumps({**_make_valid_payload(tmp_path),
                                    "approved_at": (now_a + timedelta(seconds=400)).isoformat()}), encoding="utf-8")
        res_a = _assert_same_as_legacy(path, config, now=now_a)
        res_b = _assert_same_as_legacy(path, config, now=now_b)
        assert res_a.reason_code == ApprovalReasonCode.FUTURE_APPROVAL
        assert res_b.state == ApprovalState.VALID

    def test_t5_now_omitted_uses_real_clock(self, tmp_path: Path):
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        real = datetime.now(timezone.utc)
        for name, approved, want_future in (("future", real + timedelta(days=1), True),
                                            ("past", real - timedelta(days=1), False)):
            path = approval_dir / f"omit_{name}.json"
            path.write_text(json.dumps({**valid, "approved_at": approved.isoformat()}), encoding="utf-8")
            new = evaluate_approval_v2(path, config_path=config, expected_target_paths=None,
                                       dataset_sha256_current=_T_DS)
            legacy = _legacy_evaluate_approval_v2(path, config_path=config, expected_target_paths=None,
                                                  dataset_sha256_current=_T_DS)
            assert _compare_evaluation(new, legacy, "new", "legacy") == []
            if want_future:
                assert new.reason_code == ApprovalReasonCode.FUTURE_APPROVAL
            else:
                assert new.state == ApprovalState.VALID


# --------------------------------------------------------------------------- T6
class TestT6ExpectedTargetPaths:
    def _assert_run(self, tmp_path, expected):
        approval_dir, config = _t_env(tmp_path)
        path = approval_dir / "tp.json"
        path.write_text(json.dumps(_make_valid_payload(tmp_path)), encoding="utf-8")
        return _assert_same_as_legacy(path, config, expected=expected)

    def test_t6_none_is_valid(self, tmp_path: Path):
        assert self._assert_run(tmp_path, None).state == ApprovalState.VALID

    def test_t6_matching_list_is_valid(self, tmp_path: Path):
        assert self._assert_run(tmp_path, list(_make_valid_payload(tmp_path)["target_paths_realpath"])).state == ApprovalState.VALID

    @pytest.mark.parametrize("variant", ["empty", "reordered", "extra", "missing", "relative", "tuple", "non_list_str"])
    def test_t6_mismatching_variants_are_target_mismatch(self, tmp_path: Path, variant):
        tp = list(_make_valid_payload(tmp_path)["target_paths_realpath"])
        expected = {
            "empty": [],
            "reordered": list(reversed(tp)),
            "extra": tp + ["/extra/path"],
            "missing": tp[:-1],
            "relative": ["rel/a", "rel/b", "rel/c"],
            "tuple": tuple(tp),
            "non_list_str": "not-a-list",
        }[variant]
        res = self._assert_run(tmp_path, expected)
        assert res.state == _T_REJ
        assert res.reason_code == ApprovalReasonCode.TARGET_MISMATCH

    def test_t6_case_variant_matches_legacy(self, tmp_path: Path):
        tp = [p.upper() for p in _make_valid_payload(tmp_path)["target_paths_realpath"]]
        self._assert_run(tmp_path, tp)       # 동작은 legacy 가 정한다 — 동일 비교만


# --------------------------------------------------------------------------- T8
class TestT8DatasetFreshness:
    def test_t8_freshness_never_hides_an_earlier_rejection(self, tmp_path: Path):
        approval_dir, config = _t_env(tmp_path)
        valid = _make_valid_payload(tmp_path)
        defects = _t_payload_defects()
        by_reason = {}
        for did, fn in defects:
            path = approval_dir / "fresh.json"
            path.write_text(json.dumps(fn(_t_copy.deepcopy(valid))), encoding="utf-8")
            match = _assert_same_as_legacy(path, config, dataset=_T_DS)
            mismatch = _assert_same_as_legacy(path, config, dataset="b" * 64)
            assert (match.state, match.reason_code, match.source_id) == (mismatch.state, mismatch.reason_code, mismatch.source_id), did
            assert mismatch.reason_code != ApprovalReasonCode.DATASET_SHA_MISMATCH, did
            by_reason.setdefault(match.reason_code, did)
        assert len(by_reason) >= 8

    def test_t8_valid_approval_freshness(self, tmp_path: Path):
        approval_dir, config = _t_env(tmp_path)
        path = approval_dir / "ok.json"
        path.write_text(json.dumps(_make_valid_payload(tmp_path)), encoding="utf-8")
        ok = _assert_same_as_legacy(path, config, dataset=_T_DS)
        stale = _assert_same_as_legacy(path, config, dataset="b" * 64)
        assert ok.state == ApprovalState.VALID and ok.scope is None
        assert stale.state == _T_REJ
        assert stale.reason_code == ApprovalReasonCode.DATASET_SHA_MISMATCH
        assert stale.scope == FRESH_MERGE_PRECONDITION


# --------------------------------------------------------------------------- T9
class TestT9ReadFailure:
    def test_t9_directory_as_approval_path_is_malformed(self, tmp_path: Path):
        """patch 없이 읽기 실패를 만든다: 승인 경로가 디렉터리면 exists() 는 참이고 read_bytes() 는 OSError."""
        approval_dir, config = _t_env(tmp_path)
        d = approval_dir / "isadir.json"
        d.mkdir()
        assert d.exists() and d.is_dir()
        res = _assert_same_as_legacy(d, config)
        assert res.state == _T_REJ
        assert res.reason_code == ApprovalReasonCode.MALFORMED

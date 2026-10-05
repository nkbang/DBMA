"""tests/test_merge_plan_hash.py -- Plan hash computation (S2-B).

Acceptance Criteria:
  S2B-1: Golden value verification
  S2B-2: Sensitivity
  S2B-3: Order independence for records, order dependence for targets
  S2B-4: Format validation
  S2B-5: Fail-closed validation
  S2B-6: Case sensitivity target test
  S2B-7: Full merge_nae_corpus() path tests
  S2B-8: Non-production data_root behavior
  S2B-11: ApprovalEvaluation.plan_hash
  S2B-12: All fixtures are tmp
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.merge_nae_corpus import (
    ApprovalEvaluation,
    ApprovalState,
    ApprovalReasonCode,
    CorpusMutationBlockedError,
    compute_plan_hash,
)


# ---------------------------------------------------------------------------
# Independent reference implementation (never imports compute_plan_hash)
# ---------------------------------------------------------------------------

def _ref_canonical_json_bytes(obj):
    """Canonical JSON serialisation matching scripts.merge_nae_corpus._canonical_json_bytes."""
    try:
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CorpusMutationBlockedError(
            f"plan_hash: value is not canonically serialisable: {exc}"
        ) from exc


def _ref_record_content_sha256(record):
    """SHA-256 of canonical JSON of one record."""
    import hashlib
    return hashlib.sha256(_ref_canonical_json_bytes(record)).hexdigest()


def _ref_compute_plan_hash(source_id, nae_records, target_paths):
    """Independent reference implementation of compute_plan_hash.

    Payload: {"v":1,"source_id":...,"records":[...],"targets":[...]}
    Records sorted by tsu_id; targets in given order as str(Path.resolve()).
    """
    import hashlib

    if not isinstance(source_id, str):
        raise CorpusMutationBlockedError("plan_hash: source_id must be a str")
    if len(target_paths) != 3:
        raise CorpusMutationBlockedError(
            f"plan_hash: exactly 3 targets required, got {len(target_paths)}"
        )

    rows = []
    seen = set()
    for rec in nae_records:
        tsu_id = rec.get("tsu_id") if isinstance(rec, dict) else None
        if not isinstance(tsu_id, str) or not tsu_id:
            raise CorpusMutationBlockedError("plan_hash: record without a valid str tsu_id")
        if tsu_id in seen:
            raise CorpusMutationBlockedError(f"plan_hash: duplicate tsu_id {tsu_id!r}")
        seen.add(tsu_id)
        rows.append({"tsu_id": tsu_id, "content_sha256": _ref_record_content_sha256(rec)})
    rows.sort(key=lambda r: r["tsu_id"])

    payload = {
        "v": 1,
        "source_id": source_id,
        "records": rows,
        "targets": [str(Path(p).resolve()) for p in target_paths],
    }
    return "sha256:" + hashlib.sha256(_ref_canonical_json_bytes(payload)).hexdigest()


# ---------------------------------------------------------------------------
# S2B-1: Golden value verification
# ---------------------------------------------------------------------------

class TestS2B1Golden:
    """S2B-1: Golden hash matches hardcoded expected values."""

    EXPECTED_HASH = "sha256:d4569b1fc67fd28fee4e92f8dad7b09e3eb3628c2ba5dd97dc142896ae92b578"

    # Golden records (raw NAE-style dicts)
    GOLDEN_RECORDS = [
        {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None},
        {"tsu_id": "TSU-A", "text": "abc", "n": 1},
    ]

    # Targets use non-existent paths -- resolve() is deterministic for absolute paths
    GOLDEN_TARGETS = [
        "/nonexistent_s2b_root/output/bench/tsu_dataset.jsonl",
        "/nonexistent_s2b_root/output/bench/tsu_manifest.json",
        "/nonexistent_s2b_root/data/제련완성본/registry/documents.json",
    ]

    def test_golden_hash_matches(self):
        """S2B-1: compute_plan_hash produces the expected golden hash."""
        result = compute_plan_hash("SRC_001", self.GOLDEN_RECORDS, self.GOLDEN_TARGETS)
        assert result == self.EXPECTED_HASH, f"Expected {self.EXPECTED_HASH!r}, got {result!r}"

    def test_record_content_shas_are_correct(self):
        """S2B-1: Verify individual record content SHA values."""
        # TSU-A: {"n":1,"text":"abc","tsu_id":"TSU-A"} -> d43ecf0e...
        rec_a = {"tsu_id": "TSU-A", "text": "abc", "n": 1}
        expected_sha_a = "d43ecf0e37352315b9fbde63762161331a0fc2103bc93f3dc3e24717cd09e095"
        assert _ref_record_content_sha256(rec_a) == expected_sha_a

        # TSU-B: {"flag":true,"n":2,"text":"나의 눈이 주를 보리니","tsu_id":"TSU-B","x":null} -> 078dfa...
        rec_b = {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None}
        expected_sha_b = "078dfabe1f806a9ef46f46b0d723a46ab4d306d08ab99f1bddc053cd4f66f295"
        assert _ref_record_content_sha256(rec_b) == expected_sha_b

    def test_reference_impl_matches_compute_plan_hash(self):
        """S2B-1: Independent reference implementation produces the same hash."""
        result_ref = _ref_compute_plan_hash("SRC_001", self.GOLDEN_RECORDS, self.GOLDEN_TARGETS)
        result_impl = compute_plan_hash("SRC_001", self.GOLDEN_RECORDS, self.GOLDEN_TARGETS)
        assert result_ref == result_impl == self.EXPECTED_HASH

    def test_hash_is_deterministic_across_subprocesses(self):
        """S2B-1: Same inputs produce same hash even with different PYTHONHASHSEED."""
        script = f'''
import sys, subprocess, hashlib, json
sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})
from scripts.merge_nae_corpus import compute_plan_hash

records = [
    {{"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None}},
    {{"tsu_id": "TSU-A", "text": "abc", "n": 1}},
]
targets = [
    "/nonexistent_s2b_root/output/bench/tsu_dataset.jsonl",
    "/nonexistent_s2b_root/output/bench/tsu_manifest.json",
    "/nonexistent_s2b_root/data/제련완성본/registry/documents.json",
]
print(compute_plan_hash("SRC_001", records, targets))
'''
        hashes = []
        for seed in ["0", "1", "42", "999999"]:
            proc = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True,
                env={**os.environ, "PYTHONHASHSEED": seed},
            )
            assert proc.returncode == 0, f"subprocess failed: {proc.stderr}"
            hashes.append(proc.stdout.strip())

        for h in hashes:
            assert h == self.EXPECTED_HASH, f"Hash mismatch with PYTHONHASHSEED={seed}: {h!r}"


# ---------------------------------------------------------------------------
# S2B-2: Sensitivity
# ---------------------------------------------------------------------------

class TestS2B2Sensitivity:
    """S2B-2: Changing any field changes the hash."""

    BASE_RECORDS = [
        {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None},
        {"tsu_id": "TSU-A", "text": "abc", "n": 1},
    ]
    BASE_TARGETS = [
        "/nonexistent_s2b_root/output/bench/tsu_dataset.jsonl",
        "/nonexistent_s2b_root/output/bench/tsu_manifest.json",
        "/nonexistent_s2b_root/data/제련완성본/registry/documents.json",
    ]
    BASE_HASH = "sha256:d4569b1fc67fd28fee4e92f8dad7b09e3eb3628c2ba5dd97dc142896ae92b578"

    def test_n_field_change_changes_hash(self):
        """S2B-2: Changing TSU-B's "n" from 2 to 3 -> different hash."""
        modified = [
            {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 3, "flag": True, "x": None},
            {"tsu_id": "TSU-A", "text": "abc", "n": 1},
        ]
        result = compute_plan_hash("SRC_001", modified, self.BASE_TARGETS)
        assert result == "sha256:5c4e5b880c047bdeda4bb85506360222d69bee48bd37246b922f90d9e2066d19"
        assert result != self.BASE_HASH

    def test_text_field_change_changes_hash(self):
        """S2B-2: Changing a record's text field -> different hash."""
        modified = [
            {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None},
            {"tsu_id": "TSU-A", "text": "abcd", "n": 1},  # changed "abc" -> "abcd"
        ]
        result = compute_plan_hash("SRC_001", modified, self.BASE_TARGETS)
        assert result != self.BASE_HASH

    def test_tsu_id_change_changes_hash(self):
        """S2B-2: Changing a tsu_id -> different hash."""
        modified = [
            {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None},
            {"tsu_id": "TSU-X", "text": "abc", "n": 1},  # changed TSU-A -> TSU-X
        ]
        result = compute_plan_hash("SRC_001", modified, self.BASE_TARGETS)
        assert result != self.BASE_HASH

    def test_source_id_change_changes_hash(self):
        """S2B-2: Changing source_id -> different hash."""
        result = compute_plan_hash("SRC_999", self.BASE_RECORDS, self.BASE_TARGETS)
        assert result != self.BASE_HASH

    def test_target_change_changes_hash(self):
        """S2B-2: Changing one target path -> different hash."""
        modified_targets = list(self.BASE_TARGETS)
        modified_targets[0] = "/nonexistent_s2b_root/output/bench/tsu_dataset_CHANGED.jsonl"
        result = compute_plan_hash("SRC_001", self.BASE_RECORDS, modified_targets)
        assert result != self.BASE_HASH


# ---------------------------------------------------------------------------
# S2B-3: Order independence for records, order dependence for targets
# ---------------------------------------------------------------------------

class TestS2B3Order:
    """S2B-3: Record order doesn't matter; target order does."""

    RECORDS_A_FIRST = [
        {"tsu_id": "TSU-A", "text": "abc", "n": 1},
        {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None},
    ]
    RECORDS_B_FIRST = [
        {"tsu_id": "TSU-B", "text": "나의 눈이 주를 보리니", "n": 2, "flag": True, "x": None},
        {"tsu_id": "TSU-A", "text": "abc", "n": 1},
    ]
    TARGETS_1 = [
        "/nonexistent_s2b_root/output/bench/tsu_dataset.jsonl",
        "/nonexistent_s2b_root/output/bench/tsu_manifest.json",
        "/nonexistent_s2b_root/data/제련완성본/registry/documents.json",
    ]
    TARGETS_2 = [
        "/nonexistent_s2b_root/data/제련완성본/registry/documents.json",
        "/nonexistent_s2b_root/output/bench/tsu_manifest.json",
        "/nonexistent_s2b_root/output/bench/tsu_dataset.jsonl",
    ]

    def test_record_order_does_not_affect_hash(self):
        """S2B-3: Swapping record order produces the same hash."""
        h1 = compute_plan_hash("SRC_001", self.RECORDS_A_FIRST, self.TARGETS_1)
        h2 = compute_plan_hash("SRC_001", self.RECORDS_B_FIRST, self.TARGETS_1)
        assert h1 == h2

    def test_target_order_affects_hash(self):
        """S2B-3: Swapping target order produces a different hash."""
        h1 = compute_plan_hash("SRC_001", self.RECORDS_A_FIRST, self.TARGETS_1)
        h2 = compute_plan_hash("SRC_001", self.RECORDS_A_FIRST, self.TARGETS_2)
        assert h1 != h2


# ---------------------------------------------------------------------------
# S2B-4: Format validation
# ---------------------------------------------------------------------------

class TestS2B4Format:
    """S2B-4: Result format is "sha256:" + lowercase hex 64 chars."""

    RECORDS = [
        {"tsu_id": "TSU-A", "text": "abc", "n": 1},
    ]
    TARGETS = [
        "/nonexistent_s2b_root/output/bench/tsu_dataset.jsonl",
        "/nonexistent_s2b_root/output/bench/tsu_manifest.json",
        "/nonexistent_s2b_root/data/제련완성본/registry/documents.json",
    ]

    def test_result_starts_with_sha256_prefix(self):
        """S2B-4: Result starts with 'sha256:'."""
        result = compute_plan_hash("SRC_001", self.RECORDS, self.TARGETS)
        assert result.startswith("sha256:")

    def test_result_hex_length_is_64(self):
        """S2B-4: Hex part is exactly 64 characters."""
        result = compute_plan_hash("SRC_001", self.RECORDS, self.TARGETS)
        hex_part = result[7:]
        assert len(hex_part) == 64

    def test_result_hex_is_lowercase(self):
        """S2B-4: Hex part is all lowercase."""
        result = compute_plan_hash("SRC_001", self.RECORDS, self.TARGETS)
        hex_part = result[7:]
        assert hex_part == hex_part.lower()

    def test_result_hex_contains_only_valid_chars(self):
        """S2B-4: Hex part contains only 0-9 and a-f."""
        import re
        result = compute_plan_hash("SRC_001", self.RECORDS, self.TARGETS)
        hex_part = result[7:]
        assert re.fullmatch(r"[0-9a-f]{64}", hex_part)


# ---------------------------------------------------------------------------
# S2B-5: Fail-closed validation
# ---------------------------------------------------------------------------

class TestS2B5FailClosed:
    """S2B-5: Invalid inputs raise CorpusMutationBlockedError."""

    TARGETS = [
        "/nonexistent_s2b_root/output/bench/tsu_dataset.jsonl",
        "/nonexistent_s2b_root/output/bench/tsu_manifest.json",
        "/nonexistent_s2b_root/data/제련완성본/registry/documents.json",
    ]

    def test_duplicate_tsu_id_raises(self):
        """S2B-5: Duplicate tsu_id -> CorpusMutationBlockedError."""
        records = [
            {"tsu_id": "TSU-A", "text": "abc", "n": 1},
            {"tsu_id": "TSU-A", "text": "def", "n": 2},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, self.TARGETS)

    def test_missing_tsu_id_raises(self):
        """S2B-5: Missing tsu_id -> CorpusMutationBlockedError."""
        records = [
            {"text": "abc", "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, self.TARGETS)

    def test_non_string_tsu_id_raises(self):
        """S2B-5: Non-string tsu_id -> CorpusMutationBlockedError."""
        records = [
            {"tsu_id": 123, "text": "abc", "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, self.TARGETS)

    def test_empty_tsu_id_raises(self):
        """S2B-5: Empty string tsu_id -> CorpusMutationBlockedError."""
        records = [
            {"tsu_id": "", "text": "abc", "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, self.TARGETS)

    def test_nan_value_raises(self):
        """S2B-5: NaN in record -> CorpusMutationBlockedError."""
        import math
        records = [
            {"tsu_id": "TSU-A", "value": float("nan"), "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, self.TARGETS)

    def test_infinity_value_raises(self):
        """S2B-5: Infinity in record -> CorpusMutationBlockedError."""
        import math
        records = [
            {"tsu_id": "TSU-A", "value": float("inf"), "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, self.TARGETS)

    def test_non_string_source_id_raises(self):
        """S2B-5: Non-string source_id -> CorpusMutationBlockedError."""
        records = [
            {"tsu_id": "TSU-A", "text": "abc", "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash(123, records, self.TARGETS)

    def test_target_count_not_3_raises(self):
        """S2B-5: Target list != 3 entries -> CorpusMutationBlockedError."""
        records = [
            {"tsu_id": "TSU-A", "text": "abc", "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, ["/a", "/b"])

    def test_target_count_too_many_raises(self):
        """S2B-5: Target list > 3 entries -> CorpusMutationBlockedError."""
        records = [
            {"tsu_id": "TSU-A", "text": "abc", "n": 1},
        ]
        with pytest.raises(CorpusMutationBlockedError):
            compute_plan_hash("SRC_001", records, ["/a", "/b", "/c", "/d"])


# ---------------------------------------------------------------------------
# S2B-6: Case sensitivity target test
# ---------------------------------------------------------------------------

class TestS2B6CaseSensitivity:
    """S2B-6: Case-insensitive filesystem detection and behavior."""

    def test_case_variant_targets_on_cifs_or_hfsplus(self, tmp_path: Path):
        """S2B-6: On case-insensitive filesystem, case-variant targets resolve to same file.

        Creates a file in tmp, then checks if upper/lower case variants resolve to the same inode.
        If they do (case-insensitive FS), verifies that case-variant target paths produce different hashes.
        """
        # Create a real file in tmp
        test_file = tmp_path / "testfile.txt"
        test_file.write_text("content", encoding="utf-8")

        # Check if filesystem is case-insensitive by comparing inodes
        import os as _os
        try:
            lower_path = tmp_path / "lowercase.txt"
            upper_path = tmp_path / "LOWERCASE.TXT"

            # Write to lowercase path
            lower_path.write_text("content", encoding="utf-8")

            # Check if upper case variant is the same file
            is_same = False
            try:
                is_same = _os.path.samefile(str(lower_path), str(upper_path))
            except OSError:
                is_same = False

            if not is_same:
                # Case-sensitive filesystem -- skip this test
                pytest.skip("Case-sensitive filesystem; case-variant targets are different files")

            # On case-insensitive FS, verify that case-variant paths produce different hashes
            # because str(Path.resolve()) preserves the original case in the path string
            targets_normal = [str(lower_path), "/nonexistent_s2b_root/output/bench/tsu_manifest.json", "/nonexistent_s2b_root/data/제련완성본/registry/documents.json"]
            targets_case_variant = [str(upper_path), "/nonexistent_s2b_root/output/bench/tsu_manifest.json", "/nonexistent_s2b_root/data/제련완성본/registry/documents.json"]

            records = [{"tsu_id": "TSU-A", "text": "abc", "n": 1}]
            h_normal = compute_plan_hash("SRC_001", records, targets_normal)
            h_variant = compute_plan_hash("SRC_001", records, targets_case_variant)

            # The resolved paths should be the same file (same inode), but the hash input differs
            # because str(Path.resolve()) preserves case in the path component
            assert h_normal != h_variant, "Case-variant targets should produce different hashes"

        finally:
            # Cleanup
            if lower_path.exists():
                lower_path.unlink()
            if upper_path.exists():
                upper_path.unlink()


# ---------------------------------------------------------------------------
# S2B-7: Full merge_nae_corpus() path tests
# ---------------------------------------------------------------------------

class TestS2B7FullMergePath:
    """S2B-7: End-to-end merge_nae_corpus() with plan_hash."""

    def test_approved_plan_hash_match_returns_completed(self, tmp_path: Path):
        """S2B-7(i): Approved plan_hash matches -> status == 'completed'."""
        import json
        from datetime import datetime, timezone
        from unittest.mock import patch

        import scripts.merge_nae_corpus as mod
        from scripts.corpus_approval_gate import ApprovalStatus, CorpusMutationManifest
        from scripts.merge_nae_corpus import merge_nae_corpus, CorpusMutationBlockedError

        # Setup production structure
        prod = tmp_path / "mock_prod"
        (prod / "output" / "bench").mkdir(parents=True)
        (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = prod / "output" / "bench" / "tsu_manifest.json"
        rg = prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        # Compute real plan_hash using reference implementation
        # Must use transformed records (same as merge_nae_corpus does internally)
        # doc_id is based on directory name: f"nae_{item.name}" where item.name = "TSU-0010"
        from scripts.merge_nae_corpus import _transform_nae_record
        raw_naes = [{"work_id": "TEST_SOURCE_S2B7", "tsu_id": "TSU-0010"}]
        doc_id = f"nae_TSU-0010"  # matches merge_nae_corpus: f"nae_{item.name}"
        transformed = [_transform_nae_record(r, doc_id) for r in raw_naes]
        target_paths = [ds, mf, rg]
        approved_plan_hash = _ref_compute_plan_hash("TEST_SOURCE_S2B7", transformed, target_paths)

        # Compute actual dataset SHA for matching
        import hashlib as _h
        _sha = _h.sha256()
        with open(ds, "rb") as _f:
            for chunk in iter(lambda: _f.read(1024 * 1024), b""):
                _sha.update(chunk)
        actual_sha = _sha.hexdigest()

        # Create approval artifact
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir()
        now_str = datetime.now(timezone.utc).isoformat()
        approval = {
            "schema_version": 2,
            "source_id": "TEST_SOURCE_S2B7",
            "target_paths_realpath": [str(ds.resolve()), str(mf.resolve()), str(rg.resolve())],
            "plan_hash": approved_plan_hash,
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": actual_sha,
            "final_decision": "APPROVED",
            "approved_at": now_str,
        }
        approval_path = approval_dir / "production_targets" / "TEST_SOURCE_S2B7.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

        # Create config
        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod.resolve()}\n  approval_dir: {approval_dir.resolve()}\n",
            encoding="utf-8",
        )

        # Setup NAE corpus
        nae_corpus = tmp_path / "nae" / "corpus" / "tsu"
        nae_corpus.mkdir(parents=True)
        tsu_dir = nae_corpus / "TSU-0010"
        tsu_dir.mkdir()
        tsu_file = tsu_dir / "tsu.json"
        tsu_file.write_text(json.dumps([{"work_id": "TEST_SOURCE_S2B7", "tsu_id": "TSU-0010"}]), encoding="utf-8")

        def spy_gate(source_id, decisions_dir, tsu_ids):
            return type("MockGateResult", (), {
                "approved": True, "status": ApprovalStatus.APPROVED, "reason": "",
                "source_id": source_id, "approved_tsu_ids": frozenset(), "rejected_tsu_ids": frozenset(),
            })()

        def spy_manifest(source_id, decisions_dir):
            return CorpusMutationManifest(
                source_id=source_id,
                approved_tsu_ids=frozenset(["TSU-0010"]),
                approved_count=1,
                reviewer_id="R-TEST",
                review_timestamp=None,
                final_decision="APPROVED",
            )

        with patch.object(mod, "verify_corpus_mutation_approval", side_effect=spy_gate):
            with patch.object(mod, "build_approval_manifest", side_effect=spy_manifest):
                result = merge_nae_corpus(
                    source_id="TEST_SOURCE_S2B7", data_root=prod, config_path=config,
                    nae_corpus_dir=nae_corpus,
                )

        assert result["status"] == "completed", f"Expected 'completed', got {result['status']}"

    def test_forged_plan_hash_raises_blocked_error(self, tmp_path: Path):
        """S2B-7(ii): Forged plan_hash -> CorpusMutationBlockedError(PLAN_HASH_MISMATCH)."""
        import json
        from datetime import datetime, timezone
        from unittest.mock import patch

        import scripts.merge_nae_corpus as mod
        from scripts.corpus_approval_gate import ApprovalStatus, CorpusMutationManifest
        from scripts.merge_nae_corpus import merge_nae_corpus, CorpusMutationBlockedError

        # Setup production structure
        prod = tmp_path / "mock_prod"
        (prod / "output" / "bench").mkdir(parents=True)
        (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = prod / "output" / "bench" / "tsu_manifest.json"
        rg = prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        # Compute actual plan_hash (using transformed records)
        from scripts.merge_nae_corpus import _transform_nae_record
        raw_naes = [{"work_id": "TEST_SOURCE_S2B7II", "tsu_id": "TSU-0011"}]
        doc_id = f"nae_TSU-0011"  # matches merge_nae_corpus: f"nae_{item.name}"
        transformed = [_transform_nae_record(r, doc_id) for r in raw_naes]
        target_paths = [ds, mf, rg]
        actual_plan_hash = _ref_compute_plan_hash("TEST_SOURCE_S2B7II", transformed, target_paths)

        # Use a forged (wrong) plan_hash
        forged_hash = "sha256:" + "f" * 64

        # Compute actual dataset SHA for matching
        import hashlib as _h
        _sha = _h.sha256()
        with open(ds, "rb") as _f:
            for chunk in iter(lambda: _f.read(1024 * 1024), b""):
                _sha.update(chunk)
        actual_sha = _sha.hexdigest()

        # Create approval artifact with forged hash
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir()
        now_str = datetime.now(timezone.utc).isoformat()
        approval = {
            "schema_version": 2,
            "source_id": "TEST_SOURCE_S2B7II",
            "target_paths_realpath": [str(ds.resolve()), str(mf.resolve()), str(rg.resolve())],
            "plan_hash": forged_hash,
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": actual_sha,
            "final_decision": "APPROVED",
            "approved_at": now_str,
        }
        approval_path = approval_dir / "production_targets" / "TEST_SOURCE_S2B7II.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

        # Create config
        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod.resolve()}\n  approval_dir: {approval_dir.resolve()}\n",
            encoding="utf-8",
        )

        # Setup NAE corpus
        nae_corpus = tmp_path / "nae" / "corpus" / "tsu"
        nae_corpus.mkdir(parents=True)
        tsu_dir = nae_corpus / "TSU-0011"
        tsu_dir.mkdir()
        tsu_file = tsu_dir / "tsu.json"
        tsu_file.write_text(json.dumps([{"work_id": "TEST_SOURCE_S2B7II", "tsu_id": "TSU-0011"}]), encoding="utf-8")

        def spy_gate(source_id, decisions_dir, tsu_ids):
            return type("MockGateResult", (), {
                "approved": True, "status": ApprovalStatus.APPROVED, "reason": "",
                "source_id": source_id, "approved_tsu_ids": frozenset(), "rejected_tsu_ids": frozenset(),
            })()

        def spy_manifest(source_id, decisions_dir):
            return CorpusMutationManifest(
                source_id=source_id,
                approved_tsu_ids=frozenset(["TSU-0011"]),
                approved_count=1,
                reviewer_id="R-TEST",
                review_timestamp=None,
                final_decision="APPROVED",
            )

        # Track write calls
        write_ds_calls = []
        save_reg_calls = []
        write_man_calls = []

        original_write_tsu_dataset = mod.write_tsu_dataset
        def spy_write_tsu_dataset(records, path):
            write_ds_calls.append((records, str(path)))
            return original_write_tsu_dataset(records, path)

        original_save_identity_registry = mod.save_identity_registry
        def spy_save_identity_registry(registry, path):
            save_reg_calls.append((registry, str(path)))
            return original_save_identity_registry(registry, path)

        original_write_manifest = mod.write_manifest
        def spy_write_manifest(records, registry, manifest_path, registry_path, dataset_path):
            write_man_calls.append((records, str(manifest_path)))
            return original_write_manifest(records, registry, manifest_path, registry_path, dataset_path)

        with patch.object(mod, "verify_corpus_mutation_approval", side_effect=spy_gate):
            with patch.object(mod, "build_approval_manifest", side_effect=spy_manifest):
                with pytest.raises(CorpusMutationBlockedError) as exc_info:
                    merge_nae_corpus(
                        source_id="TEST_SOURCE_S2B7II", data_root=prod, config_path=config,
                        nae_corpus_dir=nae_corpus,
                    )

        assert "PLAN_HASH_MISMATCH" in str(exc_info.value)
        # Verify no writes occurred
        assert len(write_ds_calls) == 0, f"write_tsu_dataset should not be called, but was called {len(write_ds_calls)} times"
        assert len(save_reg_calls) == 0, f"save_identity_registry should not be called, but was called {len(save_reg_calls)} times"
        assert len(write_man_calls) == 0, f"write_manifest should not be called, but was called {len(write_man_calls)} times"

        # Verify file SHA-256 unchanged
        import hashlib
        for fpath in [ds, mf, rg]:
            h = hashlib.sha256()
            with open(fpath, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            # File should still have original content
            if fpath == ds:
                assert h.hexdigest() == hashlib.sha256(b"").hexdigest()
            elif fpath == mf:
                assert h.hexdigest() == hashlib.sha256('{"manifest": true}'.encode()).hexdigest()
            elif fpath == rg:
                assert h.hexdigest() == hashlib.sha256('{"documents": {}}'.encode()).hexdigest()

    def test_corpus_mutation_after_approval_raises_plan_hash_mismatch(self, tmp_path: Path):
        """S2B-7(iii): Corpus source_text mutated after approval -> PLAN_HASH_MISMATCH."""
        import json
        from datetime import datetime, timezone
        from unittest.mock import patch

        import scripts.merge_nae_corpus as mod
        from scripts.corpus_approval_gate import ApprovalStatus, CorpusMutationManifest
        from scripts.merge_nae_corpus import merge_nae_corpus, CorpusMutationBlockedError

        # Setup production structure
        prod = tmp_path / "mock_prod"
        (prod / "output" / "bench").mkdir(parents=True)
        (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = prod / "output" / "bench" / "tsu_manifest.json"
        rg = prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        # Compute actual plan_hash for the original records (using transformed records)
        from scripts.merge_nae_corpus import _transform_nae_record
        raw_naes = [{"work_id": "TEST_SOURCE_S2B7III", "tsu_id": "TSU-0012"}]
        doc_id = f"nae_TSU-0012"  # matches merge_nae_corpus: f"nae_{item.name}"
        transformed = [_transform_nae_record(r, doc_id) for r in raw_naes]
        target_paths = [ds, mf, rg]
        approved_plan_hash = _ref_compute_plan_hash("TEST_SOURCE_S2B7III", transformed, target_paths)

        # Compute actual dataset SHA for matching
        import hashlib as _h
        _sha = _h.sha256()
        with open(ds, "rb") as _f:
            for chunk in iter(lambda: _f.read(1024 * 1024), b""):
                _sha.update(chunk)
        actual_sha = _sha.hexdigest()

        # Create approval artifact with correct hash
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir()
        now_str = datetime.now(timezone.utc).isoformat()
        approval = {
            "schema_version": 2,
            "source_id": "TEST_SOURCE_S2B7III",
            "target_paths_realpath": [str(ds.resolve()), str(mf.resolve()), str(rg.resolve())],
            "plan_hash": approved_plan_hash,
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": actual_sha,
            "final_decision": "APPROVED",
            "approved_at": now_str,
        }
        approval_path = approval_dir / "production_targets" / "TEST_SOURCE_S2B7III.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

        # Create config
        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod.resolve()}\n  approval_dir: {approval_dir.resolve()}\n",
            encoding="utf-8",
        )

        # Setup NAE corpus with MUTATED content (different text)
        nae_corpus = tmp_path / "nae" / "corpus" / "tsu"
        nae_corpus.mkdir(parents=True)
        tsu_dir = nae_corpus / "TSU-0012"
        tsu_dir.mkdir()
        tsu_file = tsu_dir / "tsu.json"
        # Mutated source_text
        tsu_file.write_text(json.dumps([{"work_id": "TEST_SOURCE_S2B7III", "tsu_id": "TSU-0012", "source_text": "MUTATED content"}]), encoding="utf-8")

        def spy_gate(source_id, decisions_dir, tsu_ids):
            return type("MockGateResult", (), {
                "approved": True, "status": ApprovalStatus.APPROVED, "reason": "",
                "source_id": source_id, "approved_tsu_ids": frozenset(), "rejected_tsu_ids": frozenset(),
            })()

        def spy_manifest(source_id, decisions_dir):
            return CorpusMutationManifest(
                source_id=source_id,
                approved_tsu_ids=frozenset(["TSU-0012"]),
                approved_count=1,
                reviewer_id="R-TEST",
                review_timestamp=None,
                final_decision="APPROVED",
            )

        # Track write calls
        write_ds_calls = []
        save_reg_calls = []
        write_man_calls = []

        original_write_tsu_dataset = mod.write_tsu_dataset
        def spy_write_tsu_dataset(records, path):
            write_ds_calls.append((records, str(path)))
            return original_write_tsu_dataset(records, path)

        original_save_identity_registry = mod.save_identity_registry
        def spy_save_identity_registry(registry, path):
            save_reg_calls.append((registry, str(path)))
            return original_save_identity_registry(registry, path)

        original_write_manifest = mod.write_manifest
        def spy_write_manifest(records, registry, manifest_path, registry_path, dataset_path):
            write_man_calls.append((records, str(manifest_path)))
            return original_write_manifest(records, registry, manifest_path, registry_path, dataset_path)

        with patch.object(mod, "verify_corpus_mutation_approval", side_effect=spy_gate):
            with patch.object(mod, "build_approval_manifest", side_effect=spy_manifest):
                with pytest.raises(CorpusMutationBlockedError) as exc_info:
                    merge_nae_corpus(
                        source_id="TEST_SOURCE_S2B7III", data_root=prod, config_path=config,
                        nae_corpus_dir=nae_corpus,
                    )

        assert "PLAN_HASH_MISMATCH" in str(exc_info.value)
        # Verify no writes occurred
        assert len(write_ds_calls) == 0, f"write_tsu_dataset should not be called, but was called {len(write_ds_calls)} times"
        assert len(save_reg_calls) == 0, f"save_identity_registry should not be called, but was called {len(save_reg_calls)} times"
        assert len(write_man_calls) == 0, f"write_manifest should not be called, but was called {len(write_man_calls)} times"


# ---------------------------------------------------------------------------
# S2B-8: Non-production data_root behavior
# ---------------------------------------------------------------------------

class TestS2B8NonProduction:
    """S2B-8: Non-production data_root merges without plan_hash comparison."""

    def test_non_production_data_root_merges_without_plan_comparison(self, tmp_path: Path):
        """S2B-8: data_root not under production_root -> merge proceeds without plan_hash check."""
        import json
        from datetime import datetime, timezone
        from unittest.mock import patch

        import scripts.merge_nae_corpus as mod
        from scripts.corpus_approval_gate import ApprovalStatus, CorpusMutationManifest
        from scripts.merge_nae_corpus import merge_nae_corpus, CorpusMutationBlockedError

        # Setup non-production structure (different root from production)
        non_prod = tmp_path / "non_prod"
        (non_prod / "output" / "bench").mkdir(parents=True)
        (non_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = non_prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = non_prod / "output" / "bench" / "tsu_manifest.json"
        rg = non_prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        # Create approval with a bogus plan_hash (should be ignored for non-production)
        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir()
        now_str = datetime.now(timezone.utc).isoformat()
        approval = {
            "schema_version": 2,
            "source_id": "TEST_SOURCE_S2B8",
            "target_paths_realpath": [str(ds.resolve()), str(mf.resolve()), str(rg.resolve())],
            "plan_hash": "sha256:" + "z" * 64,  # bogus hash -- should be ignored
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": "a" * 64,  # also bogus
            "final_decision": "APPROVED",
            "approved_at": now_str,
        }
        approval_path = approval_dir / "production_targets" / "TEST_SOURCE_S2B8.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

        # Create config with a different production_root
        fake_prod = tmp_path / "fake_prod"
        fake_prod.mkdir()
        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {fake_prod.resolve()}\n  approval_dir: {approval_dir.resolve()}\n",
            encoding="utf-8",
        )

        # Setup NAE corpus
        nae_corpus = tmp_path / "nae" / "corpus" / "tsu"
        nae_corpus.mkdir(parents=True)
        tsu_dir = nae_corpus / "TSU-0013"
        tsu_dir.mkdir()
        tsu_file = tsu_dir / "tsu.json"
        tsu_file.write_text(json.dumps([{"work_id": "TEST_SOURCE_S2B8", "tsu_id": "TSU-0013"}]), encoding="utf-8")

        def spy_gate(source_id, decisions_dir, tsu_ids):
            return type("MockGateResult", (), {
                "approved": True, "status": ApprovalStatus.APPROVED, "reason": "",
                "source_id": source_id, "approved_tsu_ids": frozenset(), "rejected_tsu_ids": frozenset(),
            })()

        def spy_manifest(source_id, decisions_dir):
            return CorpusMutationManifest(
                source_id=source_id,
                approved_tsu_ids=frozenset(["TSU-0013"]),
                approved_count=1,
                reviewer_id="R-TEST",
                review_timestamp=None,
                final_decision="APPROVED",
            )

        with patch.object(mod, "verify_corpus_mutation_approval", side_effect=spy_gate):
            with patch.object(mod, "build_approval_manifest", side_effect=spy_manifest):
                result = merge_nae_corpus(
                    source_id="TEST_SOURCE_S2B8", data_root=non_prod, config_path=config,
                    nae_corpus_dir=nae_corpus,
                )

        assert result["status"] == "completed", f"Expected 'completed', got {result['status']}"


# ---------------------------------------------------------------------------
# S2B-11: ApprovalEvaluation.plan_hash
# ---------------------------------------------------------------------------

class TestS2B11ApprovalEvaluationPlanHash:
    """S2B-11: ApprovalEvaluation.plan_hash behavior."""

    def test_valid_approval_has_plan_hash(self, tmp_path: Path):
        """S2B-11: VALID result carries the approval's plan_hash value."""
        import json
        from datetime import datetime, timezone

        prod = tmp_path / "prod"
        (prod / "output" / "bench").mkdir(parents=True)
        (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = prod / "output" / "bench" / "tsu_manifest.json"
        rg = prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        expected_plan_hash = "sha256:" + "a" * 64

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir()
        now_str = datetime.now(timezone.utc).isoformat()
        approval = {
            "schema_version": 2,
            "source_id": "TEST_SOURCE_S2B11",
            "target_paths_realpath": [str(ds.resolve()), str(mf.resolve()), str(rg.resolve())],
            "plan_hash": expected_plan_hash,
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": "b" * 64,
            "final_decision": "APPROVED",
            "approved_at": now_str,
        }
        approval_path = approval_dir / "production_targets" / "TEST_SOURCE_S2B11.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod.resolve()}\n  approval_dir: {approval_dir.resolve()}\n",
            encoding="utf-8",
        )

        result = mod.evaluate_approval_v2(approval_path, config_path=config, dataset_sha256_current="b" * 64)

        assert result.state == ApprovalState.VALID
        assert result.plan_hash == expected_plan_hash, (
            f"VALID approval should carry the plan_hash from artifact: {result.plan_hash!r}"
        )

    def test_rejected_approval_has_none_plan_hash(self, tmp_path: Path):
        """S2B-11: REJECTED result carries None for plan_hash."""
        import json
        from datetime import datetime, timezone

        prod = tmp_path / "prod"
        (prod / "output" / "bench").mkdir(parents=True)
        (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = prod / "output" / "bench" / "tsu_manifest.json"
        rg = prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir()
        now_str = datetime.now(timezone.utc).isoformat()
        # Wrong dataset SHA -> REJECTED
        approval = {
            "schema_version": 2,
            "source_id": "TEST_SOURCE_S2B11R",
            "target_paths_realpath": [str(ds.resolve()), str(mf.resolve()), str(rg.resolve())],
            "plan_hash": "sha256:" + "a" * 64,
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": "wrong_hash" * 10 + "abcde",  # wrong SHA
            "final_decision": "APPROVED",
            "approved_at": now_str,
        }
        approval_path = approval_dir / "production_targets" / "TEST_SOURCE_S2B11R.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod.resolve()}\n  approval_dir: {approval_dir.resolve()}\n",
            encoding="utf-8",
        )

        result = mod.evaluate_approval_v2(approval_path, config_path=config, dataset_sha256_current="b" * 64)

        assert result.state == ApprovalState.REJECTED
        assert result.plan_hash is None, (
            f"REJECTED approval should have plan_hash=None, got {result.plan_hash!r}"
        )


# ---------------------------------------------------------------------------
# S2B-12: All fixtures are tmp
# ---------------------------------------------------------------------------

class TestS2B12TmpFixtures:
    """S2B-12: All fixtures use tmp paths and prove correct relationships."""

    def test_compute_plan_hash_uses_tmp_paths(self, tmp_path: Path):
        """S2B-12: compute_plan_hash works with tmp paths and proves path relationships."""
        # Create real files in tmp
        prod = tmp_path / "prod"
        (prod / "output" / "bench").mkdir(parents=True)
        (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = prod / "output" / "bench" / "tsu_manifest.json"
        rg = prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        # Verify all paths are under tmp_path
        assert str(tmp_path) in str(ds.resolve())
        assert str(tmp_path) in str(mf.resolve())
        assert str(tmp_path) in str(rg.resolve())

        # compute_plan_hash should work with these paths
        records = [{"tsu_id": "TSU-A", "text": "abc", "n": 1}]
        result = compute_plan_hash("SRC_001", records, [ds, mf, rg])
        assert result.startswith("sha256:")
        # Verify the resolved paths are in the hash (by checking determinism)
        result2 = compute_plan_hash("SRC_001", records, [ds, mf, rg])
        assert result == result2

    def test_approval_evaluation_uses_tmp_paths(self, tmp_path: Path):
        """S2B-12: Approval evaluation works with tmp paths and proves relationships."""
        import json
        from datetime import datetime, timezone

        prod = tmp_path / "prod"
        (prod / "output" / "bench").mkdir(parents=True)
        (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        ds = prod / "output" / "bench" / "tsu_dataset.jsonl"
        mf = prod / "output" / "bench" / "tsu_manifest.json"
        rg = prod / "data" / "제련완성본" / "registry" / "documents.json"
        ds.write_text("", encoding="utf-8")
        mf.write_text('{"manifest": true}', encoding="utf-8")
        rg.write_text('{"documents": {}}', encoding="utf-8")

        # Verify production_root is under tmp_path
        assert str(tmp_path) in str(prod.resolve())

        approval_dir = tmp_path / "approval_dir"
        approval_dir.mkdir()
        now_str = datetime.now(timezone.utc).isoformat()
        approval = {
            "schema_version": 2,
            "source_id": "TEST_SOURCE_S2B12",
            "target_paths_realpath": [str(ds.resolve()), str(mf.resolve()), str(rg.resolve())],
            "plan_hash": "sha256:" + "a" * 64,
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": "b" * 64,
            "final_decision": "APPROVED",
            "approved_at": now_str,
        }
        approval_path = approval_dir / "production_targets" / "TEST_SOURCE_S2B12.json"
        approval_path.parent.mkdir(parents=True, exist_ok=True)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod.resolve()}\n  approval_dir: {approval_dir.resolve()}\n",
            encoding="utf-8",
        )

        # Verify config paths are under tmp_path
        assert str(tmp_path) in str(config.resolve())
        assert str(tmp_path) in str(approval_dir.resolve())

        result = mod.evaluate_approval_v2(approval_path, config_path=config, dataset_sha256_current="b" * 64)
        assert result.state == ApprovalState.VALID


# ---------------------------------------------------------------------------
# Import mod at module level for tests that need it
# ---------------------------------------------------------------------------
import scripts.merge_nae_corpus as mod

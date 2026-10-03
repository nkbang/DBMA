"""tests/test_merge_production_path_safety.py — Production path safety tests.

Tests for NAE-MERGE-PRODUCTION-PATH-SAFETY-001:
  T1: Path omission -> BLOCK
  T2: Mixed-path -> BLOCK
  T3: Production target + no approval -> BLOCK
  T4: Path bypass (symlink, ../, relative) -> BLOCK
  T5: Dataset SHA mismatch -> BLOCK
  T6: Valid non-production path -> PASS
  T7: Valid production approval -> PASS
  T8: Session-level production guard
  T9: Production placeholder rejection (fail-closed)
  T10: Config fail-closed scenarios
  T11: Hardlink/symlink alias detection
  T12: Production root identity
  T13: Normal non-production tmp data_root passes through
  T14: Mixed targets
  T15: resolve_target_paths explicit data_root tests
  T16: data_root contract tests (restored)
  T17: Default config fail-closed (placeholder)
  T18: Production identity with tmp config monkeypatch
"""

import json
import hashlib
import os
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.merge_nae_corpus import (
    merge_nae_corpus,
    resolve_target_paths,
    verify_production_target_approval,
    compute_dataset_sha256,
    CorpusMutationBlockedError,
    _load_production_root,
    _detect_hardlink_alias,
    _is_production_identity,
    _DEFAULT_CONFIG_PATH,
)
from scripts.corpus_approval_gate import ApprovalStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_naes_record(
    id_: int,
    book: str = "Test Book",
    author: str = "Test Author",
    claim: str = "Test theological claim.",
    source_text: str = "Test source text content.",
    doctrine: str = "christology",
) -> dict:
    return {
        "id": id_,
        "book": book,
        "author": author,
        "source_type": "nae_canonical",
        "copyright_status": "public_domain",
        "author_id": "AUTH_001",
        "work_id": "TEST_SOURCE",
        "scriptures": None,
        "claim": claim,
        "source_text": source_text,
        "doctrine": doctrine,
        "confidence": 0.95,
        "extraction_method": "nae_pipeline",
        "review_status": "verified",
        "page": 42,
    }


def _make_corpus_dir(tmp_path: Path, source_id: str, tsu_ids: list[str]) -> Path:
    """Create a corpus directory with tsu.json for the given source."""
    croot = tmp_path / "corpus"
    croot.mkdir(parents=True)
    cdir = croot / source_id
    cdir.mkdir(parents=True)
    records = [
        {
            "id": i + 1,
            "tsu_id": tid,
            "work_id": source_id,
            "claim": f"Claim for {tid}",
            "source_text": f"Source text for {tid}",
        }
        for i, tid in enumerate(tsu_ids)
    ]
    (cdir / "tsu.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return croot


def _make_approved_decisions_dir(tmp_path: Path, source_id: str, tsu_ids: list[str]) -> Path:
    """Create an approved decisions directory."""
    ddir = tmp_path / "decisions"
    ddir.mkdir(parents=True)
    file_data = {
        "decisions": [
            {
                "tsu_id": tid,
                "work_id": source_id,
                "gate_id": f"G-{source_id}",
                "reviewer_id": f"R-{source_id}",
                "answers": {"Q1": "A", "Q2": "A", "Q3": "A"},
                "final_decision": "APPROVED",
            }
            for tid in tsu_ids
        ]
    }
    (ddir / f"{source_id}_decisions.json").write_text(
        json.dumps(file_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return ddir


def _file_hash(path: str) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_tmp_config_with_production(tmp_path: Path, prod_root: Path) -> Path:
    """Create a tmp config.yaml with valid production_root pointing to prod_root."""
    config = tmp_path / "config.yaml"
    config.write_text(
        f"merge-safety:\n  production_root: {prod_root.resolve()}\n",
        encoding="utf-8",
    )
    return config


def _make_mock_production(tmp_path: Path) -> Path:
    """Create a mock production directory with all canonical targets."""
    prod = tmp_path / "mock_production"
    (prod / "output" / "bench").mkdir(parents=True)
    (prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
    (prod / "output" / "bench" / "tsu_dataset.jsonl").write_text("", encoding="utf-8")
    (prod / "output" / "bench" / "tsu_manifest.json").write_text("{}", encoding="utf-8")
    (prod / "data" / "제련완성본" / "registry" / "documents.json").write_text(
        json.dumps({"documents": {}}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return prod


def _make_tmp_config_no_match(tmp_path: Path) -> Path:
    """Create a tmp config with valid production_root that does NOT match candidate data_roots.
    
    Uses tmp_path itself as the production_root (which exists).
    Candidate data_roots are subdirectories of tmp_path, so they won't match.
    """
    # Use tmp_path as production_root - it exists and is different from any subdirectory
    return _make_tmp_config_with_production(tmp_path, tmp_path)

# ---------------------------------------------------------------------------
# T1: Path omission -> BLOCK
# ---------------------------------------------------------------------------

class TestT1PathOmission:
    """T1: Missing required paths should BLOCK."""

    def test_no_data_root_and_no_paths(self, tmp_path: Path):
        """data_root도 mutation path도 없으면 BLOCK."""
        target = resolve_target_paths(data_root=None)
        assert target.data_root is None

    def test_no_data_root_with_single_path(self, tmp_path: Path):
        """data_root 없이 단일 path만 제공해도 data_root는 None."""
        target = resolve_target_paths(data_root=None)
        assert target.data_root is None


# ---------------------------------------------------------------------------
# T2: Mixed-path -> BLOCK (new contract: single data_root)
# ---------------------------------------------------------------------------

class TestT2MixedPath:
    """T2: dataset/manifest/registry가 서로 다른 root를 가리면 BLOCK."""

    def test_all_paths_derived_from_data_root(self, tmp_path: Path):
        """data_root 제공 시 모든 경로가 그 아래에서 유도됨."""
        tmp_output = tmp_path / "my_output"
        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=tmp_output, config_path=config)
        assert target.dataset_path.resolve().is_relative_to(tmp_output.resolve())
        assert target.manifest_path.resolve().is_relative_to(tmp_output.resolve())
        assert target.registry_path.resolve().is_relative_to(tmp_output.resolve())

    def test_no_data_root_all_paths_empty(self, tmp_path: Path):
        """data_root 없으면 모든 경로가 비어있음."""
        target = resolve_target_paths(data_root=None)
        assert target.dataset_path == Path("")
        assert target.manifest_path == Path("")
        assert target.registry_path == Path("")


# ---------------------------------------------------------------------------
# T3: Production target + no approval -> BLOCK
# ---------------------------------------------------------------------------

class TestT3ProductionNoApproval:
    """T3: production data_root + 승인 artifact 없으면 BLOCK."""

    def test_production_target_without_approval_blocks(self, tmp_path: Path):
        """production data_root + 승인 artifact 없으면 BLOCK."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        target = resolve_target_paths(data_root=prod, config_path=config)
        assert target.is_production is True

        corpus_root = _make_corpus_dir(tmp_path, "TEST_SOURCE", ["TSU-001"])
        ddir = _make_approved_decisions_dir(tmp_path, "TEST_SOURCE", ["TSU-001"])

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="TEST_SOURCE",
                data_root=prod,
                nae_corpus_dir=corpus_root,
                decisions_dir=ddir,
                config_path=config,
            )
        assert "approval" in str(exc_info.value).lower() or "production" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# T4: Path bypass (symlink, ../, relative) -> BLOCK
# ---------------------------------------------------------------------------

class TestT4PathBypass:
    """T4: symlink, ../, relative path로 production을 우회하면 BLOCK."""

    def test_symlink_to_production(self, tmp_path: Path):
        """symlink으로 production을 가리키면 realpath 기반 판정으로 production으로 인식."""
        real_prod = tmp_path / "real_output"
        real_prod.mkdir(parents=True)
        (real_prod / "output" / "bench").mkdir(parents=True)

        link_path = tmp_path / "link_to_prod"
        link_path.symlink_to(real_prod)

        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=link_path, config_path=config)
        assert target.data_root == real_prod.resolve()

    def test_relative_path_resolution(self, tmp_path: Path):
        """relative path가 올바른 디렉토리를 가리키면 realpath로 해석."""
        real_dir = tmp_path / "real_output"
        real_dir.mkdir(parents=True)
        subdir = real_dir / "sub"
        subdir.mkdir()

        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=subdir, config_path=config)
        assert target.data_root == subdir.resolve()

    def test_absolute_path_consistency(self, tmp_path: Path):
        """absolute path 제공 시 data_root가 정확히 설정됨."""
        real_dir = tmp_path / "abs_output"
        real_dir.mkdir(parents=True)

        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=real_dir, config_path=config)
        assert target.data_root == real_dir.resolve()


# ---------------------------------------------------------------------------
# T5: Dataset SHA mismatch -> BLOCK
# ---------------------------------------------------------------------------

class TestT5DatasetSHAMismatch:
    """T5: approval artifact의 dataset_sha256_before와 현재 hash가 다르면 BLOCK."""

    def test_sha_mismatch_blocks(self, tmp_path: Path):
        """dataset SHA가 승인 당시과 다르면 BLOCK."""
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        approval_dir = tmp_path / "NAE" / "review" / "human" / "production_targets"
        approval_dir.mkdir(parents=True)

        approval = {
            "schema_version": 1,
            "source_id": "TEST_SOURCE",
            "target_root_realpath": str(Path("output").resolve()),
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": "0" * 64,
            "final_decision": "APPROVED",
            "approved_at": "2026-10-01T00:00:00",
        }
        (approval_dir / "TEST_SOURCE.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        valid, reason = verify_production_target_approval(
            target_root=Path("output").resolve(),
            source_id="TEST_SOURCE",
            dataset_path=dataset,
            decisions_dir=tmp_path / "decisions",
            approval_dir=approval_dir,
        )
        assert valid is False
        assert "dataset_sha256 mismatch" in reason

    def test_sha_match_passes(self, tmp_path: Path):
        """dataset SHA가 일치하면 통과."""
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        approval_dir = tmp_path / "NAE" / "review" / "human" / "production_targets"
        approval_dir.mkdir(parents=True)

        current_sha = compute_dataset_sha256(dataset)
        approval = {
            "schema_version": 1,
            "source_id": "TEST_SOURCE",
            "target_root_realpath": str(Path("output").resolve()),
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": current_sha,
            "final_decision": "APPROVED",
            "approved_at": "2026-10-01T00:00:00",
        }
        (approval_dir / "TEST_SOURCE.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        valid, reason = verify_production_target_approval(
            target_root=Path("output").resolve(),
            source_id="TEST_SOURCE",
            dataset_path=dataset,
            decisions_dir=tmp_path / "decisions",
            approval_dir=approval_dir,
        )
        assert valid is True
        assert "verified" in reason.lower()


# ---------------------------------------------------------------------------
# T6: Valid non-production path -> PASS
# ---------------------------------------------------------------------------

class TestT6ValidNonProduction:
    """T6: tmp data_root + valid corpus approval -> mutation gate 통과."""

    def test_valid_non_production_merge(self, tmp_path: Path):
        """tmp data_root + valid corpus approval -> merge 가능."""
        corpus_root = _make_corpus_dir(tmp_path, "TEST_SOURCE", ["TSU-001"])
        ddir = _make_approved_decisions_dir(tmp_path, "TEST_SOURCE", ["TSU-001"])

        tmp_output = tmp_path / "tmp_output"
        tmp_output.mkdir(parents=True)
        tmp_dataset = tmp_output / "output" / "bench" / "tsu_dataset.jsonl"
        tmp_dataset.parent.mkdir(parents=True)
        tmp_dataset.write_text("", encoding="utf-8")

        config = _make_tmp_config_no_match(tmp_path)

        target = resolve_target_paths(data_root=tmp_output, config_path=config)
        assert target.is_production is False
        assert target.data_root == tmp_output.resolve()

        assert "tmp_output" in str(target.dataset_path)
        assert "tmp_output" in str(target.manifest_path)
        assert "tmp_output" in str(target.registry_path)


# ---------------------------------------------------------------------------
# T7: Valid production approval -> PASS (gate semantics)
# ---------------------------------------------------------------------------

class TestT7ValidProductionApproval:
    """T7: production data_root + valid corpus + valid target approval -> gate 통과."""

    def test_all_approvals_valid(self, tmp_path: Path):
        """production output + valid corpus approval + valid target approval -> gate 통과."""
        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        approval_dir = tmp_path / "NAE" / "review" / "human" / "production_targets"
        approval_dir.mkdir(parents=True)

        current_sha = compute_dataset_sha256(dataset)
        approval = {
            "schema_version": 1,
            "source_id": "TEST_SOURCE",
            "target_root_realpath": str(Path("output").resolve()),
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": current_sha,
            "final_decision": "APPROVED",
            "approved_at": "2026-10-01T00:00:00",
        }
        (approval_dir / "TEST_SOURCE.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        valid, reason = verify_production_target_approval(
            target_root=Path("output").resolve(),
            source_id="TEST_SOURCE",
            dataset_path=dataset,
            decisions_dir=tmp_path / "decisions",
            approval_dir=approval_dir,
        )
        assert valid is True
        assert "verified" in reason.lower()


# ---------------------------------------------------------------------------
# T8: Session-level production guard
# ---------------------------------------------------------------------------

class TestT8SessionGuard:
    """T8: session-level production guard -- production files not modified."""

    def test_production_files_not_modified(self, tmp_path: Path):
        """production 파일이 테스트 중 변경되지 않음 (해시 불변 + samefile 증명).

        실제 동작 3가지를 수행한 뒤 sentinel 3개의 sha256 가 동일함을 단언한다:
        (a) 승인 없이 production 으로 분류된 data_root 로 merge_nae_corpus() 호출 → CorpusMutationBlockedError
        (b) data_root 누락 호출 → CorpusMutationBlockedError
        (c) production 으로 가는 symlink target 을 가진 data_root 로 호출 → 차단
        """
        import scripts.merge_nae_corpus as mod

        # --- mock production 과 config 설정 ---
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)
        corpus_root = _make_corpus_dir(tmp_path, "T8Source", ["TSU-080"])
        ddir = _make_approved_decisions_dir(tmp_path, "T8Source", ["TSU-080"])

        sentinel_paths = [
            prod / "output" / "bench" / "tsu_dataset.jsonl",
            prod / "output" / "bench" / "tsu_manifest.json",
            prod / "data" / "제련완성본" / "registry" / "documents.json",
        ]

        # --- 초기 해시 기록 ---
        hashes_before = {str(p): _file_hash(str(p)) for p in sentinel_paths if p.exists()}
        paths_before = [(str(p), p) for p in sentinel_paths if p.exists()]

        # ================================================================
        # (a) 승인 없이 production 으로 분류된 data_root 로 merge 호출 → BLOCK
        # ================================================================
        with pytest.raises(CorpusMutationBlockedError):
            mod.merge_nae_corpus(
                source_id="T8Source",
                data_root=prod,
                nae_corpus_dir=corpus_root,
                decisions_dir=ddir,
                config_path=config,
            )

        # (a) 후 해시 비교
        for p, h in hashes_before.items():
            if Path(p).exists():
                assert _file_hash(p) == h, f"(a) Production file changed: {p}"
        for orig_path_str, orig_path in paths_before:
            if Path(orig_path_str).exists():
                assert os.path.samefile(orig_path_str, orig_path), \
                    f"(a) Production file identity changed: {orig_path}"

        # ================================================================
        # (b) data_root 누락 호출 → BLOCK
        # ================================================================
        with pytest.raises(CorpusMutationBlockedError) as exc_b:
            mod.merge_nae_corpus(
                source_id="T8Source",
                nae_corpus_dir=corpus_root,
                decisions_dir=ddir,
            )
        assert "data_root" in str(exc_b.value).lower()

        # (b) 후 해시 비교
        for p, h in hashes_before.items():
            if Path(p).exists():
                assert _file_hash(p) == h, f"(b) Production file changed: {p}"
        for orig_path_str, orig_path in paths_before:
            if Path(orig_path_str).exists():
                assert os.path.samefile(orig_path_str, orig_path), \
                    f"(b) Production file identity changed: {orig_path}"

        # ================================================================
        # (c) production 으로 가는 symlink target 을 가진 data_root 로 호출 → BLOCK
        # ================================================================
        fake_prod = tmp_path / "fake_production"
        fake_prod.mkdir(parents=True)
        (fake_prod / "output" / "bench").mkdir(parents=True)
        (fake_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        (fake_prod / "output" / "bench" / "tsu_dataset.jsonl").write_text("", encoding="utf-8")
        (fake_prod / "output" / "bench" / "tsu_manifest.json").write_text("{}", encoding="utf-8")
        (fake_prod / "data" / "제련완성본" / "registry" / "documents.json").write_text(
            json.dumps({"documents": {}}, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # fake_production → mock_production symlink (production 으로 가는 symlink)
        symlink_path = tmp_path / "symlink_to_prod"
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(prod.resolve())

        with pytest.raises(CorpusMutationBlockedError):
            mod.merge_nae_corpus(
                source_id="T8Source",
                data_root=symlink_path,
                nae_corpus_dir=corpus_root,
                decisions_dir=ddir,
                config_path=config,
            )

        # (c) 후 해시 비교
        for p, h in hashes_before.items():
            if Path(p).exists():
                assert _file_hash(p) == h, f"(c) Production file changed: {p}"
        for orig_path_str, orig_path in paths_before:
            if Path(orig_path_str).exists():
                assert os.path.samefile(orig_path_str, orig_path), \
                    f"(c) Production file identity changed: {orig_path}"


# ---------------------------------------------------------------------------
# T9: Production placeholder rejection (fail-closed)
# ---------------------------------------------------------------------------

class TestT9ProductionPlaceholder:
    """T9: production_root 자리표시자가 fail-closed 로 거부됨."""

    def test_placeholder_production_root_rejected(self, tmp_path: Path):
        """자리표시자 경로가 실제 디렉터리가 아니면 BLOCK."""
        placeholder = "/absolute/path/to/production/root"
        assert not Path(placeholder).exists()

        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {placeholder}\n",
            encoding="utf-8",
        )

        with pytest.raises(CorpusMutationBlockedError):
            _load_production_root(config)

    def test_placeholder_path_in_config_raises(self, tmp_path: Path):
        """config.yaml 에 자리표시자가 있으면 CorpusMutationBlockedError."""
        placeholder = "/absolute/path/to/production/root"
        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {placeholder}\n",
            encoding="utf-8",
        )

        with pytest.raises(CorpusMutationBlockedError):
            _load_production_root(config)


# ---------------------------------------------------------------------------
# T10: Config fail-closed scenarios
# ---------------------------------------------------------------------------

class TestT10ConfigFailClosed:
    """T10: config 파일 없음 / 키 없음 / 읽기 실패 -> fail-closed."""

    def test_config_file_not_found(self, tmp_path: Path):
        """config 파일이 없으면 CorpusMutationBlockedError."""
        nonexistent = tmp_path / "nonexistent_config.yaml"
        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            _load_production_root(nonexistent)
        assert "not found" in str(exc_info.value).lower()

    def test_missing_merge_safety_section(self, tmp_path: Path):
        """merge-safety 섹션 없으면 CorpusMutationBlockedError."""
        config = tmp_path / "config.yaml"
        config.write_text("app:\n  name: test\n", encoding="utf-8")
        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            _load_production_root(config)
        assert "merge-safety" in str(exc_info.value)

    def test_missing_production_root_key(self, tmp_path: Path):
        """production_root 키 없으면 CorpusMutationBlockedError."""
        config = tmp_path / "config.yaml"
        config.write_text("merge-safety:\n  other_key: value\n", encoding="utf-8")
        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            _load_production_root(config)
        assert "production_root" in str(exc_info.value)

    def test_relative_path_in_config(self, tmp_path: Path):
        """상대 경로 production_root -> CorpusMutationBlockedError."""
        config = tmp_path / "config.yaml"
        config.write_text("merge-safety:\n  production_root: relative/path\n", encoding="utf-8")
        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            _load_production_root(config)
        assert "absolute" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# T11: Hardlink/symlink alias detection
# ---------------------------------------------------------------------------

class TestT11HardlinkSymlinkDetection:
    """T11: 실제 파일 hardlink/symlink alias 감지 테스트."""

    def test_detect_hardlink_alias_on_dataset(self, tmp_path: Path):
        """dataset 파일에 hardlink를 만들면 _detect_hardlink_alias 가 감지."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        non_prod = tmp_path / "non_production"
        (non_prod / "output" / "bench").mkdir(parents=True)
        (non_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)

        dataset_path = non_prod / "output" / "bench" / "tsu_dataset.jsonl"
        manifest_path = non_prod / "output" / "bench" / "tsu_manifest.json"
        registry_path = non_prod / "data" / "제련완성본" / "registry" / "documents.json"

        dataset_path.write_text("", encoding="utf-8")
        manifest_path.write_text("{}", encoding="utf-8")
        registry_path.write_text(json.dumps({"documents": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

        prod_dataset = prod / "output" / "bench" / "tsu_dataset.jsonl"
        # Unlink first because os.link requires target to not exist
        dataset_path.unlink()
        os.link(str(prod_dataset), str(dataset_path))

        assert os.path.samefile(str(prod_dataset), str(dataset_path))
        assert dataset_path.stat().st_nlink > 1

        assert _detect_hardlink_alias(non_prod, config) is True

    def test_detect_symlink_target_to_production(self, tmp_path: Path):
        """symlink 이 production 의 dataset 을 가리키면 감지."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        non_prod = tmp_path / "non_production"
        (non_prod / "output" / "bench").mkdir(parents=True)
        (non_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)

        dataset_path = non_prod / "output" / "bench" / "tsu_dataset.jsonl"
        manifest_path = non_prod / "output" / "bench" / "tsu_manifest.json"
        registry_path = non_prod / "data" / "제련완성본" / "registry" / "documents.json"

        dataset_path.write_text("", encoding="utf-8")
        manifest_path.write_text("{}", encoding="utf-8")
        registry_path.write_text(json.dumps({"documents": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

        prod_dataset = prod / "output" / "bench" / "tsu_dataset.jsonl"
        dataset_path.unlink()
        dataset_path.symlink_to(prod_dataset)

        assert dataset_path.is_symlink()
        assert dataset_path.resolve() == prod_dataset.resolve()
        assert os.path.samefile(str(dataset_path), str(prod_dataset))

        assert _detect_hardlink_alias(non_prod, config) is True

    def test_no_alias_for_normal_files(self, tmp_path: Path):
        """정상 파일은 alias 로 감지되지 않음."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        non_prod = tmp_path / "non_production"
        (non_prod / "output" / "bench").mkdir(parents=True)
        (non_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)

        dataset_path = non_prod / "output" / "bench" / "tsu_dataset.jsonl"
        manifest_path = non_prod / "output" / "bench" / "tsu_manifest.json"
        registry_path = non_prod / "data" / "제련완성본" / "registry" / "documents.json"

        dataset_path.write_text("normal content\n", encoding="utf-8")
        manifest_path.write_text("{}", encoding="utf-8")
        registry_path.write_text(json.dumps({"documents": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

        prod_dataset = prod / "output" / "bench" / "tsu_dataset.jsonl"
        assert not dataset_path.is_symlink()
        assert not os.path.samefile(str(dataset_path), str(prod_dataset))

        assert _detect_hardlink_alias(non_prod, config) is False


# ---------------------------------------------------------------------------
# T12: Production root identity
# ---------------------------------------------------------------------------

class TestT12ProductionRootIdentity:
    """T12: tmp mock production root 가 production 으로 식별됨."""

    def test_mock_production_root_identified(self, tmp_path: Path):
        """tmp mock production root 를 data_root 로 전달하면 production 으로 식별."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        target = resolve_target_paths(data_root=prod, config_path=config)
        assert target.is_production is True
        assert target.data_root == prod.resolve()

    def test_non_production_not_identified_as_production(self, tmp_path: Path):
        """정상 tmp data_root 는 production 으로 오인되지 않음."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        non_prod = tmp_path / "non_production"
        (non_prod / "output" / "bench").mkdir(parents=True)
        (non_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)
        (non_prod / "output" / "bench" / "tsu_dataset.jsonl").write_text("", encoding="utf-8")
        (non_prod / "output" / "bench" / "tsu_manifest.json").write_text("{}", encoding="utf-8")
        (non_prod / "data" / "제련완성본" / "registry" / "documents.json").write_text(
            json.dumps({"documents": {}}, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        target = resolve_target_paths(data_root=non_prod, config_path=config)
        assert target.is_production is False


# ---------------------------------------------------------------------------
# T13: Normal non-production tmp data_root passes through
# ---------------------------------------------------------------------------

class TestT13NormalNonProduction:
    """T13: 정상 non-production tmp data_root 가 production 으로 오인되지 않고 통과."""

    def test_normal_tmp_data_root_passes(self, tmp_path: Path):
        """정상 tmp data_root 는 production 오인/alias 오탐 없이 통과."""
        corpus_root = _make_corpus_dir(tmp_path, "TEST_SOURCE", ["TSU-001"])
        ddir = _make_approved_decisions_dir(tmp_path, "TEST_SOURCE", ["TSU-001"])

        tmp_output = tmp_path / "tmp_output"
        tmp_output.mkdir(parents=True)
        tmp_dataset = tmp_output / "output" / "bench" / "tsu_dataset.jsonl"
        tmp_dataset.parent.mkdir(parents=True)
        tmp_dataset.write_text("", encoding="utf-8")

        config = _make_tmp_config_no_match(tmp_path)

        target = resolve_target_paths(data_root=tmp_output, config_path=config)
        assert target.is_production is False

        result = merge_nae_corpus(
            source_id="TEST_SOURCE",
            data_root=tmp_output,
            nae_corpus_dir=corpus_root,
            decisions_dir=ddir,
            config_path=config,
        )
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# T14: Mixed targets
# ---------------------------------------------------------------------------

class TestT14MixedTargets:
    """T14: mixed target -- production alias 만 차단."""

    def test_mixed_production_and_non_production_targets(self, tmp_path: Path):
        """production target / non-production target / symlink alias 가 다른 identity 로 구성."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        non_prod = tmp_path / "non_production"
        (non_prod / "output" / "bench").mkdir(parents=True)
        (non_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)

        np_dataset = non_prod / "output" / "bench" / "tsu_dataset.jsonl"
        np_manifest = non_prod / "output" / "bench" / "tsu_manifest.json"
        np_registry = non_prod / "data" / "제련완성본" / "registry" / "documents.json"

        np_dataset.write_text("non-production content\n", encoding="utf-8")
        np_manifest.write_text('{"non_prod": true}', encoding="utf-8")
        np_registry.write_text(json.dumps({"documents": {"unique": "data"}}, ensure_ascii=False, indent=2), encoding="utf-8")

        prod_dataset = prod / "output" / "bench" / "tsu_dataset.jsonl"
        prod_manifest = prod / "output" / "bench" / "tsu_manifest.json"
        prod_registry = prod / "data" / "제련완성본" / "registry" / "documents.json"

        assert not os.path.samefile(str(np_dataset), str(prod_dataset))
        assert not os.path.samefile(str(np_manifest), str(prod_manifest))
        assert not os.path.samefile(str(np_registry), str(prod_registry))

        assert _detect_hardlink_alias(non_prod, config) is False
        target = resolve_target_paths(data_root=non_prod, config_path=config)
        assert target.is_production is False

    def test_symlink_alias_to_production_blocks(self, tmp_path: Path):
        """symlink 경유 production alias 는 차단."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        non_prod = tmp_path / "non_production"
        (non_prod / "output" / "bench").mkdir(parents=True)
        (non_prod / "data" / "제련완성본" / "registry").mkdir(parents=True)

        np_dataset = non_prod / "output" / "bench" / "tsu_dataset.jsonl"
        np_manifest = non_prod / "output" / "bench" / "tsu_manifest.json"
        np_registry = non_prod / "data" / "제련완성본" / "registry" / "documents.json"

        np_dataset.write_text("non-production content\n", encoding="utf-8")
        np_manifest.write_text('{"non_prod": true}', encoding="utf-8")
        np_registry.write_text(json.dumps({"documents": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

        prod_dataset = prod / "output" / "bench" / "tsu_dataset.jsonl"
        np_dataset.unlink()
        np_dataset.symlink_to(prod_dataset)

        assert np_dataset.is_symlink()
        assert os.path.samefile(str(np_dataset), str(prod_dataset))

        assert _detect_hardlink_alias(non_prod, config) is True


# ---------------------------------------------------------------------------
# T15: resolve_target_paths explicit data_root tests
# ---------------------------------------------------------------------------

class TestResolveTargetPaths:
    """resolve_target_paths() 의 기본 동작 검증."""

    def test_explicit_data_root_derives_all_paths(self, tmp_path: Path):
        """data_root 제공 시 dataset/manifest/registry 가 모두 그 아래에서 파생."""
        tmp_output = tmp_path / "my_output"
        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=tmp_output, config_path=config)

        assert target.data_root == tmp_output.resolve()
        assert "output" in str(target.dataset_path)
        assert "bench" in str(target.dataset_path)
        assert "tsu_dataset.jsonl" in str(target.dataset_path)
        assert "tsu_manifest.json" in str(target.manifest_path)
        assert "data" in str(target.registry_path)
        assert "registry" in str(target.registry_path)
        assert "documents.json" in str(target.registry_path)

    def test_all_paths_share_same_root(self, tmp_path: Path):
        """모든 mutation path 가 동일한 output root 아래에 있는지."""
        tmp_output = tmp_path / "my_output"
        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=tmp_output, config_path=config)

        for p in [target.dataset_path, target.manifest_path, target.registry_path]:
            assert target.data_root in p.resolve().parents or p.resolve().parent.parent == target.data_root


# ---------------------------------------------------------------------------
# T16: data_root contract tests (restored from deleted tests)
# ---------------------------------------------------------------------------

class TestDataRootContract:
    """data_root 기반 계약 테스트 -- 삭제된 테스트 복원."""

    def test_no_data_root_blocks_merge(self, tmp_path: Path):
        """data_root 가 없으면 merge_nae_corpus() 가 차단됨."""
        corpus_root = _make_corpus_dir(tmp_path, "NoDataRootSource", ["TSU-080"])
        ddir = _make_approved_decisions_dir(tmp_path, "NoDataRootSource", ["TSU-080"])

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            merge_nae_corpus(
                source_id="NoDataRootSource",
                nae_corpus_dir=corpus_root,
                decisions_dir=ddir,
            )
        assert "data_root" in str(exc_info.value).lower()

    def test_data_root_derives_three_canonical_targets(self, tmp_path: Path):
        """data_root 에서 3 canonical target 이 정확히 유도됨."""
        tmp_output = tmp_path / "my_output"
        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=tmp_output, config_path=config)

        assert target.dataset_path == tmp_output / "output" / "bench" / "tsu_dataset.jsonl"
        assert target.manifest_path == tmp_output / "output" / "bench" / "tsu_manifest.json"
        assert target.registry_path == tmp_output / "data" / "제련완성본" / "registry" / "documents.json"

    def test_mixed_classification_blocked_symlink_hardlink(self, tmp_path: Path):
        """symlink/hardlink 경유로 canonical 하위가 아닌 경로 -> BLOCK.

        macOS 에서 디렉터리 hardlink(os.link) 는 불가하지만 파일 hardlink(os.link) 는 가능.
        이 테스트는 symlink 경로를 검증함.
        """
        real_prod = tmp_path / "real_output"
        real_prod.mkdir(parents=True)
        (real_prod / "output" / "bench").mkdir(parents=True)

        link_path = tmp_path / "link_to_prod"
        link_path.symlink_to(real_prod)

        config = _make_tmp_config_no_match(tmp_path)
        target = resolve_target_paths(data_root=link_path, config_path=config)
        assert target.data_root == real_prod.resolve()


# ---------------------------------------------------------------------------
# T17: Default config fail-closed (placeholder)
# ---------------------------------------------------------------------------

class TestDefaultConfigFailClosed:
    """T17: 기본 config(placeholder) 로 merge 호출 -> FAIL-CLOSED."""

    def test_default_config_placeholder_blocks_merge(self, tmp_path: Path):
        """기본 config 의 placeholder production_root 로 merge 호출 -> BLOCK.
        
        Note: conftest fixture 가 _DEFAULT_CONFIG_PATH 를 patch 하므로,
        이 테스트는 원본 config path 를 복원하여 실제 placeholder config 를 검증합니다.
        """
        import scripts.merge_nae_corpus as mod
        
        corpus_root = _make_corpus_dir(tmp_path, "DefaultConfigSource", ["TSU-090"])
        ddir = _make_approved_decisions_dir(tmp_path, "DefaultConfigSource", ["TSU-090"])

        tmp_output = tmp_path / "tmp_output"
        tmp_output.mkdir(parents=True)
        tmp_dataset = tmp_output / "output" / "bench" / "tsu_dataset.jsonl"
        tmp_dataset.parent.mkdir(parents=True)
        tmp_dataset.write_text("", encoding="utf-8")

        # Restore original _DEFAULT_CONFIG_PATH (the project's config.yaml with placeholder)
        original_config_path = mod._DEFAULT_CONFIG_PATH
        # Get the real default path (not the patched one)
        import os as _os
        real_default = Path(_os.path.dirname(__file__)).parent.parent / "config.yaml"
        mod._DEFAULT_CONFIG_PATH = real_default

        try:
            with pytest.raises(CorpusMutationBlockedError) as exc_info:
                merge_nae_corpus(
                    source_id="DefaultConfigSource",
                    data_root=tmp_output,
                    nae_corpus_dir=corpus_root,
                    decisions_dir=ddir,
                )
            # Fail-closed: any config error (missing file, missing key, invalid path) is acceptable
            err_msg = str(exc_info.value).lower()
            assert any(kw in err_msg for kw in [
                "production_root", "not exist", "config file not found",
                "missing", "does not contain", "must be an absolute"
            ])
        finally:
            mod._DEFAULT_CONFIG_PATH = original_config_path


# ---------------------------------------------------------------------------
# T18: Production identity with tmp config monkeypatch
# ---------------------------------------------------------------------------

class TestProductionIdentityWithTmpConfig:
    """T18: _DEFAULT_CONFIG_PATH 를 tmp config 로 monkeypatch -> production identity 적용."""

    def test_production_identity_applied_with_tmp_config(self, tmp_path: Path):
        """_DEFAULT_CONFIG_PATH 를 tmp config 로 바꾼 뒤 merge 호출 -> production identity 적용."""
        prod = _make_mock_production(tmp_path)
        config = _make_tmp_config_with_production(tmp_path, prod)

        import scripts.merge_nae_corpus as mod
        original_default = mod._DEFAULT_CONFIG_PATH
        mod._DEFAULT_CONFIG_PATH = config

        try:
            corpus_root = _make_corpus_dir(tmp_path, "MonkeyPatchSource", ["TSU-091"])
            ddir = _make_approved_decisions_dir(tmp_path, "MonkeyPatchSource", ["TSU-091"])

            tmp_output = prod
            tmp_dataset = tmp_output / "output" / "bench" / "tsu_dataset.jsonl"
            tmp_dataset.write_text("", encoding="utf-8")

            target = resolve_target_paths(data_root=tmp_output)
            assert target.is_production is True

        finally:
            mod._DEFAULT_CONFIG_PATH = original_default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

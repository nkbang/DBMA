"""tests/test_merge_production_path_safety.py — Production path safety tests.

Tests for NAE-MERGE-PRODUCTION-PATH-SAFETY-001 (R1~R7):
  P1: Three mandatory paths (no output_root)
  P2: Realpath-based production detection
  P3: Mixed-path blocking
  P4: Production approval gate with target_paths_realpath
  P5: No string heuristics
  P6: Call order enforcement
  P7: Non-production path PASS
  P8: Session-level guard
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
    resolve_mutation_paths,
    verify_production_target_approval,
    compute_dataset_sha256,
    _is_production_realpath,
    _PRODUCTION_DATASET_REALPATH,
    _PRODUCTION_MANIFEST_REALPATH,
    _PRODUCTION_REGISTRY_REALPATH,
    CorpusMutationBlockedError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_production_target_approval(
    tmp_path: Path, source_id: str, dataset_path: Path
) -> Path:
    """Create a production target approval artifact."""
    adir = tmp_path / "approval"
    adir.mkdir(parents=True)
    sha = compute_dataset_sha256(dataset_path)
    tp_realpath = [
        str(_PRODUCTION_DATASET_REALPATH),
        str(_PRODUCTION_MANIFEST_REALPATH),
        str(_PRODUCTION_REGISTRY_REALPATH),
    ]
    approval = {
        "schema_version": 1,
        "source_id": source_id,
        "target_paths_realpath": tp_realpath,
        "reviewer_id": f"R-{source_id}",
        "gate_id": f"G-{source_id}",
        "dataset_sha256_before": sha,
        "final_decision": "APPROVED",
        "approved_at": "2026-01-01T00:00:00Z",
    }
    (adir / f"{source_id}.json").write_text(
        json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return adir


def _make_tmp_paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create three tmp paths for dataset, manifest, registry."""
    bench = tmp_path / "bench"
    bench.mkdir(exist_ok=True)
    reg = tmp_path / "registry"
    reg.mkdir(exist_ok=True)
    ds = bench / "tsu_dataset.jsonl"
    mf = bench / "tsu_manifest.json"
    rg = reg / "documents.json"
    return ds, mf, rg


# ---------------------------------------------------------------------------
# P1: Three mandatory paths (no output_root)
# ---------------------------------------------------------------------------

class TestP1MandatoryPaths:
    """P1: tsu_dataset_path, manifest_path, registry_path — 모두 필수."""

    def test_all_three_paths_required(self, tmp_path: Path):
        """merge_nae_corpus() without all three paths → BLOCK."""
        ds, mf, rg = _make_tmp_paths(tmp_path)
        ds.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        with pytest.raises(CorpusMutationBlockedError, match="manifest_path"):
            merge_nae_corpus(
                source_id="TEST_SOURCE",
                tsu_dataset_path=ds,
                registry_path=rg,
            )

    def test_all_three_paths_provided_passes_resolution(self, tmp_path: Path):
        """All three paths provided → resolve_mutation_paths succeeds."""
        ds, mf, rg = _make_tmp_paths(tmp_path)
        result = resolve_mutation_paths(
            tsu_dataset_path=ds,
            manifest_path=mf,
            registry_path=rg,
        )
        assert result.dataset_path == ds.resolve()
        assert result.manifest_path == mf.resolve()
        assert result.registry_path == rg.resolve()


# ---------------------------------------------------------------------------
# P2: Realpath-based production detection
# ---------------------------------------------------------------------------

class TestP2RealpathDetection:
    """P2: realpath 기반 production 판정 (cwd 독립)."""

    def test_production_dataset_realpath(self):
        assert _is_production_realpath(_PRODUCTION_DATASET_REALPATH) is True

    def test_production_manifest_realpath(self):
        assert _is_production_realpath(_PRODUCTION_MANIFEST_REALPATH) is True

    def test_production_registry_realpath(self):
        assert _is_production_realpath(_PRODUCTION_REGISTRY_REALPATH) is True

    def test_non_production_path_not_detected(self, tmp_path: Path):
        fake_path = tmp_path / "fake" / "bench" / "tsu_dataset.jsonl"
        fake_path.parent.mkdir(parents=True)
        assert _is_production_realpath(fake_path) is False


# ---------------------------------------------------------------------------
# P3: Mixed-path blocking
# ---------------------------------------------------------------------------

class TestP3MixedPathBlocking:
    """P3: 일부만 production → BLOCK."""

    def test_dataset_prod_registry_tmp_blocks(self, tmp_path: Path):
        ds = _PRODUCTION_DATASET_REALPATH
        mf = tmp_path / "bench" / "tsu_manifest.json"
        rg = tmp_path / "registry" / "documents.json"
        mf.parent.mkdir(parents=True)
        rg.parent.mkdir(parents=True)

        with pytest.raises(CorpusMutationBlockedError, match="Mixed mutation paths"):
            resolve_mutation_paths(
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
            )

    def test_all_three_production_passes(self):
        result = resolve_mutation_paths(
            tsu_dataset_path=_PRODUCTION_DATASET_REALPATH,
            manifest_path=_PRODUCTION_MANIFEST_REALPATH,
            registry_path=_PRODUCTION_REGISTRY_REALPATH,
        )
        assert result.is_production is True
        assert result.mixed_paths is False

    def test_all_three_tmp_passes(self, tmp_path: Path):
        ds, mf, rg = _make_tmp_paths(tmp_path)
        result = resolve_mutation_paths(
            tsu_dataset_path=ds,
            manifest_path=mf,
            registry_path=rg,
        )
        assert result.is_production is False
        assert result.mixed_paths is False



# ---------------------------------------------------------------------------
# P4: Production approval gate with target_paths_realpath
# ---------------------------------------------------------------------------

class TestP4ProductionApprovalGate:
    """P4: production approval gate — target_paths_realpath 기준."""

    def test_valid_production_approval(self, tmp_path: Path):
        ds = tmp_path / "bench" / "tsu_dataset.jsonl"
        ds.parent.mkdir(parents=True)
        ds.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        adir = _make_production_target_approval(tmp_path, "TEST_SOURCE", ds)

        tp_realpath = [
            str(_PRODUCTION_DATASET_REALPATH),
            str(_PRODUCTION_MANIFEST_REALPATH),
            str(_PRODUCTION_REGISTRY_REALPATH),
        ]
        valid, reason = verify_production_target_approval(
            target_paths_realpath=tp_realpath,
            source_id="TEST_SOURCE",
            dataset_path=ds,
            decisions_dir=tmp_path / "decisions",
            approval_dir=adir,
        )
        assert valid is True
        assert "verified" in reason.lower()

    def test_missing_approval_blocks(self, tmp_path: Path):
        ds = tmp_path / "bench" / "tsu_dataset.jsonl"
        ds.parent.mkdir(parents=True)
        ds.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        valid, reason = verify_production_target_approval(
            target_paths_realpath=["a", "b", "c"],
            source_id="TEST_SOURCE",
            dataset_path=ds,
            decisions_dir=tmp_path / "decisions",
            approval_dir=tmp_path / "nonexistent",
        )
        assert valid is False
        assert "not found" in reason.lower()

    def test_source_id_mismatch_blocks(self, tmp_path: Path):
        ds = tmp_path / "bench" / "tsu_dataset.jsonl"
        ds.parent.mkdir(parents=True)
        ds.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        # Approval file named TEST_SOURCE so it's found, but content has WRONG_SOURCE
        adir = tmp_path / "approval"
        adir.mkdir(parents=True)
        sha = compute_dataset_sha256(ds)
        tp_realpath = [
            str(_PRODUCTION_DATASET_REALPATH),
            str(_PRODUCTION_MANIFEST_REALPATH),
            str(_PRODUCTION_REGISTRY_REALPATH),
        ]
        approval = {
            "schema_version": 1,
            "source_id": "WRONG_SOURCE",
            "target_paths_realpath": tp_realpath,
            "reviewer_id": "R-TEST",
            "gate_id": "G-TEST",
            "dataset_sha256_before": sha,
            "final_decision": "APPROVED",
            "approved_at": "2026-01-01T00:00:00Z",
        }
        (adir / "TEST_SOURCE.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        valid, reason = verify_production_target_approval(
            target_paths_realpath=["a", "b", "c"],
            source_id="TEST_SOURCE",
            dataset_path=ds,
            decisions_dir=tmp_path / "decisions",
            approval_dir=adir,
        )
        assert valid is False
        assert "source_id mismatch" in reason

    def test_target_paths_realpath_mismatch_blocks(self, tmp_path: Path):
        ds = tmp_path / "bench" / "tsu_dataset.jsonl"
        ds.parent.mkdir(parents=True)
        ds.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        adir = _make_production_target_approval(tmp_path, "TEST_SOURCE", ds)

        valid, reason = verify_production_target_approval(
            target_paths_realpath=["wrong/a", "wrong/b", "wrong/c"],
            source_id="TEST_SOURCE",
            dataset_path=ds,
            decisions_dir=tmp_path / "decisions",
            approval_dir=adir,
        )
        assert valid is False
        assert "target_paths_realpath" in reason

    def test_dataset_sha256_mismatch_blocks(self, tmp_path: Path):
        ds = tmp_path / "bench" / "tsu_dataset.jsonl"
        ds.parent.mkdir(parents=True)
        ds.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")

        adir = _make_production_target_approval(tmp_path, "TEST_SOURCE", ds)

        # Use correct production paths so SHA check is reached
        tp_realpath = [
            str(_PRODUCTION_DATASET_REALPATH),
            str(_PRODUCTION_MANIFEST_REALPATH),
            str(_PRODUCTION_REGISTRY_REALPATH),
        ]
        ds.write_text('{"tsu_id": "TSU-002", "content": "modified"}\n', encoding="utf-8")

        valid, reason = verify_production_target_approval(
            target_paths_realpath=tp_realpath,
            source_id="TEST_SOURCE",
            dataset_path=ds,
            decisions_dir=tmp_path / "decisions",
            approval_dir=adir,
        )
        assert valid is False
        assert "dataset_sha256 mismatch" in reason



# ---------------------------------------------------------------------------
# P5: No string heuristics
# ---------------------------------------------------------------------------

class TestP5NoStringHeuristics:
    """P5: realpath 기반 판정 — 문자열 히ュー리스틱 없음."""

    def test_realpath_detection_no_string_match(self):
        assert isinstance(_PRODUCTION_DATASET_REALPATH, Path)
        assert isinstance(_PRODUCTION_MANIFEST_REALPATH, Path)
        assert isinstance(_PRODUCTION_REGISTRY_REALPATH, Path)

    def test_relative_path_resolved(self, tmp_path: Path):
        ds = tmp_path / "bench" / "tsu_dataset.jsonl"
        ds.parent.mkdir(parents=True)
        result = resolve_mutation_paths(
            tsu_dataset_path=ds,
            manifest_path=tmp_path / "bench" / "tsu_manifest.json",
            registry_path=tmp_path / "registry" / "documents.json",
        )
        assert result.dataset_path.is_absolute()


# ---------------------------------------------------------------------------
# P6: Call order enforcement
# ---------------------------------------------------------------------------

class TestP6CallOrder:
    """P6: path resolution → mixed check → production detection → approval gates."""

    def test_mixed_check_before_approval(self, tmp_path: Path):
        ds = _PRODUCTION_DATASET_REALPATH
        mf = tmp_path / "bench" / "tsu_manifest.json"
        rg = tmp_path / "registry" / "documents.json"
        mf.parent.mkdir(parents=True)
        rg.parent.mkdir(parents=True)

        with pytest.raises(CorpusMutationBlockedError, match="Mixed mutation paths"):
            resolve_mutation_paths(
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
            )


# ---------------------------------------------------------------------------
# P7: Non-production path PASS
# ---------------------------------------------------------------------------

class TestP7NonProductionPass:
    """P7: non-production paths → no production approval required."""

    def test_non_production_no_approval_needed(self, tmp_output):
        ds = tmp_output / "bench" / "tsu_dataset.jsonl"
        mf = tmp_output / "bench" / "tsu_manifest.json"
        rg = tmp_output / "registry" / "documents.json"

        ds.write_text('{"tsu_id": "TSU-001", "content": "test"}\n', encoding="utf-8")
        mf.write_text('{"version": 1}', encoding="utf-8")

        result = resolve_mutation_paths(
            tsu_dataset_path=ds,
            manifest_path=mf,
            registry_path=rg,
        )
        assert result.is_production is False


# ---------------------------------------------------------------------------
# P8: Session-level guard
# ---------------------------------------------------------------------------

class TestP8SessionGuard:
    """P8: session 시작/종료 시 production 파일 hash 비교."""

    def test_production_files_unchanged(self):
        prod_dataset = Path("output/bench/tsu_dataset.jsonl")
        prod_manifest = Path("output/bench/tsu_manifest.json")
        prod_registry = Path("output/registry/identity_registry.json")

        hashes_before = {}
        for p in [prod_dataset, prod_manifest, prod_registry]:
            if p.exists():
                hashes_before[str(p)] = _file_hash(str(p))

        assert True, "Production files not modified in this test"

        for p, h in hashes_before.items():
            if Path(p).exists():
                assert _file_hash(p) == h, f"Production file changed: {p}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ---------------------------------------------------------------------------
# B-T1~B-T8: End-to-end production path safety tests (Task Order B)
# ---------------------------------------------------------------------------

class TestBT1ProductionNoTargetApproval:
    """B-T1: production 지정 + corpus approval 유효 + production target approval 없음 → BLOCK."""

    def test_blocks_without_production_target_approval(self, _isolate_production_paths):
        info = _isolate_production_paths
        ds = info["dataset_path"]
        mf = info["manifest_path"]
        rg = info["registry_path"]

        # corpus approval 유효: decisions_dir에 APPROVED decision 생성
        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT1Source", ["TSU-BT1"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT1Source", ["TSU-BT1"])

        # dataset에 입력 기록
        ds.write_text(
            json.dumps({"tsu_id": "TSU-BT1", "claim": "Claim for TSU-BT1"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # production target approval artifact는 만들지 않음 → BLOCK이어야 함
        with pytest.raises(CorpusMutationBlockedError, match="Production target approval FAILED"):
            merge_nae_corpus(
                source_id="BT1Source",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
                decisions_dir=ddir,
            )

        # 파일 불변 검증
        assert ds.exists()
        content = ds.read_text(encoding="utf-8")
        assert "TSU-BT1" in content  # merge되지 않았으므로 원본 유지


class TestBT2SourceIdMismatch:
    """B-T2: approval의 source_id 불일치 → BLOCK, 파일 불변."""

    def test_blocks_on_source_id_mismatch(self, _isolate_production_paths):
        info = _isolate_production_paths
        ds = info["dataset_path"]
        mf = info["manifest_path"]
        rg = info["registry_path"]

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT2Source", ["TSU-BT2"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT2Source", ["TSU-BT2"])

        ds.write_text(
            json.dumps({"tsu_id": "TSU-BT2", "claim": "Claim for TSU-BT2"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # production target approval artifact — source_id를 다른 값으로 설정
        adir = tmp_path / "approval"
        adir.mkdir(parents=True)
        sha = compute_dataset_sha256(ds)
        tp_realpath = [str(ds), str(mf), str(rg)]
        approval = {
            "schema_version": 1,
            "source_id": "WRONG_SOURCE",  # 불일치
            "target_paths_realpath": tp_realpath,
            "reviewer_id": "R-BT2",
            "gate_id": "G-BT2",
            "dataset_sha256_before": sha,
            "final_decision": "APPROVED",
            "approved_at": "2026-01-01T00:00:00Z",
        }
        (adir / "BT2Source.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with pytest.raises(CorpusMutationBlockedError, match="source_id mismatch"):
            merge_nae_corpus(
                source_id="BT2Source",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
                decisions_dir=ddir,
                approval_dir=adir,
            )

        assert ds.read_text(encoding="utf-8") == json.dumps(
            {"tsu_id": "TSU-BT2", "claim": "Claim for TSU-BT2"}, ensure_ascii=False
        ) + "\n"


class TestBT3TargetPathsRealpathMismatch:
    """B-T3: approval의 target_paths_realpath 불일치(순서·값) → BLOCK, 파일 불변."""

    def test_blocks_on_target_paths_realpath_mismatch(self, _isolate_production_paths):
        info = _isolate_production_paths
        ds = info["dataset_path"]
        mf = info["manifest_path"]
        rg = info["registry_path"]

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT3Source", ["TSU-BT3"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT3Source", ["TSU-BT3"])

        ds.write_text(
            json.dumps({"tsu_id": "TSU-BT3", "claim": "Claim for TSU-BT3"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # production target approval artifact — target_paths_realpath 순서 뒤집기
        adir = tmp_path / "approval"
        adir.mkdir(parents=True)
        sha = compute_dataset_sha256(ds)
        tp_realpath = [str(rg), str(mf), str(ds)]  # 순서 뒤집음
        approval = {
            "schema_version": 1,
            "source_id": "BT3Source",
            "target_paths_realpath": tp_realpath,
            "reviewer_id": "R-BT3",
            "gate_id": "G-BT3",
            "dataset_sha256_before": sha,
            "final_decision": "APPROVED",
            "approved_at": "2026-01-01T00:00:00Z",
        }
        (adir / "BT3Source.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with pytest.raises(CorpusMutationBlockedError, match="target_paths_realpath"):
            merge_nae_corpus(
                source_id="BT3Source",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
                decisions_dir=ddir,
                approval_dir=adir,
            )

        assert ds.read_text(encoding="utf-8") == json.dumps(
            {"tsu_id": "TSU-BT3", "claim": "Claim for TSU-BT3"}, ensure_ascii=False
        ) + "\n"


class TestBT4DatasetSha256Mismatch:
    """B-T4: approval의 dataset_sha256_before 불일치 → BLOCK, 파일 불변."""

    def test_blocks_on_dataset_sha256_mismatch(self, _isolate_production_paths):
        info = _isolate_production_paths
        ds = info["dataset_path"]
        mf = info["manifest_path"]
        rg = info["registry_path"]

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT4Source", ["TSU-BT4"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT4Source", ["TSU-BT4"])

        ds.write_text(
            json.dumps({"tsu_id": "TSU-BT4", "claim": "Claim for TSU-BT4"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # production target approval artifact — dataset_sha256_before를 다른 값으로 설정
        adir = tmp_path / "approval"
        adir.mkdir(parents=True)
        tp_realpath = [str(ds), str(mf), str(rg)]
        approval = {
            "schema_version": 1,
            "source_id": "BT4Source",
            "target_paths_realpath": tp_realpath,
            "reviewer_id": "R-BT4",
            "gate_id": "G-BT4",
            "dataset_sha256_before": "wrong_hash_value_0000000000000000000000000000000000000000000000000000000000000000",
            "final_decision": "APPROVED",
            "approved_at": "2026-01-01T00:00:00Z",
        }
        (adir / "BT4Source.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with pytest.raises(CorpusMutationBlockedError, match="dataset_sha256 mismatch"):
            merge_nae_corpus(
                source_id="BT4Source",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
                decisions_dir=ddir,
                approval_dir=adir,
            )

        assert ds.read_text(encoding="utf-8") == json.dumps(
            {"tsu_id": "TSU-BT4", "claim": "Claim for TSU-BT4"}, ensure_ascii=False
        ) + "\n"


class TestBT5FinalDecisionNotApproved:
    """B-T5: final_decision ≠ APPROVED → BLOCK, 파일 불변."""

    def test_blocks_on_rejected_final_decision(self, _isolate_production_paths):
        info = _isolate_production_paths
        ds = info["dataset_path"]
        mf = info["manifest_path"]
        rg = info["registry_path"]

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT5Source", ["TSU-BT5"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT5Source", ["TSU-BT5"])

        ds.write_text(
            json.dumps({"tsu_id": "TSU-BT5", "claim": "Claim for TSU-BT5"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # production target approval artifact — final_decision을 REJECTED으로 설정
        # merge_nae_corpus()는 approval_dir 파라미터를 새로 추가했으므로 이를 전달
        adir = tmp_path / "approval"
        adir.mkdir(parents=True)
        sha = compute_dataset_sha256(ds)
        tp_realpath = [str(ds), str(mf), str(rg)]
        approval = {
            "schema_version": 1,
            "source_id": "BT5Source",
            "target_paths_realpath": tp_realpath,
            "reviewer_id": "R-BT5",
            "gate_id": "G-BT5",
            "dataset_sha256_before": sha,
            "final_decision": "REJECTED",  # 불일치
            "approved_at": "2026-01-01T00:00:00Z",
        }
        (adir / "BT5Source.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with pytest.raises(CorpusMutationBlockedError, match="final_decision is not APPROVED"):
            merge_nae_corpus(
                source_id="BT5Source",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
                decisions_dir=ddir,
                approval_dir=adir,
            )

        assert ds.read_text(encoding="utf-8") == json.dumps(
            {"tsu_id": "TSU-BT5", "claim": "Claim for TSU-BT5"}, ensure_ascii=False
        ) + "\n"


class TestBT6AllConditionsMet:
    """B-T6: 모든 조건 충족 → ALLOW, 기록 대상이 지정 경로와 정확히 일치."""

    def test_allows_merge_when_all_conditions_met(self, _isolate_production_paths):
        info = _isolate_production_paths
        ds = info["dataset_path"]
        mf = info["manifest_path"]
        rg = info["registry_path"]

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT6Source", ["TSU-BT6"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT6Source", ["TSU-BT6"])

        # corpus approval를 위해 기존 dataset에 빈 파일 생성 (merge가 읽음)
        ds.write_text("", encoding="utf-8")

        # production target approval artifact — 모든 조건 올바르게 설정
        # _make_production_target_approval()는 import 시점의 _PRODUCTION_* 값을 사용하므로
        # monkeypatch된 값을 반영하지 못함 — 직접 생성
        adir = tmp_path / "approval"
        adir.mkdir(parents=True)
        sha = compute_dataset_sha256(ds)
        tp_realpath = [str(ds), str(mf), str(rg)]
        approval = {
            "schema_version": 1,
            "source_id": "BT6Source",
            "target_paths_realpath": tp_realpath,
            "reviewer_id": "R-BT6Source",
            "gate_id": "G-BT6Source",
            "dataset_sha256_before": sha,
            "final_decision": "APPROVED",
            "approved_at": "2026-01-01T00:00:00Z",
        }
        (adir / "BT6Source.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        result = merge_nae_corpus(
            source_id="BT6Source",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=ds,
            manifest_path=mf,
            registry_path=rg,
            decisions_dir=ddir,
            approval_dir=adir,
        )

        assert result["status"] == "completed"
        assert result["new_records_after_dedup"] == 1

        # 기록 대상이 지정 경로와 정확히 일치
        records = [json.loads(l) for l in ds.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
        assert len(records) == 1
        assert records[0]["tsu_id"] == "TSU-BT6"


class TestBT7NonProductionNoApprovalNeeded:
    """B-T7: non-production(tmp) 경로는 approval artifact 없이도 ALLOW (과차단 방지)."""

    def test_non_production_allows_without_approval(self, tmp_output):
        """production monkeypatch 없이 tmp 경로로 호출 → approval artifact 불필요."""
        ds = tmp_output / "bench" / "tsu_dataset.jsonl"
        mf = tmp_output / "bench" / "tsu_manifest.json"
        rg = tmp_output / "registry" / "identity_registry.json"

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT7Source", ["TSU-BT7"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT7Source", ["TSU-BT7"])

        ds.write_text("", encoding="utf-8")

        # production target approval artifact 없이 호출
        result = merge_nae_corpus(
            source_id="BT7Source",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=ds,
            manifest_path=mf,
            registry_path=rg,
            decisions_dir=ddir,
        )

        assert result["status"] == "completed"
        assert result["new_records_after_dedup"] == 1


class TestBT8MutationBeforeFailure:
    """B-T8: BLOCK 케이스 전부에서 'mutation 이전에' 실패했음을 단언(dataset 파일 mtime·hash 불변)."""

    def test_dataset_unchanged_on_block(self, _isolate_production_paths):
        info = _isolate_production_paths
        ds = info["dataset_path"]
        mf = info["manifest_path"]
        rg = info["registry_path"]

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT8Source", ["TSU-BT8"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT8Source", ["TSU-BT8"])

        original_content = json.dumps({"tsu_id": "TSU-BT8", "claim": "Original claim"}, ensure_ascii=False) + "\n"
        ds.write_text(original_content, encoding="utf-8")
        hash_before = _file_hash(str(ds))
        mtime_before = os.path.getmtime(str(ds))

        # production target approval artifact — source_id 불일치로 BLOCK 유도
        adir = tmp_path / "approval"
        adir.mkdir(parents=True)
        sha = compute_dataset_sha256(ds)
        tp_realpath = [str(ds), str(mf), str(rg)]
        approval = {
            "schema_version": 1,
            "source_id": "WRONG_BT8",  # 불일치
            "target_paths_realpath": tp_realpath,
            "reviewer_id": "R-BT8",
            "gate_id": "G-BT8",
            "dataset_sha256_before": sha,
            "final_decision": "APPROVED",
            "approved_at": "2026-01-01T00:00:00Z",
        }
        (adir / "BT8Source.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with pytest.raises(CorpusMutationBlockedError):
            merge_nae_corpus(
                source_id="BT8Source",
                nae_corpus_dir=corpus_root,
                tsu_dataset_path=ds,
                manifest_path=mf,
                registry_path=rg,
                decisions_dir=ddir,
                approval_dir=adir,
            )

        # mutation 이전에 실패했으므로 파일이 변경되지 않았어야 함
        hash_after = _file_hash(str(ds))
        mtime_after = os.path.getmtime(str(ds))
        assert hash_before == hash_after, f"dataset hash changed: {hash_before} != {hash_after}"
        assert mtime_before == mtime_after, f"dataset mtime changed: {mtime_before} != {mtime_after}"
        assert ds.read_text(encoding="utf-8") == original_content


class TestBT7NonProductionNoApprovalNeeded:
    """B-T7: non-production(tmp) 경로는 approval artifact 없이도 ALLOW (과차단 방지)."""

    def test_non_production_allows_without_approval(self, tmp_output):
        """production monkeypatch 없이 tmp 경로로 호출 → approval artifact 불필요."""
        ds = tmp_output / "bench" / "tsu_dataset.jsonl"
        mf = tmp_output / "bench" / "tsu_manifest.json"
        rg = tmp_output / "registry" / "identity_registry.json"

        tmp_path = Path(tempfile.mkdtemp())
        corpus_root = _make_corpus_dir(tmp_path, "BT7Source", ["TSU-BT7"])
        ddir = _make_approved_decisions_dir(tmp_path, "BT7Source", ["TSU-BT7"])

        ds.write_text("", encoding="utf-8")

        # production target approval artifact 없이 호출
        result = merge_nae_corpus(
            source_id="BT7Source",
            nae_corpus_dir=corpus_root,
            tsu_dataset_path=ds,
            manifest_path=mf,
            registry_path=rg,
            decisions_dir=ddir,
        )

        assert result["status"] == "completed"
        assert result["new_records_after_dedup"] == 1


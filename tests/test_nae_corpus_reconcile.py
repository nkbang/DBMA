"""tests/test_nae_corpus_reconcile.py — NAE Corpus Reconciliation Tool Tests.

reconcile tool skeleton 검증.

실행:
    cd ~/DBMA and source ~/envs/dbma311/bin/activate
    python -m pytest tests/test_nae_corpus_reconcile.py -v
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Constants ────────────────────────────────────────────────────────────────

M2_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"
INCREMENTAL_STATE = PROJECT_ROOT / "NAE" / "pipeline" / "ingest" / "state" / "incremental_state.json"
TSU_DIR = PROJECT_ROOT / "NAE" / "corpus" / "tsu"


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── Test: M2 count ──────────────────────────────────────────────────────────

class TestM2Count:
    def test_m2_count_is_14(self):
        """M2에 14개 source가 있어야 함."""
        m2_data = _load_yaml(M2_PATH)
        assert len(m2_data["sources"]) == 14

    def test_m2_source_ids_are_unique(self):
        """M2 source_id가 모두 고유해야 함."""
        m2_data = _load_yaml(M2_PATH)
        sids = [s["source_id"] for s in m2_data["sources"]]
        assert len(sids) == len(set(sids))


# ── Test: Incremental state ─────────────────────────────────────────────────

class TestIncrementalState:
    def test_incremental_state_exists(self):
        """incremental_state.json이 존재해야 함."""
        assert INCREMENTAL_STATE.exists()

    def test_incremental_state_is_dict(self):
        """incremental_state가 dict여야 함."""
        with open(INCREMENTAL_STATE) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_incremental_state_has_entries(self):
        """incremental_state에 엔트리가 있어야 함."""
        with open(INCREMENTAL_STATE) as f:
            data = json.load(f)
        assert len(data) > 0


# ── Test: TSU count ─────────────────────────────────────────────────────────

class TestTSUCount:
    def test_tsu_dir_exists(self):
        """TSU 디렉터리가 존재해야 함."""
        assert TSU_DIR.exists()

    def test_tsu_subdirectories_exist(self):
        """TSU에 하위 디렉터리가 있어야 함."""
        subdirs = [d for d in TSU_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")]
        assert len(subdirs) > 0

    def test_tsu_json_files_exist(self):
        """각 하위 디렉터리에 tsu.json이 있어야 함."""
        for subdir in TSU_DIR.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            assert (subdir / "tsu.json").exists()

    def test_tsu_json_is_list(self):
        """tsu.json이 list여야 함."""
        for subdir in TSU_DIR.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            tsu_json = subdir / "tsu.json"
            with open(tsu_json) as f:
                data = json.load(f)
            assert isinstance(data, list)

    def test_tsu_records_have_required_fields(self):
        """TSU record에 필수 필드가 있어야 함."""
        for subdir in TSU_DIR.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            tsu_json = subdir / "tsu.json"
            with open(tsu_json) as f:
                data = json.load(f)
            if len(data) > 0:
                required = ("id", "tsu_schema_version", "source_text", "claim")
                for field in required:
                    assert field in data[0], f"{field} missing from first record"


# ── Test: Reconcile tool skeleton ───────────────────────────────────────────

class TestReconcileSkeleton:
    def test_reconcile_tool_exists(self):
        """reconcile tool이 존재해야 함."""
        reconcile_path = PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"
        assert reconcile_path.exists()

    def test_reconcile_tool_runs(self):
        """reconcile tool이 실행되어야 함."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        # exit code 1은 discrepancy가 있음을 의미 (정상)
        assert result.returncode in (0, 1), f"Unexpected exit: {result.returncode}"

    def test_reconcile_tool_reports_qdrant_unreachable(self):
        """reconcile tool이 Qdrant를 unreachable로 보고해야 함."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert "unreachable" in result.stdout

    def test_reconcile_tool_reports_counts(self):
        """reconcile tool이 M2/incremental/TSU 카운트를 보고해야 함."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert "M2" in result.stdout
        assert "Incremental state" in result.stdout
        assert "TSU" in result.stdout

    def test_reconcile_tool_no_apply_flag(self):
        """reconcile tool에 --apply 플래그가 없어야 함."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"), "--apply"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert "unrecognized arguments: --apply" in result.stderr

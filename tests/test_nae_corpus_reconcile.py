"""tests/test_nae_corpus_reconcile.py — NAE Corpus Reconciliation Tool Tests.

Tests for the read-only corpus reconciliation tool.

All tests use tmp fixtures with path overrides -- no contact with actual NAE/ files
except the smoke test which runs against real files and records output without modification.

Execution:
    cd ~/DBMA && source ~/envs/dbma311/bin/activate
    python -m pytest tests/test_nae_corpus_reconcile.py -v
"""

import json
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tmp_dir(name: str) -> Path:
    """Create a temporary directory for test fixtures."""
    d = Path(f"/tmp/nae_reconcile_test_{name}_{os.getpid()}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _write_yaml(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def _write_jsonl(path: Path, records):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_paths():
    """Create temporary paths for all four authorities."""
    td = _tmp_dir("paths")
    m2_path = td / "source_manifest.yaml"
    state_path = td / "incremental_state.json"
    tsu_base = td / "tsu"
    adm_path = td / "corpus_admissions.jsonl"

    # Create M2 with 3 sources
    m2_data = {
        "schema_version": "1",
        "sources": [
            {"source_id": "SRC-001", "work_id": "work-001", "edition_id": "ed-001"},
            {"source_id": "SRC-002", "work_id": "work-002", "edition_id": "ed-002"},
            {"source_id": "SRC-003", "work_id": "work-003", "edition_id": "ed-003"},
        ],
    }
    _write_yaml(m2_path, m2_data)

    # Create incremental_state with 5 INDEXED entries
    state = {}
    for i in range(1, 6):
        state[f"TSU-{i:05d}"] = {"state": "INDEXED", "content_hash": f"hash{i}", "updated_at": "2026-01-01T00:00:00Z"}
    _write_json(state_path, state)

    # Create TSU dirs with review_status (use parents=True for nested mkdir)
    for dname in ("DirA", "DirB"):
        d = tsu_base / dname
        d.mkdir(parents=True, exist_ok=True)
        records = []
        for i in range(1, 6):
            rec = {
                "id": f"TSU-{i:05d}",
                "review_status": "verified",
                "source_id": "SRC-001",
                "work_id": "work-001",
                "edition_id": "ed-001",
            }
            records.append(rec)
        _write_json(d / "tsu.json", records)

    # Create admissions
    admissions = [
        {"source_id": "SRC-001", "decided_by": "HQ", "date": "2026-01-01", "track": "tsu"},
        {"source_id": "SRC-002", "decided_by": "HQ", "date": "2026-01-01", "track": "tsu"},
    ]
    _write_jsonl(adm_path, admissions)

    yield {
        "m2_path": m2_path,
        "state_path": state_path,
        "tsu_dir": tsu_base,
        "admissions_path": adm_path,
    }

    # Cleanup
    shutil.rmtree(td, ignore_errors=True)


# ── (a) Qdrant unreachable ────────────────────────────────────────────────────

class TestQdrantUnreachable:
    def test_probe_returns_unreachable(self):
        """probe_qdrant returns ('unreachable', reason) when connection fails."""
        from scripts.nae_corpus_reconcile import probe_qdrant
        result = probe_qdrant(url="http://localhost:19999")
        assert result[0] == "unreachable"

    def test_reconcile_completes_with_unreachable(self, tmp_paths):
        """reconcile() completes without exception when Qdrant is unreachable."""
        from scripts.nae_corpus_reconcile import reconcile

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("unreachable", "connection refused")
            result = reconcile(
                m2_path=tmp_paths["m2_path"],
                incremental_state=tmp_paths["state_path"],
                tsu_dir=tmp_paths["tsu_dir"],
                admissions_path=tmp_paths["admissions_path"],
                qdrant_url="http://localhost:19999",
            )
        assert result.qdrant_status == "unreachable"
        # INV-2 should be skipped
        inv2 = [i for i in result.invariants if i["id"] == "INV-2"][0]
        assert inv2["ok"] is False
        assert inv2.get("skipped") is True


# ── (b) reachable + consistent input -> drift 0 ───────────────────────────────

class TestReachableConsistent:
    def test_no_drift_with_consistent_ids(self, tmp_paths):
        """verified_ids == indexed_ids == qdrant_ids -> core_drift == [], exit 0."""
        from scripts.nae_corpus_reconcile import reconcile

        # Make all TSU records verified
        for d in tmp_paths["tsu_dir"].iterdir():
            tsu_json = d / "tsu.json"
            if tsu_json.exists():
                with open(tsu_json) as f:
                    records = json.load(f)
                for r in records:
                    r["review_status"] = "verified"
                _write_json(tsu_json, records)

        fake_ids = {"TSU-00001", "TSU-00002", "TSU-00003", "TSU-00004", "TSU-00005"}

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("reachable", fake_ids)
            result = reconcile(
                m2_path=tmp_paths["m2_path"],
                incremental_state=tmp_paths["state_path"],
                tsu_dir=tmp_paths["tsu_dir"],
                admissions_path=tmp_paths["admissions_path"],
                qdrant_url="http://localhost:9999",
            )

        assert result.core_drift == [], f"Expected no core drift, got: {result.core_drift}"
        assert result.governance_drift == [], f"Expected no gov drift, got: {result.governance_drift}"


# ── (c1) INV-1 flag ───────────────────────────────────────────────────────────

class TestINV1:
    def test_inv1_flag_when_verified_not_indexed(self, tmp_paths):
        """Remove 1 id from indexed_ids -> INV-1 violation + tsu_id in verified_only."""
        from scripts.nae_corpus_reconcile import reconcile

        # Remove TSU-00005 from incremental state
        with open(tmp_paths["state_path"]) as f:
            state = json.load(f)
        del state["TSU-00005"]
        _write_json(tmp_paths["state_path"], state)

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("reachable", {"TSU-00001", "TSU-00002", "TSU-00003", "TSU-00004", "TSU-00005"})
            result = reconcile(
                m2_path=tmp_paths["m2_path"],
                incremental_state=tmp_paths["state_path"],
                tsu_dir=tmp_paths["tsu_dir"],
                admissions_path=tmp_paths["admissions_path"],
                qdrant_url="http://localhost:9999",
            )

        inv1 = [i for i in result.invariants if i["id"] == "INV-1"][0]
        assert inv1["ok"] is False
        assert "verified_only" in inv1["detail"]
        assert len(result.core_drift) > 0


# ── (c2) INV-2 flag ───────────────────────────────────────────────────────────

class TestINV2:
    def test_inv2_flag_when_qdrant_ids_differ(self, tmp_paths):
        """Different qdrant_ids -> INV-2 violation."""
        from scripts.nae_corpus_reconcile import reconcile

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            # Different set from verified_ids
            mock_probe.return_value = ("reachable", {"TSU-00099", "TSU-00002", "TSU-00003", "TSU-00004", "TSU-00005"})
            result = reconcile(
                m2_path=tmp_paths["m2_path"],
                incremental_state=tmp_paths["state_path"],
                tsu_dir=tmp_paths["tsu_dir"],
                admissions_path=tmp_paths["admissions_path"],
                qdrant_url="http://localhost:9999",
            )

        inv2 = [i for i in result.invariants if i["id"] == "INV-2"][0]
        assert inv2["ok"] is False
        assert len(result.core_drift) > 0


# ── (c3) INV-3 flag ───────────────────────────────────────────────────────────

class TestINV3:
    def test_inv3_flag_when_generated_in_indexed(self, tmp_paths):
        """Inject generated tsu_id into indexed_ids -> INV-3 violation."""
        from scripts.nae_corpus_reconcile import reconcile

        # Add a generated record to one TSU dir
        d = tmp_paths["tsu_dir"] / "DirA"
        with open(d / "tsu.json") as f:
            records = json.load(f)
        records.append({
            "id": "TSU-00099",
            "review_status": "generated",
            "source_id": "SRC-001",
        })
        _write_json(d / "tsu.json", records)

        # Add TSU-00099 to indexed state
        with open(tmp_paths["state_path"]) as f:
            state = json.load(f)
        state["TSU-00099"] = {"state": "INDEXED", "content_hash": "h99", "updated_at": "2026-01-01T00:00:00Z"}
        _write_json(tmp_paths["state_path"], state)

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("reachable", {"TSU-00001", "TSU-00002", "TSU-00003", "TSU-00004", "TSU-00005"})
            result = reconcile(
                m2_path=tmp_paths["m2_path"],
                incremental_state=tmp_paths["state_path"],
                tsu_dir=tmp_paths["tsu_dir"],
                admissions_path=tmp_paths["admissions_path"],
                qdrant_url="http://localhost:9999",
            )

        inv3 = [i for i in result.invariants if i["id"] == "INV-3"][0]
        assert inv3["ok"] is False
        assert len(result.core_drift) > 0


# ── (c4) INV-4 flag ───────────────────────────────────────────────────────────

class TestINV4:
    def test_inv4_flag_when_linkage_not_in_m2(self, tmp_paths):
        """TSU record linkage not in M2 -> INV-4 violation."""
        from scripts.nae_corpus_reconcile import reconcile

        # Add a record with non-existent linkage
        d = tmp_paths["tsu_dir"] / "DirA"
        with open(d / "tsu.json") as f:
            records = json.load(f)
        records.append({
            "id": "TSU-00099",
            "review_status": "verified",
            "source_id": "SRC-FAKE",  # not in M2
        })
        _write_json(d / "tsu.json", records)

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("reachable", {"TSU-00001", "TSU-00002", "TSU-00003", "TSU-00004", "TSU-00005"})
            result = reconcile(
                m2_path=tmp_paths["m2_path"],
                incremental_state=tmp_paths["state_path"],
                tsu_dir=tmp_paths["tsu_dir"],
                admissions_path=tmp_paths["admissions_path"],
                qdrant_url="http://localhost:9999",
            )

        inv4 = [d for d in result.core_drift if "INV-4" in d]
        assert len(inv4) > 0


# ── (c5) GC-2 flag ────────────────────────────────────────────────────────────

class TestGC2:
    def test_gc2_flag_when_verified_source_no_admission(self, tmp_paths):
        """Verified TSU from source without admission -> GOVERNANCE DRIFT."""
        from scripts.nae_corpus_reconcile import reconcile

        # Remove SRC-002 from admissions (but keep verified TSUs pointing to it)
        admissions = [
            {"source_id": "SRC-001", "decided_by": "HQ", "date": "2026-01-01", "track": "tsu"},
        ]
        _write_jsonl(tmp_paths["admissions_path"], admissions)

        # Change some TSU records to point to SRC-002 (which has no admission)
        for d in tmp_paths["tsu_dir"].iterdir():
            tsu_json = d / "tsu.json"
            if tsu_json.exists():
                with open(tsu_json) as f:
                    records = json.load(f)
                # Change first record to point to SRC-002
                records[0]["source_id"] = "SRC-002"
                records[0]["work_id"] = "work-002"
                records[0]["edition_id"] = "ed-002"
                _write_json(tsu_json, records)

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("reachable", {"TSU-00001", "TSU-00002", "TSU-00003", "TSU-00004", "TSU-00005"})
            result = reconcile(
                m2_path=tmp_paths["m2_path"],
                incremental_state=tmp_paths["state_path"],
                tsu_dir=tmp_paths["tsu_dir"],
                admissions_path=tmp_paths["admissions_path"],
                qdrant_url="http://localhost:9999",
            )

        gc2 = [g for g in result.governance if g["id"] == "GC-2"][0]
        assert gc2["ok"] is False
        assert len(result.governance_drift) > 0


# ── (d) mutation 0 + --apply reject ───────────────────────────────────────────

class TestMutationAndApply:
    def test_mutation_zero(self):
        """Pre/post sha256 of production files must be identical."""
        target_files = [
            Path("NAE/pipeline/ingest/state/incremental_state.json"),
            Path("NAE/pipeline/registration/state/source_manifest.yaml"),
            Path("NAE/governance/corpus_admissions.jsonl"),
        ]

        pre_hashes = {}
        for f in target_files:
            fp = PROJECT_ROOT / f
            if fp.exists():
                pre_hashes[str(f)] = _sha256_file(fp)

        # Run reconcile via subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )

        post_hashes = {}
        for f in target_files:
            fp = PROJECT_ROOT / f
            if fp.exists():
                post_hashes[str(f)] = _sha256_file(fp)

        # All pre == post
        for f in pre_hashes:
            assert pre_hashes[f] == post_hashes[f], f"Mutation detected on {f}: pre={pre_hashes[f]} post={post_hashes[f]}"

    def test_apply_flag_rejected(self):
        """--apply should produce 'unrecognized arguments' error."""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"), "--apply"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "unrecognized arguments: --apply" in result.stderr


# ── D-4: probe_qdrant error classification ────────────────────────────────────

class TestD4ErrorClassification:
    def test_connection_refused_returns_unreachable(self):
        """Connection refused should be ('unreachable', ...), not ('error', ...)."""
        from scripts.nae_corpus_reconcile import probe_qdrant
        result = probe_qdrant(url="http://localhost:19999")
        assert result[0] == "unreachable", f"Expected 'unreachable' for connection refused, got '{result[0]}'"

    def test_collection_not_found_returns_error(self):
        """'collection not found' type errors should be ('error', ...), not ('unreachable', ...)."""
        from scripts.nae_corpus_reconcile import probe_qdrant

        # Mock the QdrantClient to simulate UnexpectedResponse (collection not found)
        with patch("qdrant_client.QdrantClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client

            from qdrant_client.http.exceptions import UnexpectedResponse
            mock_client.get_collection.side_effect = UnexpectedResponse(
                status_code=404,
                reason_phrase="Not Found",
                content=b'{"status":"error","message":"Collection not found"}',
                headers=MagicMock(),
            )

            result = probe_qdrant(url="http://localhost:9999", collection="nonexistent")
            assert result[0] == "error", f"Expected 'error' for collection-not-found, got '{result[0]}'"


# ── Smoke test (not a judgment test) ──────────────────────────────────────────

class TestSmoke:
    def test_smoke_run_real_files(self):
        """Run reconcile against real files -- capture stdout + exit code as-is.

        Do NOT modify data to force pass. Report drift if found.
        """
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        # Should complete without exception
        assert result.returncode in (0, 1), f"Unexpected exit code: {result.returncode}, stderr: {result.stderr}"
        # Should have output
        assert len(result.stdout) > 0, "Expected stdout output"

    def test_smoke_run_json(self):
        """Run reconcile --json against real files."""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"), "--json"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode in (0, 1)
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "authorities" in data
        assert "invariants" in data
        assert "governance" in data
        assert "qdrant" in data
        assert "drift" in data

    def test_smoke_apply_rejected(self):
        """--apply should be rejected."""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"), "--apply"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert "unrecognized arguments: --apply" in result.stderr


# ── F-1: INV-2 payload tsu_id vs point.id ──────────────────────────────────────

class TestF1PayloadTsuId:
    def test_inv2_passes_when_payload_tsu_id_matches_verified(self):
        """point.id=6, payload.tsu_id='TSU-00006', verified='TSU-00006' → INV-2 PASS.

        Numeric point ID ≠ TSU ID 이지만 payload tsu_id 가 일치하므로 false drift 아님.
        """
        from scripts.nae_corpus_reconcile import reconcile

        td = _tmp_dir("f1_payload")
        m2_path = td / "source_manifest.yaml"
        state_path = td / "incremental_state.json"
        tsu_base = td / "tsu"
        adm_path = td / "corpus_admissions.jsonl"

        m2_data = {"schema_version": "1", "sources": [{"source_id": "SRC-001", "work_id": "work-001", "edition_id": "ed-001"}]}
        _write_yaml(m2_path, m2_data)

        state = {"TSU-00006": {"state": "INDEXED", "content_hash": "h6", "updated_at": "2026-01-01T00:00:00Z"}}
        _write_json(state_path, state)

        d = tsu_base / "DirA"
        d.mkdir(parents=True, exist_ok=True)
        records = [{"id": "TSU-00006", "review_status": "verified", "source_id": "SRC-001"}]
        _write_json(d / "tsu.json", records)

        _write_jsonl(adm_path, [{"source_id": "SRC-001", "decided_by": "HQ", "date": "2026-01-01", "track": "tsu"}])

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            # probe returns set of tsu_id strings from payload (not numeric point.id)
            mock_probe.return_value = ("reachable", {"TSU-00006"})
            result = reconcile(
                m2_path=m2_path,
                incremental_state=state_path,
                tsu_dir=tsu_base,
                admissions_path=adm_path,
                qdrant_url="http://localhost:9999",
            )

        shutil.rmtree(td, ignore_errors=True)

        inv2 = [i for i in result.invariants if i["id"] == "INV-2"][0]
        assert inv2["ok"] is True, f"Expected INV-2 PASS when payload tsu_id matches, got: {inv2}"


# ── F-2: INV-4b linkage missing → INFO, not CORE DRIFT ─────────────────────────

class TestF2LinkageMissing:
    def test_no_linkage_fields_returns_info_not_core_drift(self):
        """TSU record with no linkage fields → [INFO], not CORE DRIFT, exit 0 possible."""
        from scripts.nae_corpus_reconcile import reconcile

        td = _tmp_dir("f2_nolinkage")
        m2_path = td / "source_manifest.yaml"
        state_path = td / "incremental_state.json"
        tsu_base = td / "tsu"
        adm_path = td / "corpus_admissions.jsonl"

        m2_data = {"schema_version": "1", "sources": [{"source_id": "SRC-001", "work_id": "work-001", "edition_id": "ed-001"}]}
        _write_yaml(m2_path, m2_data)

        state = {"TSU-00001": {"state": "INDEXED", "content_hash": "h1", "updated_at": "2026-01-01T00:00:00Z"}}
        _write_json(state_path, state)

        d = tsu_base / "DirA"
        d.mkdir(parents=True, exist_ok=True)
        records = [{"id": "TSU-00001", "review_status": "verified"}]
        _write_json(d / "tsu.json", records)

        _write_jsonl(adm_path, [{"source_id": "SRC-001", "decided_by": "HQ", "date": "2026-01-01", "track": "tsu"}])

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("reachable", {"TSU-00001"})
            result = reconcile(m2_path=m2_path, incremental_state=state_path, tsu_dir=tsu_base, admissions_path=adm_path, qdrant_url="http://localhost:9999")

        shutil.rmtree(td, ignore_errors=True)

        inv4b_info = [i for i in result.info_lines if "INV-4b" in i]
        assert len(inv4b_info) > 0, f"Expected INV-4b INFO line, got: {result.info_lines}"

        inv4_drift = [d for d in result.core_drift if "INV-4" in d and "INV-4b" not in d]
        assert len(inv4_drift) == 0, f"Expected no INV-4 CORE DRIFT for missing linkage, got: {inv4_drift}"

    def test_linkage_exists_but_not_in_m2_returns_core_drift(self):
        """Linkage field exists but value not in M2 → CORE DRIFT, exit 1."""
        from scripts.nae_corpus_reconcile import reconcile

        td = _tmp_dir("f2_badlinkage")
        m2_path = td / "source_manifest.yaml"
        state_path = td / "incremental_state.json"
        tsu_base = td / "tsu"
        adm_path = td / "corpus_admissions.jsonl"

        m2_data = {"schema_version": "1", "sources": [{"source_id": "SRC-001", "work_id": "work-001", "edition_id": "ed-001"}]}
        _write_yaml(m2_path, m2_data)

        state = {"TSU-00001": {"state": "INDEXED", "content_hash": "h1", "updated_at": "2026-01-01T00:00:00Z"}}
        _write_json(state_path, state)

        d = tsu_base / "DirA"
        d.mkdir(parents=True, exist_ok=True)
        records = [{"id": "TSU-00001", "review_status": "verified", "source_id": "SRC-FAKE"}]
        _write_json(d / "tsu.json", records)

        _write_jsonl(adm_path, [{"source_id": "SRC-001", "decided_by": "HQ", "date": "2026-01-01", "track": "tsu"}])

        with patch("scripts.nae_corpus_reconcile.probe_qdrant") as mock_probe:
            mock_probe.return_value = ("reachable", {"TSU-00001"})
            result = reconcile(m2_path=m2_path, incremental_state=state_path, tsu_dir=tsu_base, admissions_path=adm_path, qdrant_url="http://localhost:9999")

        shutil.rmtree(td, ignore_errors=True)

        inv4_drift = [d for d in result.core_drift if "INV-4" in d and "INV-4b" not in d]
        assert len(inv4_drift) > 0, f"Expected INV-4 CORE DRIFT for bad linkage, got: {result.core_drift}"


# ── F-3: --json ok is boolean ───────────────────────────────────────────────────

class TestF3JsonBooleanOk:
    def test_json_ok_is_boolean_true(self):
        """--json output ok field must be JSON boolean, not string."""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"), "--json"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        invariants = data.get("invariants", [])
        for inv in invariants:
            ok_val = inv.get("ok")
            assert isinstance(ok_val, bool), f"INV {inv.get('id')}: ok must be bool, got {type(ok_val).__name__} = {ok_val!r}"

    def test_json_skipped_has_separate_field(self):
        """skipped must be separate field, not string in ok."""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "nae_corpus_reconcile.py"), "--json"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        invariants = data.get("invariants", [])
        for inv in invariants:
            if inv.get("skipped"):
                assert inv["ok"] is False, f"INV {inv['id']}: when skipped=True, ok must be False, got {inv['ok']!r}"

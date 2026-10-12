"""PR-2: 호출부 strict 적용·mutate_registry 회귀 테스트 (경로는 tmp_path 아래만)."""
import json
import os

import pytest

from core import identity_registry as ir
from core import index_orchestrator as io_


def _seed(tmp_path, state="PROCESSED"):
    d = tmp_path / "registry"
    d.mkdir()
    doc = {"source_file": "a.md", "chunk_count": 1, "pipeline_state": state,
           "ingest_status": "PROCESSED", "language": "ko", "source_type": "md"}
    p = d / "documents.json"
    p.write_text(json.dumps({"schema_version": "2.0", "documents": {"d1": doc}}), encoding="utf-8")
    return str(p)


def test_mutate_registry_saves_and_returns(tmp_path):
    p = _seed(tmp_path)
    def fn(reg):
        reg["documents"]["d1"]["title"] = "T"
        return True
    assert ir.mutate_registry(p, fn) is True
    assert ir.load_identity_registry(p)["documents"]["d1"]["title"] == "T"


def test_mutate_registry_none_means_no_save(tmp_path):
    p = _seed(tmp_path)
    before = os.stat(p).st_mtime_ns
    assert ir.mutate_registry(p, lambda reg: None) is None
    assert os.stat(p).st_mtime_ns == before


def test_mutate_registry_corrupt_raises_and_leaves_file(tmp_path):
    p = _seed(tmp_path)
    open(p, "w").write("{broken")
    with pytest.raises(ir.RegistryCorruptError):
        ir.mutate_registry(p, lambda reg: True)
    assert open(p).read() == "{broken"  # 빈 레지스트리로 덮어쓰지 않음


def test_mutate_registry_save_failure_raises(tmp_path, monkeypatch):
    p = _seed(tmp_path)
    monkeypatch.setattr(ir, "replace_with_retry", lambda *a, **k: (_ for _ in ()).throw(PermissionError(13, "x")))
    with pytest.raises(ir.RegistrySaveError):
        ir.mutate_registry(p, lambda reg: True)


def test_reconcile_skips_cycle_when_registry_corrupt(tmp_path):
    p = _seed(tmp_path)
    open(p, "w").write("{broken")
    r = io_.reconcile_pending(output_dir=str(tmp_path))
    assert r["reconciled"] == 0 and r["pending"] == 0
    assert r["failed"] and r["failed"][0]["document_id"] == "*registry*"
    assert open(p).read() == "{broken"


def test_reconcile_reports_unpersisted_when_save_fails(tmp_path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.setattr(io_, "reindex_document", lambda *a, **k: {})
    monkeypatch.setattr(io_, "save_identity_registry", lambda *a, **k: False)
    r = io_.reconcile_pending(output_dir=str(tmp_path))
    assert r["reconciled"] == 0
    assert any(f["document_id"] == "*registry*" for f in r["failed"])

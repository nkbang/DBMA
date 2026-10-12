"""레지스트리 저장·읽기 보강(PR-1) 회귀 테스트.

실제 경로 오염 방지: 모든 경로는 tmp_path 아래만 쓴다.
"""
import json
import os
import stat

import pytest

from core import atomic_io, identity_registry as ir


def _reg(path):
    return str(path / "documents.json")


def test_roundtrip_unicode(tmp_path):
    p = _reg(tmp_path)
    reg = ir.load_identity_registry(p)
    reg["documents"]["x"] = {"title": "ἀγάπη — אהבה 사랑"}
    assert ir.save_identity_registry(reg, p) is True
    assert ir.load_identity_registry(p)["documents"]["x"]["title"] == "ἀγάπη — אהבה 사랑"


def test_no_fixed_tmp_name_and_no_leftovers(tmp_path):
    p = _reg(tmp_path)
    assert ir.save_identity_registry(ir.load_identity_registry(p), p)
    assert sorted(os.listdir(tmp_path)) == ["documents.json"]


def test_corrupt_default_returns_empty_but_preserves_copy(tmp_path):
    p = _reg(tmp_path)
    with open(p, "w", encoding="utf-8") as f:
        f.write("{not json")
    reg = ir.load_identity_registry(p)
    assert reg["documents"] == {}
    copies = [n for n in os.listdir(tmp_path) if ".corrupt-" in n]
    assert len(copies) == 1
    assert open(os.path.join(tmp_path, copies[0]), encoding="utf-8").read() == "{not json"
    assert open(p, encoding="utf-8").read() == "{not json"  # 원본은 건드리지 않음


def test_corrupt_strict_raises(tmp_path):
    p = _reg(tmp_path)
    open(p, "w").write("[1,2]")
    with pytest.raises(ir.RegistryCorruptError):
        ir.load_identity_registry(p, strict=True)


def test_invalid_utf8_is_corruption(tmp_path):
    p = _reg(tmp_path)
    open(p, "wb").write(b"\xff\xfe\x00bad")
    assert ir.load_identity_registry(p)["documents"] == {}
    with pytest.raises(ir.RegistryCorruptError):
        ir.load_identity_registry(p, strict=True)


def test_incompatible_schema_preserved(tmp_path):
    p = _reg(tmp_path)
    json.dump({"schema_version": "9.9", "documents": {"a": {}}}, open(p, "w"))
    assert ir.load_identity_registry(p)["documents"] == {}
    assert [n for n in os.listdir(tmp_path) if ".schema-9.9-" in n]
    with pytest.raises(ir.RegistrySchemaError):
        ir.load_identity_registry(p, strict=True)


def test_missing_file_is_empty_even_strict(tmp_path):
    assert ir.load_identity_registry(_reg(tmp_path), strict=True)["documents"] == {}


def test_preserved_copy_is_capped(tmp_path):
    p = _reg(tmp_path)
    for i in range(ir.MAX_PRESERVED_COPIES + 4):
        open(p, "w").write("{bad %d" % i)
        ir.load_identity_registry(p)
    copies = [n for n in os.listdir(tmp_path) if ".corrupt-" in n]
    assert len(copies) <= ir.MAX_PRESERVED_COPIES


def test_save_failure_returns_false_and_strict_raises(tmp_path, monkeypatch):
    p = _reg(tmp_path)
    def boom(*a, **k):
        raise PermissionError(13, "denied")
    monkeypatch.setattr(ir, "replace_with_retry", boom)
    reg = ir.load_identity_registry(p)
    assert ir.save_identity_registry(reg, p) is False
    with pytest.raises(ir.RegistrySaveError):
        ir.save_identity_registry(reg, p, strict=True)
    assert os.listdir(tmp_path) == []  # 임시 파일 정리됨


def test_transient_replace_failure_is_retried(tmp_path, monkeypatch):
    p = _reg(tmp_path)
    monkeypatch.setattr(atomic_io, "_TREAT_ALL_AS_TRANSIENT", True)
    real = os.replace
    calls = {"n": 0}
    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] < 3:
            raise PermissionError(13, "busy")
        return real(a, b)
    monkeypatch.setattr(os, "replace", flaky)
    assert ir.save_identity_registry(ir.load_identity_registry(p), p) is True
    assert calls["n"] == 3


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode")
def test_mode_preserved_and_default(tmp_path):
    p = _reg(tmp_path)
    assert ir.save_identity_registry(ir.load_identity_registry(p), p)
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o644
    os.chmod(p, 0o600)
    assert ir.save_identity_registry(ir.load_identity_registry(p), p)
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600


def test_is_transient_classification():
    assert atomic_io.is_transient_os_error(OSError(__import__("errno").EBUSY, "x"))
    assert not atomic_io.is_transient_os_error(FileNotFoundError(2, "x"))

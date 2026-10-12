"""PR-3: atomic_write_text / fsync_dir / 호출부 이전 회귀 (경로는 tmp_path 아래만)."""
import os

import pytest

from core import atomic_io


def test_atomic_write_text_roundtrip_unicode_and_no_leftover(tmp_path):
    p = str(tmp_path / "a.json")
    atomic_io.atomic_write_text(p, "ἀγάπη — אהבה 사랑")
    assert open(p, encoding="utf-8").read() == "ἀγάπη — אהבה 사랑"
    assert os.listdir(tmp_path) == ["a.json"]


def test_atomic_write_text_failure_cleans_tmp_and_keeps_original(tmp_path, monkeypatch):
    p = str(tmp_path / "a.json")
    open(p, "w").write("old")
    monkeypatch.setattr(atomic_io, "replace_with_retry", lambda *a, **k: (_ for _ in ()).throw(PermissionError(13, "x")))
    with pytest.raises(PermissionError):
        atomic_io.atomic_write_text(p, "new")
    assert open(p).read() == "old"
    assert os.listdir(tmp_path) == ["a.json"]


def test_atomic_write_text_retries_transient(tmp_path, monkeypatch):
    p = str(tmp_path / "a.json")
    monkeypatch.setattr(atomic_io, "_TREAT_ALL_AS_TRANSIENT", True)
    real, n = os.replace, {"n": 0}
    def flaky(a, b):
        n["n"] += 1
        if n["n"] < 2:
            raise PermissionError(13, "busy")
        return real(a, b)
    monkeypatch.setattr(os, "replace", flaky)
    atomic_io.atomic_write_text(p, "x")
    assert n["n"] == 2 and open(p).read() == "x"


def test_fsync_dir_skipped_on_windows_without_touching_os_open(tmp_path, monkeypatch):
    monkeypatch.setattr(atomic_io, "_IS_WINDOWS", True)
    def boom(*a, **k):
        raise AssertionError("os.open must not be called on Windows")
    monkeypatch.setattr(os, "open", boom)
    atomic_io.fsync_dir(str(tmp_path))


def test_fsync_dir_tolerates_open_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(atomic_io, "_IS_WINDOWS", False)
    monkeypatch.setattr(os, "open", lambda *a, **k: (_ for _ in ()).throw(PermissionError(13, "x")))
    atomic_io.fsync_dir(str(tmp_path))


def test_tsu_dataset_write_survives_windows_dir_open_failure(tmp_path, monkeypatch):
    """tsu_builder 가 디렉터리 os.open 실패(Windows)에 죽지 않는다."""
    from pathlib import Path
    from core import tsu_builder
    monkeypatch.setattr(atomic_io, "_IS_WINDOWS", True)
    p = Path(tmp_path) / "ds.jsonl"
    tsu_builder.write_tsu_dataset([{"a": 1}], p)
    assert p.read_text(encoding="utf-8").strip() == '{"a": 1}'

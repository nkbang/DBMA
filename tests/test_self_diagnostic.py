"""tests/test_self_diagnostic.py — core/self_diagnostic.py 회귀.

[S5-3] 앱 내 자가 진단 5개 항목(Ollama 연결/필수 모델/디스크/성경 본문/
코퍼스 건수)의 정상·이상 판정을 mock으로 검증한다.

핵심 회귀 대상: `ollama.list()`는 dict가 아니라 `.models`(Model 객체
리스트, 이름은 `.model` 속성)를 가진 객체를 반환한다 — 실측 확인
(ollama 0.34.x). 초기 구현이 `.get("models", [])`로 잘못 접근해 정상
연결 시에도 AttributeError로 죽는 결함이 있었다.
"""

import os
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import core.self_diagnostic as sd


class _FakeModel:
    def __init__(self, name):
        self.model = name


class _FakeListResponse:
    def __init__(self, names):
        self.models = [_FakeModel(n) for n in names]


def test_ollama_connection_ok(monkeypatch):
    fake_ollama = types.SimpleNamespace(list=lambda: _FakeListResponse([]))
    monkeypatch.setitem(sys.modules, "ollama", fake_ollama)

    result = sd._check_ollama_connection()

    assert result.status == "정상"


def test_ollama_connection_fails_when_unreachable(monkeypatch):
    def raise_conn_error():
        raise ConnectionError("연결 거부")

    fake_ollama = types.SimpleNamespace(list=raise_conn_error)
    monkeypatch.setitem(sys.modules, "ollama", fake_ollama)

    result = sd._check_ollama_connection()

    assert result.status == "오류"


def test_required_models_ok_with_object_shaped_response(monkeypatch):
    """ollama.list()가 dict가 아니라 .models(.model 속성) 객체를 반환하는
    실제 shape을 정확히 처리하는지 확인 — 회귀 방지의 핵심."""
    monkeypatch.setattr(sd, "DEFAULT_EMBED_MODEL", "bge-m3:latest")
    monkeypatch.setattr(sd, "DEFAULT_GEN_MODEL", "llama3.1:8b")
    fake_ollama = types.SimpleNamespace(
        list=lambda: _FakeListResponse(["bge-m3:latest", "llama3.1:8b", "other-model:latest"])
    )
    monkeypatch.setitem(sys.modules, "ollama", fake_ollama)

    result = sd._check_required_models()

    assert result.status == "정상"


def test_required_models_reports_missing(monkeypatch):
    monkeypatch.setattr(sd, "DEFAULT_EMBED_MODEL", "bge-m3:latest")
    monkeypatch.setattr(sd, "DEFAULT_GEN_MODEL", "llama3.1:8b")
    fake_ollama = types.SimpleNamespace(list=lambda: _FakeListResponse(["bge-m3:latest"]))
    monkeypatch.setitem(sys.modules, "ollama", fake_ollama)

    result = sd._check_required_models()

    assert result.status == "오류"
    assert "llama3.1:8b" in result.detail


def test_disk_space_warns_when_low(monkeypatch):
    fake_usage = types.SimpleNamespace(free=1 * (1024 ** 3), total=100 * (1024 ** 3), used=99 * (1024 ** 3))
    monkeypatch.setattr(sd.shutil, "disk_usage", lambda path: fake_usage)

    result = sd._check_disk_space()

    assert result.status == "오류"


def test_disk_space_ok_when_plenty(monkeypatch):
    fake_usage = types.SimpleNamespace(free=50 * (1024 ** 3), total=100 * (1024 ** 3), used=50 * (1024 ** 3))
    monkeypatch.setattr(sd.shutil, "disk_usage", lambda path: fake_usage)

    result = sd._check_disk_space()

    assert result.status == "정상"


def test_bible_text_warns_when_unavailable(monkeypatch):
    fake_bible = types.SimpleNamespace(available=False)
    monkeypatch.setattr(
        "core.bible_text.load_bible_text", lambda: fake_bible,
    )

    result = sd._check_bible_text()

    assert result.status == "확인 필요"


def test_bible_text_ok_when_available(monkeypatch):
    fake_bible = types.SimpleNamespace(
        available=True, version_label="개역개정", list_books=lambda: [("GEN", "창세기")],
    )
    monkeypatch.setattr(
        "core.bible_text.load_bible_text", lambda: fake_bible,
    )

    result = sd._check_bible_text()

    assert result.status == "정상"


def test_corpus_size_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sd, "DEFAULT_TSU_DATASET_PATH", str(tmp_path / "does_not_exist.jsonl"))

    result = sd._check_corpus_size()

    assert result.status == "확인 필요"


def test_corpus_size_zero_records(monkeypatch, tmp_path):
    empty = tmp_path / "tsu.jsonl"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setattr(sd, "DEFAULT_TSU_DATASET_PATH", str(empty))

    result = sd._check_corpus_size()

    assert result.status == "확인 필요"


def test_corpus_size_ok(monkeypatch, tmp_path):
    populated = tmp_path / "tsu.jsonl"
    populated.write_text('{"a":1}\n{"a":2}\n{"a":3}\n', encoding="utf-8")
    monkeypatch.setattr(sd, "DEFAULT_TSU_DATASET_PATH", str(populated))

    result = sd._check_corpus_size()

    assert result.status == "정상"
    assert "3" in result.detail


def test_run_self_diagnostic_returns_five_results_and_never_raises(monkeypatch):
    """항목 하나가 죽어도(예외) 전체 진단이 죽지 않는다."""
    def boom():
        raise RuntimeError("고장")

    monkeypatch.setattr(sd, "_check_ollama_connection", boom)

    results = sd.run_self_diagnostic()

    assert len(results) == 5
    assert any(r.status == "오류" for r in results)

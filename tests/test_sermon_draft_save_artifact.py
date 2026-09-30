"""Regression test — ui/pages/sermon_draft.py::_save_current_artifact().

[P1, docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md §4] 완성된 설교
상태를 SermonArtifact로 변환하는 로직만 검증한다 — 실제 파일 I/O는
core/test_sermon_artifact.py가 이미 커버하므로, 여기서는
save_sermon_artifact를 monkeypatch해 인자만 검사한다([[feedback_test_fixture_path_overrides]]
— 실제 DEFAULT_SERMON_ARTIFACT_DIR을 건드리지 않기 위함).
"""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import ollama  # noqa: F401
except ImportError:
    if "ollama" not in sys.modules:
        _ollama_stub = types.ModuleType("ollama")
        _ollama_stub.generate = lambda *a, **k: {"response": ""}
        _ollama_stub.embeddings = lambda *a, **k: {"embedding": []}
        sys.modules["ollama"] = _ollama_stub

import ui.pages.sermon_draft as mod
from core.generation import SermonOutline
from core.sermon.doctrine_filter import DoctrineReport


class _FakeCandidate:
    def __init__(self, tsu_id):
        self.tsu_id = tsu_id


def _make_state():
    return {
        "scripture_and_theme": "로마서 5:1-5, 고난 중의 소망",
        "sermon_format": "주제설교",
        "style_files": ["foo.txt"],
        "candidates": [_FakeCandidate("TSU-ROM-001"), _FakeCandidate("TSU-ROM-002")],
        "expanded": {0: "대지 1 확장", 1: "대지 2 확장"},
        "doctrine_report": DoctrineReport(passed=True, warnings=[], flagged_categories=[], confidence="medium"),
    }


def test_save_current_artifact_builds_correct_fields(monkeypatch):
    outline = SermonOutline(title="고난 중의 소망", introduction="서론", points=["대지 1", "대지 2"], conclusion="결론")
    state = _make_state()

    captured = {}

    def _fake_save(artifact, output_dir=None):
        captured["artifact"] = artifact
        return "/fake/path.json"

    monkeypatch.setattr(mod, "save_sermon_artifact", _fake_save)

    sermon_id = mod._save_current_artifact(outline, state)

    artifact = captured["artifact"]
    assert sermon_id == artifact.sermon_id
    assert artifact.scripture_and_theme == state["scripture_and_theme"]
    assert artifact.sermon_format == "주제설교"
    assert artifact.outline == {
        "title": "고난 중의 소망",
        "introduction": "서론",
        "points": ["대지 1", "대지 2"],
        "conclusion": "결론",
    }
    assert artifact.expanded == {"0": "대지 1 확장", "1": "대지 2 확장"}
    assert artifact.evidence["candidate_tsu_ids"] == ["TSU-ROM-001", "TSU-ROM-002"]
    from dataclasses import asdict
    assert artifact.doctrine_report == asdict(state["doctrine_report"])
    assert artifact.groundedness is None
    assert artifact.generation == {"style_files": ["foo.txt"]}


def test_save_current_artifact_handles_missing_doctrine_report(monkeypatch):
    outline = SermonOutline(title="t", introduction="i", points=["p"], conclusion="c")
    state = _make_state()
    state["doctrine_report"] = None

    captured = {}
    monkeypatch.setattr(mod, "save_sermon_artifact", lambda artifact, output_dir=None: captured.setdefault("a", artifact))

    mod._save_current_artifact(outline, state)
    assert captured["a"].doctrine_report is None

"""ParagraphResolver 검증 — NAE/pipeline/canonical/paragraph_lookup.py
(PM 정렬 감사 선결 #4 / 옵션 A, Task Order §2 산출물).

canonical.json에서 원문 문단 복원 정확도, fail-soft 폴백, identifier 캐시,
neighbors, canonical_version 불일치 처리.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from NAE.pipeline.canonical import paragraph_lookup
from NAE.pipeline.canonical.paragraph_lookup import ResolvedParagraph, resolve

# 이 워크트리에 실제로 존재하는 canonical corpus
_REAL_ID = "PBC1765"
_REAL_ROOT = os.path.join(os.path.dirname(__file__), "..", "NAE", "corpus", "canonical")


@pytest.fixture(autouse=True)
def _clear_cache():
    paragraph_lookup.clear_cache()
    yield
    paragraph_lookup.clear_cache()


@pytest.fixture
def synth_canonical(tmp_path):
    """합성 canonical.json — 경로 override 픽스처 (memory: Test Fixture Path Overrides)."""
    root = tmp_path / "canonical"
    ident = "TEST_WORK_01"
    (root / ident).mkdir(parents=True)
    doc = {
        "identifier": ident,
        "pipeline_version": "2.0.0",
        "paragraphs": [
            {"index": 0, "type": "prose", "text": "첫 문단입니다.", "page_start": 1, "page_end": 1,
             "sentences": [{"sentence_index": 0, "text": "첫 문단입니다."}], "scripture_references": []},
            {"index": 1, "type": "prose", "text": "두 번째 문단의 완결된 원문 텍스트다. 두 문장으로 되어 있다.",
             "page_start": 2, "page_end": 3,
             "sentences": [{"sentence_index": 0, "text": "두 번째 문단의 완결된 원문 텍스트다."}],
             "scripture_references": ["Rom.8.1"]},
            {"index": 2, "type": "prose", "text": "세 번째 문단.", "page_start": 3, "page_end": 3,
             "sentences": [], "scripture_references": []},
        ],
    }
    (root / ident / "canonical.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return root, ident


# ── 합성 픽스처 기반 ────────────────────────────────────────────

def test_resolve_returns_full_paragraph_text(synth_canonical):
    root, ident = synth_canonical
    r = resolve(ident, 1, canonical_root=root)
    assert isinstance(r, ResolvedParagraph)
    assert r.text == "두 번째 문단의 완결된 원문 텍스트다. 두 문장으로 되어 있다."
    assert r.page_start == 2 and r.page_end == 3
    assert r.scripture_references == ["Rom.8.1"]
    assert r.index == 1


def test_missing_file_returns_none(tmp_path):
    assert resolve("NOPE", 0, canonical_root=tmp_path / "canonical") is None


def test_missing_index_returns_none(synth_canonical):
    root, ident = synth_canonical
    assert resolve(ident, 999, canonical_root=root) is None


def test_canonical_version_mismatch_returns_none(synth_canonical):
    root, ident = synth_canonical
    assert resolve(ident, 1, canonical_root=root, expected_canonical_version="1.0.0") is None
    # 일치하면 정상
    assert resolve(ident, 1, canonical_root=root, expected_canonical_version="2.0.0") is not None


def test_neighbors_joins_adjacent_paragraphs(synth_canonical):
    root, ident = synth_canonical
    r = resolve(ident, 1, canonical_root=root, neighbors=1)
    assert "첫 문단입니다." in r.text
    assert "두 번째 문단" in r.text
    assert "세 번째 문단." in r.text
    assert r.neighbor_indices == [0, 1, 2]
    assert r.page_start == 1 and r.page_end == 3


def test_neighbors_at_boundary_skips_out_of_range(synth_canonical):
    root, ident = synth_canonical
    r = resolve(ident, 0, canonical_root=root, neighbors=1)  # index -1 없음
    assert r.neighbor_indices == [0, 1]


def test_none_args_return_none(synth_canonical):
    root, ident = synth_canonical
    assert resolve("", 1, canonical_root=root) is None
    assert resolve(ident, None, canonical_root=root) is None


def test_identifier_cache_reused(synth_canonical, monkeypatch):
    root, ident = synth_canonical
    real_open = open
    calls = {"n": 0}

    def counting_open(path, *a, **k):
        if str(path).endswith("canonical.json"):
            calls["n"] += 1
        return real_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", counting_open)
    resolve(ident, 0, canonical_root=root)
    resolve(ident, 1, canonical_root=root)
    resolve(ident, 2, canonical_root=root)
    assert calls["n"] == 1  # identifier 단위 1회 파싱


# ── 실제 corpus 기반 (consistency.py 패턴 동등성) ───────────────

def test_resolve_matches_canonical_json_verbatim():
    r = resolve(_REAL_ID, 46, canonical_root=os.path.abspath(_REAL_ROOT))
    assert r is not None
    raw = json.load(open(os.path.join(_REAL_ROOT, _REAL_ID, "canonical.json"), encoding="utf-8"))
    expected = next(p for p in raw["paragraphs"] if p["index"] == 46)
    assert r.text == expected["text"].strip()
    assert r.canonical_version == "2.0.0"

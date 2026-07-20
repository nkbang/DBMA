"""Unit tests — Hierarchical Chunk Builder prototype (SPRINT33-D Phase 1).

Dormant module: core.hierarchical_chunk_builder is not imported by
chunking_optimizer.py/processing.py or any production path.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.heading_provider import ProviderHeading
from core.hierarchical_chunk_builder import build_chunks


def _heading(text: str, level: int = 1, confidence: float = 1.0, source: str = "atx") -> ProviderHeading:
    return ProviderHeading(text=text, level=level, confidence=confidence, source=source)


def _cands(*texts: str) -> list:
    # Sequential fake offsets, spaced as if joined by "\n\n" — good enough
    # for tests that only assert relative ordering / first-candidate offset.
    out = []
    offset = 0
    for t in texts:
        out.append((t, offset))
        offset += len(t) + 2
    return out


class TestNoHeadingsFallsBackToSafetyCap:
    def test_short_candidates_merge_into_one_chunk_below_safety_cap(self):
        candidates = _cands("문단 하나", "문단 둘", "문단 셋")
        chunks = build_chunks(candidates, headings=[], chunk_size=1000, min_chunk_size=5)
        assert len(chunks) == 1
        assert chunks[0][1] == 0  # starts at first candidate's offset

    def test_force_flushes_at_safety_cap_without_any_semantic_signal(self):
        # chunk_size=10 -> safety cap = 15. Each candidate is 20 chars, so
        # every single candidate alone already exceeds the cap.
        candidates = _cands("x" * 20, "y" * 20, "z" * 20)
        chunks = build_chunks(candidates, headings=[], chunk_size=10, min_chunk_size=1)
        assert len(chunks) == 3


class TestMinChunkSizeFloor:
    def test_boundary_signal_ignored_below_min_chunk_size(self):
        headings = [_heading("서론")]
        candidates = _cands("서론", "본문 내용이 이어집니다")
        # min_chunk_size huge -> buffer never reaches the floor, so the
        # heading match on candidate 0 cannot itself trigger a flush (buf
        # is empty when candidate 0 is being evaluated), and nothing after
        # it can flush either since buf_len stays under the floor.
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=500)
        assert len(chunks) == 1

    def test_boundary_signal_honored_once_floor_is_met(self):
        headings = [_heading("서론"), _heading("본론")]
        candidates = _cands("아무 문단 내용입니다 채우기용 텍스트", "서론", "본론")
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=10)
        # first candidate alone clears min_chunk_size(10) -> "서론" (heading
        # match) should flush it into its own chunk before being folded in.
        assert len(chunks) >= 2
        assert chunks[0][0] == "아무 문단 내용입니다 채우기용 텍스트"


class TestSemanticBoundarySplitsBuffer:
    def test_heading_match_starts_a_new_chunk(self):
        headings = [_heading("서론"), _heading("결론")]
        candidates = _cands(
            "채우기용 본문 문단입니다 충분히 깁니다",
            "서론",
            "본문이 이어지는 두번째 문단입니다",
            "결론",
        )
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=5)
        texts = [c[0] for c in chunks]
        assert any(t.startswith("서론") for t in texts)
        assert any(t.startswith("결론") for t in texts)

    def test_chunk_start_offset_matches_first_candidate_offset(self):
        headings = [_heading("서론")]
        candidates = _cands("채우기용 문단입니다 충분한 길이", "서론", "이어지는 본문")
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=5)
        offsets = {text: offset for text, offset in candidates}
        for chunk_text, chunk_offset in chunks:
            first_candidate = chunk_text.split("\n\n")[0]
            assert offsets[first_candidate] == chunk_offset


class TestEmptyInput:
    def test_no_candidates_yields_no_chunks(self):
        assert build_chunks([], headings=[], chunk_size=1000, min_chunk_size=5) == []

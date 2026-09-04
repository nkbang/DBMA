"""Unit tests — chunk overflow audit driver
(docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md follow-up).
Diagnostic-only, not production code.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from shadow_chunk_overflow_audit import chunk_size_violation_stats


class TestChunkSizeViolationStats:
    def test_empty_chunks(self):
        stats = chunk_size_violation_stats([], chunk_size=1200)
        assert stats.total_chunks == 0
        assert stats.over_target == 0
        assert stats.over_cap == 0
        assert stats.over_target_ratio == 0.0
        assert stats.over_cap_ratio == 0.0

    def test_all_within_target(self):
        chunks = ["x" * 100, "y" * 1200, "z" * 500]
        stats = chunk_size_violation_stats(chunks, chunk_size=1200)
        assert stats.total_chunks == 3
        assert stats.over_target == 0
        assert stats.over_cap == 0
        assert stats.max_len == 1200

    def test_over_target_but_within_cap(self):
        # 1201-1800 chars: over the 1200 target but not yet past the 1.5x
        # (1800) cap that flags the reproduced production defect.
        chunks = ["x" * 1500]
        stats = chunk_size_violation_stats(chunks, chunk_size=1200)
        assert stats.over_target == 1
        assert stats.over_cap == 0

    def test_over_cap_flagged_as_likely_defect_b(self):
        # Reproduces docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md's
        # synthetic repro scale (2999-char single chunk from a 1200/200
        # config) -- this is exactly the "over_cap" bucket.
        chunks = ["x" * 2999]
        stats = chunk_size_violation_stats(chunks, chunk_size=1200)
        assert stats.total_chunks == 1
        assert stats.over_target == 1
        assert stats.over_cap == 1
        assert stats.over_cap_lens == [2999]
        assert stats.max_len == 2999

    def test_ratios(self):
        chunks = ["x" * 100, "y" * 2999, "z" * 100, "w" * 100]
        stats = chunk_size_violation_stats(chunks, chunk_size=1200)
        assert stats.total_chunks == 4
        assert stats.over_cap == 1
        assert stats.over_cap_ratio == 0.25

    def test_custom_overflow_ratio(self):
        chunks = ["x" * 1300]
        stats = chunk_size_violation_stats(chunks, chunk_size=1200, overflow_ratio=1.1)
        # cap = 1320 at ratio 1.1, so 1300 is over target but not over cap
        assert stats.over_target == 1
        assert stats.over_cap == 0

        stats2 = chunk_size_violation_stats(chunks, chunk_size=1200, overflow_ratio=1.0)
        # cap = 1200 at ratio 1.0, so 1300 now exceeds the cap too
        assert stats2.over_cap == 1

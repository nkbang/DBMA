"""Regression test — Evidence Reliability Adjustment (SPRINT19-C).

Guards the multiplicative confidence adjustment added at
RetrievalEngine.retrieve()'s final_score calculation (core/retrieval.py):

    final_score = base_score * (0.9 + 0.1 * evidence_confidence)

Per SPRINT19-C Preflight/decision: confidence is a narrow (+/-10%)
reliability adjustment, never a primary ranking signal — a large
semantic-relevance gap must always outweigh it, and TSUs with no
provenance (no scripture reference detected in their content, most of
the corpus) must default to the neutral midpoint 0.5, not be penalized.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import RetrievalEngine, QueryProcessor


def _write_tsu(tmp_path, records):
    path = tmp_path / "tsu.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def _tsu(tsu_id, content, confidence=None, book_id="JHN", chapter=3):
    rec = {
        "tsu_id": tsu_id,
        "content": content,
        "verse_mapping": {"book_id": book_id, "chapter": chapter},
        "themes": [],
    }
    if confidence is not None:
        rec["provenance"] = {
            "resolver": "scripture_evidence_resolver_v1",
            "confidence": confidence,
            "candidate_count": 1,
            "selected_reason": ["canonical_range_valid"],
        }
    return rec


class TestEvidenceAdjustmentDoesNotOverrideRelevance:
    def test_higher_relevance_low_confidence_beats_lower_relevance_high_confidence(self, tmp_path):
        """SPRINT19-C Preflight §3's worked example: a topically strong
        candidate with low confidence must still outrank a topically weak
        candidate with high confidence — the +/-10% band cannot close a
        real relevance gap."""
        strong_relevance_low_conf = _tsu(
            "TSU-A", "바울의 선교 전략과 교회 개척에 대한 신학적 논문 분석", confidence=0.1,
        )
        weak_relevance_high_conf = _tsu(
            "TSU-B", "설교 예화 모음집 목차 색인 페이지", confidence=1.0,
        )
        tsu_path = _write_tsu(tmp_path, [strong_relevance_low_conf, weak_relevance_high_conf])

        engine = RetrievalEngine(tsu_dataset_path=tsu_path)
        processor = QueryProcessor(engine)
        response = processor.process("바울의 선교 전략을 설명하라", query_id="t1", k=2)

        ranked_ids = [c.tsu_id for c in response.top_k_results]
        assert ranked_ids[0] == "TSU-A"


class TestEvidenceAdjustmentTieBreaking:
    def test_equal_relevance_higher_confidence_ranks_first(self, tmp_path):
        """When base relevance is effectively tied, the confidence
        adjustment should still nudge the more reliable evidence ahead —
        this is the "adjustment," not "ignored," half of the contract."""
        # Near-identical (not byte-identical) content — _deduplicate()
        # collapses candidates whose first 200 chars hash the same, so a
        # trivial per-record marker keeps both distinct while base
        # relevance scores stay effectively tied.
        low_conf = _tsu("TSU-LOW", "(low) 요한복음 3장에 대한 신학적 해설과 주석 내용입니다", confidence=0.1)
        high_conf = _tsu("TSU-HIGH", "(high) 요한복음 3장에 대한 신학적 해설과 주석 내용입니다", confidence=1.0)
        tsu_path = _write_tsu(tmp_path, [low_conf, high_conf])

        engine = RetrievalEngine(tsu_dataset_path=tsu_path)
        processor = QueryProcessor(engine)
        response = processor.process("요한복음 3장 해설", query_id="t2", k=2)

        by_id = {c.tsu_id: c.final_score for c in response.top_k_results}
        assert by_id["TSU-HIGH"] >= by_id["TSU-LOW"]


class TestMissingProvenanceDefaultsToNeutral:
    def test_no_provenance_is_not_penalized_below_low_confidence(self, tmp_path):
        """A TSU with no provenance (no scripture reference in its
        content — most of the corpus, SPRINT18-C/19-B coverage) must
        default to the neutral midpoint 0.5, not be treated as
        confidence=0 and pushed below an explicitly low-confidence TSU."""
        no_provenance = _tsu("TSU-NONE", "(none) 바울의 선교 전략 신학적 분석", confidence=None)
        low_conf = _tsu("TSU-LOW", "(low) 바울의 선교 전략 신학적 분석", confidence=0.0)
        tsu_path = _write_tsu(tmp_path, [no_provenance, low_conf])

        engine = RetrievalEngine(tsu_dataset_path=tsu_path)
        processor = QueryProcessor(engine)
        response = processor.process("바울의 선교 전략", query_id="t3", k=2)

        by_id = {c.tsu_id: c.final_score for c in response.top_k_results}
        assert by_id["TSU-NONE"] > by_id["TSU-LOW"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

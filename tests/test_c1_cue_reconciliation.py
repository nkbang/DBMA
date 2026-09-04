"""Targeted tests for scripts/c1_cue_reconciliation.py classification logic.

READ-ONLY reconciliation — these tests exercise `classify()` in isolation
(pure function, no file I/O) so Production/output files are never touched.
"""
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "c1_cue_reconciliation", REPO_ROOT / "scripts" / "c1_cue_reconciliation.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
classify = mod.classify

# build_c1_evidence() / run() read generated C1 evidence JSON under output/
# and NAE/corpus + NAE/review state that a fresh checkout / CI lacks. The
# pure classify() tests above stay active; only the file-backed ones skip.
_C1_EVIDENCE_INPUT = REPO_ROOT / "output" / "c1_cjk_contamination.json"
_needs_c1_evidence = pytest.mark.skipif(
    not _C1_EVIDENCE_INPUT.exists(),
    reason="requires generated output/c1_*.json evidence inputs (not in repo / CI)",
)


class TestClassify:
    def test_clear_with_no_c1_evidence_is_reconciled_clear(self):
        r = classify("TSU-X", "SCREENING_CLEAR", {})
        assert r["reconciliation_status"] == "RECONCILED_CLEAR"
        assert not r["discrepancy"]
        assert not r["human_review_required"]

    def test_c1_cjk_found_but_cue_clear_is_critical_discrepancy(self):
        r = classify("TSU-X", "SCREENING_CLEAR", {"CJK_FOREIGN_CONTAMINATION": [{"a": 1}]})
        assert r["reconciliation_status"] == "C1_CUE_DISCREPANCY"
        assert r["discrepancy"]
        assert r["human_review_required"]

    def test_cue_blocking_and_c1_agree_is_reconciled_exception(self):
        r = classify("TSU-X", "CJK_FOREIGN_CONTAMINATION", {"CJK_FOREIGN_CONTAMINATION": [{"a": 1}]})
        assert r["reconciliation_status"] == "RECONCILED_EXCEPTION"
        assert not r["discrepancy"]

    def test_cue_only_blocking_no_c1_evidence_is_reconciled_exception(self):
        r = classify("TSU-X", "NEEDS_CLAIM_REVIEW", {})
        assert r["reconciliation_status"] == "RECONCILED_EXCEPTION"

    def test_theological_weakening_always_routes_to_human_review(self):
        r = classify("TSU-X", "SCREENING_CLEAR", {"THEOLOGICAL_WEAKENING": [{}]})
        assert r["reconciliation_status"] == "HUMAN_THEOLOGICAL_REVIEW_REQUIRED"
        assert r["human_review_required"]
        assert r["discrepancy"]  # CUE said clear, C1 found weakening

    def test_semantic_duplicate_not_auto_approved(self):
        r = classify("TSU-X", "SCREENING_CLEAR", {"SEMANTIC_DUPLICATE": [{}]})
        assert r["reconciliation_status"] == "HUMAN_THEOLOGICAL_REVIEW_REQUIRED"
        assert r["human_review_required"]

    def test_qa_flag_nonblocking_stays_separate_from_clear(self):
        r = classify("TSU-X", "QA_FLAG_NONBLOCKING", {})
        assert r["reconciliation_status"] == "RECONCILED_QA"

    def test_informational_only_evidence_does_not_block_clear(self):
        """OCR/boundary/adjacent-overlap 등 informational 카테고리만 있는
        경우, instruction 4.5/4.6에 따라 자동으로 defect 판정하지 않는다."""
        r = classify("TSU-X", "SCREENING_CLEAR", {"OCR_ARTIFACT": [{}], "BOUNDARY_TRUNCATED": [{}]})
        assert r["reconciliation_status"] == "RECONCILED_CLEAR"
        assert not r["discrepancy"]
        assert r["c1_has_informational_evidence"]
        assert not r["c1_has_blocking_evidence"]


@_needs_c1_evidence
class TestBuildC1Evidence:
    def test_loads_without_error_and_covers_expected_categories(self):
        ev = mod.build_c1_evidence()
        assert isinstance(ev, dict)
        assert len(ev) > 0
        all_categories = {cat for v in ev.values() for cat in v.keys()}
        expected = {
            "CJK_FOREIGN_CONTAMINATION", "EXACT_DUPLICATE", "SEMANTIC_DUPLICATE",
            "ADJACENT_CONTEXT_OVERLAP", "THEOLOGICAL_WEAKENING", "OCR_ARTIFACT",
            "BOUNDARY_TRUNCATED", "SCRIPTURE_METADATA_GAP_WITH_IMPLICIT_REF",
        }
        assert expected.issubset(all_categories)

    def test_hedge_distortion_tsu_present(self):
        ev = mod.build_c1_evidence()
        assert "TSU-0001756" in ev
        assert "THEOLOGICAL_WEAKENING" in ev["TSU-0001756"]


@_needs_c1_evidence
class TestRunProducesNoProductionMutation:
    def test_run_does_not_touch_production_files(self, tmp_path):
        import json
        from pathlib import Path as P

        dagg_path = P("NAE/corpus/tsu/Dagg_Church_Order/tsu.json")
        hiscox_path = P("NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json")
        eq_path = P("NAE/review/human/exception_queue.json")
        decisions_dir = P("NAE/review/human/decisions")

        before = {
            "dagg": dagg_path.read_bytes(),
            "hiscox": hiscox_path.read_bytes(),
            "eq": eq_path.read_bytes(),
            "decisions_count": len(list(decisions_dir.glob("*.json"))),
        }

        result = mod.run()
        assert "records" in result
        assert "summary" in result

        assert dagg_path.read_bytes() == before["dagg"]
        assert hiscox_path.read_bytes() == before["hiscox"]
        assert eq_path.read_bytes() == before["eq"]
        assert len(list(decisions_dir.glob("*.json"))) == before["decisions_count"]

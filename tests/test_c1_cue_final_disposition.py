"""Targeted tests for scripts/c1_cue_final_disposition.py.

READ-ONLY — verifies the 1,601 candidate pool is partitioned into
FINAL_HUMAN_REVIEW_CANDIDATE / HUMAN_REVIEW_REQUIRED / Hiscox-pending
without loss or double-count, and that no Production file is mutated.
"""
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "c1_cue_final_disposition", REPO_ROOT / "scripts" / "c1_cue_final_disposition.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

# TestNoProductionMutation reads generated disposition artifacts under
# output/ (and NAE/corpus, NAE/review state) that a fresh checkout / CI
# does not have. Skip rather than fail on an environment gap unrelated to
# the code under test.
_DISPOSITION_ARTIFACT = REPO_ROOT / "output" / "final_human_review_candidate.json"


class TestPartitionIntegrity:
    def test_1601_candidates_partition_without_loss_or_overlap(self):
        clear_ids, qa_only_ids = mod.load_1601_candidates()
        candidates_1601 = clear_ids | qa_only_ids
        assert len(candidates_1601) == 1601
        assert clear_ids & qa_only_ids == set()

    def test_clear_and_qa_never_merged(self):
        clear_ids, qa_only_ids = mod.load_1601_candidates()
        assert clear_ids.isdisjoint(qa_only_ids)


@pytest.mark.skipif(
    not _DISPOSITION_ARTIFACT.exists(),
    reason="requires generated output/*.json disposition artifacts (not in repo / CI)",
)
class TestNoProductionMutation:
    def test_run_main_does_not_touch_production_or_review_state(self):
        dagg_path = REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json"
        hiscox_path = REPO_ROOT / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json"
        eq_path = REPO_ROOT / "NAE/review/human/exception_queue.json"
        screening_state_path = REPO_ROOT / "NAE/review/human/screening_state.json"
        batch_state_path = REPO_ROOT / "NAE/review/human/batch_state.json"

        before = {p: p.read_bytes() for p in (dagg_path, hiscox_path, eq_path, screening_state_path, batch_state_path)}

        mod.main()

        for p, content in before.items():
            assert p.read_bytes() == content, f"{p} was mutated"

    def test_output_files_partition_correctly(self):
        final = json.loads((REPO_ROOT / "output/final_human_review_candidate.json").read_text(encoding="utf-8"))
        human_review = json.loads((REPO_ROOT / "output/human_review_required.json").read_text(encoding="utf-8"))
        hiscox = json.loads((REPO_ROOT / "output/hiscox_cue_forensic_package.json").read_text(encoding="utf-8"))

        final_ids = set(final["screening_clear"]["tsu_ids"]) | set(final["qa_flag_nonblocking"]["tsu_ids"])
        hr_ids = (
            set(human_review["exact_duplicate_discrepancy"]["tsu_ids"])
            | set(human_review["theological_review_required"]["tsu_ids"])
            | set(human_review["pre_existing_unresolved_exception"]["tsu_ids"])
        )
        hiscox_ids = {r["tsu_id"] for r in hiscox["records"]}

        assert final["total"] == len(final_ids)
        assert human_review["total"] == len(hr_ids)
        assert hiscox["total"] == len(hiscox_ids)

        # 세 그룹은 서로 겹치지 않아야 한다(1,601을 정확히 분할)
        assert final_ids & hr_ids == set()
        assert final_ids & hiscox_ids == set()
        assert hr_ids & hiscox_ids == set()

        clear_ids, qa_only_ids = mod.load_1601_candidates()
        assert final_ids | hr_ids | hiscox_ids == (clear_ids | qa_only_ids)

    def test_pre_existing_unresolved_exceptions_excluded_from_final(self):
        """회귀 방지: nae_screening_sweep.py의 기계적 검사는 exception_queue
        의 기존(이번 스윕 이전) unresolved 항목을 교차검증하지 않으므로,
        Batch 2 backfill(READY_FOR_HUMAN_REVIEW)이나 STRUCTURAL_EXCEPTION
        같은 기존 미해결 예외가 최종 승인 후보에 섞여 들어가면 안 된다."""
        final = json.loads((REPO_ROOT / "output/final_human_review_candidate.json").read_text(encoding="utf-8"))
        final_ids = set(final["screening_clear"]["tsu_ids"]) | set(final["qa_flag_nonblocking"]["tsu_ids"])
        known_conflicts = {"TSU-0000250", "TSU-0000253", "TSU-0000255", "TSU-0000256", "TSU-0000265", "TSU-0000271"}
        assert final_ids & known_conflicts == set()

        human_review = json.loads((REPO_ROOT / "output/human_review_required.json").read_text(encoding="utf-8"))
        assert set(human_review["pre_existing_unresolved_exception"]["tsu_ids"]) == known_conflicts

    def test_hiscox_package_marked_not_approved(self):
        hiscox = json.loads((REPO_ROOT / "output/hiscox_cue_forensic_package.json").read_text(encoding="utf-8"))
        assert "NOT APPROVED" in hiscox["status"]
        for r in hiscox["records"]:
            assert "NOT_PERFORMED" in r["c1_independent_verification"]

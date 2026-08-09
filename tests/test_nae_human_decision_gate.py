"""Tests for NAE/review/human/decision_gate.py
(NAE-HUMAN-DECISION-GATE-PILOT-IMPLEMENTATION-001).

All tests use tmp_path / in-memory objects. Production TSU
(NAE/corpus/tsu/) and the real requests/decisions directories are never
written to by this suite except where explicitly targeted with tmp_path.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from NAE.review.human import decision_gate as dg
from NAE.review.human.schema import PILOT_TSU_IDS


class TestRequestGeneration:
    def test_build_requests_returns_10(self):
        requests = dg.build_requests()
        assert len(requests) == 10

    def test_build_requests_covers_exact_pilot_ids(self):
        requests = dg.build_requests()
        assert {r.tsu_id for r in requests} == PILOT_TSU_IDS

    def test_requests_do_not_add_or_replace_tsu(self):
        """Pilot 10건 외 TSU가 섞여 들어가지 않는지 확인(재선정/교체 금지)."""
        requests = dg.build_requests()
        for r in requests:
            assert r.tsu_id in PILOT_TSU_IDS

    def test_write_requests_creates_file(self, tmp_path):
        requests = dg.build_requests()
        path = dg.write_requests(requests, directory=tmp_path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["requests"]) == 10


class TestQuestionCompleteness:
    def test_every_request_has_at_least_3_questions(self):
        for r in dg.build_requests():
            assert len(r.review_questions) >= 3

    def test_first_three_questions_are_q1_q2_q3(self):
        for r in dg.build_requests():
            codes = [q.code for q in r.review_questions[:3]]
            assert codes == ["Q1", "Q2", "Q3"]

    def test_q4_only_present_when_concerning_flags_exist(self):
        for r in dg.build_requests():
            has_q4 = any(q.code == "Q4" for q in r.review_questions)
            concerning = [f for f in r.flags if f != "NO_OBJECTION"]
            assert has_q4 == bool(concerning)

    def test_no_more_than_4_questions(self):
        for r in dg.build_requests():
            assert len(r.review_questions) <= 4


class TestHighAttention:
    def test_high_attention_set_matches_spec(self):
        assert dg.HIGH_ATTENTION_TSU_IDS == {
            "TSU-0003661", "TSU-0003893", "TSU-0003525", "TSU-0000330",
        }

    def test_every_high_attention_tsu_has_a_reason(self):
        for tsu_id in dg.HIGH_ATTENTION_TSU_IDS:
            assert tsu_id in dg.HIGH_ATTENTION_REASONS
            assert len(dg.HIGH_ATTENTION_REASONS[tsu_id]) > 0


class TestDecisionVocabularyValidation:
    def test_valid_answers_are_exactly_a_r_c(self):
        assert dg.VALID_ANSWERS == {"A", "R", "C"}

    def test_valid_decision_entry_parses(self):
        entry = {"gate_id": "GATE-TSU-0000713", "tsu_id": "TSU-0000713",
                  "reviewer_id": "pastor-1", "answers": {"Q1": "A", "Q2": "A", "Q3": "A"}}
        record = dg._validate_decision_entry(entry)
        assert record.tsu_id == "TSU-0000713"

    def test_invalid_answer_value_rejected(self):
        entry = {"gate_id": "g", "tsu_id": "TSU-0000713", "reviewer_id": "p1",
                  "answers": {"Q1": "MAYBE"}}
        with pytest.raises(dg.DecisionError):
            dg._validate_decision_entry(entry)

    def test_missing_reviewer_id_rejected(self):
        entry = {"gate_id": "g", "tsu_id": "TSU-0000713", "answers": {"Q1": "A"}}
        with pytest.raises(dg.DecisionError):
            dg._validate_decision_entry(entry)

    def test_missing_answers_rejected(self):
        entry = {"gate_id": "g", "tsu_id": "TSU-0000713", "reviewer_id": "p1"}
        with pytest.raises(dg.DecisionError):
            dg._validate_decision_entry(entry)


class TestPendingInitialState:
    def test_all_requests_start_pending(self):
        for r in dg.build_requests():
            assert r.decision_status == dg.PENDING

    def test_pending_constant_value(self):
        assert dg.PENDING == "PENDING"


class TestPromotionEligibility:
    def test_no_decision_not_eligible(self):
        assert dg.is_promotion_eligible(None) == dg.NOT_ELIGIBLE_NO_DECISION

    def test_reject_not_eligible(self):
        record = dg.HumanDecisionRecord(
            gate_id="g", tsu_id="TSU-0000713", reviewer_id="p1",
            answers={"Q1": "A", "Q2": "R", "Q3": "A"},
        )
        assert dg.is_promotion_eligible(record) == dg.NOT_ELIGIBLE_REJECTED

    def test_needs_context_not_eligible(self):
        record = dg.HumanDecisionRecord(
            gate_id="g", tsu_id="TSU-0000713", reviewer_id="p1",
            answers={"Q1": "A", "Q2": "C", "Q3": "A"},
        )
        assert dg.is_promotion_eligible(record) == dg.NOT_ELIGIBLE_NEEDS_CONTEXT

    def test_all_approve_is_eligible(self):
        record = dg.HumanDecisionRecord(
            gate_id="g", tsu_id="TSU-0000713", reviewer_id="p1",
            answers={"Q1": "A", "Q2": "A", "Q3": "A"},
        )
        assert dg.is_promotion_eligible(record) == dg.PROMOTION_ELIGIBLE

    def test_reject_takes_priority_over_needs_context(self):
        """R과 C가 섞이면 더 보수적인 REJECTED로 판정한다(승격 방지 우선)."""
        record = dg.HumanDecisionRecord(
            gate_id="g", tsu_id="TSU-0000713", reviewer_id="p1",
            answers={"Q1": "R", "Q2": "C", "Q3": "A"},
        )
        assert dg.is_promotion_eligible(record) == dg.NOT_ELIGIBLE_REJECTED


class TestNoActualPromotionCall:
    def test_decision_gate_module_never_imports_review_promotion(self):
        import inspect
        source = inspect.getsource(dg)
        import_lines = [l for l in source.splitlines() if l.strip().startswith(("import ", "from "))]
        assert not any("review_promotion" in line for line in import_lines)

    def test_is_promotion_eligible_returns_string_not_side_effect(self):
        record = dg.HumanDecisionRecord(
            gate_id="g", tsu_id="TSU-0000713", reviewer_id="p1",
            answers={"Q1": "A", "Q2": "A", "Q3": "A"},
        )
        result = dg.is_promotion_eligible(record)
        assert isinstance(result, str)


class TestNoQdrantNoEmbedding:
    def test_no_qdrant_or_ollama_import(self):
        import inspect
        import_lines = [
            l for l in inspect.getsource(dg).splitlines() if l.strip().startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines).lower()
        assert "qdrant" not in joined
        assert "ollama" not in joined


class TestProductionTsuWriteProhibition:
    def test_decision_gate_module_has_no_write_to_tsu_json(self):
        import inspect
        source = inspect.getsource(dg)
        assert "tsu.json" not in source

    def test_write_requests_only_writes_inside_given_directory(self, tmp_path):
        requests = dg.build_requests()
        path = dg.write_requests(requests, directory=tmp_path)
        assert str(path).startswith(str(tmp_path))

    def test_review_status_never_referenced_for_writing(self):
        import inspect
        source = inspect.getsource(dg)
        # review_status라는 문자열 자체가 아예 등장하지 않아야 함(이 모듈은
        # TSU review_status와 무관하게 순수 Human Decision만 다룸)
        assert "review_status" not in source


class TestRequestDecisionSeparation:
    def test_requests_and_decisions_are_different_directories(self):
        assert dg.REQUESTS_DIR != dg.DECISIONS_DIR
        assert dg.REQUESTS_DIR.name == "requests"
        assert dg.DECISIONS_DIR.name == "decisions"

    def test_load_decisions_returns_empty_when_directory_missing(self, tmp_path):
        result = dg.load_decisions(tmp_path / "nonexistent")
        assert result == []

    def test_load_decisions_parses_real_file(self, tmp_path):
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        payload = {"decisions": [
            {"gate_id": "g", "tsu_id": "TSU-0000713", "reviewer_id": "pastor-1",
             "answers": {"Q1": "A", "Q2": "A", "Q3": "A"}}
        ]}
        (decisions_dir / "batch1.json").write_text(json.dumps(payload), encoding="utf-8")
        results = dg.load_decisions(decisions_dir)
        assert len(results) == 1
        assert results[0].tsu_id == "TSU-0000713"

    def test_write_requests_never_touches_decisions_dir(self, tmp_path):
        requests_dir = tmp_path / "requests"
        decisions_dir = tmp_path / "decisions"
        dg.write_requests(dg.build_requests(), directory=requests_dir)
        assert not decisions_dir.exists()


class TestConcurrentWriterProtection:
    def test_write_requests_is_idempotent_overwrite_not_append(self, tmp_path):
        """동일 경로에 두 번 write_requests를 호출해도 파일이 깨지거나
        중복 누적되지 않는다(항상 새로 직렬화, append 아님)."""
        requests = dg.build_requests()
        path1 = dg.write_requests(requests, directory=tmp_path)
        path2 = dg.write_requests(requests, directory=tmp_path)
        assert path1 == path2
        data = json.loads(path1.read_text(encoding="utf-8"))
        assert len(data["requests"]) == 10  # 20건으로 누적되지 않음

    def test_existing_files_in_review_human_not_modified_by_this_module_import(self):
        """decision_gate 모듈을 import하는 것만으로 기존
        schema.py/intake.py/integrity.py/promotion.py 파일이 수정되지
        않아야 한다(신규 파일만 추가하는 원칙)."""
        import NAE.review.human.schema as schema_mod
        import NAE.review.human.intake as intake_mod
        before_schema = open(schema_mod.__file__, encoding="utf-8").read()
        before_intake = open(intake_mod.__file__, encoding="utf-8").read()
        import importlib
        importlib.reload(dg)
        after_schema = open(schema_mod.__file__, encoding="utf-8").read()
        after_intake = open(intake_mod.__file__, encoding="utf-8").read()
        assert before_schema == after_schema
        assert before_intake == after_intake


class TestHumanDecisionImmutability:
    def test_human_decision_record_is_frozen(self):
        record = dg.HumanDecisionRecord(
            gate_id="g", tsu_id="TSU-0000713", reviewer_id="p1", answers={"Q1": "A"},
        )
        with pytest.raises(Exception):
            record.reviewer_id = "someone-else"


class TestRegression:
    def test_pilot_reference_reused_not_duplicated(self):
        """decision_gate.py가 schema.PILOT_REFERENCE를 재사용하는지(별도
        10건을 새로 정의하지 않는지) 확인."""
        from NAE.review.human import schema
        requests = dg.build_requests()
        for r in requests:
            ref = schema.PILOT_REFERENCE_BY_ID[r.tsu_id]
            assert r.claim == ref["claim"]
            assert r.source_id == ref["source_id"]

    def test_gate_id_format(self):
        for r in dg.build_requests():
            assert r.gate_id == f"GATE-{r.tsu_id}"

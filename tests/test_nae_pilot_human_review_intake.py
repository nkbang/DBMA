"""Tests for NAE/review/human/{schema,intake,integrity,promotion}.py
(NAE-PILOT-HUMAN-REVIEW-001).

All tests use tmp_path / synthetic data — Production TSU
(NAE/corpus/tsu/) and the real review results file
(NAE/review/human/pilot_001_review_results.jsonl) are never written by
this suite except where explicitly noted as a read-only check.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from NAE.review.human import integrity, intake, promotion, schema

REF_DAGG = schema.PILOT_REFERENCE[0]  # TSU-0000713
REF_HISCOX = schema.PILOT_REFERENCE[5]  # TSU-0003524


def _valid_entry(**overrides):
    defaults = dict(
        tsu_id=REF_DAGG["tsu_id"], reviewer_id="rev-1", review_timestamp="2026-08-09T00:00:00+00:00",
        decision="VERIFY",
    )
    defaults.update(overrides)
    return defaults


class TestDecisionParsing:
    def test_verify_parsing(self):
        r = intake.validate_review_result(_valid_entry(decision="VERIFY"))
        assert r.decision == "VERIFY"

    def test_revise_parsing(self):
        r = intake.validate_review_result(_valid_entry(decision="REVISE", revised_claim="corrected claim text"))
        assert r.decision == "REVISE"
        assert r.revised_claim == "corrected claim text"

    def test_reject_parsing(self):
        r = intake.validate_review_result(_valid_entry(decision="REJECT"))
        assert r.decision == "REJECT"

    def test_hold_parsing(self):
        r = intake.validate_review_result(_valid_entry(decision="HOLD"))
        assert r.decision == "HOLD"


class TestValidationErrors:
    def test_invalid_decision_rejected(self):
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(_valid_entry(decision="APPROVED"))

    def test_missing_reviewer_rejected(self):
        entry = _valid_entry()
        del entry["reviewer_id"]
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(entry)

    def test_missing_revised_claim_for_revise_rejected(self):
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(_valid_entry(decision="REVISE"))

    def test_unknown_tsu_rejected(self):
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(_valid_entry(tsu_id="TSU-9999999"))

    def test_non_pilot_tsu_rejected(self):
        """Pilot 10건에 없는 실제 존재하는 TSU ID도 거부되어야 한다
        (10건 외 확장 금지)."""
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(_valid_entry(tsu_id="TSU-0000001"))

    def test_missing_decision_rejected(self):
        entry = _valid_entry()
        del entry["decision"]
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(entry)

    def test_missing_tsu_id_rejected(self):
        entry = _valid_entry()
        del entry["tsu_id"]
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(entry)

    def test_missing_review_timestamp_rejected(self):
        entry = _valid_entry()
        del entry["review_timestamp"]
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(entry)

    def test_reject_with_revised_claim_rejected(self):
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(_valid_entry(decision="REJECT", revised_claim="should not be here"))

    def test_hold_with_revised_doctrine_rejected(self):
        with pytest.raises(intake.IntakeError):
            intake.validate_review_result(_valid_entry(decision="HOLD", revised_doctrine="should not be here"))


class TestDuplicateAndConflict:
    def test_duplicate_identical_review_deduplicated(self, tmp_path):
        path = tmp_path / "results.jsonl"
        entry = _valid_entry()
        path.write_text(json.dumps(entry) + "\n" + json.dumps(entry) + "\n", encoding="utf-8")
        results, notes = intake.load_review_results(path)
        assert len(results) == 1
        assert notes  # duplicate로 기록됨

    def test_conflicting_review_raises(self, tmp_path):
        path = tmp_path / "results.jsonl"
        e1 = _valid_entry(decision="VERIFY", reviewer_id="rev-1")
        e2 = _valid_entry(decision="REJECT", reviewer_id="rev-2")
        path.write_text(json.dumps(e1) + "\n" + json.dumps(e2) + "\n", encoding="utf-8")
        with pytest.raises(intake.IntakeError):
            intake.load_review_results(path)

    def test_pending_preservation_when_file_missing(self, tmp_path):
        results, notes = intake.load_review_results(tmp_path / "does_not_exist.jsonl")
        assert results == []
        assert notes == []

    def test_pending_preservation_when_file_empty(self, tmp_path):
        path = tmp_path / "results.jsonl"
        path.write_text("", encoding="utf-8")
        results, notes = intake.load_review_results(path)
        assert results == []


class TestPromotionCandidateGeneration:
    def test_verify_promotion_candidate_generation(self):
        r = intake.validate_review_result(_valid_entry(decision="VERIFY"))
        prep = promotion.build_promotion_preparation([r])
        promo = prep.by_category(promotion.PROMOTION_CANDIDATE)
        assert len(promo) == 1
        assert promo[0].tsu_id == REF_DAGG["tsu_id"]

    def test_revise_candidate_generation(self):
        r = intake.validate_review_result(_valid_entry(decision="REVISE", revised_claim="fixed claim"))
        prep = promotion.build_promotion_preparation([r])
        revs = prep.by_category(promotion.REVISION_CANDIDATE)
        assert len(revs) == 1
        assert revs[0].revised_claim == "fixed claim"

    def test_reject_candidate_generation(self):
        r = intake.validate_review_result(_valid_entry(decision="REJECT"))
        prep = promotion.build_promotion_preparation([r])
        rejected = prep.by_category(promotion.REJECTED_CANDIDATE)
        assert len(rejected) == 1

    def test_hold_candidate_generation(self):
        r = intake.validate_review_result(_valid_entry(decision="HOLD"))
        prep = promotion.build_promotion_preparation([r])
        pending = prep.by_category(promotion.PENDING_CANDIDATE)
        assert any(c.tsu_id == REF_DAGG["tsu_id"] for c in pending)

    def test_unreviewed_pilot_tsu_defaults_to_pending(self):
        prep = promotion.build_promotion_preparation([])
        pending_ids = {c.tsu_id for c in prep.by_category(promotion.PENDING_CANDIDATE)}
        assert pending_ids == schema.PILOT_TSU_IDS

    def test_promotion_preparation_status_is_ready_for_promotion_review(self):
        prep = promotion.build_promotion_preparation([])
        assert prep.status == "READY_FOR_PROMOTION_REVIEW"

    def test_verify_does_not_set_review_status_anywhere(self):
        """PromotionCandidate 객체에 review_status 필드 자체가 없다 —
        VERIFY라도 이 레이어에서 review_status를 절대 결정/기록하지 않음."""
        r = intake.validate_review_result(_valid_entry(decision="VERIFY"))
        prep = promotion.build_promotion_preparation([r])
        candidate = prep.by_category(promotion.PROMOTION_CANDIDATE)[0]
        assert not hasattr(candidate, "review_status")


class TestIntegrityVerification:
    def _write_tsu(self, tmp_path, identifier, records):
        d = tmp_path / identifier
        d.mkdir(parents=True, exist_ok=True)
        (d / "tsu.json").write_text(json.dumps(records), encoding="utf-8")

    def _matching_record(self, ref, **overrides):
        rec = {
            "id": ref["tsu_id"], "source_id": ref["source_id"], "work_id": ref["work_id"],
            "edition_id": ref["edition_id"], "doctrine": ref["doctrine"], "claim": ref["claim"],
            "review_status": "generated",
            "metadata_provenance": {"crosswalk_id": ref["crosswalk_id"]},
        }
        rec.update(overrides)
        return rec

    def test_integrity_pass_when_matching(self, tmp_path):
        self._write_tsu(tmp_path, "Dagg_Church_Order", [self._matching_record(REF_DAGG)])
        self._write_tsu(tmp_path, "Hiscox_Standard_Manual", [self._matching_record(REF_HISCOX)])
        report = integrity.verify_pilot_integrity(tmp_path)
        # 나머지 8건은 tmp_path에 없으므로 missing으로 잡히는 게 정상 — 이 2건만 확인
        assert REF_DAGG["tsu_id"] not in [m.tsu_id for m in report.mismatches]
        assert REF_HISCOX["tsu_id"] not in [m.tsu_id for m in report.mismatches]

    def test_integrity_detects_claim_mismatch(self, tmp_path):
        self._write_tsu(tmp_path, "Dagg_Church_Order", [self._matching_record(REF_DAGG, claim="TAMPERED CLAIM")])
        report = integrity.verify_pilot_integrity(tmp_path)
        mismatch_fields = [m.field for m in report.mismatches if m.tsu_id == REF_DAGG["tsu_id"]]
        assert "claim" in mismatch_fields
        assert report.status == "BLOCKED"

    def test_integrity_detects_doctrine_mismatch(self, tmp_path):
        self._write_tsu(tmp_path, "Dagg_Church_Order", [self._matching_record(REF_DAGG, doctrine="Wrong")])
        report = integrity.verify_pilot_integrity(tmp_path)
        assert any(m.tsu_id == REF_DAGG["tsu_id"] and m.field == "doctrine" for m in report.mismatches)

    def test_integrity_detects_missing_tsu(self, tmp_path):
        (tmp_path / "Dagg_Church_Order").mkdir()
        (tmp_path / "Dagg_Church_Order" / "tsu.json").write_text("[]", encoding="utf-8")
        report = integrity.verify_pilot_integrity(tmp_path)
        assert REF_DAGG["tsu_id"] in report.missing_tsu_ids
        assert not report.ok

    def test_integrity_detects_non_generated_review_status(self, tmp_path):
        self._write_tsu(tmp_path, "Dagg_Church_Order", [self._matching_record(REF_DAGG, review_status="verified")])
        report = integrity.verify_pilot_integrity(tmp_path)
        assert REF_DAGG["tsu_id"] in report.non_generated_review_status
        assert not report.ok

    def test_integrity_detects_provenance_mismatch(self, tmp_path):
        rec = self._matching_record(REF_DAGG)
        rec["metadata_provenance"] = {"crosswalk_id": "WRONG-ID"}
        self._write_tsu(tmp_path, "Dagg_Church_Order", [rec])
        report = integrity.verify_pilot_integrity(tmp_path)
        assert any(m.field == "metadata_provenance.crosswalk_id" for m in report.mismatches)


class TestProductionImmutability:
    def test_intake_module_never_imports_write_capable_tsu_functions(self):
        import inspect
        from NAE.review.human import intake as intake_mod
        source = inspect.getsource(intake_mod)
        assert "write_text" not in source
        assert "json.dump(" not in source  # dump(obj, file) 형태의 쓰기 없음 — loads만 사용

    def test_integrity_module_is_read_only(self):
        import inspect
        from NAE.review.human import integrity as integrity_mod
        source = inspect.getsource(integrity_mod)
        assert "write_text" not in source
        assert "open(" not in source or "'w'" not in source

    def test_promotion_module_never_calls_review_promotion(self):
        """promotion.py는 review_promotion 모듈을 import하지 않는다 —
        docstring에서 이름을 언급(참조 설명)하는 것과 실제로 그 함수를
        호출하는 것은 다르다. import 부재로 "호출 불가능"함을 검증한다."""
        import NAE.review.human.promotion as promotion_mod
        assert not hasattr(promotion_mod, "promote_tsu_to_verified")
        assert "review_promotion" not in dir(promotion_mod)


class TestReviewGateImmutability:
    def test_real_production_review_gate_state_unchanged_by_import(self):
        """이 테스트 스위트를 import/실행하는 것만으로 실제 Production
        Review Gate 판정이 바뀌지 않아야 한다(읽기 전용 재확인). Pilot 001
        Promotion(1차 5건) + Remediation re-review 승인(2차 5건) 10건에
        4,107건 확장 Batch 1의 첫 10건(TSU-0000006~0000015)이 더해져
        총 20건이 verified 상태인 것이 현재 Production의 정상 상태이며,
        import가 이 값을 바꾸지 않는다는 것이 검증 대상."""
        from NAE.pipeline.index import indexer
        summary = indexer.index_all(dry_run=True)
        assert summary["indexed"] == 260


class TestNoQdrantNoEmbeddingGuarantee:
    def test_no_module_in_review_human_imports_qdrant_client(self):
        """실제 import 구문에 qdrant_client/ollama가 없는지 확인한다 —
        상수 이름/주석에 "qdrant"라는 단어가 등장하는 것(예:
        SAFETY_GATES["qdrant_write"]=False, 오히려 금지를 명시하는 것)은
        허용된다. 실제 import line만 검사한다."""
        import inspect
        from NAE.review.human import intake as m1, integrity as m2, promotion as m3, schema as m4
        for mod in (m1, m2, m3, m4):
            import_lines = [
                line for line in inspect.getsource(mod).splitlines()
                if line.strip().startswith(("import ", "from "))
            ]
            joined = "\n".join(import_lines).lower()
            assert "qdrant" not in joined
            assert "ollama" not in joined


class TestRegression:
    def test_pilot_reference_has_exactly_10_entries(self):
        assert len(schema.PILOT_REFERENCE) == 10

    def test_pilot_reference_5_dagg_5_hiscox(self):
        dagg = [r for r in schema.PILOT_REFERENCE if r["source_id"] == "BAP-CHURCH-DAGG-001"]
        hiscox = [r for r in schema.PILOT_REFERENCE if r["source_id"] == "BAP-CHURCH-HISCOX"]
        assert len(dagg) == 5
        assert len(hiscox) == 5

    def test_valid_decisions_exactly_four(self):
        assert schema.VALID_DECISIONS == {"VERIFY", "REVISE", "REJECT", "HOLD"}

    def test_human_review_result_is_frozen(self):
        r = intake.validate_review_result(_valid_entry())
        with pytest.raises(Exception):
            r.decision = "REJECT"

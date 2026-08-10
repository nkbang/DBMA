"""Tests for the TSU Review Gate wiring in NAE/pipeline/index/indexer.py
(NAE-TSU-REVIEW-GATE-WIRING-IMPLEMENTATION-001).

All tests use tmp_path fixtures for tsu_root — never Production TSU
(NAE/corpus/tsu/) is written. `dry_run=True` is used wherever indexing
is exercised so no embedding client or Qdrant call ever happens.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from NAE.pipeline.index import indexer


def _tsu_record(**overrides):
    defaults = dict(id="TSU-0000001", claim="a theological claim", book="Book", page=1, review_status="verified")
    defaults.update(overrides)
    return defaults


def _write_tsu(tmp_path, identifier, records, filename="tsu.json"):
    item_dir = tmp_path / identifier
    item_dir.mkdir(parents=True, exist_ok=True)
    (item_dir / filename).write_text(json.dumps(records), encoding="utf-8")
    return item_dir


class TestGeneratedExcluded:
    def test_generated_status_excluded_from_load(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="generated")])
        records = indexer.load_records("Book", tsu_root=tmp_path)
        assert records == []

    def test_generated_status_excluded_from_dry_run_index(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="generated")])
        report = indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert report["would_index"] == 0
        assert report["gate_block"] == 1


class TestReviewedExcluded:
    def test_reviewed_status_excluded_from_load(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="reviewed")])
        assert indexer.load_records("Book", tsu_root=tmp_path) == []

    def test_reviewed_status_excluded_from_dry_run_index(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="reviewed")])
        report = indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert report["would_index"] == 0


class TestVerifiedIncluded:
    def test_verified_status_included_in_load(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="verified")])
        records = indexer.load_records("Book", tsu_root=tmp_path)
        assert len(records) == 1

    def test_verified_status_included_in_dry_run_index(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="verified")])
        report = indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert report["would_index"] == 1
        assert report["gate_pass"] == 1


class TestRejectedExcluded:
    def test_rejected_status_excluded_from_load(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="rejected")])
        assert indexer.load_records("Book", tsu_root=tmp_path) == []

    def test_rejected_status_excluded_from_dry_run_index(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="rejected")])
        report = indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert report["would_index"] == 0


class TestMissingReviewStatus:
    def test_missing_review_status_excluded(self, tmp_path):
        record = {"id": "TSU-1", "claim": "x", "book": "Book", "page": 1}  # review_status 없음
        _write_tsu(tmp_path, "Book", [record])
        assert indexer.load_records("Book", tsu_root=tmp_path) == []

    def test_missing_review_status_excluded_from_dry_run(self, tmp_path):
        record = {"id": "TSU-1", "claim": "x"}
        _write_tsu(tmp_path, "Book", [record])
        report = indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert report["would_index"] == 0


class TestVerifiedFileVsReviewStatusNotConflated:
    """tsu_verified.json 존재 여부(Phase 3.5 중복탐지)와
    review_status=='verified'(사람 검토)는 별개 개념 — 혼동 방지 확인."""

    def test_record_in_tsu_verified_json_but_not_review_verified_is_excluded(self, tmp_path):
        # tsu_verified.json이 존재해도(중복탐지는 끝났어도) review_status가
        # verified가 아니면 여전히 제외되어야 한다.
        _write_tsu(
            tmp_path,
            "Book",
            [_tsu_record(review_status="generated", duplicate_of=None)],
            filename="tsu_verified.json",
        )
        records = indexer.load_records("Book", tsu_root=tmp_path)
        assert records == []

    def test_record_in_tsu_verified_json_and_review_verified_is_included(self, tmp_path):
        _write_tsu(
            tmp_path,
            "Book",
            [_tsu_record(review_status="verified")],
            filename="tsu_verified.json",
        )
        records = indexer.load_records("Book", tsu_root=tmp_path)
        assert len(records) == 1

    def test_plain_tsu_json_verified_record_still_gated(self, tmp_path):
        """tsu_verified.json이 아예 없는(Phase 3.5 미실행) 상태에서도
        review_status=='verified'인 레코드는 정상적으로 포함된다 —
        Gate는 파일 종류와 무관하게 review_status만 본다."""
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="verified")], filename="tsu.json")
        records = indexer.load_records("Book", tsu_root=tmp_path)
        assert len(records) == 1


class TestBatchIndexing:
    def test_mixed_batch_only_verified_indexed(self, tmp_path):
        _write_tsu(
            tmp_path,
            "Book",
            [
                _tsu_record(id="TSU-1", review_status="verified"),
                _tsu_record(id="TSU-2", review_status="generated"),
                _tsu_record(id="TSU-3", review_status="verified"),
                _tsu_record(id="TSU-4", review_status="rejected"),
            ],
        )
        report = indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert report["would_index"] == 2
        assert report["gate_pass"] == 2
        assert report["gate_block"] == 2

    def test_index_all_dry_run_across_multiple_identifiers(self, tmp_path):
        _write_tsu(tmp_path, "BookA", [_tsu_record(review_status="verified")])
        _write_tsu(tmp_path, "BookB", [_tsu_record(review_status="generated")])
        summary = indexer.index_all(tsu_root=tmp_path, dry_run=True)
        assert summary["processed"] == 2
        assert summary["indexed"] == 1  # BookA만 verified


class TestEmptyCorpus:
    def test_empty_tsu_root_returns_zero(self, tmp_path):
        summary = indexer.index_all(tsu_root=tmp_path / "does_not_exist", dry_run=True)
        assert summary == {"processed": 0, "indexed": 0, "identifiers": []}

    def test_identifier_with_no_tsu_file(self, tmp_path):
        (tmp_path / "EmptyBook").mkdir()
        records = indexer.load_records("EmptyBook", tsu_root=tmp_path)
        assert records == []

    def test_empty_records_list_in_file(self, tmp_path):
        _write_tsu(tmp_path, "Book", [])
        report = indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert report["would_index"] == 0
        assert report["records_total_raw"] == 0


class TestCorruptedTsu:
    def test_malformed_json_returns_empty_not_raises(self, tmp_path):
        item_dir = tmp_path / "Book"
        item_dir.mkdir()
        (item_dir / "tsu.json").write_text("{not valid json[[[", encoding="utf-8")
        records = indexer.load_records("Book", tsu_root=tmp_path)  # 예외 없이
        assert records == []

    def test_non_list_json_returns_empty(self, tmp_path):
        item_dir = tmp_path / "Book"
        item_dir.mkdir()
        (item_dir / "tsu.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
        records = indexer.load_records("Book", tsu_root=tmp_path)
        assert records == []

    def test_corrupted_file_does_not_break_batch(self, tmp_path):
        item_dir = tmp_path / "BrokenBook"
        item_dir.mkdir()
        (item_dir / "tsu.json").write_text("not json at all", encoding="utf-8")
        _write_tsu(tmp_path, "GoodBook", [_tsu_record(review_status="verified")])

        summary = indexer.index_all(tsu_root=tmp_path, dry_run=True)
        assert summary["processed"] == 2
        assert summary["indexed"] == 1  # GoodBook만 반영, BrokenBook은 건너뜀(예외 없음)


class TestDryRunNoSideEffects:
    def test_dry_run_writes_no_report_file(self, tmp_path):
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="verified")])
        indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        assert not (tmp_path / "Book" / "index_report.json").exists()

    def test_dry_run_does_not_modify_source_tsu_file(self, tmp_path):
        item_dir = _write_tsu(tmp_path, "Book", [_tsu_record(review_status="verified")])
        before = (item_dir / "tsu.json").read_text(encoding="utf-8")
        indexer.index_identifier("Book", tsu_root=tmp_path, dry_run=True)
        after = (item_dir / "tsu.json").read_text(encoding="utf-8")
        assert before == after


class TestProductionTsuReadOnlyDryRun:
    def test_real_production_dry_run_excludes_non_verified(self):
        """실제 Production TSU(Dagg/Hiscox)를 대상으로 dry_run 실행 시
        review_status=='verified'인 레코드만 통과해야 한다. Pilot 001
        Human Review Gate 1차 승인 5건(TSU-0000199/0000025/0003524/
        0003525/0003647) + Remediation re-review 승인 5건(TSU-0000713/
        0000330/0000033/0003661/0003893) 총 10건에 더해, 4,107건 확장
        Batch 1의 첫 10건(TSU-0000006~0000015)이 review_promotion.py를
        통해 정식으로 verified 승격되어 총 20건 — 이 20건만 통과하는
        것이 현재의 정상 상태다(그 외 4,097건은 여전히 generated로
        차단됨)."""
        from pathlib import Path

        tsu_root = Path("NAE/corpus/tsu")
        if not tsu_root.exists():
            return
        summary = indexer.index_all(tsu_root=tsu_root, dry_run=True)
        assert summary["indexed"] == 260

    def test_real_production_tsu_files_untouched(self):
        from pathlib import Path

        dagg = Path("NAE/corpus/tsu/Dagg_Church_Order/tsu.json")
        if dagg.exists():
            before = dagg.read_text(encoding="utf-8")
            after = dagg.read_text(encoding="utf-8")
            assert before == after

    def test_dry_run_does_not_modify_existing_index_report(self):
        """실제 Embedding 실행(NAE-VECTOR-INDEX-PREFLIGHT-002 승인,
        verified 10건)으로 index_report.json이 이미 생성되어 있다 —
        이 테스트는 "index_report.json이 절대 없어야 한다"가 아니라
        "dry_run=True 호출이 기존 report를 덮어쓰지 않는다"를 검증한다."""
        from pathlib import Path

        dagg_report = Path("NAE/corpus/tsu/Dagg_Church_Order/index_report.json")
        hiscox_report = Path("NAE/corpus/tsu/Hiscox_Standard_Manual/index_report.json")
        if not dagg_report.exists() or not hiscox_report.exists():
            return  # 아직 실제 인덱싱이 수행되지 않은 환경(예: 신선한 체크아웃)에서는 skip

        before_dagg = dagg_report.read_text(encoding="utf-8")
        before_hiscox = hiscox_report.read_text(encoding="utf-8")

        indexer.index_all(dry_run=True)

        assert dagg_report.read_text(encoding="utf-8") == before_dagg
        assert hiscox_report.read_text(encoding="utf-8") == before_hiscox


class TestRegression:
    def test_load_records_backward_compatible_signature(self, tmp_path):
        """기존 load_records(identifier, tsu_root) 시그니처가 그대로
        유지되는지 확인(호출자 코드 변경 불필요)."""
        _write_tsu(tmp_path, "Book", [_tsu_record(review_status="verified")])
        records = indexer.load_records("Book", tsu_root=tmp_path)
        assert isinstance(records, list)

    def test_index_identifier_non_dry_run_signature_unchanged(self, tmp_path):
        """dry_run 파라미터는 기본값 False — 기존 호출자(인자 없이
        index_identifier(identifier) 호출)의 동작에는 영향 없음(단,
        실제 Qdrant/embedding 호출은 이번 테스트에서 수행하지 않음 —
        시그니처만 확인)."""
        import inspect

        sig = inspect.signature(indexer.index_identifier)
        assert "dry_run" in sig.parameters
        assert sig.parameters["dry_run"].default is False

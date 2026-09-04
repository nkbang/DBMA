"""Tests for NAE/review/human/batch_manager.py — batch selection logic
(NAE-TSU-4107-EXPANSION-001, Batch 23 offset-bug fix).

All tests use tmp_path synthetic TSU data, monkeypatching
`batch_manager.CORPUS_ROOT` — Production TSU files are never read or
written by this suite.
"""
import json

import pytest

from NAE.review.human import batch_manager as bm


def _write_tsu(tmp_path, identifier, records):
    d = tmp_path / "tsu" / identifier
    d.mkdir(parents=True, exist_ok=True)
    (d / "tsu.json").write_text(json.dumps(records), encoding="utf-8")


def _record(tid, review_status="generated"):
    return {"id": tid, "review_status": review_status, "doctrine": "Baptism", "claim": "x", "source_text": "y"}


@pytest.fixture()
def synthetic_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(bm, "CORPUS_ROOT", tmp_path)
    return tmp_path


class TestGetBatchRecordsAlwaysTakesPoolFront:
    def test_batch_number_does_not_offset_into_pool(self, synthetic_corpus):
        """핵심 회귀 방지: batch_number가 커져도 pool이 그만큼 줄어든
        상태라면 항상 pool의 맨 앞을 반환해야 한다(과거에는
        (batch_number-1)*100 offset을 써서 pool보다 커지면 빈 결과를
        반환하거나 에러가 났다)."""
        # PILOT_TSU_IDS(TSU-0000025 등)와 겹치지 않도록 5000번대 사용
        records = [_record(f"TSU-{i:07d}") for i in range(5001, 5051)]  # 50건
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        # 과거 버그라면 batch_number=23, batch_size=100일 때
        # offset=2200이라 무조건 빈 리스트가 됐다. 새 로직은 pool 크기만
        # 본다.
        got = bm.get_batch_records(batch_number=23, batch_size=100)
        assert len(got) == 50
        assert got[0]["id"] == "TSU-0005001"
        assert got[-1]["id"] == "TSU-0005050"

    def test_different_batch_numbers_return_identical_pool_front(self, synthetic_corpus):
        records = [_record(f"TSU-{i:07d}") for i in range(1, 21)]
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        batch1 = bm.get_batch_records(batch_number=1, batch_size=10)
        batch99 = bm.get_batch_records(batch_number=99, batch_size=10)
        assert [r["id"] for r in batch1] == [r["id"] for r in batch99]

    def test_batch_number_must_be_positive(self, synthetic_corpus):
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", [])
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])
        with pytest.raises(ValueError):
            bm.get_batch_records(batch_number=0)


class TestPromotedRecordsNeverReappear:
    def test_verified_records_excluded_from_next_batch(self, synthetic_corpus):
        """이미 Promotion된(review_status != 'generated') TSU는 다음
        배치 selection에 다시 나타나지 않는다."""
        records = [_record(f"TSU-{i:07d}") for i in range(1, 11)]
        # 처음 5건은 이미 승격되었다고 가정
        for r in records[:5]:
            r["review_status"] = "verified"
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        got = bm.get_batch_records(batch_number=1, batch_size=100)
        got_ids = {r["id"] for r in got}
        assert got_ids == {f"TSU-{i:07d}" for i in range(6, 11)}
        assert "TSU-0000001" not in got_ids

    def test_rejected_records_excluded(self, synthetic_corpus):
        records = [_record(f"TSU-{i:07d}") for i in range(1, 6)]
        records[0]["review_status"] = "rejected"
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        got = bm.get_batch_records(batch_number=1, batch_size=100)
        assert "TSU-0000001" not in {r["id"] for r in got}
        assert len(got) == 4


class TestEmptyPool:
    def test_empty_pool_returns_empty_list_not_error(self, synthetic_corpus):
        """pool이 완전히 소진된 경우 get_batch_records 자체는 빈 리스트를
        반환한다 — 에러(ValueError)는 generate_batch()에서만 발생."""
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", [])
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])
        got = bm.get_batch_records(batch_number=1, batch_size=100)
        assert got == []

    def test_generate_batch_raises_on_empty_pool(self, synthetic_corpus, monkeypatch, tmp_path):
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", [])
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])
        monkeypatch.setattr(bm, "BATCH_STATE_PATH", tmp_path / "batch_state.json")
        with pytest.raises(ValueError):
            bm.generate_batch(1)


class TestTotalBatchesUnaffected:
    def test_total_batches_still_computed_from_current_pool(self, synthetic_corpus):
        records = [_record(f"TSU-{i:07d}") for i in range(1, 251)]  # 250건
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])
        assert bm.total_batches(batch_size=100) == 3  # ceil(250/100)


class TestScreeningCursor:
    """screening_cursor: Promotion과 무관하게 각 TSU를 정확히 한 번만
    screening하기 위한 별도 persistent state (screening_state.json)."""

    def test_no_promotion_between_batches_still_advances(self, synthetic_corpus, tmp_path, monkeypatch):
        """Promotion 없이 연속 호출해도 Batch 24 -> 25 -> 26이 서로 다른
        TSU를 선택해야 한다 — 과거 runaway-loop 사고의 재발 방지 회귀
        테스트."""
        monkeypatch.setattr(bm, "SCREENING_STATE_PATH", tmp_path / "screening_state.json")
        records = [_record(f"TSU-{i:07d}") for i in range(5001, 5031)]  # 30건
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        batch1 = bm.get_screening_batch(batch_size=10)
        batch2 = bm.get_screening_batch(batch_size=10)
        batch3 = bm.get_screening_batch(batch_size=10)

        ids1 = [r["id"] for r in batch1]
        ids2 = [r["id"] for r in batch2]
        ids3 = [r["id"] for r in batch3]
        assert ids1 == [f"TSU-{i:07d}" for i in range(5001, 5011)]
        assert ids2 == [f"TSU-{i:07d}" for i in range(5011, 5021)]
        assert ids3 == [f"TSU-{i:07d}" for i in range(5021, 5031)]
        assert set(ids1) & set(ids2) == set()
        assert set(ids2) & set(ids3) == set()

    def test_same_tsu_never_reappears_across_screening_batches(self, synthetic_corpus, tmp_path, monkeypatch):
        monkeypatch.setattr(bm, "SCREENING_STATE_PATH", tmp_path / "screening_state.json")
        records = [_record(f"TSU-{i:07d}") for i in range(1, 21)]
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        all_seen: list[str] = []
        while True:
            batch = bm.get_screening_batch(batch_size=7)
            if not batch:
                break
            all_seen.extend(r["id"] for r in batch)

        assert len(all_seen) == len(set(all_seen)) == 20

    def test_cursor_persists_across_restart(self, synthetic_corpus, tmp_path, monkeypatch):
        """프로세스 재시작(새 monkeypatch 적용이 아닌, 같은 경로를 다시
        읽는 상황)을 흉내낸다 — cursor는 디스크에 저장되므로 새로 함수를
        호출해도 이미 screening된 TSU를 다시 반환하지 않는다."""
        state_path = tmp_path / "screening_state.json"
        monkeypatch.setattr(bm, "SCREENING_STATE_PATH", state_path)
        records = [_record(f"TSU-{i:07d}") for i in range(1, 11)]
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        first = bm.get_screening_batch(batch_size=5)
        assert state_path.exists()

        # "재시작": 상태는 그대로 디스크에 남아있고, 새로 호출만 한다.
        second = bm.get_screening_batch(batch_size=5)
        assert {r["id"] for r in first} & {r["id"] for r in second} == set()
        assert len(second) == 5

    def test_pool_exhausted_returns_empty_and_terminates(self, synthetic_corpus, tmp_path, monkeypatch):
        monkeypatch.setattr(bm, "SCREENING_STATE_PATH", tmp_path / "screening_state.json")
        records = [_record(f"TSU-{i:07d}") for i in range(1, 6)]  # 5건
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        got1 = bm.get_screening_batch(batch_size=10)
        assert len(got1) == 5
        got2 = bm.get_screening_batch(batch_size=10)
        assert got2 == []

    def test_promotion_does_not_reset_or_affect_cursor(self, synthetic_corpus, tmp_path, monkeypatch):
        """Promotion(= review_status 변경)이 screening cursor 자체에는
        영향을 주지 않아야 한다 — screening 완료 여부와 promotion 완료
        여부는 별개 상태."""
        monkeypatch.setattr(bm, "SCREENING_STATE_PATH", tmp_path / "screening_state.json")
        records = [_record(f"TSU-{i:07d}") for i in range(1, 11)]
        _write_tsu(synthetic_corpus, "Dagg_Church_Order", records)
        _write_tsu(synthetic_corpus, "Hiscox_Standard_Manual", [])

        first = bm.get_screening_batch(batch_size=5)
        assert [r["id"] for r in first] == [f"TSU-{i:07d}" for i in range(1, 6)]

        # 이제 그 5건 중 3건이 Promotion되어 review_status가 바뀌었다고
        # 가정(pool에서 빠짐).
        path = synthetic_corpus / "tsu" / "Dagg_Church_Order" / "tsu.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data[:3]:
            r["review_status"] = "verified"
        path.write_text(json.dumps(data), encoding="utf-8")

        second = bm.get_screening_batch(batch_size=5)
        # 다음 screening은 여전히 6~10번을 가져와야 한다(1~5는 이미
        # screened 처리됐으므로 promotion 여부와 무관하게 재선택 안 됨).
        assert [r["id"] for r in second] == [f"TSU-{i:07d}" for i in range(6, 11)]

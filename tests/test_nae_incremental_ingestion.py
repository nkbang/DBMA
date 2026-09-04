"""Tests for NAE/pipeline/ingest/* (NAE-INCREMENTAL-INGESTION-001).

전부 tmp_path/synthetic 데이터와 fake embed/Qdrant client를 사용한다 —
실제 Production TSU, 실제 Ollama, 실제 Qdrant 서버에 절대 접속하지 않는다
(Test D/E/F가 요구하는 "isolated test dataset" 원칙).
"""
from __future__ import annotations

import json

import pytest

from NAE.pipeline.ingest import content_hash as ch
from NAE.pipeline.ingest import embedding as emb
from NAE.pipeline.ingest import indexing as idx
from NAE.pipeline.ingest import manifest as mf
from NAE.pipeline.ingest import pipeline
from NAE.pipeline.ingest.identity import extract_identity, validate_identity
from NAE.pipeline.ingest.state import IncrementalStateStore, ProcessingState


def _record(tid, claim="claim text", **overrides):
    defaults = dict(
        id=tid, claim=claim, book="Book", page=1, scriptures=[],
        tsu_schema_version="1", review_status="verified",
        author_id="author-1", work_id="work-1", edition_id="edition-1",
        source_id="source-1",
    )
    defaults.update(overrides)
    return defaults


class FakeQdrantClient:
    """실제 qdrant_client.QdrantClient의 최소 호환 in-memory fake."""

    def __init__(self):
        self._collections: dict[str, dict] = {}

    def get_collections(self):
        class _Cols:
            def __init__(self, names):
                self.collections = [type("C", (), {"name": n}) for n in names]
        return _Cols(list(self._collections.keys()))

    def create_collection(self, collection_name, vectors_config):
        self._collections[collection_name] = {}

    def get_collection(self, collection_name):
        points = self._collections.get(collection_name, {})
        return type("Info", (), {"points_count": len(points)})

    def upsert(self, collection_name, points):
        self._collections.setdefault(collection_name, {})
        for p in points:
            self._collections[collection_name][p.id] = p

    def scroll(self, collection_name, limit=500, offset=None, with_payload=True, with_vectors=False):
        points = list(self._collections.get(collection_name, {}).values())
        return points, None


def _fake_embed_fn(text, *, content_hash, model, cache_root=None, **_):
    """content_hash를 그대로 결정적 벡터로 변환 — 실제 Ollama 호출 없음.
    실제 embed_client.embed_text()처럼 cache_root에 결과를 기록해
    이후 SKIP 판정이 실제 동작과 동일하게 재현되도록 한다."""
    vector = [float(int(content_hash[i:i+2], 16)) for i in range(0, 8, 2)]
    if cache_root is not None:
        import json as _json
        cache_root.mkdir(parents=True, exist_ok=True)
        (cache_root / f"{content_hash}.json").write_text(
            _json.dumps({"hash": content_hash, "model": model, "vector": vector}), encoding="utf-8"
        )
    return vector


class TestIdentityModel:
    def test_extract_identity_from_record(self):
        rec = _record("TSU-0009001")
        key = extract_identity(rec)
        assert key.author_id == "author-1"
        assert key.work_id == "work-1"
        assert key.edition_id == "edition-1"
        assert key.source_file_id == "source-1"
        assert key.tsu_id == "TSU-0009001"

    def test_validate_identity_flags_missing_fields(self):
        rec = _record("TSU-0009002", author_id="", work_id="")
        key = extract_identity(rec)
        missing = validate_identity(key)
        assert "author_id" in missing and "work_id" in missing

    def test_batch_number_is_not_identity(self):
        """동일 tsu_id가 다른 batch에서 다시 나타나도(예: 재처리) identity는
        같다 — batch_id는 identity 필드에 없다."""
        key = extract_identity(_record("TSU-0009003"))
        assert not hasattr(key, "batch_id")


class TestContentHashIdempotency:
    def test_new_tsu_classified_new(self):
        rec = _record("TSU-0009001")
        h = ch.compute_content_hash(rec)
        status = ch.classify("TSU-0009001", h, known_hashes={})
        assert status == ch.ChangeStatus.NEW

    def test_same_content_classified_unchanged(self):
        rec = _record("TSU-0009001")
        h = ch.compute_content_hash(rec)
        status = ch.classify("TSU-0009001", h, known_hashes={"TSU-0009001": h})
        assert status == ch.ChangeStatus.UNCHANGED

    def test_changed_claim_classified_changed(self):
        rec_v1 = _record("TSU-0009001", claim="original claim")
        rec_v2 = _record("TSU-0009001", claim="revised claim")
        h1 = ch.compute_content_hash(rec_v1)
        h2 = ch.compute_content_hash(rec_v2)
        assert h1 != h2
        status = ch.classify("TSU-0009001", h2, known_hashes={"TSU-0009001": h1})
        assert status == ch.ChangeStatus.CHANGED


class TestProcessingState:
    def test_state_store_persists_across_instances(self, tmp_path):
        path = tmp_path / "state.json"
        store1 = IncrementalStateStore(path)
        store1.set_state("TSU-0009001", ProcessingState.INDEXED, "hash-abc")
        store1.save()

        store2 = IncrementalStateStore(path)
        assert store2.get_state("TSU-0009001") == ProcessingState.INDEXED
        assert store2.get_hash("TSU-0009001") == "hash-abc"

    def test_failed_record_does_not_block_others(self, tmp_path):
        store = IncrementalStateStore(tmp_path / "state.json")
        store.set_state("TSU-A", ProcessingState.EMBEDDING_FAILED)
        store.set_state("TSU-B", ProcessingState.INDEXED, "hash-b")
        assert store.get_state("TSU-A") == ProcessingState.EMBEDDING_FAILED
        assert store.get_state("TSU-B") == ProcessingState.INDEXED


class TestIncrementalEmbedding:
    def test_embed_plan_skip_when_cache_and_model_match(self, tmp_path):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        rec = _record("TSU-0009001")
        h = ch.compute_content_hash(rec)
        (cache_root / f"{h}.json").write_text(json.dumps({"hash": h, "model": "bge-m3:latest", "vector": [0.1] * 4}), encoding="utf-8")

        plan = emb.plan_embedding([rec], model="bge-m3:latest", cache_root=cache_root)
        assert plan["TSU-0009001"] == "SKIP"

    def test_embed_plan_embed_when_model_differs(self, tmp_path):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        rec = _record("TSU-0009001")
        h = ch.compute_content_hash(rec)
        (cache_root / f"{h}.json").write_text(json.dumps({"hash": h, "model": "old-model", "vector": [0.1] * 4}), encoding="utf-8")

        plan = emb.plan_embedding([rec], model="bge-m3:latest", cache_root=cache_root)
        assert plan["TSU-0009001"] == "EMBED"

    def test_execute_incremental_embed_only_touches_embed_records(self, tmp_path):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        already = _record("TSU-0009001", claim="already-cached claim")
        h = ch.compute_content_hash(already)
        (cache_root / f"{h}.json").write_text(json.dumps({"hash": h, "model": "bge-m3:latest", "vector": [1.0] * 4}), encoding="utf-8")
        new = _record("TSU-0009002", claim="brand-new claim")

        result = emb.execute_incremental_embed(
            [already, new], model="bge-m3:latest", cache_root=cache_root, embed_fn=_fake_embed_fn,
        )
        assert result["skipped"] == ["TSU-0009001"]
        assert result["embedded"] == ["TSU-0009002"]
        assert "TSU-0009002" in result["vectors"]
        # SKIP이어도 vector는 캐시에서 채워져 반환된다(embed_fn 재호출 없이) —
        # 그래야 embedding 이후 indexing만 실패했던 레코드를 재시도할 때
        # 색인 단계가 이 레코드를 계속 포함할 수 있다.
        assert result["vectors"]["TSU-0009001"] == [1.0, 1.0, 1.0, 1.0]


class TestIncrementalIndexing:
    def test_upsert_only_new_leaves_existing_untouched(self):
        client = FakeQdrantClient()
        rec_a = _record("TSU-0009001")
        vec_a = [1.0, 2.0, 3.0, 4.0]
        idx.execute_incremental_index({"TSU-0009001": rec_a}, {"TSU-0009001": vec_a}, client=client, collection_name="test_col")

        existing_before = idx.existing_point_ids(client, "test_col")
        assert existing_before == {"TSU-0009001"}

        rec_b = _record("TSU-0009002")
        vec_b = [5.0, 6.0, 7.0, 8.0]
        idx.execute_incremental_index({"TSU-0009002": rec_b}, {"TSU-0009002": vec_b}, client=client, collection_name="test_col")

        existing_after = idx.existing_point_ids(client, "test_col")
        assert existing_after == {"TSU-0009001", "TSU-0009002"}  # 기존 것 유지 + 신규 추가

    def test_large_batch_splits_into_multiple_upsert_calls(self):
        """Qdrant HTTP payload 크기 제한(2026-08-11, Batch 1-23 backlog
        embedding 중 1,682건 단일 upsert가 33.5MB로 거부된 실사고) 재발
        방지 회귀 테스트 — UPSERT_BATCH_SIZE를 넘는 건수는 여러 번의
        upsert 호출로 나뉘어야 한다."""
        call_count = {"n": 0}
        client = FakeQdrantClient()
        original_upsert = client.upsert

        def counting_upsert(collection_name, points):
            call_count["n"] += 1
            return original_upsert(collection_name, points)

        client.upsert = counting_upsert

        n = idx.UPSERT_BATCH_SIZE * 2 + 30  # 배치 크기의 2.x배
        records_by_id = {f"TSU-{i:07d}": _record(f"TSU-{i:07d}", claim=f"claim {i}") for i in range(1, n + 1)}
        vectors_by_id = {tid: [1.0, 2.0, 3.0, 4.0] for tid in records_by_id}

        idx.execute_incremental_index(records_by_id, vectors_by_id, client=client, collection_name="test_col")

        assert call_count["n"] == 3  # ceil(n / UPSERT_BATCH_SIZE)
        assert idx.existing_point_ids(client, "test_col") == set(records_by_id.keys())

    def test_lifecycle_active_vs_replaced(self):
        client = FakeQdrantClient()
        rec = _record("TSU-0009001")
        r1 = idx.execute_incremental_index({"TSU-0009001": rec}, {"TSU-0009001": [1.0] * 4}, client=client, collection_name="test_col")
        assert r1["lifecycle"]["TSU-0009001"] == "ACTIVE"

        r2 = idx.execute_incremental_index({"TSU-0009001": rec}, {"TSU-0009001": [9.0] * 4}, client=client, collection_name="test_col")
        assert r2["lifecycle"]["TSU-0009001"] == "REPLACED"


class TestEmbedSucceedsIndexFailsRetry:
    """회귀 방지 — 2026-08-11 Batch 1-23 backlog embedding 실사고 재현:
    embedding은 전부 성공(Ollama 호출+cache 기록)했으나 단일 대량 upsert가
    Qdrant payload 크기 제한으로 실패한 뒤, 재시도 시 캐시 hit(SKIP)이라는
    이유로 indexing까지 건너뛰어 0건 색인되는 문제가 있었다."""

    def test_retry_after_index_failure_still_indexes_cached_records(self, tmp_path):
        cache_root = tmp_path / "cache"
        state_path = tmp_path / "state.json"
        records = [_record(f"TSU-000900{i}", claim=f"claim {i}") for i in range(1, 4)]

        class FailingThenWorkingClient(FakeQdrantClient):
            def __init__(self):
                super().__init__()
                self.fail_next = True

            def upsert(self, collection_name, points):
                if self.fail_next:
                    self.fail_next = False
                    raise RuntimeError("simulated Qdrant payload-too-large failure")
                return super().upsert(collection_name, points)

        failing_client = FailingThenWorkingClient()
        store1 = IncrementalStateStore(state_path)
        with pytest.raises(RuntimeError):
            pipeline.apply(records, state_store=store1, embed_fn=_fake_embed_fn, qdrant_client=failing_client, cache_root=cache_root)

        # embedding cache는 이미 채워졌다(embed_fn이 upsert 실패 이전에 호출됨)
        assert len(list(cache_root.glob("*.json"))) == 3

        # 재시도 — 이번엔 upsert가 성공하는 클라이언트로, 캐시는 그대로 재사용
        working_client = FakeQdrantClient()
        store2 = IncrementalStateStore(state_path)
        result = pipeline.apply(records, state_store=store2, embed_fn=_fake_embed_fn, qdrant_client=working_client, cache_root=cache_root)

        assert result["embedded"] == []  # 전부 캐시 hit, embed_fn 재호출 없음
        assert result["indexed_count"] == 3  # 그럼에도 3건 전부 색인되어야 한다
        assert idx.existing_point_ids(working_client, index_config_collection()) == {r["id"] for r in records}


def index_config_collection():
    from NAE.pipeline.index import config as index_config
    return index_config.COLLECTION_NAME


class TestDryRunVsApply:
    def test_dry_run_writes_nothing(self, tmp_path):
        state_path = tmp_path / "state.json"
        store = IncrementalStateStore(state_path)
        records = [_record("TSU-0009001")]

        result = pipeline.dry_run(records, state_store=store, cache_root=tmp_path / "cache")
        assert result["mode"] == "dry_run"
        assert not state_path.exists()  # dry-run은 상태 저장소도 쓰지 않음


class TestScenarioABC:
    """Test A/B/C — 새 자료 / 동일 자료 재투입 / 변경된 자료."""

    def test_a_new_source(self, tmp_path):
        store = IncrementalStateStore(tmp_path / "state.json")
        records = [_record("TSU-0009001")]
        result = pipeline.dry_run(records, state_store=store, cache_root=tmp_path / "cache")
        assert result["NEW"] == 1
        assert result["UNCHANGED"] == 0
        assert result["CHANGED"] == 0

    def test_b_same_source_again(self, tmp_path):
        state_path = tmp_path / "state.json"
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        store = IncrementalStateStore(state_path)
        records = [_record("TSU-0009001")]

        apply_result = pipeline.apply(records, state_store=store, embed_fn=_fake_embed_fn, qdrant_client=FakeQdrantClient(), cache_root=cache_root)
        assert apply_result["NEW"] == 1
        assert len(apply_result["embedded"]) == 1

        store2 = IncrementalStateStore(state_path)
        result_again = pipeline.dry_run(records, state_store=store2, cache_root=cache_root)
        assert result_again["NEW"] == 0
        assert result_again["CHANGED"] == 0
        assert result_again["UNCHANGED"] == 1
        assert result_again["EMBED"] == 0  # 불필요한 재-embedding 없음

    def test_c_changed_source(self, tmp_path):
        state_path = tmp_path / "state.json"
        cache_root = tmp_path / "cache"
        store = IncrementalStateStore(state_path)
        rec_v1 = _record("TSU-0009001", claim="original")
        pipeline.apply([rec_v1], state_store=store, embed_fn=_fake_embed_fn, qdrant_client=FakeQdrantClient(), cache_root=cache_root)

        store2 = IncrementalStateStore(state_path)
        rec_v2 = _record("TSU-0009001", claim="revised claim text")
        result = pipeline.dry_run([rec_v2], state_store=store2, cache_root=cache_root)
        assert result["CHANGED"] == 1
        assert result["NEW"] == 0
        assert result["UNCHANGED"] == 0


class TestScenarioDE_ProductionSafety:
    """Test D/E — 기존 Production/embedding에 영향 없음(isolated fixture로 시뮬레이션)."""

    def test_d_existing_production_untouched_by_new_source(self, tmp_path):
        state_path = tmp_path / "state.json"
        cache_root = tmp_path / "cache"
        store = IncrementalStateStore(state_path)
        existing = [_record(f"TSU-000900{i}") for i in range(1, 4)]  # 기존 3건 "Production"
        pipeline.apply(existing, state_store=store, embed_fn=_fake_embed_fn, qdrant_client=FakeQdrantClient(), cache_root=cache_root)

        before_hashes = IncrementalStateStore(state_path).known_hashes()

        store2 = IncrementalStateStore(state_path)
        new_record = _record("TSU-0009999")  # 신규 1건 추가
        pipeline.apply(existing + [new_record], state_store=store2, embed_fn=_fake_embed_fn, qdrant_client=FakeQdrantClient(), cache_root=cache_root)

        after_hashes = IncrementalStateStore(state_path).known_hashes()
        for tid in before_hashes:
            assert before_hashes[tid] == after_hashes[tid]  # 기존 3건 hash 불변 = mutation 0

    def test_e_existing_embedding_not_recomputed(self, tmp_path):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        state_path = tmp_path / "state.json"
        store = IncrementalStateStore(state_path)
        rec = _record("TSU-0009001")

        call_count = {"n": 0}
        def counting_embed_fn(text, *, content_hash, model, cache_root=cache_root, **_):
            call_count["n"] += 1
            return _fake_embed_fn(text, content_hash=content_hash, model=model)

        # 최초 embedding — 캐시에 기록되도록 실제 embed_client 캐시 저장 로직을 흉내
        vec = counting_embed_fn(rec["claim"], content_hash=ch.compute_content_hash(rec), model="bge-m3:latest")
        (cache_root / f"{ch.compute_content_hash(rec)}.json").write_text(
            json.dumps({"hash": ch.compute_content_hash(rec), "model": "bge-m3:latest", "vector": vec}), encoding="utf-8"
        )
        first_call_count = call_count["n"]

        plan = emb.plan_embedding([rec], model="bge-m3:latest", cache_root=cache_root)
        assert plan["TSU-0009001"] == "SKIP"

        result = emb.execute_incremental_embed([rec], model="bge-m3:latest", cache_root=cache_root, embed_fn=counting_embed_fn)
        assert call_count["n"] == first_call_count  # SKIP이므로 embed_fn이 추가로 호출되지 않음
        assert result["skipped"] == ["TSU-0009001"]


class TestScenarioF_Reconciliation:
    def test_incremental_result_matches_full_reconciliation(self, tmp_path):
        """isolated dataset에서 incremental 실행 결과와, 전체를 처음부터
        한 번에 index한 결과가 논리적으로 동일한 최종 상태에 도달하는지
        확인한다(Production에서 실제 full re-index를 수행하지 않음)."""
        client_incremental = FakeQdrantClient()
        client_full = FakeQdrantClient()

        batch1 = [_record(f"TSU-000900{i}") for i in range(1, 3)]
        batch2 = [_record(f"TSU-000900{i}") for i in range(3, 5)]
        all_records = batch1 + batch2

        # incremental: 두 번에 나눠 upsert
        for batch in (batch1, batch2):
            records_by_id = {r["id"]: r for r in batch}
            vectors = {r["id"]: _fake_embed_fn(r["claim"], content_hash=ch.compute_content_hash(r), model="x") for r in batch}
            idx.execute_incremental_index(records_by_id, vectors, client=client_incremental, collection_name="col")

        # full: 한 번에 전체 upsert
        records_by_id_full = {r["id"]: r for r in all_records}
        vectors_full = {r["id"]: _fake_embed_fn(r["claim"], content_hash=ch.compute_content_hash(r), model="x") for r in all_records}
        idx.execute_incremental_index(records_by_id_full, vectors_full, client=client_full, collection_name="col")

        assert idx.existing_point_ids(client_incremental, "col") == idx.existing_point_ids(client_full, "col")


class TestProductionManifest:
    def test_manifest_counts_match_synthetic_corpus(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        identifier_dir = tsu_root / "TestBook"
        identifier_dir.mkdir(parents=True)
        records = [_record(f"TSU-000900{i}") for i in range(1, 4)]
        (identifier_dir / "tsu.json").write_text(json.dumps(records), encoding="utf-8")

        manifest = mf.build_production_manifest(tsu_root=tsu_root, production_generation=1)
        assert manifest["total_tsu"] == 3
        assert manifest["total_editions"] == 1  # 전부 edition-1
        assert manifest["total_source_files"] == 1
        assert manifest["embedding_model"] == "bge-m3:latest"
        assert manifest["embedding_dimension"] == 1024
        assert manifest["schema_version"] == "1.0.0"

    def test_manifest_generation_increments_and_detects_change(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        identifier_dir = tsu_root / "TestBook"
        identifier_dir.mkdir(parents=True)
        (identifier_dir / "tsu.json").write_text(json.dumps([_record("TSU-0009001")]), encoding="utf-8")

        gen1 = mf.build_production_manifest(tsu_root=tsu_root, production_generation=1)

        (identifier_dir / "tsu.json").write_text(json.dumps([_record("TSU-0009001"), _record("TSU-0009002")]), encoding="utf-8")
        gen2 = mf.build_production_manifest(tsu_root=tsu_root, production_generation=2, previous_manifest=gen1)

        assert gen2["corpus_changed_since_previous"] is True
        assert gen2["previous_generation"] == 1
        assert gen2["total_tsu"] == 2

    def test_manifest_never_copies_full_corpus(self, tmp_path):
        """manifest는 카운트/해시 요약만 — 개별 TSU claim/source_text를
        포함하지 않는다(historical checkpoint와의 구분)."""
        tsu_root = tmp_path / "tsu"
        identifier_dir = tsu_root / "TestBook"
        identifier_dir.mkdir(parents=True)
        (identifier_dir / "tsu.json").write_text(json.dumps([_record("TSU-0009001", claim="SECRET_CLAIM_TEXT")]), encoding="utf-8")

        manifest = mf.build_production_manifest(tsu_root=tsu_root, production_generation=1)
        assert "SECRET_CLAIM_TEXT" not in json.dumps(manifest)

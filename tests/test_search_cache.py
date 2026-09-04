"""Tests for core/search_cache.py (DBMA-SEARCH-INFRA-001 HQ 제안 ⑥)."""

import time

import pytest

from core.search_cache import SearchResultCache, make_cache_key, normalize_query


class TestNormalizeQuery:
    def test_collapses_whitespace(self):
        assert normalize_query("은혜   에 대하여") == normalize_query("은혜 에 대하여")

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_query("  은혜  ") == normalize_query("은혜")

    def test_lowercases(self):
        assert normalize_query("Calvin") == normalize_query("calvin")

    def test_different_words_produce_different_keys(self):
        assert normalize_query("은혜") != normalize_query("사랑")


class TestMakeCacheKey:
    def test_same_inputs_produce_same_key(self):
        k1 = make_cache_key("은혜", 10, None, "hash1")
        k2 = make_cache_key("은혜", 10, None, "hash1")
        assert k1 == k2

    def test_different_query_produces_different_key(self):
        k1 = make_cache_key("은혜", 10, None, "hash1")
        k2 = make_cache_key("사랑", 10, None, "hash1")
        assert k1 != k2

    def test_different_k_produces_different_key(self):
        k1 = make_cache_key("은혜", 10, None, "hash1")
        k2 = make_cache_key("은혜", 5, None, "hash1")
        assert k1 != k2

    def test_different_file_scope_produces_different_key(self):
        k1 = make_cache_key("은혜", 10, ["a.pdf"], "hash1")
        k2 = make_cache_key("은혜", 10, ["b.pdf"], "hash1")
        assert k1 != k2

    def test_file_scope_order_does_not_matter(self):
        k1 = make_cache_key("은혜", 10, ["a.pdf", "b.pdf"], "hash1")
        k2 = make_cache_key("은혜", 10, ["b.pdf", "a.pdf"], "hash1")
        assert k1 == k2

    def test_different_dataset_fingerprint_produces_different_key(self):
        # This is the index-version invalidation mechanism — a reindex
        # changes the fingerprint, so old cache rows become unreachable.
        k1 = make_cache_key("은혜", 10, None, "hash1")
        k2 = make_cache_key("은혜", 10, None, "hash2")
        assert k1 != k2

    def test_normalized_query_variants_produce_same_key(self):
        k1 = make_cache_key("은혜   ", 10, None, "hash1")
        k2 = make_cache_key("은혜", 10, None, "hash1")
        assert k1 == k2


class TestSearchResultCache:
    @pytest.fixture()
    def cache(self, tmp_path):
        return SearchResultCache(tmp_path / "cache.sqlite3")

    def test_miss_returns_none(self, cache):
        assert cache.get("nonexistent") is None

    def test_set_then_get_returns_value(self, cache):
        cache.set("k1", {"results": ["a", "b"]}, ttl_seconds=60)
        assert cache.get("k1") == {"results": ["a", "b"]}

    def test_l1_hit_avoids_l2_lookup(self, cache, monkeypatch):
        cache.set("k1", {"results": ["a"]}, ttl_seconds=60)

        def fail(*args, **kwargs):
            raise AssertionError("L2 should not have been queried — L1 should have hit")

        monkeypatch.setattr(cache.l2, "get", fail)
        assert cache.get("k1") == {"results": ["a"]}

    def test_l2_hit_backfills_l1(self, cache):
        cache.set("k1", {"results": ["a"]}, ttl_seconds=60)
        cache.l1.clear()  # simulate a fresh process with only L2 populated
        assert cache.get("k1") == {"results": ["a"]}
        # Now L1 should have it without touching L2.
        assert cache.l1.get("k1") == {"results": ["a"]}

    def test_expired_entry_returns_none(self, cache):
        cache.set("k1", {"results": ["a"]}, ttl_seconds=0.05)
        time.sleep(0.1)
        assert cache.get("k1") is None

    def test_clear_removes_both_tiers(self, cache):
        cache.set("k1", {"results": ["a"]}, ttl_seconds=60)
        cache.clear()
        assert cache.get("k1") is None

    def test_survives_new_cache_instance_same_db_path(self, tmp_path):
        db_path = tmp_path / "cache.sqlite3"
        cache1 = SearchResultCache(db_path)
        cache1.set("k1", {"results": ["a"]}, ttl_seconds=60)
        cache1.close()

        # A fresh instance (simulating a process restart) should still see
        # it via L2 — this is the "L2 survives restart" property.
        cache2 = SearchResultCache(db_path)
        assert cache2.get("k1") == {"results": ["a"]}


class TestL2PurgeExpired:
    def test_purge_expired_removes_only_expired_rows(self, tmp_path):
        cache = SearchResultCache(tmp_path / "cache.sqlite3")
        cache.set("fresh", {"v": 1}, ttl_seconds=60)
        cache.set("stale", {"v": 2}, ttl_seconds=0.05)
        time.sleep(0.1)

        removed = cache.l2.purge_expired()
        assert removed == 1
        assert cache.l2.get("fresh") == {"v": 1}

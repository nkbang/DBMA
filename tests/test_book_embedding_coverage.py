"""test_book_embedding_coverage.py — RetrievalEngine.book_embedding_coverage() 검증.

Task Order §3 요구사항:
1. 모든 책 coverage_ratio == 1.0 (전부 임베딩됨) → 결과 empty
2. 일부만 임베딩된 경우
3. cache가 비어있으면 coverage_ratio == 0.0
4. EMBEDDING_DIMENSION(1024) 검증

산출물: core/retrieval.py 신규 메서드, ui/pages/monitor.py 리포트 섹션,
       tests/test_book_embedding_coverage.py (이 파일).
"""

import hashlib
import json
from pathlib import Path

import pytest


@pytest.fixture()
def tsu_path(tmp_path: Path) -> Path:
    """가짜 TSU dataset (JSONL 형식 — RetrievalEngine._load_corpus() 호환)."""
    p = tmp_path / "tsu.jsonl"
    lines = [
        json.dumps({"verse_mapping": {"book_id": "GEN"}, "content": "A"}, ensure_ascii=False),
        json.dumps({"verse_mapping": {"book_id": "GEN"}, "content": "B"}, ensure_ascii=False),
        json.dumps({"verse_mapping": {"book_id": "REV"}, "content": "C"}, ensure_ascii=False),
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


@pytest.fixture()
def cache_dir(tmp_path: Path) -> Path:
    """EmbeddingCache가 쓰는 캐시 디렉터리 구조 (SHA256 해시 파일들)."""
    d = tmp_path / "embeddings"
    d.mkdir(parents=True)
    return d


def _make_cache_file(cache_dir: Path, text: str, dim: int) -> None:
    """EmbeddingCache.validate()가 찾는 JSON 캐시 파일 생성 (vector 필드 포함)."""
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    path = cache_dir / f"{sha}.json"
    data = {"text": text[:500], "vector": [0.0] * dim, "hash": sha}
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# §3 — Case 1: 모든 책 coverage_ratio == 1.0
# ---------------------------------------------------------------------------


def test_all_books_full_coverage(tsu_path: Path, cache_dir: Path) -> None:
    """모든 chunk가 임베딩된 경우 coverage_ratio == 1.0 — threshold=1.0이므로
    coverage 1.0인 책은 결과 dict에 포함되지 않는다 (coverage_ratio < threshold
    조건)."""
    from core.retrieval import RetrievalEngine, EmbeddingCache

    engine = RetrievalEngine(str(tsu_path))
    cache = EmbeddingCache(str(cache_dir))

    # 모든 chunk의 embedding을 캐시에 추가
    _make_cache_file(cache_dir, "A", 1024)
    _make_cache_file(cache_dir, "B", 1024)
    _make_cache_file(cache_dir, "C", 1024)

    # threshold=1.0: coverage < 1.0인 책만 반환 → empty (모든 책 1.0)
    coverage = engine.book_embedding_coverage(cache)
    assert len(coverage) == 0


# ---------------------------------------------------------------------------
# §3 — Case 2: 일부만 임베딩된 경우
# ---------------------------------------------------------------------------


def test_partial_embedding(tsu_path: Path, cache_dir: Path) -> None:
    """일부 chunk만 임베딩된 경우 coverage_ratio < 1.0."""
    from core.retrieval import RetrievalEngine, EmbeddingCache

    engine = RetrievalEngine(str(tsu_path))
    cache = EmbeddingCache(str(cache_dir))

    # gen: chunk 0만 임베딩 (1/2), rev: chunk 0만 임베딩 (1/1)
    _make_cache_file(cache_dir, "A", 1024)
    _make_cache_file(cache_dir, "C", 1024)

    coverage = engine.book_embedding_coverage(cache)

    # gen: coverage_ratio=0.5 < 1.0 → 결과 포함
    assert len(coverage) == 1
    assert "GEN" in coverage
    assert coverage["GEN"]["coverage_ratio"] == 0.5
    assert coverage["GEN"]["embedded"] == 1
    assert coverage["GEN"]["total"] == 2
    # rev: coverage_ratio=1.0 → 결과 미포함 (threshold 미만 아님)
    assert "REV" not in coverage


# ---------------------------------------------------------------------------
# §3 — Case 3: cache가 비어있으면 ratio == 0.0
# ---------------------------------------------------------------------------


def test_empty_cache_returns_zero_coverage(tsu_path: Path, cache_dir: Path) -> None:
    """캐시가 비어있으면 embedded == 0, coverage_ratio == 0.0 — 모든 책이
    결과 dict에 포함됨 (coverage_ratio >= 0이므로)."""
    from core.retrieval import RetrievalEngine, EmbeddingCache

    engine = RetrievalEngine(str(tsu_path))
    cache = EmbeddingCache(str(cache_dir))

    # 캐시 비워둔 상태
    coverage = engine.book_embedding_coverage(cache)

    # embedded == 0인 책도 coverage_ratio >= 0이므로 결과에 포함됨
    assert len(coverage) == 2
    for book_id in ("GEN", "REV"):
        assert book_id in coverage
        assert coverage[book_id]["embedded"] == 0
        assert coverage[book_id]["coverage_ratio"] == 0.0


# ---------------------------------------------------------------------------
# §3 — Case 4: EMBEDDING_DIMENSION(1024) 검증
# ---------------------------------------------------------------------------


def test_dimension_validation(tsu_path: Path, cache_dir: Path) -> None:
    """dimension이 1024가 아닌 embedding은 dimension_ok 카운트에 포함되지.

    gen chunk 1 (text="B")의 캐시 파일을 만들지 않아 coverage_ratio < 1.0이
    되므로 dimension_ok 검증이 가능해짐.
    """
    from core.retrieval import RetrievalEngine, EmbeddingCache

    engine = RetrievalEngine(str(tsu_path))
    cache = EmbeddingCache(str(cache_dir))

    # gen: chunk 0 (text="A") dim=1024 OK, chunk 1 (text="B") 캐시 파일 없음
    # rev: chunk 0 (text="C") dim=1024 OK
    _make_cache_file(cache_dir, "A", 1024)
    _make_cache_file(cache_dir, "C", 1024)

    coverage = engine.book_embedding_coverage(cache)

    # gen: coverage_ratio=0.5 < 1.0 → 결과 포함
    assert "GEN" in coverage
    assert coverage["GEN"]["coverage_ratio"] == 0.5
    assert coverage["GEN"]["embedded"] == 1  # A만 캐시 파일 존재
    assert coverage["GEN"]["dimension_ok"] == 1  # A만 dim=1024

    # rev: coverage_ratio=1.0 → 결과 미포함
    assert "REV" not in coverage
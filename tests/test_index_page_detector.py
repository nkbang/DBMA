"""core/index_page_detector.py + its use in HybridRetriever (2026-09-26).

Sample texts are trimmed excerpts of real corpus chunks that drove the
threshold choice (docs/NAE_INDEX_PAGE_DOWNWEIGHT_BUILD_REPORT_001.md)."""

import json

import pytest

from core.candidate_generator import CandidateGenerator, build_index
from core.hybrid_candidate_pipeline import HybridRetriever, _quality_factor, load_tsu_by_id
from core.index_page_detector import is_index_page
from core.retrieval import QueryParser

# Maclaren Expositions — scripture/subject index with "Name, page" locators.
MACLAREN_INDEX = (
    "ROMANS I. 7, Romans, 6 — 11-12, Romans, 13 — 14, Esther, 19; — 16, Romans, 30; "
    "Philippians, 311 — 17, Acts xiii., 38 ROMANS II. 1, Deuteronomy, 335 — 4, Esther, 370 "
    "— 20, ii. Kings, 73 — 17-29, Romans, 417 ROMANS III. 19-26, Romans, 46 — 20, ii. Kings, 63 "
    "— 22, Romans, 52 — 24, Romans, 60; Hebrews, 142; Peter, 65"
)
# Spurgeon Morning by Morning — scripture index without locator commas.
SPURGEON_SCRIPTURE_INDEX = (
    "ii. 21 . . . 109 xxv. 9 , 335 i. 5 . 153 v. 12 . . . 1 iv. 2 . 20 EZRA. vii. 16 157 "
    "JUDGES. vii. 22 . 348 xxi. 6 . 167 vii. 20 . . 264 viii. 42 217 viii. 47 45 ROMANS. "
    "x. 21 . 84 iii. 31 . . 26 ii. 17 218 x. 40 . 24 vi. 9 151"
)
# Broadus — subject index.
BROADUS_INDEX = (
    "Argument, use of, 158; men fond of, 159; preliminaries to, 162; varieties of, 173-198; "
    "order of, 206; general suggestions as to, 207. Brougham, Lord, allusion to, 277. "
    "Buffon on style, 320. Burden of proof, 164. Butler, Bishop, quoted on habit, 236."
)
# Keach 1681 — prose dense with inline references; must NOT be flagged.
KEACH_PROSE = (
    "Our Divines propose some Types of the Lord's Supper, as the Tree of Life in the midst "
    "of Paradise, Gen. 2. 9. see Rev. 22. 14, John 6. 53, 54. and the Manna which came down "
    "from Heaven, Exod. 16. 15. which our Saviour applieth unto himself, as being the true "
    "Bread of Life that giveth life unto the world."
)
SERMON_PROSE = (
    "We know that all things work together for good to them that love God. This is a "
    "wonderful text, and I pray that the Holy Spirit may open it to us this morning, "
    "for there is comfort here for every tried believer who walks in darkness."
)


@pytest.mark.parametrize("text", [MACLAREN_INDEX, SPURGEON_SCRIPTURE_INDEX, BROADUS_INDEX])
def test_index_pages_detected(text):
    assert is_index_page(text)


@pytest.mark.parametrize("text", [KEACH_PROSE, SERMON_PROSE, "", "Romans, 12"])
def test_prose_and_short_text_not_detected(text):
    assert not is_index_page(text)


def test_quality_factor_downweights_index_page_and_respects_stored_quality():
    normal = {"content": SERMON_PROSE, "content_quality": {"quality_score": 1.0}}
    index_normal_label = {"content": MACLAREN_INDEX, "content_quality": {"quality_score": 1.0}}
    removed = {"content": MACLAREN_INDEX, "content_quality": {"quality_score": 0.0}}
    assert _quality_factor(normal) == 1.0
    assert _quality_factor(index_normal_label) == pytest.approx(0.79)
    # Never *raises* a worse stored score back up.
    assert _quality_factor(removed) == pytest.approx(0.7)
    assert _quality_factor({"content": SERMON_PROSE, "content_quality": None}) == 1.0


def _tsu(tsu_id, content, source):
    return {"tsu_id": tsu_id, "content": content, "title": "t", "author": "a",
            "source_file": source, "verse_mapping": {}, "language": "en"}


@pytest.fixture()
def retriever(tmp_path):
    # Several index pages that out-score the single prose chunk on BM25
    # ("romans" repeated), mirroring the real "로마서 8장 28절" failure.
    tsus = [_tsu(f"TSU-UNK-idx_{i}", MACLAREN_INDEX, "maclaren.txt") for i in range(5)]
    tsus.append(_tsu("TSU-UNK-prose", "Paul writes to the Romans that all things work "
                     "together for good to them that love God, " * 3, "spurgeon.txt"))
    dataset = tmp_path / "tsu.jsonl"
    dataset.write_text("\n".join(json.dumps(t) for t in tsus), encoding="utf-8")
    build_index(dataset, tmp_path / "idx")
    return HybridRetriever(CandidateGenerator(tmp_path / "idx"), load_tsu_by_id(str(dataset)))


def test_prose_ranks_above_index_pages(retriever):
    parsed = QueryParser().parse("Romans all things work together")
    results = retriever.retrieve(parsed, k_output=6)
    assert results[0].tsu_id == "TSU-UNK-prose"


def test_index_pages_kept_as_backfill_not_dropped(retriever):
    parsed = QueryParser().parse("Romans all things work together")
    results = retriever.retrieve(parsed, k_output=6)
    assert len(results) == 6


def test_demotion_happens_before_candidate_cap(retriever):
    # candidate_k=1: prose must win the single slot even though five index
    # pages outrank it in Stage-1 BM25 order.
    parsed = QueryParser().parse("Romans all things work together")
    results = retriever.retrieve(parsed, k_output=1, candidate_k=1)
    assert [r.tsu_id for r in results] == ["TSU-UNK-prose"]

"""Regression tests — Baptist commentary reference-track generalization.

Covers the changes made to reuse the Smith Bible Dictionary reference
pipeline for a second, isolated collection (Spurgeon's Treasury of David
pilot, `docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md`):

  1. `NAE.pipeline.reference.chunker.chunk_canonical_verse_anchored` —
     new verse-anchored chunking strategy for commentary corpora.
  2. `NAE.pipeline.reference.ingest.ingest()` — generalized to accept
     `collection_name`/`chunker_fn`, default args unchanged so every
     existing caller (Smith ingestion scripts) is byte-for-byte unaffected.
  3. `NAE.reference_retrieval_adapter.search_reference()` — generalized to
     accept `collection_names`, default unchanged (Smith-only).
  4. `NAE.smith_activation.should_activate_smith()` — new
     `NAE_SMITH_ACTIVATION_NARROW` flag (default off = unchanged).
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from NAE.pipeline.reference import chunker, config as ref_config
from NAE.pipeline.reference import ingest as ref_ingest
from NAE import smith_activation
import scripts.nae_commentary_ingest as commentary_cli


# ── chunker.chunk_canonical_verse_anchored ─────────────────────────────

class TestVerseAnchoredChunker:
    def _fixture(self):
        # canonical strings use the full English book name — matches the
        # actual output of NAE.pipeline.canonical.annotate.canonicalize_scripture_ref
        # (verified: canonicalize_scripture_ref("Ps. iv. 2") == "Psalms 4:2").
        return {
            "paragraphs": [
                {"type": "heading", "text": "PSALM I."},
                {
                    "type": "prose",
                    "text": "Blessed is the man that walketh not in the counsel of the ungodly. " * 3,
                    "page_start": 1,
                    "scripture_references": [{"original": "Ps. i. 1", "canonical": "Psalms 1:1"}],
                },
                {
                    "type": "prose",
                    "text": "This is a most instructive verse, and gives a very significant title. " * 3,
                    "page_start": 1,
                    "scripture_references": [{"original": "Ps. i. 1", "canonical": "Psalms 1:1"}],
                },
                {
                    "type": "prose",
                    "text": "His delight is in the law of the LORD, and in his law doth he meditate. " * 3,
                    "page_start": 2,
                    "scripture_references": [{"original": "Ps. i. 2", "canonical": "Psalms 1:2"}],
                },
                {
                    "type": "prose",
                    "text": "No new scripture marker here — a continuation of the previous verse's discussion.",
                    "page_start": 2,
                    "scripture_references": [],
                },
            ]
        }

    def test_groups_paragraphs_by_scripture_reference(self):
        chunks = chunker.chunk_canonical_verse_anchored(self._fixture())
        refs = [c.scripture_reference for c in chunks]
        assert refs == ["Psalms 1:1", "Psalms 1:2"]

    def test_incidental_cross_reference_does_not_override_anchor(self):
        """Regression: verified against the real Spurgeon Vol.1 canonical.json
        that a paragraph commenting on one Psalm verse routinely cites another
        book in passing (e.g. "...as in Prov. xii. 26...") without restating
        the Psalms reference. An earlier version of this chunker took the
        paragraph's *first* scripture reference as the anchor and would have
        mis-tagged such a paragraph as "Proverbs 12:26" instead of the Psalm
        actually being expounded."""
        fixture = {
            "paragraphs": [
                {"type": "heading", "text": "PSALM IV."},
                {
                    "type": "prose",
                    "text": "Verse 3.—What rare persons the godly are, as excellent as in Prov. xii. 26.",
                    "page_start": 34,
                    "scripture_references": [{"original": "Prov. xii. 26", "canonical": "Proverbs 12:26"}],
                },
                {
                    "type": "prose",
                    "text": "Continuing the same exposition of the fourth Psalm, verse three.",
                    "page_start": 34,
                    "scripture_references": [],
                },
            ]
        }
        chunks = chunker.chunk_canonical_verse_anchored(fixture)
        assert len(chunks) == 1
        assert chunks[0].scripture_reference is None  # no qualifying (Psalms) anchor found yet
        assert "Prov. xii. 26" in chunks[0].text  # cross-reference stays in the text, just isn't the anchor

    def test_anchor_book_prefix_none_falls_back_to_first_reference(self):
        fixture = {
            "paragraphs": [
                {
                    "type": "prose",
                    "text": "Some multi-book commentary paragraph.",
                    "page_start": 1,
                    "scripture_references": [{"original": "Prov. xii. 26", "canonical": "Proverbs 12:26"}],
                },
            ]
        }
        chunks = chunker.chunk_canonical_verse_anchored(fixture, anchor_book_prefix=None)
        assert chunks[0].scripture_reference == "Proverbs 12:26"

    def test_heading_context_is_preserved(self):
        chunks = chunker.chunk_canonical_verse_anchored(self._fixture())
        assert all(c.heading_context == "PSALM I." for c in chunks)

    def test_reference_less_paragraph_continues_current_anchor(self):
        chunks = chunker.chunk_canonical_verse_anchored(self._fixture())
        assert "No new scripture marker here" in chunks[-1].text

    def test_empty_paragraphs_returns_empty(self):
        assert chunker.chunk_canonical_verse_anchored({"paragraphs": []}) == []

    def test_chunk_canonical_unaffected_by_new_field(self):
        """chunk_canonical() (dictionary/heading chunker, used by Smith) must
        not set scripture_reference — new field defaults to None."""
        fixture = {
            "paragraphs": [
                {"type": "heading", "text": "AARON"},
                {"type": "prose", "text": "Aaron was the elder son of Amram and Jochebed." * 5, "page_start": 1},
            ]
        }
        chunks = chunker.chunk_canonical(fixture)
        assert len(chunks) == 1
        assert chunks[0].scripture_reference is None


# ── verse_anchored anchor-diversity footgun (2026-09-15 production finding) ──

class TestAnchorDiversityGuard:
    """The real Spurgeon Vol.1 --apply run shipped 1,627 of 1,978 chunks all
    tagged with the same wrong anchor ("Psalms 109:17") because the source
    text almost never restates chapter:verse for its own subject — only one
    paragraph in the whole 4,145-paragraph document has a qualifying
    citation, so the anchor carries that single (wrong, cross-referenced)
    value forward for the rest of the book. chunk_canonical_verse_anchored
    itself isn't buggy (carry-forward is its documented, correct behavior)
    — the gap was that verification checked tagged/untagged/wrong-book
    counts but never whether the tagged *values* were actually diverse.
    `_warn_if_anchor_values_lack_diversity` closes that gap."""

    def _sparse_citation_fixture(self, n_prose_paragraphs=20):
        """One qualifying citation up front, then many paragraphs with no
        further scripture_references at all — mirrors the real failure
        shape (single stray cross-reference, rest of the book silent)."""
        paragraphs = [
            {
                "type": "prose",
                "text": "Opening remarks citing another passage in passing.",
                "page_start": 1,
                "scripture_references": [{"original": "Ps. cix. 17", "canonical": "Psalms 109:17"}],
            },
        ]
        for i in range(n_prose_paragraphs):
            paragraphs.append({
                "type": "prose",
                "text": f"Verse {i + 1}.—continuing exposition with no restated reference. " * 3,
                "page_start": 2 + i,
                "scripture_references": [],
            })
        return {"paragraphs": paragraphs}

    def test_sparse_citations_produce_degenerate_single_value_anchor(self):
        """Documents the actual (correct, by design) carry-forward behavior
        that makes this a footgun on sparse-citation sources."""
        chunks = chunker.chunk_canonical_verse_anchored(self._sparse_citation_fixture())
        tagged = [c.scripture_reference for c in chunks if c.scripture_reference]
        assert len(tagged) > 1
        assert len(set(tagged)) == 1

    def test_diversity_guard_warns_on_degenerate_fixture(self, tmp_path, capsys):
        fixture = self._sparse_citation_fixture()
        canonical_path = tmp_path / "canonical.json"
        canonical_path.write_text(__import__("json").dumps(fixture), encoding="utf-8")

        commentary_cli._warn_if_anchor_values_lack_diversity(canonical_path)

        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "Psalms 109:17" in err

    def test_diversity_guard_silent_on_healthy_fixture(self, tmp_path, capsys):
        """A source that actually restates chapter:verse per section (each
        paragraph gets its own distinct anchor) should not warn."""
        paragraphs = [
            {
                "type": "prose",
                "text": f"Verse {i}.—exposition text here. " * 3,
                "page_start": i,
                "scripture_references": [{"original": f"Ps. i. {i}", "canonical": f"Psalms 1:{i}"}],
            }
            for i in range(1, 11)
        ]
        canonical_path = tmp_path / "canonical.json"
        canonical_path.write_text(__import__("json").dumps({"paragraphs": paragraphs}), encoding="utf-8")

        commentary_cli._warn_if_anchor_values_lack_diversity(canonical_path)

        assert capsys.readouterr().err == ""


# ── ingest.ingest() default-argument regression ────────────────────────

class TestIngestDefaultsUnchanged:
    def test_default_collection_is_smith_collection(self):
        sig = inspect.signature(ref_ingest.ingest)
        assert sig.parameters["collection_name"].default == ref_config.REFERENCE_COLLECTION_NAME

    def test_default_chunker_is_heading_chunker(self):
        sig = inspect.signature(ref_ingest.ingest)
        assert sig.parameters["chunker_fn"].default is chunker.chunk_canonical

    def test_default_content_type_is_reference_dictionary(self):
        sig = inspect.signature(ref_ingest.ingest)
        assert sig.parameters["content_type"].default == "reference_dictionary"

    def test_commentary_collection_isolated_from_smith_collection(self):
        assert ref_config.COMMENTARY_COLLECTION_NAME != ref_config.REFERENCE_COLLECTION_NAME
        assert ref_config.COMMENTARY_COLLECTION_NAME in ref_config.KNOWN_REFERENCE_COLLECTIONS
        assert ref_config.REFERENCE_COLLECTION_NAME in ref_config.KNOWN_REFERENCE_COLLECTIONS

    def test_build_payload_includes_scripture_reference_only_when_set(self):
        dict_chunk = chunker.ReferenceChunk(
            chunk_index=0, text="t", page_start=1, page_end=1, heading_context="H",
        )
        commentary_chunk = chunker.ReferenceChunk(
            chunk_index=0, text="t", page_start=1, page_end=1, heading_context="H",
            scripture_reference="PS 1:1",
        )
        dict_payload = ref_ingest._build_payload(dict_chunk, "id1", "SRC1", "vol_1")
        commentary_payload = ref_ingest._build_payload(commentary_chunk, "id2", "SRC2", "vol_1")
        assert "scripture_reference" not in dict_payload
        assert commentary_payload["scripture_reference"] == "PS 1:1"


# ── reference_retrieval_adapter.search_reference() signature regression ─

class TestSearchReferenceDefaultsUnchanged:
    def test_default_collection_names_param_is_none(self):
        from NAE import reference_retrieval_adapter as adapter
        sig = inspect.signature(adapter.search_reference)
        assert sig.parameters["collection_names"].default is None

    def test_empty_query_returns_empty_list_regardless_of_collections(self):
        from NAE import reference_retrieval_adapter as adapter
        assert adapter.search_reference("", top_k=3) == []
        assert adapter.search_reference("   ", top_k=3, collection_names=["x", "y"]) == []


# ── smith_activation narrowing flag ─────────────────────────────────────

class TestSmithActivationNarrowFlag:
    LONG_CONCEPT_ONLY_QUERY = "오늘 예배에서 나눈 은혜와 사랑에 대한 이야기가 계속 마음에 남습니다"
    SHORT_CONCEPT_ONLY_QUERY = "은혜와 사랑"
    PROPER_NOUN_QUERY = "모세는 누구인가"
    DEFINITION_QUERY = "은혜란 무엇인가 설명해줘"

    def setup_method(self):
        os.environ.pop("NAE_SMITH_ACTIVATION_NARROW", None)

    def teardown_method(self):
        os.environ.pop("NAE_SMITH_ACTIVATION_NARROW", None)

    def test_flag_off_default_matches_current_behavior(self):
        assert smith_activation.should_activate_smith(self.LONG_CONCEPT_ONLY_QUERY) is True
        assert smith_activation.should_activate_smith(self.SHORT_CONCEPT_ONLY_QUERY) is True

    def test_flag_on_narrows_long_concept_only_query(self):
        os.environ["NAE_SMITH_ACTIVATION_NARROW"] = "true"
        assert smith_activation.should_activate_smith(self.LONG_CONCEPT_ONLY_QUERY) is False

    def test_flag_on_keeps_short_concept_only_query(self):
        os.environ["NAE_SMITH_ACTIVATION_NARROW"] = "true"
        assert smith_activation.should_activate_smith(self.SHORT_CONCEPT_ONLY_QUERY) is True

    def test_flag_on_keeps_proper_noun_activation(self):
        os.environ["NAE_SMITH_ACTIVATION_NARROW"] = "true"
        assert smith_activation.should_activate_smith(self.PROPER_NOUN_QUERY) is True

    def test_flag_on_keeps_definition_pattern_activation(self):
        os.environ["NAE_SMITH_ACTIVATION_NARROW"] = "true"
        assert smith_activation.should_activate_smith(self.DEFINITION_QUERY) is True

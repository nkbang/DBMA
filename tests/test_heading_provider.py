"""Regression test — core/heading_provider.py (SPRINT31-A).

Provider Registry architecture: provider contract, factory-based registry
resolution, and Phase-1 containment assembler. Also a drift-guard that the
shared ATX pattern in heading_constants matches heading_extractor's private
copy (unification deferred; see heading_constants docstring).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.heading_provider as hp
from core.heading_provider import (
    ProviderHeading,
    HeadingProvider,
    MarkdownProvider,
    PdfHeadingProvider,
    NullProvider,
    ProviderRegistry,
    HeadingAssembler,
    AssembledHeading,
    get_registry,
)


class TestSharedConstantDriftGuard:
    def test_atx_pattern_matches_extractor_copy(self):
        # heading_extractor.py keeps its own private copy (SPRINT31-A must not
        # modify it); guard that the shared constant stays identical.
        from core import heading_constants, heading_extractor
        assert heading_constants.ATX_HEADING_RE.pattern == heading_extractor._ATX_HEADING_RE.pattern
        assert heading_constants.ATX_HEADING_RE.flags == heading_extractor._ATX_HEADING_RE.flags


class TestMarkdownProvider:
    def test_atx_levels_titles_confidence(self):
        p = MarkdownProvider("# One\n\nbody\n\n### Three deep\n\nbody")
        hs = p.headings()
        assert [(h.text, h.level, h.confidence, h.source) for h in hs] == [
            ("One", 1, 1.0, "atx"),
            ("Three deep", 3, 1.0, "atx"),
        ]

    def test_no_heading_text_is_empty(self):
        assert MarkdownProvider("plain body, no markers.").headings() == []

    def test_satisfies_protocol(self):
        assert isinstance(MarkdownProvider("x"), HeadingProvider)


class TestPdfHeadingProvider:
    def test_wraps_detector_candidates(self, monkeypatch):
        from core.pdf_structure_detector import HeadingCandidate
        fake = [
            HeadingCandidate(text="Introduction", page=3, signal="bold",
                             confidence=0.82, validity=1.0),
            HeadingCandidate(text="나사로의죽음", page=5, signal="size",
                             confidence=0.67, validity=1.0),
        ]
        monkeypatch.setattr(hp, "detect_headings_from_spans", lambda spans: fake)
        hs = PdfHeadingProvider([{"text": "x"}]).headings()
        assert [(h.text, h.confidence, h.source) for h in hs] == [
            ("Introduction", 0.82, "pdf-bold"),
            ("나사로의죽음", 0.67, "pdf-size"),
        ]
        assert all(h.level == 1 for h in hs)

    def test_no_candidates_is_empty(self, monkeypatch):
        monkeypatch.setattr(hp, "detect_headings_from_spans", lambda spans: [])
        assert PdfHeadingProvider([]).headings() == []

    def test_does_not_reopen_pdf(self, monkeypatch):
        # D-3 core gate: the provider must consume spans, never re-open a PDF.
        import core.pdf_structure_detector as det
        calls = []
        if det._HAS_FITZ:
            monkeypatch.setattr(det.fitz, "open",
                                lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(
                                    AssertionError("fitz.open must not be called")))
        spans = [
            {"text": "body line here that is prose", "size": 9.6, "bold": False,
             "page": 0, "is_block_top": False} for _ in range(40)
        ] + [
            {"text": "나사로의죽음", "size": 12.0, "bold": False, "page": 0, "is_block_top": True},
            {"text": "부활과생명", "size": 12.0, "bold": False, "page": 0, "is_block_top": True},
            {"text": "예수께서무덤에가시다", "size": 12.0, "bold": False, "page": 0, "is_block_top": True},
        ]
        hs = PdfHeadingProvider(spans).headings()
        assert calls == []                      # no fitz.open
        assert hs and all(h.source == "pdf-size" for h in hs)


class TestNullProvider:
    def test_yields_nothing(self):
        assert NullProvider().headings() == []


class TestProviderRegistry:
    def test_resolve_returns_registered_factory(self):
        r = ProviderRegistry()
        r.register("md", MarkdownProvider)
        assert r.resolve("md") is MarkdownProvider
        # resolution only — caller constructs
        provider = r.resolve("md")("# H\n\nbody")
        assert provider.headings()[0].text == "H"

    def test_unknown_source_resolves_to_null(self):
        r = ProviderRegistry()
        factory = r.resolve("docx")
        assert factory is NullProvider
        assert factory("anything").headings() == []

    def test_case_insensitive(self):
        r = ProviderRegistry()
        r.register("PDF", PdfHeadingProvider)
        assert r.resolve("pdf") is PdfHeadingProvider

    def test_reregister_overwrites_phase_d_swap_contract(self):
        r = ProviderRegistry()
        r.register("pdf", PdfHeadingProvider)
        r.register("pdf", NullProvider)  # simulate Phase D hook-provider swap
        assert r.resolve("pdf") is NullProvider

    def test_default_registry_singleton(self):
        assert get_registry() is get_registry()
        assert get_registry().resolve("pdf") is PdfHeadingProvider
        assert get_registry().resolve("md") is MarkdownProvider


class TestHeadingAssembler:
    def test_containment_inheritance_and_confidence(self):
        chunks = [
            "# Chapter 1\n\nintro body",
            "continuation with no heading line",
            "## Section 1.1\n\nsection body",
        ]
        headings = [
            ProviderHeading("Chapter 1", 1, 0.9, "atx"),
            ProviderHeading("Section 1.1", 2, 0.8, "atx"),
        ]
        out = HeadingAssembler().assign(chunks, headings)
        assert [a.heading_path for a in out] == [
            ["Chapter 1"],
            ["Chapter 1"],           # inherited
            ["Chapter 1", "Section 1.1"],
        ]
        assert out[0].heading_confidence == 0.9
        assert out[2].heading_confidence == 0.8
        assert out[2].heading_source == "atx"

    def test_exact_line_guard_rejects_partial_match(self):
        # "INTRODUCT" line must NOT match heading "INTRODUCTION"
        chunks = ["INTRODUCT\n\nsome body text here"]
        headings = [ProviderHeading("INTRODUCTION", 1, 0.8, "pdf-bold")]
        out = HeadingAssembler().assign(chunks, headings)
        assert out[0].heading_path == []  # no false match

    def test_exact_line_match_accepts(self):
        chunks = ["INTRODUCTION\n\nbody"]
        headings = [ProviderHeading("INTRODUCTION", 1, 0.8, "pdf-bold")]
        out = HeadingAssembler().assign(chunks, headings)
        assert out[0].heading_path == ["INTRODUCTION"]

    def test_no_headings_all_empty(self):
        out = HeadingAssembler().assign(["a", "b"], [])
        assert all(a.heading_path == [] and a.heading_depth == 0 for a in out)

    def test_boundary_preserving_does_not_mutate_chunks(self):
        chunks = ["# H\n\nbody", "more"]
        before = list(chunks)
        HeadingAssembler().assign(chunks, [ProviderHeading("H", 1, 1.0, "atx")])
        assert chunks == before

    def test_sibling_replaces_and_drops_deeper(self):
        chunks = [
            "# Alpha\n\nx",
            "## Alpha.1\n\ny",
            "### Alpha.1.1\n\nz",
            "## Alpha.2\n\nw",   # sibling H2 drops the H3
        ]
        headings = [
            ProviderHeading("Alpha", 1, 1.0, "atx"),
            ProviderHeading("Alpha.1", 2, 1.0, "atx"),
            ProviderHeading("Alpha.1.1", 3, 1.0, "atx"),
            ProviderHeading("Alpha.2", 2, 1.0, "atx"),
        ]
        out = HeadingAssembler().assign(chunks, headings)
        assert out[-1].heading_path == ["Alpha", "Alpha.2"]

    def test_one_result_per_chunk(self):
        out = HeadingAssembler().assign(["a", "b", "c"], [])
        assert len(out) == 3


class TestHeadingAssemblerNormalizedSpaceMatching:
    """SPRINT31-B, Option B3: heading text and chunk lines are both projected
    through core.text_normalizer.normalize_pipeline_text — the same
    normalization real chunks undergo — before comparison."""

    def test_whitespace_variance_absorbed_by_normalization(self):
        # extra internal spaces (OCR/extraction noise) on the chunk side
        chunks = ["Introduction   to    Romans\n\nbody text here"]
        headings = [ProviderHeading("Introduction to Romans", 1, 0.8, "pdf-bold")]
        out = HeadingAssembler().assign(chunks, headings)
        assert out[0].heading_path == ["Introduction to Romans"]

    def test_still_rejects_partial_match_after_normalization(self):
        # normalization must not turn a substring match into a false positive
        chunks = ["INTRO\n\nsome body text here"]
        headings = [ProviderHeading("INTRODUCTION", 1, 0.8, "pdf-bold")]
        out = HeadingAssembler().assign(chunks, headings)
        assert out[0].heading_path == []

    def test_atx_marker_normalizes_same_as_bare_pdf_line(self):
        # "# Chapter 1" (Markdown) and a bare "Chapter 1" (PDF) both match
        # the same marker-free heading text after normalization.
        md_out = HeadingAssembler().assign(
            ["# Chapter 1\n\nbody"], [ProviderHeading("Chapter 1", 1, 1.0, "atx")]
        )
        pdf_out = HeadingAssembler().assign(
            ["Chapter 1\n\nbody"], [ProviderHeading("Chapter 1", 1, 0.8, "pdf-bold")]
        )
        assert md_out[0].heading_path == ["Chapter 1"] == pdf_out[0].heading_path


class TestHeadingAssemblerDuplicateHeadings:
    """SPRINT31-B required verification: identical titles under different
    parents must bind to their own position via the ordered cursor, not
    collapse to a single dict entry."""

    def test_duplicate_titles_bind_to_correct_chapter(self):
        chunks = [
            "# Chapter 1\n\nintro",
            "## Introduction\n\nfirst intro body",
            "# Chapter 2\n\nintro",
            "## Introduction\n\nsecond intro body",
        ]
        headings = [
            ProviderHeading("Chapter 1", 1, 1.0, "atx"),
            ProviderHeading("Introduction", 2, 1.0, "atx"),
            ProviderHeading("Chapter 2", 1, 1.0, "atx"),
            ProviderHeading("Introduction", 2, 1.0, "atx"),
        ]
        out = HeadingAssembler().assign(chunks, headings)
        assert out[1].heading_path == ["Chapter 1", "Introduction"]
        assert out[3].heading_path == ["Chapter 2", "Introduction"]

    def test_duplicate_at_same_level_does_not_desync_cursor(self):
        # three "Note" headings in a row, each must consume exactly one
        # occurrence in order, not all match the first one repeatedly.
        chunks = ["# Note\n\na", "# Note\n\nb", "# Note\n\nc"]
        headings = [
            ProviderHeading("Note", 1, 1.0, "atx"),
            ProviderHeading("Note", 1, 1.0, "atx"),
            ProviderHeading("Note", 1, 1.0, "atx"),
        ]
        out = HeadingAssembler().assign(chunks, headings)
        assert [a.heading_path for a in out] == [["Note"], ["Note"], ["Note"]]
        # each result's heading object is distinct in identity terms even
        # though text is identical (order-based, not text-keyed)
        assert out[0].heading_path == out[1].heading_path == out[2].heading_path


class TestHeadingAssemblerCursorRecovery:
    """SPRINT31-B-2 hardening: a heading that never appears verbatim in the
    chunk text (OCR corruption, extraction gap) must not permanently stall
    matching for every heading that follows it."""

    def test_recovers_after_one_undetectable_heading(self):
        chunks = [
            "# Chapter 1\n\nintro",
            # "## Lost Section" never appears literally in the extracted
            # text (simulating OCR corruption / a missed line) — omitted.
            "## Chapter 1 Continued\n\nbody one",
            "# Chapter 2\n\nintro two",
        ]
        headings = [
            ProviderHeading("Chapter 1", 1, 1.0, "atx"),
            ProviderHeading("Lost Section", 2, 0.7, "pdf-size"),  # never matches
            ProviderHeading("Chapter 1 Continued", 2, 1.0, "atx"),
            ProviderHeading("Chapter 2", 1, 1.0, "atx"),
        ]
        out = HeadingAssembler().assign(chunks, headings)
        # the skipped heading is simply absent, not a false match, and later
        # real headings still bind correctly instead of staying stuck.
        assert out[1].heading_path == ["Chapter 1", "Chapter 1 Continued"]
        assert out[2].heading_path == ["Chapter 2"]

    def test_no_match_within_window_does_not_advance_or_crash(self):
        # heading list has one entry that never appears anywhere; nothing
        # after it to recover onto — must degrade to empty, not raise.
        chunks = ["plain body", "more plain body"]
        headings = [ProviderHeading("Never Appears", 1, 0.5, "pdf-size")]
        out = HeadingAssembler().assign(chunks, headings)
        assert all(a.heading_path == [] for a in out)

    def test_still_exact_match_only_no_fuzzy_recovery(self):
        # recovery must not loosen matching into substrings even within
        # the lookahead window.
        chunks = ["INTRO\n\nbody", "INTRODUCTION\n\nbody"]
        headings = [ProviderHeading("INTRODUCTION", 1, 0.8, "pdf-bold")]
        out = HeadingAssembler().assign(chunks, headings)
        assert out[0].heading_path == []               # "INTRO" must not match
        assert out[1].heading_path == ["INTRODUCTION"]  # exact line does


class TestHeadingAssemblerBoundaryUnchanged:
    """HQ-required boundary check: chunk count and content before/after
    assembly must be identical (Assembler is read-only)."""

    def test_chunk_count_and_content_unchanged(self):
        chunks = ["# A\n\nbody one", "plain continuation", "## B\n\nbody two"]
        before_count = len(chunks)
        before_content = list(chunks)
        HeadingAssembler().assign(chunks, [
            ProviderHeading("A", 1, 1.0, "atx"),
            ProviderHeading("B", 2, 1.0, "atx"),
        ])
        assert len(chunks) == before_count
        assert chunks == before_content

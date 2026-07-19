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

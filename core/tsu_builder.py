"""core/tsu_builder.py — TSU v1 builder (Index Authority, library layer).

SPRINT20-I-C-2-B: scripts/build_tsu_dataset.py에서 TSU 생성 라이브러리
로직을 core로 승격한 모듈. Index Authority(docs/architecture/
DBMA-Index-Authority-Design-v1.md)의 "Registry → TSU JSONL" 책임을 담당한다.

원래 SPRINT17-RG-6A에서 배치 후처리 스크립트로 시작했으나, core service
layer(core/index_orchestrator.py)가 이 로직을 프로그래매틱하게 소비하면서
scripts에 두는 것이 부적절해졌다. CLI(argparse/print/main)는
scripts/build_tsu_dataset.py에 wrapper로 남고, 이 모듈은 순수 라이브러리다.

Design decisions (per SPRINT17-RG-5, 유지):
  - Batch post-processing, run separately from ingest (core/processing.py
    untouched) and separately from query time (core/retrieval.py untouched).
  - TSU schema is additive to what core/retrieval.py::RetrievalEngine already
    reads (tsu_id, content, verse_mapping, themes) plus two new link fields
    (document_id, chunk_id) that close the mapping gap identified in
    SPRINT17-RG-1/RG-4.
  - chunk_id is synthesized deterministically via
    core.document_identity.generate_chunk_id(document_id, idx) for
    idx in range(chunk_count) — the registry does not store chunk texts, so
    this module does not invent a new storage format for them; it reads the
    existing {stem}_chunks.txt file (save_chunks() output) when present.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, Optional

from core.document_identity import generate_chunk_id
from core.utils import make_safe_stem
from core.retrieval import NAME_TO_BOOK_ID, QueryParser, ScriptureReference
from core.canonical_constants import CANONICAL_MAX_CHAPTER
from core.noise_classifier import classify as classify_noise
from core.heading_extractor import HeadingStack
from core.heading_provider import get_registry, HeadingAssembler
from core.extractors import collect_pdf_spans
from core.config import DEFAULT_RAW_DIR


_CHUNK_HEADER_RE = re.compile(r"\[chunk \d+\]\n")

# [SPRINT18-C] Reuses the existing, already-stabilized scripture reference
# parsers (SPRINT18-A/B-1) against chunk *content* instead of query text —
# no new parsing logic is introduced. `core.retrieval.QueryParser` is the
# production entry point (module-level rebind to EnhancedQueryParser at the
# bottom of core/retrieval.py), so calling it here exercises the exact same
# combined extraction (colon form + chapter-only form) that already powers
# query-time parsing. One shared instance, since its alias cache is built
# lazily and reused across calls — constructing it once for the whole batch
# run avoids rebuilding that cache per chunk.
_reference_parser = QueryParser()


def _resolve_scripture_ref(content: str) -> Optional[ScriptureReference]:
    """Detect the first scripture reference in chunk content via the
    existing parser. Returns None if no reference is detected — never
    inferred/guessed (same "unknown = None" principle as
    _resolve_book_id() above). [SPRINT19-A] Single parse call shared by
    chapter, verse_start, and verse_end resolution below.
    """
    if not content:
        return None
    refs = _reference_parser.parse(content).scripture_refs
    return refs[0] if refs else None


def _resolve_chapter(content: str) -> Optional[int]:
    """Detect a chapter number from chunk content — first-match policy
    unchanged from SPRINT18-C."""
    ref = _resolve_scripture_ref(content)
    return ref.chapter if ref else None


# [SPRINT19-B] Scripture Evidence Resolver v1 — replaces the "first match
# wins" policy (_resolve_scripture_ref) at the build_tsu_records() call
# site with candidate scoring, so a target-book chapter:verse reference
# outranks an unrelated colon-adjacent digit sequence (index/appendix
# page noise, e.g. "2 Kings chapter=748") or a chapter-only match against
# a different book than the TSU's own filename-resolved book_id.
#
# Score components (HQ-specified weights, Preflight §5/§6):
#   canonical_range_valid  +0.3  chapter within the book's real chapter count
#   verse_explicit         +0.2  verse_start > 0 (not the parser's
#                                 "no verse specified" sentinel — Preflight
#                                 §4 found chapter-only matches encode
#                                 "no verse" as verse_start=0, which
#                                 SPRINT19-A's refs[0] policy had been
#                                 silently storing as if it were verse 0)
#   verse_range_present     +0.1  verse_end is set (an explicit "a-b" range)
#   duplicate_support       +0.2  the same (book_id, chapter) appears in
#                                 more than one candidate from this content
#   book_id_consistent      +0.2  candidate's book_id matches the TSU's own
#                                 filename-resolved book_id (HQ's "본문 위치
#                                 매치" — cross-checks the reference against
#                                 the document it actually came from)
# Ties broken by candidate order (first-seen wins), same as before.


def _score_candidate(
    ref: ScriptureReference,
    all_refs: list[ScriptureReference],
    tsu_book_id: Optional[str],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    max_ch = CANONICAL_MAX_CHAPTER.get(ref.book_id)
    if max_ch is not None and 1 <= ref.chapter <= max_ch:
        score += 0.3
        reasons.append("canonical_range_valid")

    if ref.verse_start and ref.verse_start > 0:
        score += 0.2
        reasons.append("verse_explicit")

    if ref.verse_end is not None:
        score += 0.1
        reasons.append("verse_range_present")

    duplicate_count = sum(
        1 for r in all_refs if r.book_id == ref.book_id and r.chapter == ref.chapter
    ) - 1
    if duplicate_count > 0:
        score += 0.2
        reasons.append("duplicate_support")

    if tsu_book_id is not None and ref.book_id == tsu_book_id:
        score += 0.2
        reasons.append("book_id_consistent")

    return min(score, 1.0), reasons


def _resolve_evidence(
    content: str,
    tsu_book_id: Optional[str],
) -> tuple[Optional[ScriptureReference], Optional[dict[str, Any]]]:
    """Score every scripture reference candidate found in content and
    return the highest-scoring one plus its provenance record. Returns
    (None, None) if no candidate is found — never guessed.
    """
    if not content:
        return None, None
    refs = _reference_parser.parse(content).scripture_refs
    if not refs:
        return None, None

    scored = [(_score_candidate(ref, refs, tsu_book_id), ref) for ref in refs]
    (best_score, best_reasons), best_ref = max(
        scored, key=lambda item: item[0][0]
    )

    provenance = {
        "resolver": "scripture_evidence_resolver_v1",
        "confidence": round(best_score, 4),
        "candidate_count": len(refs),
        "selected_reason": best_reasons,
    }
    return best_ref, provenance


def _resolve_book_id(source_file: str) -> Optional[str]:
    """Derive a book_id from source_file by substring match against
    core.retrieval.NAME_TO_BOOK_ID (the ADR-001 authoritative Korean/
    English book-name table QueryParser already uses to interpret user
    queries — reused here read-only, not redefined).

    [SPRINT17-Phase6A-1] registry.book is None for every currently
    registered document (Dataset Quality Audit finding), so every TSU
    record was previously tagged "GEN" regardless of actual content.
    This is a best-effort filename match, not a substitute for populating
    registry.book at ingest time (out of scope here — see Phase6A-1 plan
    §2, Location A).

    Longer names are checked first so e.g. "2 kings" doesn't shadow a
    later, more specific match; ties within the same length keep dict
    iteration order.

    Single-character aliases (e.g. "마" as a short-form query alias for
    MAT) are excluded — QueryParser only ever matches them via a
    word-boundary regex against short user queries (core/retrieval.py
    L405), never as a raw substring against arbitrary text. Applying the
    same substring test used for full book names here produced a false
    positive: "마가복음" (Mark) contains "마" and was silently
    misresolved to MAT (Matthew) before this guard was added.

    source_file is normalized to NFC before matching — macOS stores
    Korean filenames in NFD (decomposed) form in the registry, while
    NAME_TO_BOOK_ID's keys are NFC (composed); without this, byte-level
    substring matching silently fails for every Korean filename despite
    looking identical when printed (same fix pattern as
    ui/pages/library.py's PT-SEARCH-001 search-query normalization).
    """
    text = unicodedata.normalize("NFC", source_file).lower()
    candidates = [name for name in NAME_TO_BOOK_ID if len(name) >= 2]
    for name in sorted(candidates, key=len, reverse=True):
        if name in text:
            return NAME_TO_BOOK_ID[name]
    return None


def _read_chunk_texts(output_dir: Path, source_file: str) -> Optional[list[str]]:
    """Read per-chunk text from the deprecated {stem}_chunks.txt output, if present.

    Returns None if the file does not exist (e.g. SPRINT1_ONLY_MD_OUTPUT=True
    was in effect when the document was processed).
    """
    stem = make_safe_stem(source_file)
    txt_path = output_dir / f"{stem}_chunks.txt"
    if not txt_path.exists():
        return None

    raw = txt_path.read_text(encoding="utf-8")
    parts = [p.strip() for p in _CHUNK_HEADER_RE.split(raw) if p.strip()]
    return parts or None


def _read_md_fallback(output_dir: Path, source_file: str) -> Optional[str]:
    """Fallback content source: the canonical {stem}.md file.

    Used only when per-chunk text is unavailable. Coarser than real chunk
    boundaries — acceptable for a v1 skeleton, not a substitute for proper
    chunk-level TSU content in a later phase.
    """
    stem = make_safe_stem(source_file)
    md_path = output_dir / f"{stem}.md"
    if not md_path.exists():
        return None
    return md_path.read_text(encoding="utf-8")


def build_tsu_records(registry: dict, output_dir: Path) -> list[dict[str, Any]]:
    """Build TSU v1 records from identity registry documents.

    Read-only with respect to the registry and to core/processing.py output —
    this function only reads existing files, it does not call
    save_identity_registry() or otherwise mutate the registry.
    """
    records: list[dict[str, Any]] = []

    for document_id, doc in registry.get("documents", {}).items():
        source_file = doc.get("source_file", "")
        chunk_count = doc.get("chunk_count", 0)
        if chunk_count <= 0:
            continue

        chunk_ids = [generate_chunk_id(document_id, idx) for idx in range(chunk_count)]

        chunk_texts = _read_chunk_texts(output_dir, source_file)
        if chunk_texts is None:
            fallback_text = _read_md_fallback(output_dir, source_file) or ""
            chunk_texts = [fallback_text] * chunk_count

        # [SPRINT17-Phase6A-1] registry.book takes priority if a future
        # ingest-time fix populates it (see Phase6A-1 plan §2, Location A);
        # until then, fall back to filename-based resolution instead of the
        # previous unconditional "GEN" default, which mislabeled every
        # record regardless of actual content (Dataset Quality Audit
        # finding). "UNK" means no match was found — never invented.
        book_id = doc.get("book") or _resolve_book_id(source_file) or "UNK"

        # [SPRINT29-C] One HeadingStack per document, advanced in chunk order so
        # a chunk inherits the heading context established by earlier chunks.
        # Boundary-preserving: reads chunk content only, never re-chunks.
        # [SPRINT32-C] PDF documents use PdfHeadingProvider + HeadingAssembler
        # instead (SPRINT32-A Option 1) — HeadingStack/ATX detection is kept
        # unchanged for every other source_type (SPRINT32-C approved scope:
        # "MD: HeadingStack 유지"). assembled_headings is precomputed once per
        # PDF document (not per chunk) since the Assembler needs the full
        # chunk_texts list to walk in order.
        source_type = doc.get("source_type", "")
        heading_stack = HeadingStack()
        assembled_headings: Optional[list] = None
        if source_type == "pdf":
            raw_path = os.path.join(DEFAULT_RAW_DIR, source_file)
            spans = collect_pdf_spans(raw_path) if os.path.exists(raw_path) else []
            provider = get_registry().resolve("pdf")(spans)
            assembled_headings = HeadingAssembler().assign(chunk_texts, provider.headings())

        for idx, chunk_id in enumerate(chunk_ids):
            content = chunk_texts[idx] if idx < len(chunk_texts) else ""

            # [SPRINT18-C] verse_mapping is where RetrievalEngine actually
            # reads chapter from (_metadata_filter()/_scripture_alignment_score()
            # both read verse_mapping.get("chapter"), never the sibling
            # top-level "chapter" field below, which is unrelated
            # document-level metadata from the registry — see Phase18-C
            # Preflight for the schema-mismatch finding this fixes).
            verse_mapping: dict[str, Any] = {}
            provenance: Optional[dict[str, Any]] = None
            if book_id != "UNK":
                verse_mapping["book_id"] = book_id
                # [SPRINT19-B] "First match wins" (SPRINT18-C/19-A) replaced
                # with candidate scoring — see _resolve_evidence()/_score_candidate()
                # above. Never guessed: each key is set only when the
                # resolver's selected candidate actually carried that value.
                # verse_start==0 is the parser's "chapter-only, no verse
                # specified" sentinel (Preflight §4) — never stored as a
                # real verse.
                ref, provenance = _resolve_evidence(content, book_id)
                if ref is not None:
                    verse_mapping["chapter"] = ref.chapter
                    if ref.verse_start and ref.verse_start > 0:
                        verse_mapping["verse_start"] = ref.verse_start
                        if ref.verse_end is not None:
                            verse_mapping["verse_end"] = ref.verse_end

            record: dict[str, Any] = {
                # [SPRINT21-D fix] Was f"TSU-{book_id}-{len(records)+1:06d}" —
                # a counter local to the *batch being built*. build_tsu_records()
                # is called both on the full corpus (rebuild_tsu_index) and on
                # a single-document subset (reindex_document(), SPRINT20-I-C-3);
                # in the latter case len(records) restarts at 0 per call, so
                # every document sharing a book_id independently produced
                # TSU-{book}-000001, TSU-{book}-000002, ... — colliding across
                # documents (1448/8079 collisions observed in production,
                # SPRINT21-D). chunk_id is already a deterministic, globally
                # unique identifier (document_id-derived) regardless of which
                # batch a document is built in, so basing tsu_id on it makes
                # tsu_id collision-free by construction and stable across
                # full rebuilds and partial reindexes alike.
                "tsu_id": f"TSU-{book_id}-{chunk_id}",
                "document_id": document_id,
                "chunk_id": chunk_id,
                "content": content,
                "verse_mapping": verse_mapping,
                "themes": [],
                # [SPRINT17-Phase5-C1] M1-a — propagate document metadata
                # already present in identity_registry/DocumentContext
                # (Phase1-2) into TSU records, closing the gap identified in
                # Phase5-C0 preflight (dbma.py's 2026-07-15 metadata commits
                # were write-only and never consumed; this is the intended
                # target path instead).
                "title": doc.get("title"),
                "author": doc.get("author"),
                "chapter": doc.get("chapter"),
                "page": doc.get("page"),
                # [SPRINT20-E] propagate registry values already loaded
                # above (source_file, L245) or on doc (language,
                # source_type) — no new registry lookup, no inference.
                "source_file": source_file,
                "language": doc.get("language"),
                "source_type": doc.get("source_type"),
            }
            if provenance is not None:
                record["provenance"] = provenance

            # [SPRINT28-B] Additive-only TSU metadata — content_quality is a
            # new sibling field, no existing field above is touched or
            # removed. core/retrieval.py does not read this field yet
            # (SPRINT28-A design proposal deferred that to a separate
            # Retrieval Sprint); this only tags TSU records for future
            # consumption.
            noise_result = classify_noise(content)
            record["content_quality"] = {
                "noise_type": noise_result.noise_type,
                "quality_score": noise_result.quality_score,
                "section_type": noise_result.section_type,
            }

            # [SPRINT29-C] Additive heading foundation — same additive contract
            # as content_quality above (no existing field changed, retrieval
            # does not read it yet).
            # [SPRINT32-C] PDF documents read heading_path/confidence/source
            # from the precomputed assembled_headings (PdfHeadingProvider +
            # HeadingAssembler, SPRINT31 Phase A/D/B). Every other source_type
            # keeps the unchanged HeadingStack/ATX path — heading_confidence/
            # heading_source are populated here too (1.0/"atx" when a heading
            # matched, 0.0/"" when not) purely to normalize the record shape;
            # HeadingStack's own ATX detection logic is untouched.
            if assembled_headings is not None:
                a = assembled_headings[idx]
                record["structure"] = {
                    "heading_path": a.heading_path,
                    "heading_depth": a.heading_depth,
                    "heading_confidence": a.heading_confidence,
                    "heading_source": a.heading_source,
                }
            else:
                chunk_heading = heading_stack.apply_chunk(content)
                record["structure"] = {
                    "heading_path": chunk_heading.heading_path,
                    "heading_depth": chunk_heading.heading_depth,
                    "heading_confidence": 1.0 if chunk_heading.heading_path else 0.0,
                    "heading_source": "atx" if chunk_heading.heading_path else "",
                }

            records.append(record)

    return records


def write_tsu_dataset(records: list[dict[str, Any]], dataset_path: Path) -> None:
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dataset_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _git_commit_hash() -> Optional[str]:
    """Current HEAD commit hash, or None if git is unavailable (e.g. a zip
    distribution with no .git directory) — never invented/guessed."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(__file__).resolve().parent.parent),
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8").strip() or None
    except Exception:
        return None


def _sha256_of_file(path: Path) -> Optional[str]:
    """SHA-256 of a file's bytes, or None if it can't be read — never a
    placeholder/empty-string value."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def write_manifest(
    records: list[dict[str, Any]],
    registry: dict,
    manifest_path: Path,
    registry_path: Optional[Path] = None,
    dataset_path: Optional[Path] = None,
    config_path: Optional[Path] = None,
) -> dict:
    source_document_count = len({
        doc_id for doc_id, doc in registry.get("documents", {}).items()
        if doc.get("chunk_count", 0) > 0
    })
    manifest = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "tsu_count": len(records),
        "source_document_count": source_document_count,
        # [SPRINT20-F2] provenance fields — None when the underlying source
        # is unavailable (e.g. no .git, file not readable), never invented.
        "build_commit": _git_commit_hash(),
        "builder_script": "scripts/build_tsu_dataset.py",
        "registry_path": str(registry_path) if registry_path is not None else None,
        "registry_sha256": _sha256_of_file(registry_path) if registry_path is not None else None,
        "dataset_sha256": _sha256_of_file(dataset_path) if dataset_path is not None else None,
        "dataset_records": len(records),
        "config_file": "config.yaml",
        "config_sha256": _sha256_of_file(config_path) if config_path is not None else None,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest

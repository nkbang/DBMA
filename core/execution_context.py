"""core/execution_context.py — ExecutionContext v1.

Thin, stateless, read-only wrapper around existing runtime-state, feature-flag,
and identity-registry query functions (see docs/architecture/
DBMA-SPRINT17-Implementation-Plan-v1.md §2, and SPRINT17-Phase3-A/B analysis).

ExecutionContext owns no state of its own — every method delegates to an
existing module and returns its result unchanged (or, for get_document_state,
assembles a DocumentContext from an existing registry record). It does not
instantiate RetrievalEngine, load any embedding model, or cache anything
across calls.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from core.runtime_state import (
    get_pipeline_status,
    get_pipeline_status_dict,
    _read_tsu_manifest,
    PipelineStageState,
)
from core.feature_flags import feature_enabled
from core.identity_registry import load_identity_registry
from core.document_context import DocumentContext

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_REGISTRY_PATH

# [SPRINT17-Phase5-C4.2] Resolves against config.yaml's directories.output_dir
# instead of a hardcoded "output" literal — same stale-path class of issue as
# Phase5-C4.1 (get_tsu_status), found while auditing this file's other
# hardcoded path during that fix.
_DEFAULT_REGISTRY_PATH = DEFAULT_REGISTRY_PATH


class ExecutionContext:
    """Stateless read-only query facade over runtime state, feature flags,
    and per-document identity state.

    No required constructor arguments, no global singleton, no caching —
    every method call re-queries its underlying source fresh.
    """

    def __init__(self) -> None:
        pass

    def get_pipeline_status(self) -> list[PipelineStageState]:
        """Return core.runtime_state.get_pipeline_status() unchanged."""
        return get_pipeline_status()

    def get_pipeline_status_dict(self) -> Dict[str, Any]:
        """Return core.runtime_state.get_pipeline_status_dict() unchanged."""
        return get_pipeline_status_dict()

    def is_feature_enabled(self, name: str) -> bool:
        """Return core.feature_flags.feature_enabled(name) unchanged."""
        return feature_enabled(name)

    def get_tsu_status(self) -> Dict[str, Any]:
        """Return the TSU manifest status dict from core.runtime_state.

        Does not instantiate RetrievalEngine or touch core.retrieval at all.

        [SPRINT17-Phase5-C4.1] Resolves against config.yaml's
        directories.output_dir (DEFAULT_OUTPUT_DIR) instead of a hardcoded
        "output" literal — see Phase5-C4 discovery for why the hardcoded
        path pointed at a stale, unrelated directory.
        """
        from pathlib import Path
        return _read_tsu_manifest(Path(DEFAULT_OUTPUT_DIR))

    def get_document_state(self, document_id: str) -> Optional[DocumentContext]:
        """Look up a document in the identity registry and return it as a
        DocumentContext, or None if not found. Read-only — never writes
        back to the registry.
        """
        registry = load_identity_registry(_DEFAULT_REGISTRY_PATH)
        record = registry.get("documents", {}).get(document_id)
        if record is None:
            return None

        context = DocumentContext(
            document_id=record.get("document_id", document_id),
            file_hash=record.get("file_hash", ""),
            source_file=record.get("source_file", ""),
            source_type=record.get("source_type", ""),
            is_ocr=record.get("is_ocr", False),
            created_at=record.get("created_at", ""),
        )
        context.title = record.get("title")
        context.author = record.get("author")
        context.book = record.get("book")
        context.chapter = record.get("chapter")
        context.page = record.get("page")
        context.language = record.get("language", context.language)
        context.noise_score = record.get("noise_score", context.noise_score)
        context.noise_mode = record.get("noise_mode", context.noise_mode)
        context.chunk_count = record.get("chunk_count", context.chunk_count)
        context.ingest_status = record.get("ingest_status", context.ingest_status)
        context.retry_count = record.get("retry_count", context.retry_count)
        context.last_failure_reason = record.get("last_failure_reason")
        if "pipeline_flags" in record:
            context.pipeline_flags = dict(record["pipeline_flags"])

        return context

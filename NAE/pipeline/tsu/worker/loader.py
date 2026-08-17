"""Loader: enqueue canonical candidates into the TSU Extraction Queue (Phase 3).

Uses parser.build_candidates() — no re-implementation.
candidate_id is deterministically generated from identifier+page+paragraph_index+sentence_index.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .. import config as tsu_config, parser
from . import state as worker_state


def _make_candidate_id(identifier: str, page: int, paragraph_index: int, sentence_index: int) -> str:
    """Deterministic candidate_id from source position."""
    raw = f"{identifier}|p{page}|para{paragraph_index}|sent{sentence_index}"
    return "cand-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def enqueue_from_canonical(
    identifier: str,
    state_store,
    max_candidates: int | None = None,
    canonical_root: Path = tsu_config.CANONICAL_ROOT,
    raw_root: Path = tsu_config.RAW_ROOT,
) -> int:
    """Build candidates from canonical.json and enqueue them as READY.

    Already-present candidate_ids (any state) are left untouched (idempotent).
    Returns the number of NEW candidates added to READY.
    """
    candidates = parser.build_candidates(identifier, canonical_root=canonical_root, raw_root=raw_root)
    if not candidates:
        return 0

    new_count = 0
    for cand in candidates[:max_candidates] if max_candidates else candidates:
        cid = _make_candidate_id(cand.identifier, cand.page, cand.paragraph_index, cand.sentence_index)
        existing = state_store.get_state(cid)
        if existing is not None:
            # Already in queue — skip (idempotent)
            continue
        state_store.set_state(
            cid,
            worker_state.TSUExtractionState.READY,
            metadata={
                "source_identifier": cand.identifier,
                "source_book": cand.book,
                "source_author": cand.author,
                "page": cand.page,
                "paragraph_index": cand.paragraph_index,
                "sentence_index": cand.sentence_index,
                "text": cand.text,
                "collector_version": cand.collector_version,
                "canonical_version": cand.canonical_version,
            },
        )
        new_count += 1

    state_store.save()
    return new_count

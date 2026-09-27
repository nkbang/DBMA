"""core/evidence_pool.py — Evidence Pool & Retrieval Boundary Integration.

Phase 2: Creates an intermediate layer between Evidence and downstream consumers.
RetrievalEngine/HybridQueryProcessor authority is preserved unchanged.

Architecture:
    Query
      ↓
    RetrievalEngine.retrieve() / HybridQueryProcessor.process()  (unchanged)
      ↓
    list[RankedCandidate]
      ↓
    RankedCandidateEvidenceAdapter  (Phase 1, unchanged)
      ↓
    list[Evidence]
      ↓
    EvidencePool  (Phase 2, this module)

ABSOLUTE RULES:
- No score calculation
- No re-ranking (all() preserves insertion order)
- No Evidence mutation
- No retrieval execution
- No modification of core/evidence_model.py, core/retrieval.py, etc.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.evidence_model import Evidence
from core.evidence_adapters.tsu_adapter import RankedCandidateEvidenceAdapter
from core.retrieval import RankedCandidate

logger = logging.getLogger(__name__)


class EvidencePool:
    """Immutable evidence storage with query/corpus filtering.

    Duplicate identity policy:
        When add() / add_batch() encounters an evidence_id that already exists
        in the pool, the NEW evidence OVERWRITES the existing one.

        Rationale:
        - A re-executed query may produce updated scores or metadata for the
          same source (e.g., after ranking refinement). Overwriting ensures the
          pool always holds the latest version.
        - Evidence is immutable (frozen dataclass), so "overwrite" means replacing
          the dict entry — no mutation of existing objects.
        - Silently ignoring duplicates would hide potential updates and make
          debugging harder.

    Order preservation:
        all() returns evidence in insertion order (first-seen to last-seen).
        Duplicate overwrites do NOT change position — the key's slot remains
        at its original insertion index.
    """

    def __init__(self, default_query: str = "") -> None:
        # Internal storage: ordered list of (evidence_id, Evidence, build_query|None) tuples
        # build_query is the query context from build_evidence_pool_from_ranked_candidates()
        # Used by by_query() when Evidence.retrieval_query is None (RankedCandidate path).
        self._evidences: list[tuple[str, Evidence, Optional[str]]] = []
        # Index for O(1) lookup and overwrite detection
        self._index: dict[str, int] = {}
        # default_query is a legacy fallback — kept for backward compatibility.
        # New code should use build_query stored per-evidence instead.
        self._default_query = default_query

    def add(self, evidence: Evidence, build_query: Optional[str] = None) -> None:
        """Add a single evidence to the pool.

        If evidence_id already exists, overwrite in place (position unchanged).

        Args:
            evidence: The Evidence object to add.
            build_query: Optional query context from the build path.
                When Evidence.retrieval_query is None (RankedCandidate path),
                this value is used by by_query() for filtering.
        """
        eid = evidence.evidence_id
        if eid in self._index:
            idx = self._index[eid]
            self._evidences[idx] = (eid, evidence, build_query)
        else:
            self._evidences.append((eid, evidence, build_query))
            self._index[eid] = len(self._evidences) - 1

    def add_batch(self, evidences: list[Evidence], build_query: Optional[str] = None) -> int:
        """Add multiple evidences to the pool.

        Args:
            evidences: List of Evidence objects to add.
            build_query: Optional query context applied to all evidences in this batch.
                When Evidence.retrieval_query is None, this value is used by by_query()
                for filtering.

        Returns:
            Number of evidences successfully added (including overwrites).
        """
        count = 0
        for evidence in evidences:
            self.add(evidence, build_query=build_query)
            count += 1
        return count

    def get(self, evidence_id: str) -> Optional[Evidence]:
        """Fetch evidence by ID. Returns None if not found."""
        if evidence_id in self._index:
            idx = self._index[evidence_id]
            return self._evidences[idx][1]
        return None

    def all(self) -> list[Evidence]:
        """Return all evidences in insertion order (no re-ranking)."""
        return [ev for _, ev, _ in self._evidences]

    def by_query(self, query: Optional[str] = None) -> list[Evidence]:
        """Filter evidences by retrieval_query match.

        Matching logic:
            1. If Evidence.retrieval_query is not None and matches query → include.
            2. If Evidence.retrieval_query is None AND build_query matches query → include.
            3. If query is None, falls back to default_query set at construction time.

        This ensures both:
            - Explicit retrieval_query path (TSUEvidenceAdapter) works as before.
            - RankedCandidate integration path (build_evidence_pool_from_ranked_candidates)
              correctly filters by the build-time query context.
        """
        target = query if query is not None else self._default_query
        results: list[Evidence] = []
        for _, ev, build_q in self._evidences:
            # Priority 1: explicit retrieval_query
            if ev.retrieval_query is not None and ev.retrieval_query == target:
                results.append(ev)
            # Priority 2: build_query context (RankedCandidate path)
            elif ev.retrieval_query is None and build_q is not None and build_q == target:
                results.append(ev)
        return results

    def by_corpus_type(self, corpus_type: str) -> list[Evidence]:
        """Filter evidences by exact corpus_type match."""
        return [ev for _, ev, _ in self._evidences if ev.corpus_type == corpus_type]

    def __len__(self) -> int:
        return len(self._evidences)

    def __contains__(self, evidence_id: str) -> bool:
        return evidence_id in self._index


def build_evidence_pool_from_ranked_candidates(
    candidates: list[RankedCandidate],
    query: str,
    pool: Optional[EvidencePool] = None,
) -> EvidencePool:
    """Convert a list of RankedCandidate to an EvidencePool.

    This function does NOT call RetrievalEngine or create new retrieval paths.
    It only transforms already-produced list[RankedCandidate] into EvidencePool.

    Parameters
    ----------
    candidates : list[RankedCandidate]
        Already-ranked candidates from any retrieval source.
    query : str
        The original query string (used as pool's default_query for by_query filtering).
    pool : EvidencePool or None
        If given, evidences are added to this existing pool (append mode).
        If None, a new pool is created with the query context.

    Returns
    -------
    EvidencePool
        Pool containing Evidence objects with all scores/identity/provenance preserved.
    """
    if pool is None:
        pool = EvidencePool(default_query=query)
    else:
        # Preserve existing pool's default_query; don't overwrite it
        pass

    adapter = RankedCandidateEvidenceAdapter()
    evidences = adapter.adapt_batch(candidates)

    pool.add_batch(evidences, build_query=query)
    return pool

"""EvidenceSourceAdapter 인터페이스와 코퍼스별 어댑터 패키지.

core.dataset_adapters (성경 태그 전용) 와는 별개 — 이 패키지는 코퍼스 범용 어댑터를 다룬다.

Phase 1 additions:
    - TSUEvidenceAdapter: TSU retrieval result → Evidence 변환
    - TSUEvidenceFactory: Evidence 생성 factory + corpus_type resolver
    - RankedCandidateEvidenceAdapter: RankedCandidate → Evidence 변환 (score preservation)
"""

from core.evidence_adapters.base import EvidenceSourceAdapter
from core.evidence_adapters.tsu_adapter import (
    RankedCandidateEvidenceAdapter,
    TSUEvidenceAdapter,
    TSUEvidenceFactory,
)

__all__ = [
    "EvidenceSourceAdapter",
    "RankedCandidateEvidenceAdapter",
    "TSUEvidenceAdapter",
    "TSUEvidenceFactory",
]

"""EvidenceSourceAdapter 인터페이스와 코퍼스별 어댑터 패키지.

core.dataset_adapters (성경 태그 전용) 와는 별개 — 이 패키지는 코퍼스 범용 어댑터를 다룬다.
"""

from core.evidence_adapters.base import EvidenceSourceAdapter

__all__ = ["EvidenceSourceAdapter"]
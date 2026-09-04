"""EvidenceSourceAdapter — 외부 자료(Logos/DEVONthink/Obsidian 등)를 EvidenceUnit 리스트로 변환하는 인터페이스.

core.dataset_adapters.DatasetAdapter(Sprint B, 성경 태그 전용) 와는 별개 —
이쪽은 코퍼스 범용이다.
"""

from abc import ABC, abstractmethod
from core.evidence_unit import EvidenceUnit


class EvidenceSourceAdapter(ABC):
    """외부 자료(Logos/DEVONthink/Obsidian 등)를 EvidenceUnit 리스트로 변환하는 인터페이스.

    core.dataset_adapters.DatasetAdapter(Sprint B, 성경 태그 전용)와는 별개 —
    이쪽은 코퍼스 범용.
    """

    @abstractmethod
    def load_evidence(self, source_path: str) -> list[EvidenceUnit]:
        """source_path 에 위치한 자료에서 EvidenceUnit 리스트를 로드한다.

        Parameters
        ----------
        source_path : str
            자료의 경로. 실제 DEVONthink 연동 시에는 UUID, 파일 경로, URI 등이 될 수 있다.
            픽스처 테스트에서는 JSON 파일 경로를 받는다.

        Returns
        -------
        list[EvidenceUnit]
            변환된 EvidenceUnit 인스턴스 리스트.
        """
        ...
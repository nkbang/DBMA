"""scripts/crosswalk/resolver.py — Manifest identifier → Corpus identifier
Resolver (NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001).

`resolve(source_identifier)`는 정확히 일치하는 Crosswalk Record만
조회한다 — fuzzy matching/이름 검색/자동 추론을 절대 하지 않는다
(Mapping Policy Rule 3 "추측 매핑 금지"의 코드 레벨 강제).
"""

from __future__ import annotations

from .repository import CrosswalkRepository
from .schema import CrosswalkRecord


class CrosswalkResolver:
    def __init__(self, repository: CrosswalkRepository) -> None:
        self.repository = repository

    def resolve(self, source_identifier: str) -> str | None:
        """source_identifier(Registry/Manifest source_id)에 대응하는
        target_identifier(Corpus/TSU identifier)를 반환한다.

        Gate-eligible(mapping_status가 verified/manual-confirmed AND
        confidence_score==1.0 AND evidence 존재, schema.py
        CrosswalkRecord.is_gate_eligible()) 레코드가 **정확히 1개**일
        때만 값을 반환한다. 0개(매핑 없음) 또는 2개 이상(모호함 —
        어느 쪽이 맞는지 정할 근거가 없으므로 안전하게 실패 처리)이면
        `None`을 반환한다. exact string equality만 사용 — 어떤 형태의
        유사도/추론도 수행하지 않는다.
        """
        eligible = [r for r in self.repository.get_by_source(source_identifier) if r.is_gate_eligible()]
        if len(eligible) != 1:
            return None
        return eligible[0].target_identifier

    def resolve_record(self, source_identifier: str) -> CrosswalkRecord | None:
        """target_identifier 문자열이 아니라 근거가 되는 CrosswalkRecord
        전체가 필요한 호출자(예: TSU Gate Adapter)를 위한 변형."""
        eligible = [r for r in self.repository.get_by_source(source_identifier) if r.is_gate_eligible()]
        if len(eligible) != 1:
            return None
        return eligible[0]

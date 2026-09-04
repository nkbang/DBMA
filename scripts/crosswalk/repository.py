"""scripts/crosswalk/repository.py — Crosswalk 저장소 인터페이스
(NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001).

`docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md` §3의 3개 저장 위치
후보(별도 YAML 파일 / Manifest 확장 필드 / metadata layer DB) 중
어느 것도 이번 구현에서 확정하지 않는다(ADR-019 Storage Decision
조건부 보류) — `CrosswalkRepository`는 추상 인터페이스만 정의하고,
`InMemoryCrosswalkRepository`는 테스트/Resolver 참조용 구현일 뿐
production storage 결정이 아니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .schema import CrosswalkRecord


class DuplicateCrosswalkIdError(ValueError):
    """이미 존재하는 crosswalk_id로 add()를 호출한 경우(NAE-CROSSWALK-
    TEST-EVIDENCE-FIX-001 T2 "duplicate detection")."""


class CrosswalkRepository(ABC):
    """Crosswalk Record 저장소 추상 인터페이스.

    저장 위치(YAML/Manifest 필드/DB)와 무관하게 구현 가능해야 한다 —
    구체 구현체는 이 인터페이스만 만족하면 Resolver/Validator에 그대로
    주입 가능하다(의존성 역전 — Resolver/Validator는 이 추상 클래스에만
    의존한다).
    """

    @abstractmethod
    def get(self, crosswalk_id: str) -> CrosswalkRecord | None: ...

    @abstractmethod
    def get_by_source(self, source_identifier: str) -> list[CrosswalkRecord]: ...

    @abstractmethod
    def list_all(self) -> list[CrosswalkRecord]: ...

    @abstractmethod
    def add(self, record: CrosswalkRecord) -> None:
        """새 레코드를 저장한다. 이미 존재하는 crosswalk_id면
        `DuplicateCrosswalkIdError`를 발생시켜야 한다(구현체 공통 계약)."""
        ...


class InMemoryCrosswalkRepository(CrosswalkRepository):
    """참조/테스트용 구현 — production storage 결정이 아니다.

    실제 저장 위치가 확정되면(§Storage Decision Review) 이 클래스를
    대체할 구현체(예: `YamlFileCrosswalkRepository`,
    `ManifestFieldCrosswalkRepository`)를 추가하되, `CrosswalkRepository`
    인터페이스만 지키면 Resolver/Validator 코드는 무수정으로 재사용
    가능하다.
    """

    def __init__(self) -> None:
        self._records: dict[str, CrosswalkRecord] = {}

    def get(self, crosswalk_id: str) -> CrosswalkRecord | None:
        return self._records.get(crosswalk_id)

    def get_by_source(self, source_identifier: str) -> list[CrosswalkRecord]:
        return [r for r in self._records.values() if r.source_identifier == source_identifier]

    def list_all(self) -> list[CrosswalkRecord]:
        return list(self._records.values())

    def add(self, record: CrosswalkRecord) -> None:
        if record.crosswalk_id in self._records:
            raise DuplicateCrosswalkIdError(
                f"crosswalk_id 중복: {record.crosswalk_id!r}(이미 저장소에 존재)"
            )
        self._records[record.crosswalk_id] = record

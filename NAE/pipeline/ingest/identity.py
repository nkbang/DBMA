"""Identity model — Author -> Work -> Edition -> Source File -> TSU.

Batch 번호(`batch_0024` 등)는 processing unit(어느 Human Review 배치에서
처리됐는가)일 뿐 identity가 아니다 — Promotion마다 재계산되는 pool-front
슬라이스([[NAE/review/human/batch_manager.py]] 참고)이므로 같은 TSU가
다른 배치 번호를 가질 수 있다. Identity는 아래 계층만 사용한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IdentityKey:
    """TSU 레코드 하나를 가리키는 안정적 identity. 전부 TSU 레코드에 이미
    존재하는 필드에서만 파생한다 — 새 필드를 요구하지 않는다."""
    author_id: str
    work_id: str
    edition_id: str
    source_file_id: str
    tsu_id: str

    @property
    def edition_key(self) -> tuple[str, str, str]:
        """author/work/edition만으로 구성된 상위 키 — TSU 단위가 아니라
        판본 단위 재처리 판단(예: 특정 edition의 원문이 통째로 바뀐 경우)에
        사용한다."""
        return (self.author_id, self.work_id, self.edition_id)


def extract_identity(record: dict[str, Any]) -> IdentityKey:
    """TSU 레코드에서 identity를 추출한다. `source_file_id`는 전용 필드가
    아직 없으므로 `source_id`(source_identifier가 없으면 identifier)로
    대체한다 — source_id는 이미 `resources/theological_sources/*/source_manifest.yaml`
    의 1차 키이므로 이 계층에서 재정의하지 않는다."""
    return IdentityKey(
        author_id=record.get("author_id", ""),
        work_id=record.get("work_id", ""),
        edition_id=record.get("edition_id", ""),
        source_file_id=record.get("source_id") or record.get("source_identifier") or record.get("identifier", ""),
        tsu_id=record["id"],
    )


def validate_identity(key: IdentityKey) -> list[str]:
    """빈 identity 필드를 나열한다(전부 채워져 있어야 정상). 빈 리스트면
    유효."""
    missing = []
    if not key.author_id:
        missing.append("author_id")
    if not key.work_id:
        missing.append("work_id")
    if not key.edition_id:
        missing.append("edition_id")
    if not key.source_file_id:
        missing.append("source_file_id")
    if not key.tsu_id:
        missing.append("tsu_id")
    return missing

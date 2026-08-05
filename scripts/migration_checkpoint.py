"""scripts/migration_checkpoint.py — Migration Engine Checkpoint 관리
(NAE-METADATA-MIGRATION-IMPLEMENTATION-001).

Migration Unit 단위로 Checkpoint A(before)/B(after) 스냅샷을 저장·조회
한다(설계: docs/NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md §3 — "Migration
Unit 1개 = Checkpoint 1개"). 이 모듈은 Registry/Manifest/RAW 등 특정
파일 경로를 전혀 알지 못한다 — 호출자가 넘겨준 임의의 경로 집합에
대해서만 동작하는 범용 인프라다.

이번 구현은 Migration Engine 자체만 대상이며, 실제 Registry/Manifest/
RAW/YAML/TSU/Embedding을 수정하지 않는다.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Checkpoint:
    migration_unit_id: str
    stage: str  # "before" | "after"
    files: dict[str, str]  # path(str) -> sha256
    contents: dict[str, str] = field(default_factory=dict)  # path(str) -> raw content(before만 채움, restore용)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "migration_unit_id": self.migration_unit_id,
            "stage": self.stage,
            "files": self.files,
            "contents": self.contents,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(
            migration_unit_id=data["migration_unit_id"],
            stage=data["stage"],
            files=data.get("files", {}),
            contents=data.get("contents", {}),
            extra=data.get("extra", {}),
        )


class CheckpointManager:
    """Migration Unit별 Checkpoint를 JSON 파일로 저장/조회한다."""

    def __init__(self, checkpoint_dir: Path) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, migration_unit_id: str, stage: str) -> Path:
        return self.checkpoint_dir / f"{migration_unit_id}.{stage}.json"

    def save(self, checkpoint: Checkpoint) -> Path:
        path = self._path(checkpoint.migration_unit_id, checkpoint.stage)
        path.write_text(json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, migration_unit_id: str, stage: str) -> Checkpoint | None:
        path = self._path(migration_unit_id, stage)
        if not path.exists():
            return None
        return Checkpoint.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def has(self, migration_unit_id: str, stage: str) -> bool:
        return self._path(migration_unit_id, stage).exists()

    def resume_candidates(self) -> list[str]:
        """'before' Checkpoint는 있는데 'after' Checkpoint가 없는 Migration
        Unit ID 목록 — 중단된(Failure Recovery 대상) Migration Unit."""
        candidates = []
        for path in sorted(self.checkpoint_dir.glob("*.before.json")):
            unit_id = path.name[: -len(".before.json")]
            if not self.has(unit_id, "after"):
                candidates.append(unit_id)
        return candidates

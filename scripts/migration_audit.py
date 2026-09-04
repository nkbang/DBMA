"""scripts/migration_audit.py — Migration Engine Audit Log
(NAE-METADATA-MIGRATION-IMPLEMENTATION-001, 설계 §6).

append-only JSONL. 기존 레코드는 절대 수정/삭제하지 않는다(설계
§2 COMPLETE 불변성과 동일 원칙). 이 모듈은 Registry/Manifest/RAW
어떤 경로도 알지 못한다 — 호출자가 지정한 임의의 audit 파일 경로에
대해서만 동작한다.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class AuditRecord:
    timestamp: float
    operator: str
    migration_version: str
    migration_unit: str
    before_checksum: str | None
    after_checksum: str | None
    result: str  # PASS | FAIL | ROLLED_BACK | DRY_RUN | SKIPPED
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuditLogger:
    def __init__(self, audit_path: Path) -> None:
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: AuditRecord) -> None:
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        records = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records

    def find_by_unit(self, migration_unit_id: str) -> list[dict[str, Any]]:
        return [r for r in self.read_all() if r.get("migration_unit") == migration_unit_id]

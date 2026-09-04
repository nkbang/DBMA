"""scripts/crosswalk/storage/index_manager.py — Crosswalk index.json 관리
(NAE-CROSSWALK-STORAGE-ADAPTER-IMPLEMENTATION-001 §4).

`crosswalk.yaml`이 정본(authoritative)이고, `index.json`은 그로부터
언제든 다시 만들 수 있는(rebuildable) lookup 캐시일 뿐이다 — 이
모듈은 `index.json`을 직접 손으로 편집하는 경로를 제공하지 않는다
(항상 `CrosswalkRecord` 목록으로부터 `rebuild()`).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scripts.crosswalk.schema import CrosswalkRecord


class IndexManager:
    """`index.json`(crosswalk_id -> {source_identifier, target_identifier})
    를 관리한다. YAML authority 원칙: 이 클래스는 절대 `crosswalk.yaml`을
    읽거나 쓰지 않는다 — 호출자(YamlCrosswalkRepository)가 이미 로드한
    레코드 목록을 넘겨준다.
    """

    def __init__(self, index_path: Path) -> None:
        self.index_path = Path(index_path)

    def rebuild(self, records: list[CrosswalkRecord]) -> dict[str, dict[str, str]]:
        index: dict[str, dict[str, str]] = {
            record.crosswalk_id: {
                "source_identifier": record.source_identifier,
                "target_identifier": record.target_identifier,
            }
            for record in records
        }
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return index

    def load(self) -> dict[str, Any]:
        """현재 저장된 index.json을 읽기만 한다(정합성 보장 없음 —
        `crosswalk.yaml`과 어긋날 수 있으므로, 신뢰할 조회가 필요하면
        항상 `rebuild()` 이후의 반환값이나 Repository를 통해야 한다)."""
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

"""Incremental processing state — TSU 단위 진행 상태 추적.

상태 저장소는 Production TSU 파일(`NAE/corpus/tsu/*/tsu.json`)과 완전히
분리된 별도 파일이다 — Production 레코드에 필드를 추가하지 않는다(스키마
불변 원칙, ADR Freeze Rule 위반 방지). 기본 경로는
`NAE/pipeline/ingest/state/incremental_state.json`이며, 이 파일이 없으면
빈 상태로 시작한다(최초 실행).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

STATE_DIR = Path(__file__).resolve().parent / "state"
DEFAULT_STATE_PATH = STATE_DIR / "incremental_state.json"


class ProcessingState(str, Enum):
    DISCOVERED = "DISCOVERED"
    IDENTIFIED = "IDENTIFIED"
    INGESTED = "INGESTED"
    TSU_GENERATED = "TSU_GENERATED"
    VALIDATED = "VALIDATED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    PROMOTED = "PROMOTED"
    EMBEDDED = "EMBEDDED"
    INDEXED = "INDEXED"

    # 실패 상태 — 성공한 다른 TSU의 재처리를 막지 않기 위해 별도 보존
    VALIDATION_FAILED = "VALIDATION_FAILED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"
    INDEX_FAILED = "INDEX_FAILED"


TERMINAL_SUCCESS = {ProcessingState.INDEXED}
FAILURE_STATES = {
    ProcessingState.VALIDATION_FAILED,
    ProcessingState.HUMAN_REVIEW_REQUIRED,
    ProcessingState.EMBEDDING_FAILED,
    ProcessingState.INDEX_FAILED,
}


class IncrementalStateStore:
    """tsu_id -> {state, content_hash, updated_at} 맵을 디스크에 보존한다.
    실패한 레코드가 있어도 나머지 성공 레코드의 상태는 독립적으로
    유지된다 — 한 레코드의 실패가 다른 레코드의 재처리를 유발하지
    않는다."""

    def __init__(self, path: Path = DEFAULT_STATE_PATH):
        self.path = path
        self._data: dict[str, dict[str, Any]] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def get_state(self, tsu_id: str) -> ProcessingState | None:
        entry = self._data.get(tsu_id)
        return ProcessingState(entry["state"]) if entry else None

    def get_hash(self, tsu_id: str) -> str | None:
        entry = self._data.get(tsu_id)
        return entry.get("content_hash") if entry else None

    def known_hashes(self) -> dict[str, str]:
        return {tid: e["content_hash"] for tid, e in self._data.items() if "content_hash" in e}

    def set_state(self, tsu_id: str, state: ProcessingState, content_hash: str | None = None) -> None:
        entry = self._data.setdefault(tsu_id, {})
        entry["state"] = state.value
        if content_hash is not None:
            entry["content_hash"] = content_hash
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def summary(self) -> dict[str, int]:
        from collections import Counter
        return dict(Counter(e["state"] for e in self._data.values()))

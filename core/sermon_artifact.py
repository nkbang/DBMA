"""core/sermon_artifact.py — SermonArtifact: 생성된 설교를 1급 객체로
영속화하는 저장소 (P1, DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md §4).

TSU/registry와 물리적으로 분리된 별도 디렉터리(DEFAULT_SERMON_ARTIFACT_DIR)
에 문서 1건 = 파일 1개로 저장한다. 식별자(`SRM-` 접두사)는
identity_registry의 document_id와 다른 네임스페이스를 쓴다 — 같은
registry 파일을 공유하지 않으므로 충돌 위험이 없다(C1-TASK-ORDER-069
RQ-4, docs/DBMA_SERMON_ARTIFACT_C1_REVIEW_RESULT_001.md).

candidate 본문은 저장하지 않고 tsu_id만 저장한다 — TSU 데이터셋이
정본이고 중복 저장은 드리프트 원인이 된다(설계 §4 설계 판단).
"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.config import DEFAULT_SERMON_ARTIFACT_DIR

INDEX_FILENAME = "index.jsonl"


def generate_sermon_id() -> str:
    """SRM-{YYYYMMDD}-{6자리 hex} — identity_registry의 document_id(해시
    기반)와 다른 접두사를 써서 네임스페이스를 분리한다."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"SRM-{date_part}-{secrets.token_hex(3)}"


@dataclass
class SermonArtifact:
    sermon_id: str
    scripture_and_theme: str
    sermon_format: str
    outline: dict[str, Any]  # {"title","introduction","points","conclusion"}
    expanded: dict[str, str] = field(default_factory=dict)  # point_index(str) -> text
    evidence: dict[str, Any] = field(default_factory=dict)  # {"candidate_tsu_ids","retrieval"}
    doctrine_report: Optional[dict[str, Any]] = None
    groundedness: Optional[dict[str, Any]] = None  # P1은 미계산 — None 그대로 저장
    generation: dict[str, Any] = field(default_factory=dict)
    derivations: dict[str, Any] = field(
        default_factory=lambda: {"illustrations": [], "applications": [], "questions": [], "repurpose": {}}
    )
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SermonArtifact":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


def _artifact_path(sermon_id: str, output_dir: str) -> str:
    return os.path.join(output_dir, f"{sermon_id}.json")


def _index_path(output_dir: str) -> str:
    return os.path.join(output_dir, INDEX_FILENAME)


def save_sermon_artifact(
    artifact: SermonArtifact, output_dir: str = DEFAULT_SERMON_ARTIFACT_DIR
) -> str:
    """artifact를 `{sermon_id}.json`으로 쓰고 index.jsonl에 목록용 요약
    한 줄을 덧붙인다(append-only — 목록 조회 시 전체 JSON을 열지 않아도
    되게). 반환값은 저장된 JSON 파일의 전체 경로."""
    os.makedirs(output_dir, exist_ok=True)

    path = _artifact_path(artifact.sermon_id, output_dir)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(artifact.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

    summary = {
        "sermon_id": artifact.sermon_id,
        "title": artifact.outline.get("title", ""),
        "scripture_and_theme": artifact.scripture_and_theme,
        "sermon_format": artifact.sermon_format,
        "created_at": artifact.created_at,
    }
    with open(_index_path(output_dir), "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    return path


def load_sermon_artifact(
    sermon_id: str, output_dir: str = DEFAULT_SERMON_ARTIFACT_DIR
) -> Optional[SermonArtifact]:
    path = _artifact_path(sermon_id, output_dir)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return SermonArtifact.from_dict(data)


def list_sermon_artifacts(output_dir: str = DEFAULT_SERMON_ARTIFACT_DIR) -> list[dict[str, Any]]:
    """index.jsonl을 읽어 요약 목록을 최신순으로 반환한다. 인덱스가
    없으면(아직 저장된 설교가 없으면) 빈 목록."""
    index_path = _index_path(output_dir)
    if not os.path.isfile(index_path):
        return []
    summaries = []
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                summaries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    summaries.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return summaries

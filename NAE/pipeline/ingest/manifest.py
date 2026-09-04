"""Production Manifest — 현재 NAE Production의 canonical state 요약.

Historical checkpoint(`NAE/review/human/checkpoints/*/`, 예:
`nae-batch24-36-green-checkpoint`)와는 목적이 다르다:

- **Historical checkpoint**: 특정 작업 시점의 불변 snapshot(파일 사본).
  한 번 만들면 다시 만들지 않는다.
- **Production Manifest**: 현재 상태를 요약한 경량 문서. 매 incremental
  ingestion 실행마다 새 generation으로 갱신한다(전체 corpus를 복사하지
  않음 — 카운트/해시 요약만).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from NAE.pipeline.embed import config as embed_config
from NAE.pipeline.index import config as index_config
from NAE.pipeline.tsu.config import TSU_ROOT

MANIFEST_SCHEMA_VERSION = "1.0.0"
MANIFEST_DIR = Path(__file__).resolve().parent / "manifests"


def _load_tsu_records(identifier_dir: Path) -> list[dict[str, Any]]:
    path = identifier_dir / "tsu.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def build_production_manifest(
    *,
    tsu_root: Path = TSU_ROOT,
    qdrant_client=None,
    production_generation: int = 1,
    previous_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """현재 Production 상태를 READ-ONLY로 요약한다. Production 파일을
    수정하지 않는다."""
    identifiers = [d for d in tsu_root.iterdir() if d.is_dir() and not d.name.startswith("_")] if tsu_root.exists() else []

    total_tsu = 0
    total_editions: set[str] = set()
    total_source_files: set[str] = set()
    per_corpus_hash: dict[str, str] = {}

    for identifier_dir in identifiers:
        records = _load_tsu_records(identifier_dir)
        total_tsu += len(records)
        for r in records:
            if r.get("edition_id"):
                total_editions.add(r["edition_id"])
            sid = r.get("source_id") or r.get("source_identifier")
            if sid:
                total_source_files.add(sid)
        path = identifier_dir / "tsu.json"
        if path.exists():
            per_corpus_hash[identifier_dir.name] = hashlib.sha256(path.read_bytes()).hexdigest()

    corpus_hash = hashlib.sha256(
        json.dumps(per_corpus_hash, sort_keys=True).encode("utf-8")
    ).hexdigest()

    total_vectors = 0
    if qdrant_client is not None:
        try:
            info = qdrant_client.get_collection(index_config.COLLECTION_NAME)
            total_vectors = info.points_count
        except Exception:  # noqa: BLE001 — Qdrant 접속 불가 시 0으로 기록(재시도는 호출자 책임)
            total_vectors = -1  # 조회 실패를 0(정말 없음)과 구분

    embedding_cache_count = len(list(embed_config.EMBEDDING_CACHE_ROOT.glob("*.json"))) if embed_config.EMBEDDING_CACHE_ROOT.exists() else 0

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "production_generation": production_generation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tsu": total_tsu,
        "total_source_files": len(total_source_files),
        "total_editions": len(total_editions),
        "total_embeddings": embedding_cache_count,
        "total_vectors": total_vectors,
        "embedding_model": embed_config.DEFAULT_EMBED_MODEL,
        "embedding_dimension": embed_config.EMBED_DIMENSION,
        "index_collection": index_config.COLLECTION_NAME,
        "corpus_hash": corpus_hash,
        "per_corpus_hash": per_corpus_hash,
    }
    if previous_manifest is not None:
        manifest["previous_generation"] = previous_manifest.get("production_generation")
        manifest["previous_corpus_hash"] = previous_manifest.get("corpus_hash")
        manifest["corpus_changed_since_previous"] = previous_manifest.get("corpus_hash") != corpus_hash
    return manifest


def save_manifest(manifest: dict[str, Any], path: Path | None = None) -> Path:
    if path is None:
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        path = MANIFEST_DIR / f"manifest_gen{manifest['production_generation']:04d}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_latest_manifest(manifest_dir: Path = MANIFEST_DIR) -> dict[str, Any] | None:
    if not manifest_dir.exists():
        return None
    files = sorted(manifest_dir.glob("manifest_gen*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))

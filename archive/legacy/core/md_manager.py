"""
md_manager.py — md 파일 저장 + 해시 기반 변경 감지 + RAG 재인덱싱 트리거
"""

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import BASE_DIR

logger = logging.getLogger(__name__)

HASH_STORE_PATH = Path(BASE_DIR) / "data" / "md_hashes.json"
REINDEX_LOG_PATH = Path(BASE_DIR) / "data" / "reindex_log.jsonl"
COLLECTION_NAME = "dbma_sermon"


# ── 해시 관리 ──────────────────────────────────────────────

def _load_hashes() -> dict:
    if HASH_STORE_PATH.exists():
        try:
            return json.loads(HASH_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_hashes(hashes: dict) -> None:
    HASH_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    HASH_STORE_PATH.write_text(
        json.dumps(hashes, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ── md 저장 + 변경 감지 ──────────────────────────────────

def save_md_with_change_detection(filepath: str, content: str) -> bool:
    """
    md 파일을 저장하고 내용 변경 여부를 반환한다.
    True  → 내용 변경됨 (RAG 재인덱싱 필요)
    False → 내용 동일 (재인덱싱 불필요)
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    new_hash = _compute_hash(content)
    hashes = _load_hashes()
    key = str(path.resolve())

    changed = hashes.get(key) != new_hash
    if changed:
        hashes[key] = new_hash
        _save_hashes(hashes)
        logger.info(f"[MD_SAVE] 변경 감지: {path.name}")
    else:
        logger.info(f"[MD_SAVE] 변경 없음: {path.name}")
    return changed


# ── 헤더 기반 계층 청킹 ──────────────────────────────────

def _split_by_markdown_headers(content: str, filepath: str) -> list:
    """
    마크다운 헤더(#, ##, ###)를 기준으로 섹션을 분리한다.
    각 노드는 {id, text, metadata} 형태로 반환.
    """
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()

    header_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(header_pattern.finditer(body))
    filename = Path(filepath).stem
    nodes = []

    if not matches:
        if body.strip():
            nodes.append({
                "id": str(uuid.uuid4()),
                "text": body.strip(),
                "metadata": {
                    "source": Path(filepath).name,
                    "filepath": filepath,
                    "header_level": 0,
                    "section": filename,
                }
            })
        return nodes

    # 첫 헤더 이전 본문
    if matches[0].start() > 0:
        pre_text = body[:matches[0].start()].strip()
        if pre_text:
            nodes.append({
                "id": str(uuid.uuid4()),
                "text": pre_text,
                "metadata": {
                    "source": Path(filepath).name,
                    "filepath": filepath,
                    "header_level": 0,
                    "section": filename,
                }
            })

    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_text = body[start:end].strip()
        full_text = f"{'#' * level} {title}\n\n{section_text}".strip()
        if full_text:
            nodes.append({
                "id": str(uuid.uuid4()),
                "text": full_text,
                "metadata": {
                    "source": Path(filepath).name,
                    "filepath": filepath,
                    "header_level": level,
                    "section": title,
                }
            })

    logger.info(f"[CHUNK] {Path(filepath).name} → {len(nodes)}개 노드 생성")
    return nodes


# ── 재인덱싱 로그 ────────────────────────────────────────

def _write_reindex_log(entry: dict) -> None:
    REINDEX_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REINDEX_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_reindex_log(limit: int = 50) -> list:
    """최근 재인덱싱 로그를 반환한다 (최신순)."""
    if not REINDEX_LOG_PATH.exists():
        return []
    lines = REINDEX_LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in reversed(lines[-limit:]):
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


# ── Qdrant 선택적 재인덱싱 ───────────────────────────────

def reindex_md_to_qdrant(filepath: str, content: Optional[str] = None) -> dict:
    """
    변경된 md 파일을 Qdrant에 선택적으로 재인덱싱한다.
    Returns:
        {"status": "upserted"|"skipped"|"error", "nodes": int, "message": str}
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            PointStruct, VectorParams, Distance,
            Filter, FieldCondition, MatchValue
        )

        if content is None:
            content = Path(filepath).read_text(encoding="utf-8")

        nodes = _split_by_markdown_headers(content, filepath)
        if not nodes:
            return {"status": "skipped", "nodes": 0, "message": "청킹 결과 없음"}

        client = QdrantClient(url="http://localhost:6333")

        # 컬렉션 없으면 자동 생성
        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in existing:
            from core.embedder import embed
            sample_vec = embed(nodes[0]["text"])
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=len(sample_vec), distance=Distance.COSINE
                ),
            )
            logger.info(f"[QDRANT] 컬렉션 생성: {COLLECTION_NAME}")

        # 같은 filepath의 기존 포인트 삭제
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[FieldCondition(
                    key="filepath", match=MatchValue(value=filepath)
                )]
            ),
        )

        # 새 포인트 임베딩 후 삽입
        from core.embedder import embed
        points = []
        for node in nodes:
            vector = embed(node["text"])
            points.append(
                PointStruct(
                    id=node["id"],
                    vector=vector,
                    payload={
                        "text": node["text"],
                        "source": node["metadata"]["source"],
                        "filepath": node["metadata"]["filepath"],
                        "header_level": node["metadata"]["header_level"],
                        "section": node["metadata"]["section"],
                    },
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "file": Path(filepath).name,
            "filepath": filepath,
            "nodes": len(nodes),
            "hash": _compute_hash(content),
            "status": "upserted",
        }
        _write_reindex_log(entry)
        logger.info(f"[REINDEX] 완료: {Path(filepath).name} → {len(nodes)}개 포인트")

        return {
            "status": "upserted",
            "nodes": len(nodes),
            "message": f"{len(nodes)}개 노드 RAG 반영 완료"
        }

    except Exception as e:
        err_msg = str(e)
        logger.error(f"[REINDEX] 오류: {err_msg}")
        _write_reindex_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "file": Path(filepath).name,
            "filepath": filepath,
            "nodes": 0,
            "status": "error",
            "error": err_msg,
        })
        return {"status": "error", "nodes": 0, "message": err_msg}

"""참고 코퍼스(신학사전·주석)의 내장(로컬) Qdrant 저장소.

Docker/서버 없이 `qdrant_client.QdrantClient(path=...)`로 같은 컬렉션을 읽는다.
검증(2026-10-23, 45,465건): 디스크 529MB, 여는 데 ~2초, 질의 ~21ms, 서버와 같은
항목이 같은 순서로 반환됐다.

- 변환: `convert_from_server()` (CLI는 scripts/nae_reference_to_local.py). 임시
  폴더에 복사 → 건수 검증 → READY 표식 → 원자적 이름 변경이라, 중간에 끊긴
  복사본을 읽는 일이 없다.
- 사용: `get_local_client()`는 프로세스당 한 번만 연다(여는 데 ~2초, 폴더는 한
  프로세스만 열 수 있다). 폴더가 없거나 READY가 없거나, 다른 프로세스가 이미
  열고 있으면 None — 호출부는 서버로 대체한다.
"""
from __future__ import annotations

import atexit
import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Callable, Iterable, Optional

from NAE.pipeline.reference import config as ref_config

logger = logging.getLogger("nae.reference.local_store")

READY_MARKER = "READY"
_BATCH = 500

_lock = threading.Lock()
_client = None
_client_path: Optional[str] = None
_failed_paths: set[str] = set()


def local_store_path() -> Path:
    override = os.environ.get("NAE_REFERENCE_LOCAL_PATH")
    return Path(override) if override else Path(ref_config.LOCAL_STORE_PATH)


def is_ready(path: Optional[Path] = None) -> bool:
    """변환이 끝난 로컬 저장소가 있는지(열지 않고 표식만 확인)."""
    p = path or local_store_path()
    return (p / READY_MARKER).is_file()


def get_local_client():
    """프로세스당 하나의 내장 클라이언트. 쓸 수 없으면 None."""
    global _client, _client_path
    path = local_store_path()
    key = str(path)
    if _client is not None and _client_path == key:
        return _client
    if not is_ready(path) or key in _failed_paths:
        return None
    with _lock:
        if _client is not None and _client_path == key:
            return _client
        try:
            from qdrant_client import QdrantClient
            _client = QdrantClient(path=key)
            _client_path = key
            logger.info("[reference_local] 내장 저장소 열기: %s", key)
            return _client
        except Exception as e:  # noqa: BLE001 — 폴더 잠금 등: 서버로 대체
            _failed_paths.add(key)
            logger.warning("[reference_local] 내장 저장소를 열지 못함(서버로 대체): %s", e)
            return None


def close_local_client() -> None:
    global _client, _client_path
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:  # noqa: BLE001
                pass
        _client = None
        _client_path = None
        _failed_paths.clear()


atexit.register(close_local_client)   # 종료 시 잠금을 깨끗이 놓는다


def convert_from_server(
    url: str = ref_config.QDRANT_URL,
    collections: Iterable[str] = ref_config.KNOWN_REFERENCE_COLLECTIONS,
    dest: Optional[Path] = None,
    progress: Optional[Callable[[str, int, int], None]] = None,
) -> dict[str, int]:
    """서버의 참고 컬렉션을 로컬 폴더로 복사한다. 반환: {컬렉션: 건수}.

    기존 로컬 저장소가 있으면 완전히 새로 만든 뒤 교체한다(복사 중 실패하면 기존
    것은 그대로). 건수가 서버와 다르면 예외를 내고 교체하지 않는다.
    """
    from qdrant_client import QdrantClient, models

    dest = Path(dest) if dest else local_store_path()
    tmp = dest.with_name(dest.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.parent.mkdir(parents=True, exist_ok=True)

    src = QdrantClient(url=url, timeout=120)
    dst = QdrantClient(path=str(tmp))
    counts: dict[str, int] = {}
    try:
        for name in collections:
            info = src.get_collection(name)
            total = info.points_count or 0
            dst.create_collection(name, vectors_config=info.config.params.vectors)
            copied, offset = 0, None
            while True:
                points, offset = src.scroll(
                    name, limit=_BATCH, offset=offset, with_payload=True, with_vectors=True
                )
                if points:
                    dst.upsert(name, [
                        models.PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                        for p in points
                    ])
                    copied += len(points)
                    if progress:
                        progress(name, copied, total)
                if offset is None:
                    break
            got = dst.count(name, exact=True).count
            if got != total:
                raise RuntimeError(f"{name}: 서버 {total}건 ≠ 복사본 {got}건")
            counts[name] = got
    finally:
        dst.close()
        src.close()

    (tmp / READY_MARKER).write_text("\n".join(f"{k}={v}" for k, v in counts.items()), encoding="utf-8")
    close_local_client()           # 이 프로세스가 옛 폴더를 열고 있으면 놓는다
    if dest.exists():
        shutil.rmtree(dest)
    tmp.rename(dest)
    return counts

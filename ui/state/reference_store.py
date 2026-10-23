"""신학사전·주석 벡터 저장소(NAE Qdrant, Docker 컨테이너 nae_qdrant)를 앱이 스스로 살린다.

[2026-10-23] 컴퓨터를 다시 켜면 Docker Desktop이 꺼진 채 시작돼 컨테이너(restart:
unless-stopped)도 올라오지 않았고, 채팅은 사전을 조용히 건너뛰었다. 이제 앱이 시작될
때와 채팅이 연결 실패를 만났을 때 백그라운드에서 다음 순서로 복구를 시도한다:

    1. 포트에 연결되면 끝.
    2. Docker 데몬이 안 떠 있으면 Docker Desktop을 백그라운드로 실행하고 기다린다.
    3. 컨테이너를 `docker start`.

Docker Desktop의 "로그인 시 시작" 같은 시스템 설정은 건드리지 않는다. macOS가 아니거나
docker 실행 파일이 없으면 아무것도 하지 않는다. 모든 실패는 로그만 남기고 앱 동작엔
영향이 없다.
"""

from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger(__name__)

CONTAINER_NAME = "nae_qdrant"
_DOCKER_FALLBACKS = ("/usr/local/bin/docker", "/opt/homebrew/bin/docker")
_DAEMON_WAIT_S = 180
_PORT_WAIT_S = 40

_lock = threading.Lock()
_thread: Optional[threading.Thread] = None


def _endpoint() -> tuple[str, int]:
    try:
        from NAE.pipeline.reference import config as ref_config
        u = urlparse(ref_config.QDRANT_URL)
        return u.hostname or "localhost", u.port or 6333
    except ImportError:
        return "localhost", 7333


def local_store_ready() -> bool:
    """Docker 없는 내장 저장소(NAE/reference_local_store)가 준비돼 있는지."""
    try:
        from NAE import reference_local_store
        return reference_local_store.is_ready()
    except ImportError:
        return False


def is_reachable(timeout: float = 0.7) -> bool:
    """사전·주석을 검색할 수 있는 저장소가 있는지 — 내장 저장소 또는 서버."""
    if local_store_ready():
        return True
    return _server_reachable(timeout)


def _server_reachable(timeout: float = 0.7) -> bool:
    host, port = _endpoint()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _docker_bin() -> Optional[str]:
    found = shutil.which("docker")
    if found:
        return found
    return next((p for p in _DOCKER_FALLBACKS if os.path.exists(p)), None)


def _run(args: list[str], timeout: float) -> bool:
    try:
        return subprocess.run(
            args, capture_output=True, timeout=timeout, check=False
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _wait(predicate, seconds: float, step: float = 3.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(step)
    return predicate()


def _recover() -> None:
    if _server_reachable():
        return
    docker = _docker_bin()
    if not docker:
        log.warning("[reference_store] docker 실행 파일 없음 — 자동 복구 생략")
        return
    daemon_up = lambda: _run([docker, "info"], 8)  # noqa: E731
    if not daemon_up():
        if sys.platform != "darwin":
            log.warning("[reference_store] Docker 데몬이 꺼져 있음 (macOS 아님 — 자동 실행 생략)")
            return
        log.warning("[reference_store] Docker 데몬이 꺼져 있어 Docker Desktop 실행")
        _run(["open", "-g", "-a", "Docker"], 15)
        if not _wait(daemon_up, _DAEMON_WAIT_S):
            log.error("[reference_store] Docker가 %ds 안에 준비되지 않음", _DAEMON_WAIT_S)
            return
    # restart 정책으로 이미 올라오는 중일 수 있어 먼저 잠깐 기다린다.
    if _wait(_server_reachable, 6, step=1.0):
        return
    log.warning("[reference_store] 컨테이너 %s 시작", CONTAINER_NAME)
    _run([docker, "start", CONTAINER_NAME], 30)
    if _wait(_server_reachable, _PORT_WAIT_S, step=1.0):
        log.info("[reference_store] 사전 서버 복구 완료")
    else:
        log.error("[reference_store] 컨테이너를 시작했지만 포트에 연결되지 않음")


def ensure_async() -> None:
    """복구 스레드를 (이미 돌고 있지 않으면) 하나 띄운다. 즉시 반환."""
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        if local_store_ready():
            # Docker 불필요 — 첫 질의가 느리지 않게 내장 저장소만 미리 연다(~2초).
            def _warm() -> None:
                try:
                    from NAE import reference_local_store
                    reference_local_store.get_local_client()
                except Exception:
                    log.exception("[reference_store] 내장 저장소 예열 실패")
            _thread = threading.Thread(target=_warm, name="reference-local-warm", daemon=True)
            _thread.start()
            return
        if is_reachable():
            return
        _thread = threading.Thread(target=_recover, name="reference-store-recover", daemon=True)
        _thread.start()


def is_recovering() -> bool:
    return _thread is not None and _thread.is_alive()

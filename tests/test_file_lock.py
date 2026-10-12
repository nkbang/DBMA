"""core/file_lock.py + Windows 이식성 가드 (fcntl 제거).

`fcntl`은 POSIX 전용이라 Windows에서는 import 단계에서 실패한다 → 앱 기동 불가였다(2026-10-12 발견).
이 시험은 (1) 새 잠금의 의미(상호 배제·해제·경로)를 고정하고 (2) POSIX 전용 모듈이 core/ui에 다시 들어오는 것을 막는다.
Windows 실기 동작은 이 시험이 보장하지 않는다 — Windows 머신에서 따로 확인해야 한다.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from core.file_lock import file_lock

REPO = Path(__file__).resolve().parent.parent
POSIX_ONLY = ("fcntl", "resource", "pwd", "grp", "termios", "pty", "syslog")


def test_creates_parent_directory_and_sibling_lock_file(tmp_path):
    lock = tmp_path / "nested" / "dir" / "data.json.lock"
    with file_lock(lock):
        assert lock.parent.is_dir()
    assert not (tmp_path / "nested" / "dir" / "data.json").exists()  # 데이터 파일 자체는 건드리지 않는다


def test_mutual_exclusion_across_threads(tmp_path):
    lock = tmp_path / "a.lock"
    inside = []
    overlap = []

    def worker(name):
        with file_lock(lock):
            inside.append(name)
            if len(inside) > 1:
                overlap.append(tuple(inside))
            time.sleep(0.15)
            inside.remove(name)

    ts = [threading.Thread(target=worker, args=(n,)) for n in "ABC"]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not overlap


def test_released_on_exception(tmp_path):
    lock = tmp_path / "b.lock"
    with pytest.raises(RuntimeError):
        with file_lock(lock):
            raise RuntimeError("boom")
    with file_lock(lock, timeout=2):  # 해제되지 않았다면 Timeout
        pass


def test_timeout_raises_instead_of_waiting_forever(tmp_path):
    from filelock import Timeout
    lock = tmp_path / "c.lock"
    ready, release = threading.Event(), threading.Event()

    def holder():
        with file_lock(lock):
            ready.set()
            release.wait(5)

    t = threading.Thread(target=holder)
    t.start()
    ready.wait(5)
    try:
        with pytest.raises(Timeout):
            with file_lock(lock, timeout=0.2):
                pass
    finally:
        release.set()
        t.join()


_CHILD = """
import sys, time
sys.path.insert(0, {root!r})
from core.file_lock import file_lock
with file_lock({path!r}):
    print("child-holding", flush=True)
    time.sleep(1.0)
"""


def test_mutual_exclusion_across_processes(tmp_path):
    lock = tmp_path / "d.lock"
    child = subprocess.Popen([sys.executable, "-c", _CHILD.format(root=str(REPO), path=str(lock))],
                             stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "child-holding"
        t0 = time.monotonic()
        with file_lock(lock):
            waited = time.monotonic() - t0
        assert waited > 0.5, waited
    finally:
        child.wait(timeout=10)


def test_core_modules_import_without_posix_only_modules():
    """Windows 모사: POSIX 전용 모듈 import를 막은 인터프리터에서 잠금을 쓰는 모듈이 import돼야 한다."""
    block = ";".join(f"sys.modules[{m!r}]=None" for m in POSIX_ONLY)
    code = f"import sys;{block};import core.file_lock, core.identity_registry, core.tsu_builder"
    r = subprocess.run([sys.executable, "-W", "ignore", "-c", code], cwd=str(REPO), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-600:]


def test_app_imports_without_posix_only_modules():
    """Windows 모사: 앱 전체(ui.app)가 POSIX 전용 모듈 없이 import돼야 한다."""
    block = ";".join(f"sys.modules[{m!r}]=None" for m in POSIX_ONLY)
    code = f"import sys;{block};import ui.app"
    r = subprocess.run([sys.executable, "-W", "ignore", "-c", code], cwd=str(REPO), capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]


def test_no_posix_only_imports_in_core_and_ui():
    """core/·ui/·dbma_ui.py 어디에도 POSIX 전용 모듈 import가 없어야 한다 (함수 안·try 안 포함 — Windows 경로에서 터질 수 있음)."""
    files = []
    for r in ("core", "ui", "dbma_ui.py"):
        p = REPO / r
        files += [p] if p.is_file() else sorted(p.rglob("*.py"))
    bad = []
    for f in files:
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for n in ast.walk(tree):
            names = []
            if isinstance(n, ast.Import):
                names = [a.name.split(".")[0] for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                names = [n.module.split(".")[0]]
            for name in names:
                if name in POSIX_ONLY:
                    bad.append(f"{f.relative_to(REPO)}:{n.lineno} import {name}")
    assert not bad, "POSIX 전용 모듈 import (Windows 미지원):\n  " + "\n  ".join(bad)

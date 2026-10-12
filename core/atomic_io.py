"""원자적 파일 교체·읽기의 일시적 실패 재시도 (Windows 지원).

배경
----
``os.replace`` 로 파일을 교체할 때, Windows 에서는 대상 파일을 다른 곳(다른 스레드의 읽기, 백신 검사 등)이
열어 두고 있으면 ``PermissionError`` (winerror 5 / 32 / 33)로 실패한다. POSIX 에서는 교체가 읽는 쪽에
원자적으로 보여서 이 문제가 거의 없다. 이 모듈은 그런 *일시적* 실패만 짧게 재시도하고, 재시도로도 해결되지
않는 실패는 **삼키지 않고 예외로 올린다**(삼킬지 여부는 호출자가 정한다).

원칙
----
* 일시적 오류만 재시도한다. POSIX 의 ``PermissionError`` 는 진짜 권한 문제이므로 재시도하지 않는다.
* 재시도 총 시간에는 상한이 있다(기본 2초). 무한 대기는 없다.
* 정상 경로(실패 없음)에서는 ``os.replace`` 를 한 번 호출할 뿐이다 — 동작·성능 변화 없음.

시험 훅
-------
``_IS_WINDOWS`` 와 ``_TREAT_ALL_AS_TRANSIENT`` 는 모듈 상수다. 시험은 ``os.name`` 을 전역으로 바꾸지 않고
이 상수만 monkeypatch 해서 Windows 분기와 재시도 경로를 macOS/Linux 에서 검증한다.
환경변수 ``DBMA_IO_RETRY_ALL=1`` 은 같은 목적(점검 스크립트의 실패 주입)용이며 운영에서는 쓰지 않는다.
"""
from __future__ import annotations

import errno
import logging
import os
import tempfile
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")

_IS_WINDOWS: bool = os.name == "nt"
_WIN_TRANSIENT_WINERRORS = frozenset({5, 32, 33})  # ACCESS_DENIED, SHARING_VIOLATION, LOCK_VIOLATION
_POSIX_TRANSIENT_ERRNOS = frozenset({errno.EBUSY, errno.EAGAIN, errno.EINTR})
_TREAT_ALL_AS_TRANSIENT: bool = os.environ.get("DBMA_IO_RETRY_ALL") == "1"

DEFAULT_TOTAL_TIMEOUT = 2.0
DEFAULT_FIRST_DELAY = 0.01
DEFAULT_MAX_DELAY = 0.25


def is_transient_os_error(exc: BaseException) -> bool:
    """재시도하면 해결될 수 있는 일시적 OS 오류인가."""
    if not isinstance(exc, OSError):
        return False
    if _TREAT_ALL_AS_TRANSIENT:
        return True
    if _IS_WINDOWS:
        return getattr(exc, "winerror", None) in _WIN_TRANSIENT_WINERRORS or isinstance(exc, PermissionError)
    return exc.errno in _POSIX_TRANSIENT_ERRNOS


def retry_io(
    fn: Callable[[], T],
    *,
    what: str = "io",
    total_timeout: float = DEFAULT_TOTAL_TIMEOUT,
    first_delay: float = DEFAULT_FIRST_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
) -> T:
    """``fn`` 을 호출하고, 일시적 ``OSError`` 면 지수 백오프로 재시도한다.

    재시도 중 비일시적 오류가 나거나 ``total_timeout`` 을 넘기면 마지막 예외를 그대로 올린다.
    """
    deadline = time.monotonic() + total_timeout
    delay = first_delay
    attempts = 0
    while True:
        attempts += 1
        try:
            return fn()
        except OSError as exc:
            if not is_transient_os_error(exc) or time.monotonic() >= deadline:
                if attempts > 1:
                    logger.error("%s: %d회 시도 후 실패: %r", what, attempts, exc)
                raise
            time.sleep(delay)
            delay = min(delay * 2, max_delay)


def replace_with_retry(src: "os.PathLike[str] | str", dst: "os.PathLike[str] | str", **kw) -> None:
    """``os.replace(src, dst)`` — Windows 의 일시적 PermissionError 는 재시도한다. 최종 실패는 예외로 올린다."""
    retry_io(lambda: os.replace(src, dst), what=f"replace -> {dst}", **kw)


def fsync_dir(directory: str) -> None:
    """디렉터리 항목(rename)을 디스크에 내린다. Windows 는 디렉터리를 os.open 할 수 없어 건너뛴다(최선 노력)."""
    if _IS_WINDOWS:
        return
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_text(path: str, text: str) -> None:
    """고유 임시 파일(utf-8)에 쓴 뒤 ``replace_with_retry`` 로 교체한다. 실패는 예외로 올리고 임시 파일은 지운다.

    고정 ``<path>.tmp`` 를 쓰던 호출부들의 동시 저장 충돌(같은 tmp 에 동시에 쓰기)을 없앤다.
    """
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        replace_with_retry(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

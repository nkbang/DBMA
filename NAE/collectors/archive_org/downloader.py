"""Download files from Internet Archive with retry, checksum, and integrity checks."""
from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

from . import config

logger = logging.getLogger("nae.collector.download")


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path, *, retry: int = config.RETRY,
                   timeout: int = config.TIMEOUT) -> tuple[bool, str]:
    """Download url to dest. Returns (success, sha256_or_error)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error = ""
    for attempt in range(1, retry + 1):
        try:
            with requests.get(url, stream=True, timeout=timeout) as resp:
                if resp.status_code == 404:
                    last_error = "HTTP 404"
                    logger.warning("[download] 404 for %s (attempt %d/%d)", url, attempt, retry)
                elif resp.status_code in (500, 502, 503, 504):
                    last_error = f"HTTP {resp.status_code}"
                    logger.warning("[download] %s for %s (attempt %d/%d)", last_error, url, attempt, retry)
                else:
                    resp.raise_for_status()
                    tmp = dest.with_suffix(dest.suffix + ".part")
                    with open(tmp, "wb") as fh:
                        for chunk in resp.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                fh.write(chunk)
                    tmp.rename(dest)
                    checksum = sha256_of_file(dest)
                    logger.info("[download] success %s -> %s (sha256=%s)", url, dest, checksum[:12])
                    return True, checksum
        except requests.Timeout:
            last_error = "timeout"
            logger.warning("[download] timeout for %s (attempt %d/%d)", url, attempt, retry)
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning("[download] error for %s: %s (attempt %d/%d)", url, exc, attempt, retry)

        if attempt < retry:
            wait = config.BACKOFF_BASE ** attempt
            time.sleep(wait)

    logger.error("[download] failed permanently for %s: %s", url, last_error)
    return False, last_error


def verify_checksum(path: Path, expected_sha256: str) -> bool:
    if not path.exists():
        return False
    return sha256_of_file(path) == expected_sha256

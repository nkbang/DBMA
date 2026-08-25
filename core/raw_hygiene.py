"""core/raw_hygiene.py — RAW 폴더 중복 파일 탐지 (2026-08-24 사용자 요청).

배경: "원본 폴더에 동일한 내용 듀플리케이트 파일은 하나로 정리해야
한다. 그 폴더에 같은 내용이 들어 있지 않도록 사용자에게 워닝하고
삭제하도록 하라." — 자동 삭제가 아니라 사용자가 확인하고 직접
결정하도록 후보만 찾아서 보여준다(정밀도 우선 원칙 — 애매한 경우를
자동으로 지우지 않는다).

탐지 기준은 바이트 단위 완전 일치(SHA-256)만 다룬다 — 오늘 실측 확인된
"clearscan_cropped" 재스캔본 같은 사례(같은 책, 다른 스캔이라 추출
텍스트는 99.9% 유사하지만 바이트는 완전히 다름)는 이 기준으로는
잡히지 않는다. 유사도 기반 탐지는 오탐 위험이 있어(어느 정도의
유사도부터 "같은 문서"로 볼지가 근거 없는 임계값 결정이 됨) 의도적으로
범위에서 뺐다 — 완전 일치만 다뤄 오탐 없이 확실한 것만 사용자에게
보여준다.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR, SUPPORTED_EXTENSIONS, TRASH_RETENTION_DAYS
from core.index_orchestrator import BACKUP_ROOT


def _hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """스트리밍 SHA-256 — 큰 PDF도 한 번에 메모리에 올리지 않는다."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def find_exact_duplicate_raw_files(raw_dir: str = DEFAULT_RAW_DIR) -> list[dict[str, Any]]:
    """RAW 안에서 바이트 단위로 완전히 동일한 파일 그룹을 찾는다
    (하위 폴더 포함 재귀 탐색 — 2026-08-24 processing.py 수정과 동일 기준).

    Returns:
        [{"content_hash": str, "files": [{"path", "name", "size"}, ...]}, ...]
        파일이 2개 이상 겹치는 그룹만 포함. 그룹 내 files는 파일명 기준
        정렬(가장 먼저 오는 이름이 "원본" 후보로 자연스럽게 눈에 띄도록).
    """
    raw_root = Path(raw_dir)
    if not raw_root.exists():
        return []

    groups: dict[str, list[Path]] = {}
    for f in raw_root.rglob("*"):
        if not f.is_file() or f.name.startswith(".") or f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        digest = _hash_file(f)
        groups.setdefault(digest, []).append(f)

    result = []
    for digest, files in groups.items():
        if len(files) < 2:
            continue
        files.sort(key=lambda p: p.name)
        result.append({
            "content_hash": digest,
            "files": [{"path": str(f), "name": f.name, "size": f.stat().st_size} for f in files],
        })

    result.sort(key=lambda g: g["files"][0]["name"])
    return result


def purge_expired_trash(
    retention_days: int = TRASH_RETENTION_DAYS,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """[2026-08-24 사용자 요청: "휴지통 자동 비우기 정책"]
    backups/deleted_raw_{날짜}/(core/index_orchestrator.py::
    delete_raw_source()가 만드는 휴지통) 중 retention_days보다 오래된
    폴더를 영구 삭제한다. 실수로 지운 걸 되돌릴 시간(기본 30일,
    config.yaml::maintenance.trash_retention_days)을 준 뒤에는 무한정
    쌓이지 않게 한다.

    excluded_documents_{날짜}/(제외/삭제 시 딸려가는 .md/_chunks.txt/
    _chunks_meta.json)는 건드리지 않는다 — "휴지통"은 restore_raw_source()
    로 복구 가능한 deleted_raw_*만을 가리키며, 그 범위를 벗어나지 않는다.

    Returns:
        {"purged_dirs": [str, ...], "purged_file_count": int}
    """
    now = now or datetime.now()
    result: dict[str, Any] = {"purged_dirs": [], "purged_file_count": 0}
    if not BACKUP_ROOT.exists():
        return result

    for sub in sorted(BACKUP_ROOT.glob("deleted_raw_*")):
        if not sub.is_dir():
            continue
        date_str = sub.name.removeprefix("deleted_raw_")
        try:
            dir_date = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            continue  # 예상 밖 폴더명 — 건드리지 않는다
        if (now - dir_date).days >= retention_days:
            file_count = sum(1 for f in sub.rglob("*") if f.is_file())
            shutil.rmtree(sub)
            result["purged_dirs"].append(str(sub))
            result["purged_file_count"] += file_count
    return result


def maybe_purge_expired_trash(
    output_dir: str = DEFAULT_OUTPUT_DIR,
    retention_days: int = TRASH_RETENTION_DAYS,
) -> Optional[dict[str, Any]]:
    """하루 최대 1회만 실제로 검사하도록 마커 파일로 제한한다 —
    Streamlit 페이지를 열 때마다 backups/ 전체를 다시 훑는 낭비를 피한다.
    ui/pages/library.py::_render_trash_section()이 페이지 렌더마다 호출.

    Returns:
        오늘 이미 확인했으면 None. 실제로 검사를 실행했으면
        purge_expired_trash()의 결과(지운 게 없어도 dict 반환).
    """
    marker = Path(output_dir) / ".trash_cleanup_marker"
    today = date.today().isoformat()
    if marker.exists():
        try:
            if marker.read_text(encoding="utf-8").strip() == today:
                return None
        except OSError:
            pass

    result = purge_expired_trash(retention_days)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(today, encoding="utf-8")
    return result

"""core/raw_folder_watcher.py — RAW 폴더 신규 파일 감지 (ADR-035 §3.1 항목1).

배경: 목회자가 Finder 등으로 RAW 폴더에 파일을 직접 넣으면(업로드
UI를 거치지 않고) 감지할 방법이 없었다 — 기존 "문서 처리 시작" 버튼을
직접 눌러야만 알 수 있었다. 이 모듈은 새 파일을 **자동으로 처리하지
않고** 존재만 확인해 개수/목록을 반환한다 — 실제 처리는 여전히
사용자의 원클릭 확인(기존 Processing 화면 버튼)을 거친다. 업로드 경로
(자동 처리)와 RAW 직접 투입 경로(감지 후 원클릭)의 안전 수준을
의도적으로 다르게 유지한다.

`.batch_state.json`(core/processing.py가 쓰는 처리 완료 마커)을 기준으로
"아직 처리되지 않은 파일"을 가려낸다 — ui/pages/processing.py::
_build_file_list()가 "문서 처리 시작" 버튼을 위해 쓰는 것과 동일한
기준이라, 이 모듈이 세는 값과 그 버튼이 실제로 처리할 파일 수가
어긋나지 않는다.

`core/raw_hygiene.py::maybe_purge_expired_trash()`와 동일한 마커 파일
패턴으로 폴링을 하루 1회로 제한한다 — 페이지를 열 때마다 RAW 폴더
전체를 rglob()하지 않는다. 매 호출이 새로 스캔하고 끝나면 리스트만
반환하므로(핸들을 들고 있지 않음) 장시간 상태를 유지하지 않는다
(C1 Review, Task Order 071 RQ3 — 리소스 누적 우려 반영).
"""

from __future__ import annotations

import json
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any, Optional

from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR, SUPPORTED_EXTENSIONS


def find_new_raw_files(
    raw_dir: str = DEFAULT_RAW_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> list[dict[str, Any]]:
    """RAW 폴더에서 아직 처리되지 않은 파일 목록을 반환한다.

    Returns:
        [{"name": str, "path": str}, ...] — 이름 순 정렬. 처리 옵션(OCR
        등)은 포함하지 않는다 — 이 함수는 "몇 건 있는지" 알림 용도이고,
        실제 처리는 기존 Processing 화면 폼이 옵션을 물어서 진행한다.
    """
    raw_root = Path(raw_dir)
    if not raw_root.exists():
        return []

    processed_names: set[str] = set()
    state_file = Path(output_dir) / ".batch_state.json"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            processed_names = {
                unicodedata.normalize("NFC", name) for name in data.get("processed", [])
            }
        except (json.JSONDecodeError, OSError):
            pass

    found = []
    for f in sorted(raw_root.rglob("*")):
        if not f.is_file() or f.name.startswith("."):
            continue
        if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if unicodedata.normalize("NFC", f.name) in processed_names:
            continue
        found.append({"name": f.name, "path": str(f)})
    return found


def maybe_check_new_raw_files(
    raw_dir: str = DEFAULT_RAW_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Optional[list[dict[str, Any]]]:
    """하루 최대 1회만 실제로 검사하도록 마커 파일로 제한한다
    (`maybe_purge_expired_trash()`와 동일 패턴).

    Returns:
        오늘 이미 확인했으면 None. 실제로 검사를 실행했으면
        find_new_raw_files()의 결과(빈 리스트 포함).
    """
    marker = Path(output_dir) / ".raw_watcher_marker"
    today = date.today().isoformat()
    if marker.exists():
        try:
            if marker.read_text(encoding="utf-8").strip() == today:
                return None
        except OSError:
            pass

    result = find_new_raw_files(raw_dir, output_dir)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(today, encoding="utf-8")
    return result

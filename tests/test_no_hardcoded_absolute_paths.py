"""tests/에 로컬 개발 환경의 절대경로가 하드코딩되지 않았는지 확인.

CI 러너(/home/runner/work/...)와 로컬 개발 환경(/Users/<user>/...)의
경로가 다르므로, 테스트 코드에 특정 사용자의 홈 디렉터리 절대경로가
박혀 있으면 그 환경에서만 우연히 통과하고 다른 환경에서는 깨진다
(2026-09-28 PR #90 CI에서 실제로 발견된 사고 재발 방지).
"""

import re
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_FORBIDDEN_PATTERN = re.compile(r"/Users/[A-Za-z0-9_.-]+/DBMA")


def test_no_hardcoded_developer_absolute_paths():
    offenders = []
    for py_file in _TESTS_DIR.rglob("*.py"):  # 재귀 — tests/nae/, tests/test_control_plane/ 등 하위 디렉터리 포함
        if py_file.name == "test_no_hardcoded_absolute_paths.py":
            continue
        if "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _FORBIDDEN_PATTERN.search(line):
                offenders.append(f"{py_file.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "하드코딩된 개발자 절대경로 발견 (CI에서 깨짐):\n" + "\n".join(offenders)
    )

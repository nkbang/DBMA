"""NAE/ 없이도 UI가 임포트·기동되는지 검증한다 (Gate 2 결함 F1 회귀 방지).

배경: .gitattributes의 `NAE/ export-ignore`로 NAE/는 배포본에 포함되지 않는다
(opt-in nae_pd 모듈 전용). ui/ 코드가 NAE를 최상위에서 무조건 import하면 배포본에서
`import ui.app`이 ModuleNotFoundError로 실패한다 (docs/GATE2_REASSESSMENT_20261007.md).

격리 방법: 별도 인터프리터에서 sys.modules['NAE']=None으로 NAE 임포트를 차단한다
(실제 파일은 건드리지 않는다).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_BLOCK_NAE = "import sys; sys.modules['NAE'] = None\n"


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-W", "ignore", "-c", _BLOCK_NAE + code],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120,
    )


def test_block_is_effective():
    """차단 장치 자체 검증 — NAE import가 실제로 실패해야 시험이 의미가 있다."""
    proc = _run("import NAE")
    assert proc.returncode != 0


@pytest.mark.parametrize("module", ["ui.app", "ui.pages.chat", "ui.pages.research",
                                    "ui.components.nae_public_section"])
def test_ui_module_imports_without_nae(module):
    proc = _run(f"import {module}")
    assert proc.returncode == 0, proc.stderr[-800:]


def test_smith_inactive_without_nae():
    proc = _run(
        "from ui.pages import chat\n"
        "assert chat.should_activate_smith('anything') is False\n"
        "assert chat.rewrite_query_for_smith('anything') is None\n"
    )
    assert proc.returncode == 0, proc.stderr[-800:]


def test_no_toplevel_nae_import_in_ui():
    """ui/ 아래 NAE 최상위(들여쓰기 없는) import는 try/except로 감싼 것 외에는 금지."""
    offenders = []
    for path in (REPO_ROOT / "ui").rglob("*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith(("from NAE", "import NAE")):
                prev = lines[i - 1].strip() if i else ""
                if prev != "try:":
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{i + 1}")
    assert not offenders, offenders

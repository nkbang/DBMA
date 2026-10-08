"""setup_beta_tester.command 격리 모드(NAE_SETUP_ISOLATED) 회귀 시험 — Gate 2 재판정 D4.

안전: 모든 외부 명령(brew/ollama/pkill/open/osascript/ln/ditto/curl/streamlit/...)을 호출만 기록하는
스텁으로 대체하고, 스크립트를 임시 트리에 복사해 실행한다. 스크립트의 'export PATH=/opt/homebrew/...' 줄은
시험 사본에서만 무력화한다(실제 brew가 스텁보다 앞서 잡히는 것을 막기 위해). 이 시험은 이 Mac의 전역
상태를 바꾸지 않는다.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SETUP = REPO / "scripts" / "setup_beta_tester.command"
CLEAN40 = REPO / "scripts" / "gate2" / "40_clean_install.sh"
PATH_LINE = 'export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"'
HUNSPELL_LINKS_PRESENT = (Path("/usr/local/Cellar/hunspell/1.6.2/include/hunspell").exists()
                          and Path("/usr/local/lib/libhunspell.dylib").exists())

_LOGGING_STUB = '#!/bin/bash\necho "$(basename "$0") $*" >> "$STUB_LOG"\n'
STUBS = {
    "osascript": _LOGGING_STUB + "exit 0\n",
    "open": _LOGGING_STUB + "exit 0\n",
    "pkill": _LOGGING_STUB + "exit 0\n",
    "ditto": _LOGGING_STUB + "exit 0\n",
    "ln": _LOGGING_STUB + "exit 0\n",
    "sleep": "#!/bin/bash\nexit 0\n",
    "sysctl": "#!/bin/bash\necho 137438953472\n",
    "pdftoppm": "#!/bin/bash\nexit 0\n",
    "tesseract": "#!/bin/bash\nexit 0\n",
    "curl": _LOGGING_STUB + '[ "${STUB_CURL_FAIL:-0}" = "1" ] && exit 22\nexit 0\n',
    "brew": _LOGGING_STUB + 'case "$1" in install) exit 1;; --prefix) echo /nonexistent;; *) exit 0;; esac\n',
    "ollama": _LOGGING_STUB + 'if [ "$1" = list ]; then echo "NAME ID SIZE"; for m in ${STUB_MODELS:-bge-m3:latest llama3.1:8b}; do echo "$m x y z"; done; fi\nexit 0\n',
    "pip": _LOGGING_STUB + "exit 0\n",
    "streamlit": _LOGGING_STUB + "exec /bin/sleep 3\n",
    "python3.11": _LOGGING_STUB + 'if [ "$1" = "-m" ] && [ "$2" = venv ]; then /bin/mkdir -p "$3/bin"; : > "$3/bin/activate"; fi\nexit 0\n',
    "python3": '#!/bin/bash\nexec "$STUB_REAL_PYTHON" "$@"\n',
    # 전역 경로를 건드릴 수 있는 명령은 기록만 하고 통과시키지 않는다.
    "mkdir": _LOGGING_STUB + 'case "$*" in *"/usr/local"*|*"/Applications"*) exit 0;; esac\nexec /bin/mkdir "$@"\n',
    "rm": _LOGGING_STUB + 'case "$*" in *"/usr/local"*|*"/Applications"*) exit 0;; esac\nexec /bin/rm "$@"\n',
}


@pytest.fixture
def env_tree(tmp_path):
    original = SETUP.read_text(encoding="utf-8")
    assert original.count(PATH_LINE) == 1, "PATH 줄이 바뀌었다 — 시험 사본의 무력화 규칙을 갱신해야 한다"
    proj = tmp_path / "proj"
    (proj / "scripts").mkdir(parents=True)
    script = proj / "scripts" / "setup_beta_tester.command"
    script.write_text(original.replace(PATH_LINE, ":"), encoding="utf-8")
    script.chmod(0o755)
    (proj / "config.yaml").write_text('default_gen_model: "x"\n', encoding="utf-8")
    (proj / "requirements.txt").write_text("", encoding="utf-8")
    (proj / "dbma_ui.py").write_text("", encoding="utf-8")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, body in STUBS.items():
        f = stubs / name
        f.write_text(body)
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    return proj, stubs, tmp_path / "calls.log"


def _run(env_tree, *, isolated, omit=(), extra_env=None, port="48123"):
    proj, stubs, log = env_tree
    for name in omit:
        (stubs / name).unlink()
    env = {
        "PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(proj / "fakehome"), "STUB_LOG": str(log),
        "STUB_REAL_PYTHON": sys.executable,
    }
    if isolated:
        env.update(NAE_SETUP_ISOLATED="1", NAE_SETUP_PORT=port)
    env.update(extra_env or {})
    proc = subprocess.run(["/bin/bash", str(proj / "scripts" / "setup_beta_tester.command")],
                          capture_output=True, text=True, env=env, timeout=120)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return proc, calls


GLOBAL_EFFECT = re.compile(r"^(brew install|ollama (serve|pull)|pkill|open |osascript|ln |ditto)")


def test_isolated_mode_has_no_global_side_effects(env_tree):
    proc, calls = _run(env_tree, isolated=True)
    effects = [c for c in calls if GLOBAL_EFFECT.match(c)]
    assert not effects, effects
    if HUNSPELL_LINKS_PRESENT:
        assert proc.returncode == 0, proc.stdout + proc.stderr
        starts = [c for c in calls if c.startswith("streamlit run")]
        assert starts and "--server.port 48123" in starts[0] and "8520" not in starts[0]
        assert "ISOLATED: 서버 응답 확인" in proc.stdout
    else:  # /usr/local hunspell 링크가 없는 머신: 쓰지 않고 PREREQ_MISSING
        assert proc.returncode == 3 and "hunspell" in proc.stdout


def test_isolated_missing_prereq_exits_3_without_installing(env_tree):
    proc, calls = _run(env_tree, isolated=True, omit=("pdftoppm",))
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "PREREQ_MISSING" in proc.stdout
    assert not [c for c in calls if GLOBAL_EFFECT.match(c)], calls


def test_isolated_missing_model_exits_3_without_pulling(env_tree):
    proc, calls = _run(env_tree, isolated=True, extra_env={"STUB_MODELS": "bge-m3:latest"})
    assert proc.returncode == 3 and "PREREQ_MISSING" in proc.stdout
    assert not [c for c in calls if c.startswith("ollama pull")], calls


def test_isolated_server_not_responding_fails(env_tree):
    if not HUNSPELL_LINKS_PRESENT:
        pytest.skip("/usr/local hunspell 링크 없음 — 서버 단계까지 도달하지 않는다")
    proc, calls = _run(env_tree, isolated=True, extra_env={"STUB_CURL_FAIL": "1"})
    assert proc.returncode == 1 and "응답하지 않음" in proc.stdout
    assert not [c for c in calls if c.startswith("open ")]


# ── 기본 모드(최종 사용자 동작)는 그대로여야 한다 ────────────────────────
def test_default_mode_still_installs_missing_homebrew_packages(env_tree):
    proc, calls = _run(env_tree, isolated=False, omit=("pdftoppm",))
    assert any(c.startswith("brew install poppler") for c in calls), calls
    assert any(c.startswith("ollama serve") for c in calls)
    assert proc.returncode == 1  # 스텁 brew install이 실패하도록 해 흐름을 멈춘다


def test_default_mode_full_flow_unchanged(env_tree):
    proc, calls = _run(env_tree, isolated=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert any(c.startswith("pkill -f streamlit run dbma_ui.py") and "8520" in c for c in calls)
    assert any(c == "open http://localhost:8520" for c in calls)
    assert any(c.startswith("ollama pull bge-m3:latest") for c in calls)
    assert any(c.startswith("osascript") and "완료" in c for c in calls)


def test_default_mode_does_not_claim_done_when_server_is_silent(env_tree):
    proc, calls = _run(env_tree, isolated=False, extra_env={"STUB_CURL_FAIL": "1"})
    assert proc.returncode == 0  # 느린 첫 기동일 수 있어 기존처럼 브라우저는 연다
    assert any(c == "open http://localhost:8520" for c in calls)
    notes = [c for c in calls if c.startswith("osascript")]
    assert not any("내서재가 열렸습니다" in c for c in notes), notes
    assert any("아직 응답하지 않습니다" in c for c in notes)


# ── 40_clean_install.sh ────────────────────────────────────────────────
def test_40_dry_run_creates_nothing_and_uses_isolated_mode():
    proc = subprocess.run(["bash", str(CLEAN40)], cwd=str(REPO), capture_output=True, text=True,
                          env=dict(os.environ, DRY_RUN="true"), timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "NAE_SETUP_ISOLATED=1" in proc.stdout
    assert "DRY-RUN (no verification performed)" in proc.stdout
    iso = re.search(r"Isolated directory:\s+(\S+)", proc.stdout).group(1)
    assert not Path(iso).exists()


def test_40_passes_isolation_env_to_installer():
    text = CLEAN40.read_text(encoding="utf-8")
    assert "NAE_SETUP_ISOLATED=1" in text and "NAE_SETUP_PORT=" in text
    assert "IMPORTANT: This script writes ONLY" not in text  # 사실과 다르던 옛 격리 주장

"""Gate 2 스크립트 정비 회귀 시험 (재판정 D1·D2·D3·D5, docs/GATE2_REASSESSMENT_20261007.md).

격리 원칙: /tmp/dbma-gate2-run-pytest-* 이름의 임시 디렉터리만 만들고 지운다.
추적 중인 evidence/gate2/*.json은 건드리지 않는다(95는 임시 트리에 복사해 실행).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GATE2 = REPO / "scripts" / "gate2"
VENV_PY = Path.home() / "envs" / "dbma311" / "bin" / "python"


def _bash(script: str, *args: str, dry: bool = False):
    env = dict(os.environ, DRY_RUN="true" if dry else "false")
    return subprocess.run(["bash", str(GATE2 / script), *args], cwd=str(REPO),
                          capture_output=True, text=True, env=env, timeout=120)


@pytest.fixture
def run_dir():
    d = Path(tempfile.mkdtemp(prefix="dbma-gate2-run-pytest-", dir="/tmp"))
    (d / "marker.txt").write_text("x")
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ── D1: 80 dry-run은 아무것도 만들지 않고 PASS를 내지 않는다 ─────────────
def test_80_dry_run_creates_nothing_and_does_not_report_pass():
    proc = _bash("80_reinstall_upgrade.sh", dry=True)
    assert proc.returncode == 0, proc.stderr
    assert "RESULT: PASS" not in proc.stdout
    assert "DRY-RUN (no verification performed)" in proc.stdout
    m = re.search(r"Isolated directory:\s+(\S+)", proc.stdout)
    assert m and not Path(m.group(1)).exists()


# ── D2: 90 dry-run은 'Removed:'를 출력하지 않고 지우지 않는다 ────────────
def test_90_dry_run_does_not_claim_removal(run_dir):
    proc = _bash("90_uninstall.sh", str(run_dir), dry=True)
    assert proc.returncode == 0, proc.stderr
    assert "Removed:" not in proc.stdout
    assert "[DRY-RUN] would remove" in proc.stdout
    assert run_dir.exists()


# ── D3: 인자 없이는 거부, --all은 명시 opt-in, 대상은 run 디렉터리만 ───────
def test_90_without_argument_refuses_and_deletes_nothing(run_dir):
    proc = _bash("90_uninstall.sh")
    assert proc.returncode == 2
    assert run_dir.exists()


def test_90_all_dry_run_lists_but_keeps(run_dir):
    proc = _bash("90_uninstall.sh", "--all", dry=True)
    assert proc.returncode == 0, proc.stderr
    assert run_dir.name in proc.stdout
    assert run_dir.exists()


def test_90_refuses_non_run_directory(tmp_path):
    victim = Path(tempfile.mkdtemp(prefix="not-gate2-", dir="/tmp"))
    try:
        proc = _bash("90_uninstall.sh", str(victim))
        assert proc.returncode == 2
        assert victim.exists()
    finally:
        shutil.rmtree(victim, ignore_errors=True)


def test_90_removes_explicit_run_directory(run_dir):
    proc = _bash("90_uninstall.sh", str(run_dir))
    assert proc.returncode == 0, proc.stderr
    assert "Removed:" in proc.stdout
    assert not run_dir.exists()


def test_orchestrator_passes_all_flag_to_90():
    spec = importlib.util.spec_from_file_location("gate2_orchestrator", GATE2 / "gate2_orchestrator.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.SCRIPT_ARGS["90_uninstall.sh"] == ["--all"]


# ── D5: 95는 비교 0건이면 PASS가 아니다 ───────────────────────────────
def _tree_with_95(tmp_path: Path) -> Path:
    (tmp_path / "scripts" / "gate2").mkdir(parents=True)
    shutil.copy(GATE2 / "95_evidence_verify.py", tmp_path / "scripts" / "gate2" / "95_evidence_verify.py")
    (tmp_path / "evidence" / "gate2").mkdir(parents=True)
    return tmp_path


def _run_95(tree: Path):
    return subprocess.run([sys.executable, str(tree / "scripts" / "gate2" / "95_evidence_verify.py")],
                          cwd=str(tree), capture_output=True, text=True, timeout=120)


def test_95_vacuous_when_nothing_compared(tmp_path):
    tree = _tree_with_95(tmp_path)
    (tree / "evidence" / "gate2" / "10_x.json").write_text(json.dumps({"script": "x.py"}))
    proc = _run_95(tree)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    out = json.loads((tree / "evidence" / "gate2" / "95_evidence_verify.json").read_text())
    assert out["all_pass"] is False and out["status"] == "VACUOUS"
    assert out["checks"]["verification_coverage"]["compared"] == 0


@pytest.mark.skipif(not VENV_PY.exists(), reason="95는 ~/envs/dbma311 python으로 대상 스크립트를 재실행한다")
def test_95_passes_only_when_hash_matches_and_fails_on_mismatch(tmp_path):
    tree = _tree_with_95(tmp_path)
    (tree / "scripts" / "gate2" / "echo_ok.py").write_text("print('ok')\n")
    good = hashlib.sha256(b"ok\n").hexdigest()
    ev = tree / "evidence" / "gate2" / "10_echo.json"
    ev.write_text(json.dumps({"script": "echo_ok.py", "stdout_sha256": good}))
    proc = _run_95(tree)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads((tree / "evidence" / "gate2" / "95_evidence_verify.json").read_text())["checks"]["verification_coverage"]["compared"] == 1
    ev.write_text(json.dumps({"script": "echo_ok.py", "stdout_sha256": "0" * 64}))
    assert _run_95(tree).returncode == 1

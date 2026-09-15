"""tests/test_security_preflight.py — scripts/security_preflight.py 회귀.

[S1-3, DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md] 배포 전 보안 체크리스트 5건
판정 로직의 두 가지 핵심 실패 모드를 잠근다:

1. Qdrant 오탐 회귀 — 초기 구현은 `retrieval_py.count("qdrant_url") > 2`로
   "실제 사용 여부"를 판정했는데, __init__ 파라미터 선언 1회 + 대입문 1회
   (좌변 self.qdrant_url + 우변 qdrant_url로 2개 토큰)만으로 정확히 3회가
   나와 죽은 파라미터를 "사용 중"으로 오탐했다. 지금은 QdrantClient/
   qdrant_client 리터럴 존재 여부만 본다 — 이 테스트가 그 회귀를 막는다.
2. render_report()의 R7 차단 로직 — 항목 2(FileVault)는 사용자 기기
   설정이라 "사용자 조치 필요"여도 차단이 아니어야 한다.
"""

import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.security_preflight as sp


def test_qdrant_check_does_not_false_positive_on_unused_url_param():
    """core/retrieval.py의 실제 상태(qdrant_url 저장만, QdrantClient 미사용)
    기준으로 '해당없음'이 나와야 한다 — count()-기반 오탐 회귀 방지."""
    result = sp._check_qdrant_auth()
    assert result.status == "해당없음", (
        f"오탐 회귀 — qdrant_url이 저장만 되는데 '{result.status}'로 판정됨: "
        f"{result.detail}"
    )


def test_raw_dir_check_not_exists():
    result = _run_raw_dir_check_with_path(Path("/nonexistent/path/xyz"), apply=False)
    assert result.status == "해당없음"


def test_raw_dir_check_reports_755_as_unapplied(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    os.chmod(raw_dir, 0o755)

    result = _run_raw_dir_check_with_path(raw_dir, apply=False)

    assert result.status == "미적용"
    assert stat.S_IMODE(raw_dir.stat().st_mode) == 0o755  # dry-run은 변경 안 함


def test_raw_dir_check_applies_700_when_requested(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    os.chmod(raw_dir, 0o755)

    result = _run_raw_dir_check_with_path(raw_dir, apply=True)

    assert result.status == "적용됨"
    assert stat.S_IMODE(raw_dir.stat().st_mode) == 0o700


def test_raw_dir_check_already_700_is_applied_without_chmod_call(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    os.chmod(raw_dir, 0o700)

    chmod_calls = []
    monkeypatch.setattr(os, "chmod", lambda *a: chmod_calls.append(a))

    result = _run_raw_dir_check_with_path(raw_dir, apply=True)

    assert result.status == "적용됨"
    assert chmod_calls == []  # 이미 700이면 chmod를 다시 호출하지 않는다


def _run_raw_dir_check_with_path(path: Path, apply: bool) -> sp.CheckResult:
    """core.config.DEFAULT_RAW_DIR을 임시로 바꿔 _check_raw_dir_permissions를
    격리 실행한다."""
    import core.config as cfg

    original = cfg.DEFAULT_RAW_DIR
    cfg.DEFAULT_RAW_DIR = str(path)
    try:
        return sp._check_raw_dir_permissions(apply=apply)
    finally:
        cfg.DEFAULT_RAW_DIR = original


def test_render_report_passes_when_only_filevault_unresolved():
    results = [
        sp.CheckResult("1", "Qdrant", "해당없음", "d"),
        sp.CheckResult("2", "FileVault", "사용자 조치 필요", "d"),
        sp.CheckResult("3", "RAW", "적용됨", "d"),
        sp.CheckResult("4", "로그", "적용됨", "d"),
        sp.CheckResult("5", "스캔", "부분 충족", "d"),
    ]
    report = sp.render_report(results, apply=False)
    assert "R7 통과" in report
    assert "차단" not in report.split("## 배포 판정")[1]


def test_render_report_blocks_when_non_filevault_item_unresolved():
    results = [
        sp.CheckResult("1", "Qdrant", "사용자 조치 필요", "d"),  # 항목 2가 아닌데 미해결
        sp.CheckResult("2", "FileVault", "적용됨", "d"),
        sp.CheckResult("3", "RAW", "적용됨", "d"),
        sp.CheckResult("4", "로그", "적용됨", "d"),
        sp.CheckResult("5", "스캔", "부분 충족", "d"),
    ]
    report = sp.render_report(results, apply=False)
    assert "차단" in report
    assert "Qdrant" in report.split("## 배포 판정")[1]

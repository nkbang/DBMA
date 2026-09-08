"""tests/test_reset_workspace.py — scripts/reset_workspace.py (ADR-033) 회귀.

검증 항목 (ADR-033 §6.2):
  - Protected Paths(층위 A 추적 파일 · 층위 B prefix · config · RAW) 삭제 거부
  - dry-run 목록/용량 정확도 + 아무것도 삭제 안 함
  - 매니페스트 스키마 + backups/reset_<ts>/manifest.json 기록
  - 경로 오염 방지 — 모든 조작이 주입된 project_root 아래로 한정 (tmp 격리)
  - Qdrant 화이트리스트: 빈 목록 no-op · 정확 일치만 · 부분 일치 거부
  - T3 거부 · 확인 문구 · 클린 트리 가드 · RAW prefix 강제 복원

실행:
    cd ~/DBMA && source ~/envs/dbma311/bin/activate
    python -m pytest tests/test_reset_workspace.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.reset_workspace import (  # noqa: E402
    CONFIRM_PHRASES,
    RAW_SOURCE_PREFIXES,
    ResetAbort,
    drop_qdrant_collections,
    is_protected,
    resolve_protected_prefixes,
    resolve_tier_globs,
    run_reset,
)

RESET_CONFIG = """\
reset:
  protected_prefixes:
    - data/RAW/
    - NAE/corpus/raw/
    - data/bible/
    - sermon_corpus/
    - data/sermon_corpus/
    - data/beta_corpus/
    - .git
    - core/
    - scripts/
    - tests/
    - config.yaml
  tiers:
    T1:
      - "output/*"
      - "cache/*"
      - "data/normalized/*"
    T2:
      - "NAE/corpus/tsu/*"
vector_db:
  qdrant:
    url: "http://localhost:6333"
"""


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture()
def fake_project(tmp_path):
    """tmp_path 안에 git repo + 추적/비추적 파일을 갖춘 가짜 프로젝트."""
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")

    # config.yaml (추적)
    (root / "config.yaml").write_text(RESET_CONFIG, encoding="utf-8")

    # 소스 (추적)
    (root / "core").mkdir()
    (root / "core" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "s.py").write_text("y = 2\n", encoding="utf-8")

    # RAW/소스 (비추적 — gitignore 흉내)
    (root / "data" / "RAW").mkdir(parents=True)
    (root / "data" / "RAW" / "book.pdf").write_bytes(b"PDF" * 100)
    (root / "data" / "bible").mkdir(parents=True)
    (root / "data" / "bible" / "kjv.json").write_text("{}", encoding="utf-8")

    # 파생물 (비추적) — T1 삭제 대상
    (root / "output").mkdir()
    (root / "output" / "report.md").write_text("r" * 500, encoding="utf-8")
    (root / "output" / "sub").mkdir()
    (root / "output" / "sub" / "a.json").write_text("a" * 200, encoding="utf-8")
    (root / "cache").mkdir()
    (root / "cache" / "emb.bin").write_bytes(b"E" * 1000)
    (root / "data" / "normalized").mkdir(parents=True)
    (root / "data" / "normalized" / "n.txt").write_text("n", encoding="utf-8")

    # NAE/corpus/tsu — 일부 추적(FROZEN baseline 흉내) + 일부 비추적
    tsu = root / "NAE" / "corpus" / "tsu"
    (tsu / "Dagg").mkdir(parents=True)
    (tsu / "Dagg" / "tsu.json").write_text('{"frozen": true}', encoding="utf-8")
    (tsu / "scratch").mkdir()
    (tsu / "scratch" / "tmp.json").write_text("{}", encoding="utf-8")

    _git(root, "add", "config.yaml", "core", "scripts", "NAE/corpus/tsu/Dagg/tsu.json")
    _git(root, "commit", "-q", "-m", "base")
    return root


def _cfg(root):
    return root / "config.yaml"


# ── dry-run ───────────────────────────────────────────────────────────


def test_dry_run_deletes_nothing_and_reports(fake_project, capsys):
    before = {p for p in fake_project.rglob("*") if p.is_file()}
    m = run_reset(project_root=fake_project, config_path=_cfg(fake_project), tier="T1")
    after = {p for p in fake_project.rglob("*") if p.is_file()}
    assert before == after, "dry-run 이 파일을 건드림"
    assert m["dry_run"] is True
    assert m["delete_count"] == 4  # output/report.md, output/sub/a.json, cache/emb.bin, data/normalized/n.txt
    assert m["delete_bytes"] == 500 + 200 + 1000 + 1
    out = capsys.readouterr().out
    assert "dry-run" in out


def test_dry_run_size_matches_actual(fake_project):
    m = run_reset(project_root=fake_project, config_path=_cfg(fake_project), tier="T1")
    actual = (
        (fake_project / "output" / "report.md").stat().st_size
        + (fake_project / "output" / "sub" / "a.json").stat().st_size
        + (fake_project / "cache" / "emb.bin").stat().st_size
        + (fake_project / "data" / "normalized" / "n.txt").stat().st_size
    )
    assert m["delete_bytes"] == actual == 1701


# ── Protected Paths ──────────────────────────────────────────────────


def test_protected_tracked_source_and_config_never_deleted(fake_project):
    run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T2",
        apply=True,
        confirm=CONFIRM_PHRASES["T2"],
        non_interactive=True,
    )
    assert (fake_project / "config.yaml").exists()
    assert (fake_project / "core" / "mod.py").exists()
    assert (fake_project / "scripts" / "s.py").exists()
    # 층위 A: 추적된 FROZEN tsu 파일 보존
    assert (fake_project / "NAE" / "corpus" / "tsu" / "Dagg" / "tsu.json").exists()


def test_protected_raw_source_never_deleted(fake_project):
    run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T2",
        apply=True,
        confirm=CONFIRM_PHRASES["T2"],
        non_interactive=True,
    )
    assert (fake_project / "data" / "RAW" / "book.pdf").exists()
    assert (fake_project / "data" / "bible" / "kjv.json").exists()


def test_is_protected_layers():
    tracked = {"core/mod.py"}
    prefixes = ["data/RAW/", "config.yaml", "core/"]
    assert is_protected("core/mod.py", prefixes, tracked)  # layer A
    assert is_protected("data/RAW/x.pdf", prefixes, set())  # layer B dir
    assert is_protected("config.yaml", prefixes, set())  # layer B file
    assert is_protected("output/r.md", prefixes, set()) is None


# ── ADR-030 FROZEN 보호 / 불변식 ────────────────────────────────────


def test_t2_skips_tracked_tsu_deletes_untracked(fake_project):
    m = run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T2",
        apply=True,
        confirm=CONFIRM_PHRASES["T2"],
        non_interactive=True,
    )
    assert (fake_project / "NAE" / "corpus" / "tsu" / "Dagg" / "tsu.json").exists()
    assert not (fake_project / "NAE" / "corpus" / "tsu" / "scratch" / "tmp.json").exists()
    skipped = {s["path"] for s in m["skipped_protected"]}
    assert "NAE/corpus/tsu/Dagg/tsu.json" in skipped
    moved = {mv["src"] for mv in m["moved"]}
    assert "NAE/corpus/tsu/scratch/tmp.json" in moved


# ── 매니페스트 / backups 이동 ────────────────────────────────────────


def test_manifest_schema_and_move(fake_project):
    m = run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T1",
        apply=True,
        confirm=CONFIRM_PHRASES["T1"],
        non_interactive=True,
    )
    for key in (
        "adr", "tier", "timestamp", "git_branch", "git_head", "dry_run",
        "skipped_protected", "moved", "qdrant_dropped", "delete_bytes",
    ):
        assert key in m, f"매니페스트에 {key} 없음"
    assert m["adr"] == "ADR-033"
    assert m["dry_run"] is False

    backup_root = fake_project / "backups"
    reset_dirs = list(backup_root.glob("reset_*"))
    assert len(reset_dirs) == 1
    mf = reset_dirs[0] / "manifest.json"
    assert mf.exists()
    disk = json.loads(mf.read_text(encoding="utf-8"))
    assert disk["tier"] == "T1"
    # 이동된 파일이 backups 아래에 실재
    assert (reset_dirs[0] / "output" / "report.md").exists()
    assert not (fake_project / "output" / "report.md").exists()


def test_hard_delete_removes_without_backup_copy(fake_project):
    run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T1",
        apply=True,
        hard=True,
        confirm=CONFIRM_PHRASES["T1"],
        non_interactive=True,
    )
    assert not (fake_project / "output" / "report.md").exists()
    # manifest 는 여전히 기록
    reset_dirs = list((fake_project / "backups").glob("reset_*"))
    assert (reset_dirs[0] / "manifest.json").exists()
    assert not (reset_dirs[0] / "output").exists()


# ── 경로 오염 방지 ───────────────────────────────────────────────────


def test_no_write_outside_project_root(fake_project, tmp_path):
    sentinel = tmp_path / "OUTSIDE.txt"
    sentinel.write_text("keep", encoding="utf-8")
    run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T1",
        apply=True,
        confirm=CONFIRM_PHRASES["T1"],
        non_interactive=True,
    )
    assert sentinel.read_text(encoding="utf-8") == "keep"
    # tmp_path 아래 새로 생긴 것은 fake_project 내부뿐
    outside = [
        p for p in tmp_path.rglob("*")
        if p.is_file() and fake_project not in p.parents and p != sentinel
    ]
    assert outside == []


# ── Qdrant ───────────────────────────────────────────────────────────


def test_qdrant_empty_whitelist_is_noop():
    assert drop_qdrant_collections("http://localhost:6333", [], apply=True) == []
    assert drop_qdrant_collections("http://localhost:6333", [], apply=False) == []


def test_qdrant_dry_run_lists_exact_whitelist_only():
    planned = drop_qdrant_collections(
        "http://localhost:6333", ["nae_ref_v1"], apply=False
    )
    assert planned == ["nae_ref_v1"]


def test_drop_qdrant_not_invoked_in_dry_run_reset(fake_project):
    m = run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T2",
        drop_qdrant=True,
    )
    # config 의 whitelist 가 없으므로 빈 목록
    assert m["qdrant_dropped"] == []


# ── T3 거부 / 확인 문구 / 클린 트리 ─────────────────────────────────


def test_t3_is_refused(fake_project):
    with pytest.raises(ResetAbort, match="T3"):
        run_reset(project_root=fake_project, config_path=_cfg(fake_project), tier="T3")


def test_wrong_confirm_phrase_aborts(fake_project):
    with pytest.raises(ResetAbort, match="confirm|확인"):
        run_reset(
            project_root=fake_project,
            config_path=_cfg(fake_project),
            tier="T1",
            apply=True,
            confirm="RESET",
            non_interactive=True,
        )
    assert (fake_project / "output" / "report.md").exists()


def test_dirty_tracked_tree_aborts_without_force(fake_project):
    (fake_project / "core" / "mod.py").write_text("x = 999\n", encoding="utf-8")
    with pytest.raises(ResetAbort, match="uncommitted"):
        run_reset(
            project_root=fake_project,
            config_path=_cfg(fake_project),
            tier="T1",
            apply=True,
            confirm=CONFIRM_PHRASES["T1"],
            non_interactive=True,
        )


def test_dry_run_allowed_on_dirty_tree(fake_project):
    (fake_project / "core" / "mod.py").write_text("x = 999\n", encoding="utf-8")
    m = run_reset(project_root=fake_project, config_path=_cfg(fake_project), tier="T1")
    assert m["dry_run"] is True
    assert m["delete_count"] == 4


def test_dirty_tree_bypassed_with_force(fake_project):
    (fake_project / "core" / "mod.py").write_text("x = 999\n", encoding="utf-8")
    m = run_reset(
        project_root=fake_project,
        config_path=_cfg(fake_project),
        tier="T1",
        apply=True,
        force=True,
        confirm=CONFIRM_PHRASES["T1"],
        non_interactive=True,
    )
    assert m["forced"] is True
    assert not (fake_project / "output" / "report.md").exists()


# ── config 해석 ──────────────────────────────────────────────────────


def test_resolve_protected_prefixes_force_restores_raw(capsys):
    prefixes, restored = resolve_protected_prefixes(
        {"protected_prefixes": ["core/", "docs/"]}
    )
    for raw in RAW_SOURCE_PREFIXES:
        assert raw in prefixes
    assert set(restored) == set(RAW_SOURCE_PREFIXES)
    assert "강제 복원" in capsys.readouterr().out


def test_resolve_protected_prefixes_empty_uses_hardcoded():
    prefixes, restored = resolve_protected_prefixes({})
    assert "core/" in prefixes
    assert restored == []


def test_resolve_tier_globs_t2_includes_t1():
    cfg = {"tiers": {"T1": ["output/*"], "T2": ["NAE/corpus/tsu/*"]}}
    assert resolve_tier_globs(cfg, "T2") == ["output/*", "NAE/corpus/tsu/*"]
    assert resolve_tier_globs(cfg, "T1") == ["output/*"]


def test_resolve_tier_globs_rejects_t3():
    with pytest.raises(ValueError):
        resolve_tier_globs({}, "T3")

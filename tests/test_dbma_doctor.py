"""Regression test — scripts/dbma_doctor.py (SPRINT29-A).

Read-only diagnostic CLI. Tests exercise the pure check_*() functions
directly (unit-level) plus one end-to-end subprocess smoke test against
the real (production, read-only) repo state — dbma_doctor.py never writes
anything, so running it against real data in a test is safe.
"""

import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.dbma_doctor import (
    check_capacity,
    collect_known_issues,
    render_report,
    _ZONE_GREEN_MAX,
    _ZONE_YELLOW_MAX,
)


class TestCheckCapacity:
    def test_zero_tsu_is_green(self):
        assert check_capacity(0)["zone"] == "GREEN"

    def test_at_green_ceiling_is_green(self):
        assert check_capacity(_ZONE_GREEN_MAX)["zone"] == "GREEN"

    def test_just_over_green_ceiling_is_yellow(self):
        assert check_capacity(_ZONE_GREEN_MAX + 1)["zone"] == "YELLOW"

    def test_at_yellow_ceiling_is_yellow(self):
        assert check_capacity(_ZONE_YELLOW_MAX)["zone"] == "YELLOW"

    def test_over_yellow_ceiling_is_red(self):
        assert check_capacity(_ZONE_YELLOW_MAX + 1)["zone"] == "RED"

    def test_ram_estimates_scale_with_tsu_count(self):
        small = check_capacity(1000)
        large = check_capacity(2000)
        assert large["estimated_ram_healthy_mb"] > small["estimated_ram_healthy_mb"]
        assert large["estimated_ram_fallback_mb"] > small["estimated_ram_fallback_mb"]
        # fallback (TF-IDF built) must always estimate higher than healthy
        # (TF-IDF unbuilt) — SPRINT28-C measured ratio.
        assert small["estimated_ram_fallback_mb"] > small["estimated_ram_healthy_mb"]


class TestCollectKnownIssues:
    def _base_infos(self):
        git = {"dirty": False, "dirty_count": 0}
        cfg = {"pyyaml_ok": True, "python_ok": True, "python_version": "3.11.15"}
        corpus = {"documents_missing_metadata": 0}
        tsu = {
            "manifest_exists": True,
            "dataset_integrity_ok": True,
            "stray_vector_db_present": False,
        }
        embed = {"reachable": True, "embed_model_installed": True}
        return git, cfg, corpus, tsu, embed

    def test_clean_state_has_no_issues(self):
        git, cfg, corpus, tsu, embed = self._base_infos()
        issues = collect_known_issues(git, cfg, corpus, tsu, embed, None)
        assert issues == []

    def test_dirty_tree_is_flagged(self):
        git, cfg, corpus, tsu, embed = self._base_infos()
        git["dirty"] = True
        git["dirty_count"] = 3
        issues = collect_known_issues(git, cfg, corpus, tsu, embed, None)
        assert any("dirty" in i.lower() for i in issues)

    def test_dataset_integrity_mismatch_is_flagged(self):
        git, cfg, corpus, tsu, embed = self._base_infos()
        tsu["dataset_integrity_ok"] = False
        issues = collect_known_issues(git, cfg, corpus, tsu, embed, None)
        assert any("sha256" in i.lower() for i in issues)

    def test_stray_vector_db_is_flagged(self):
        git, cfg, corpus, tsu, embed = self._base_infos()
        tsu["stray_vector_db_present"] = True
        issues = collect_known_issues(git, cfg, corpus, tsu, embed, None)
        assert any("vector db" in i.lower() for i in issues)

    def test_unreachable_embedding_backend_is_flagged(self):
        git, cfg, corpus, tsu, embed = self._base_infos()
        embed["reachable"] = False
        embed["embed_model_installed"] = None
        issues = collect_known_issues(git, cfg, corpus, tsu, embed, None)
        assert any("unreachable" in i.lower() for i in issues)

    def test_failed_test_run_is_flagged(self):
        git, cfg, corpus, tsu, embed = self._base_infos()
        test_info = {"passed": False, "summary_line": "1 failed, 344 passed"}
        issues = collect_known_issues(git, cfg, corpus, tsu, embed, test_info)
        assert any("regression" in i.lower() for i in issues)


class TestRenderReport:
    def test_report_contains_required_sections(self):
        git = {"branch": "main", "head": "abc1234", "dirty": False, "dirty_count": 0}
        cfg = {
            "python_version": "3.11.15", "python_ok": True, "app_version": "1.3.0",
            "embed_model": "bge-m3:latest", "gen_model": "test-gen",
            "chunk_size": 1200, "chunk_overlap": 120,
        }
        corpus = {"raw_file_count": 10, "registered_document_count": 10, "total_chunk_count": 100, "documents_missing_metadata": 0}
        tsu = {
            "tsu_count": 100, "source_document_count": 10, "generated_at": "2026-01-01T00:00:00",
            "dataset_size_mb": 1.0, "dataset_integrity_ok": True,
        }
        embed = {"reachable": True}
        bench = None
        capacity = check_capacity(100)
        report = render_report(git, cfg, corpus, tsu, embed, bench, capacity, [], None, 0.1)

        assert "DBMA HEALTH REPORT" in report
        assert "Branch" in report
        assert "TSU" in report
        assert "Capacity" in report
        assert "Known Issues" in report
        assert "Recommendation" in report

    def test_no_issues_shows_none_detected(self):
        git = {"branch": "main", "head": "abc1234", "dirty": False, "dirty_count": 0}
        cfg = {
            "python_version": "3.11.15", "python_ok": True, "app_version": "1.3.0",
            "embed_model": "m", "gen_model": "g", "chunk_size": 1200, "chunk_overlap": 120,
        }
        corpus = {"raw_file_count": 0, "registered_document_count": 0, "total_chunk_count": 0, "documents_missing_metadata": 0}
        tsu = {"tsu_count": 0, "source_document_count": 0, "generated_at": None, "dataset_size_mb": 0, "dataset_integrity_ok": None}
        embed = {"reachable": True}
        capacity = check_capacity(0)
        report = render_report(git, cfg, corpus, tsu, embed, None, capacity, [], None, 0.1)
        assert "none detected" in report


def test_end_to_end_smoke_json():
    """dbma_doctor.py is read-only — safe to run against real repo state."""
    proc = subprocess.run(
        [sys.executable, "scripts/dbma_doctor.py", "--json"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True, text=True, timeout=30,
    )
    data = json.loads(proc.stdout)
    for key in ("git", "config", "corpus", "tsu", "embedding_backend", "capacity", "known_issues"):
        assert key in data
    assert data["capacity"]["zone"] in ("GREEN", "YELLOW", "RED")

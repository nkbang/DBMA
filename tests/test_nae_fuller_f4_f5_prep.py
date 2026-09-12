"""F4/F5 Fuller 준비 스크립트 회귀 테스트 (ADR-030 Amendment A §3/§8).

Amendment A는 PROPOSED 상태 — F4/F5 실제 실행(--apply)은 Approved 후에만
허용된다. 이 테스트는 스크립트의 안전장치(기본 dry-run, --apply 없이는
Ollama/Qdrant 호출 0건)와, 실제 verified 레코드가 있을 때의 로직을
synthetic 데이터 + mock으로 검증한다. Production 코퍼스나 Qdrant를
건드리지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _write_vol(tsu_dir: Path, vol: str, records: list[dict]) -> None:
    vol_dir = tsu_dir / vol
    vol_dir.mkdir(parents=True, exist_ok=True)
    (vol_dir / "tsu.json").write_text(json.dumps(records), encoding="utf-8")


class TestF4EmbedDryRun:
    def test_default_dry_run_makes_zero_embed_calls(self, tmp_path, monkeypatch):
        from scripts import nae_fuller_f4_embed as f4

        tsu_dir = tmp_path / "tsu"
        _write_vol(tsu_dir, "Fuller_Complete_Works_Vol01", [
            {"id": "TSU-0000001", "review_status": "verified", "claim": "faith and repentance", "book": "b1", "page": 1, "scriptures": []},
            {"id": "TSU-0000002", "review_status": "generated", "claim": "unverified claim", "book": "b1", "page": 2, "scriptures": []},
        ])

        embed_calls = MagicMock()
        monkeypatch.setattr(f4.embed_client, "embed_text", embed_calls)
        monkeypatch.setattr(f4.embed_client, "get_cached", lambda *a, **k: None)

        report = f4.run(apply=False, tsu_dir=tsu_dir, report_path=tmp_path / "report.json")

        embed_calls.assert_not_called()
        assert report["mode"] == "dry-run"
        assert report["verified_total"] == 1  # only the verified record counts
        assert report["would_embed"] == 1
        assert report["newly_embedded"] == 0

    def test_apply_embeds_only_cache_misses(self, tmp_path, monkeypatch):
        from scripts import nae_fuller_f4_embed as f4

        tsu_dir = tmp_path / "tsu"
        _write_vol(tsu_dir, "Fuller_Complete_Works_Vol01", [
            {"id": "TSU-0000001", "review_status": "verified", "claim": "c1", "book": "b1", "page": 1, "scriptures": []},
            {"id": "TSU-0000002", "review_status": "verified", "claim": "c2", "book": "b1", "page": 2, "scriptures": []},
        ])

        # First record already cached, second is a miss.
        monkeypatch.setattr(f4.embed_client, "get_cached", lambda h, *a, **k: [0.1] if h.endswith("dummy") else None)
        embed_calls = MagicMock(return_value=[0.1] * 1024)
        monkeypatch.setattr(f4.embed_client, "embed_text", embed_calls)

        report = f4.run(apply=True, tsu_dir=tsu_dir, report_path=tmp_path / "report.json")

        assert report["verified_total"] == 2
        assert embed_calls.call_count == 2  # both are cache misses in this monkeypatch
        assert report["newly_embedded"] == 2

    def test_missing_volume_dirs_are_skipped_not_errored(self, tmp_path):
        from scripts import nae_fuller_f4_embed as f4

        empty_tsu_dir = tmp_path / "empty"
        empty_tsu_dir.mkdir()
        report = f4.run(apply=False, tsu_dir=empty_tsu_dir, report_path=tmp_path / "report.json")
        assert report["verified_total"] == 0


class TestF5UpsertDryRun:
    def test_default_dry_run_makes_zero_qdrant_writes(self, tmp_path, monkeypatch):
        from scripts import nae_fuller_f5_upsert as f5

        tsu_dir = tmp_path / "tsu"
        _write_vol(tsu_dir, "Fuller_Complete_Works_Vol01", [
            {"id": "TSU-0000001", "review_status": "verified", "claim": "c1", "book": "b1", "page": 1, "scriptures": []},
        ])

        fake_client = MagicMock()
        # baseline: 3319 pre-existing points, none of them Fuller.
        fake_client.scroll.return_value = ([
            MagicMock(payload={"tsu_id": f"TSU-{i:07d}"}) for i in range(1, 3320)
        ], None)
        monkeypatch.setattr(f5.qdrant_store, "get_client", lambda *a, **k: fake_client)
        monkeypatch.setattr(f5, "_embed_for_upsert", lambda record: [0.1] * 1024)

        report = f5.run(apply=False, tsu_dir=tsu_dir, report_path=tmp_path / "report.json")

        fake_client.upsert.assert_not_called()
        assert report["mode"] == "dry-run"
        assert report["baseline_count"] == 3319
        assert report["fuller_verified_total"] == 1

    def test_apply_refuses_if_baseline_count_drifted(self, tmp_path, monkeypatch):
        """§ baseline guard: if the pre-upsert scroll doesn't show exactly the
        expected 3,319 baseline points, refuse to touch Qdrant at all."""
        from scripts import nae_fuller_f5_upsert as f5

        tsu_dir = tmp_path / "tsu"
        _write_vol(tsu_dir, "Fuller_Complete_Works_Vol01", [
            {"id": "TSU-0000001", "review_status": "verified", "claim": "c1", "book": "b1", "page": 1, "scriptures": []},
        ])

        fake_client = MagicMock()
        # Drifted baseline: only 3000 points instead of 3319.
        fake_client.scroll.return_value = ([
            MagicMock(payload={"tsu_id": f"TSU-{i:07d}"}) for i in range(1, 3001)
        ], None)
        monkeypatch.setattr(f5.qdrant_store, "get_client", lambda *a, **k: fake_client)

        with pytest.raises(f5.BaselineDriftError):
            f5.run(apply=True, tsu_dir=tsu_dir, report_path=tmp_path / "report.json")

        fake_client.upsert.assert_not_called()

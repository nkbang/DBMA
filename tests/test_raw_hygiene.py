"""Regression test — core/raw_hygiene.py::find_exact_duplicate_raw_files()
(2026-08-24, 사용자 요청: "원본 폴더에 동일한 내용 듀플리케이트 파일은
하나로 정리해야 한다. 워닝하고 삭제하도록 하라").

바이트 단위 완전 일치만 탐지한다 — 유사도 기반 탐지는 오탐 위험 때문에
의도적으로 범위 밖(core/raw_hygiene.py 모듈 docstring 참고).
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.raw_hygiene import (
    find_exact_duplicate_raw_files,
    purge_expired_trash,
    maybe_purge_expired_trash,
    find_orphaned_processed_documents,
    cleanup_orphaned_document,
)
from core.identity_registry import save_identity_registry, load_identity_registry, _empty_registry


class TestFindExactDuplicateRawFiles:
    def test_no_raw_dir_returns_empty(self, tmp_path):
        assert find_exact_duplicate_raw_files(str(tmp_path / "does_not_exist")) == []

    def test_no_duplicates_returns_empty(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"content-a")
        (tmp_path / "b.pdf").write_bytes(b"content-b")
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_identical_content_flagged_as_duplicate_group(self, tmp_path):
        (tmp_path / "7. 사도행전1.pdf").write_bytes(b"same bytes")
        (tmp_path / "7. 사도행전1 복사본.pdf").write_bytes(b"same bytes")
        (tmp_path / "unrelated.pdf").write_bytes(b"different")

        groups = find_exact_duplicate_raw_files(str(tmp_path))
        assert len(groups) == 1
        names = {f["name"] for f in groups[0]["files"]}
        assert names == {"7. 사도행전1.pdf", "7. 사도행전1 복사본.pdf"}

    def test_different_content_same_size_not_flagged(self, tmp_path):
        """바이트가 다르면 크기가 같아도 중복이 아니다 — 순수 해시 비교."""
        (tmp_path / "a.pdf").write_bytes(b"aaaaaaaaaa")
        (tmp_path / "b.pdf").write_bytes(b"bbbbbbbbbb")
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_near_duplicate_scans_not_flagged(self, tmp_path):
        """[의도된 범위 제한] 재스캔본처럼 내용은 거의 같아도 바이트가
        다르면(한 글자만 달라도) 탐지하지 않는다 — 오탐 방지."""
        (tmp_path / "5. 요한복음1.pdf").write_bytes(b"x" * 1000 + b"A")
        (tmp_path / "5. 요한복음1clearscan_cropped.pdf").write_bytes(b"x" * 1000 + b"B")
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_finds_duplicates_in_subfolder(self, tmp_path):
        """[동일 근본원인] processing.py의 하위 폴더 스캔 수정과 같은 기준
        — 중복 탐지도 RAW 최상위만 봐서는 안 된다."""
        sub = tmp_path / "설교_분리"
        sub.mkdir()
        (tmp_path / "top.md").write_bytes(b"sermon content")
        (sub / "copy.md").write_bytes(b"sermon content")

        groups = find_exact_duplicate_raw_files(str(tmp_path))
        assert len(groups) == 1
        names = {f["name"] for f in groups[0]["files"]}
        assert names == {"top.md", "copy.md"}

    def test_unsupported_extension_ignored(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"same")
        (tmp_path / "b.exe").write_bytes(b"same")  # not a supported document extension
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_group_of_three_returns_all_three(self, tmp_path):
        for name in ["a.pdf", "b.pdf", "c.pdf"]:
            (tmp_path / name).write_bytes(b"triple")
        groups = find_exact_duplicate_raw_files(str(tmp_path))
        assert len(groups) == 1
        assert len(groups[0]["files"]) == 3


class TestPurgeExpiredTrash:
    """[2026-08-24 사용자 요청: "휴지통 자동 비우기 정책"]"""

    def test_no_backup_root_returns_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", tmp_path / "backups")
        assert purge_expired_trash() == {"purged_dirs": [], "purged_file_count": 0}

    def test_old_trash_dir_is_purged(self, tmp_path, monkeypatch):
        backup_root = tmp_path / "backups"
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", backup_root)

        old_dir = backup_root / "deleted_raw_20260101"
        old_dir.mkdir(parents=True)
        (old_dir / "a.pdf").write_bytes(b"x")
        (old_dir / "b.pdf").write_bytes(b"y")

        result = purge_expired_trash(retention_days=30, now=datetime(2026, 8, 24))

        assert result == {"purged_dirs": [str(old_dir)], "purged_file_count": 2}
        assert not old_dir.exists()

    def test_recent_trash_dir_is_kept(self, tmp_path, monkeypatch):
        backup_root = tmp_path / "backups"
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", backup_root)

        recent_dir = backup_root / "deleted_raw_20260820"
        recent_dir.mkdir(parents=True)
        (recent_dir / "a.pdf").write_bytes(b"x")

        result = purge_expired_trash(retention_days=30, now=datetime(2026, 8, 24))

        assert result == {"purged_dirs": [], "purged_file_count": 0}
        assert recent_dir.exists()

    def test_exactly_at_boundary_is_purged(self, tmp_path, monkeypatch):
        """정확히 retention_days 지난 경계는 삭제(>=)."""
        backup_root = tmp_path / "backups"
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", backup_root)

        now = datetime(2026, 8, 24)
        boundary_dir = backup_root / (now - timedelta(days=30)).strftime("deleted_raw_%Y%m%d")
        boundary_dir.mkdir(parents=True)
        (boundary_dir / "a.pdf").write_bytes(b"x")

        result = purge_expired_trash(retention_days=30, now=now)
        assert result["purged_dirs"] == [str(boundary_dir)]

    def test_excluded_documents_dirs_are_never_touched(self, tmp_path, monkeypatch):
        """"휴지통"은 deleted_raw_*만 가리킨다 — excluded_documents_*는
        범위 밖(모듈 docstring 근거)."""
        backup_root = tmp_path / "backups"
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", backup_root)

        old_excluded = backup_root / "excluded_documents_20260101"
        old_excluded.mkdir(parents=True)
        (old_excluded / "a.md").write_bytes(b"x")

        purge_expired_trash(retention_days=30, now=datetime(2026, 8, 24))
        assert old_excluded.exists()

    def test_malformed_dir_name_is_skipped_not_crashed(self, tmp_path, monkeypatch):
        backup_root = tmp_path / "backups"
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", backup_root)
        weird_dir = backup_root / "deleted_raw_not-a-date"
        weird_dir.mkdir(parents=True)

        result = purge_expired_trash(retention_days=30, now=datetime(2026, 8, 24))
        assert result == {"purged_dirs": [], "purged_file_count": 0}
        assert weird_dir.exists()


class TestMaybePurgeExpiredTrash:
    def test_first_call_runs_check_and_writes_marker(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", tmp_path / "backups")
        output_dir = tmp_path / "output"

        result = maybe_purge_expired_trash(output_dir=str(output_dir))

        assert result == {"purged_dirs": [], "purged_file_count": 0}
        assert (output_dir / ".trash_cleanup_marker").exists()

    def test_second_call_same_day_is_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.raw_hygiene.BACKUP_ROOT", tmp_path / "backups")
        output_dir = tmp_path / "output"

        first = maybe_purge_expired_trash(output_dir=str(output_dir))
        second = maybe_purge_expired_trash(output_dir=str(output_dir))

        assert first is not None
        assert second is None  # 같은 날 두 번째 호출은 마커 때문에 건너뜀


def _write_registry(path, documents: dict) -> None:
    registry = _empty_registry()
    registry["documents"] = documents
    save_identity_registry(registry, str(path))


def _make_doc(doc_id: str, source_file: str, **overrides) -> dict:
    base = {
        "document_id": doc_id,
        "file_hash": doc_id,
        "source_file": source_file,
        "chunk_count": 2,
        "ingest_status": "PROCESSED",
        "superseded_by": None,
    }
    base.update(overrides)
    return base


class TestFindOrphanedProcessedDocuments:
    """[2026-08-24 사용자 요청: "원본 파일이 웹 밖에서 지워지면 사용자에게
    노티스"]"""

    def test_no_orphans_when_all_raw_present(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "a.pdf").write_bytes(b"x")
        output_dir = tmp_path / "output"
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {"d1": _make_doc("d1", "a.pdf")})

        assert find_orphaned_processed_documents(str(raw_dir), str(output_dir)) == []

    def test_missing_raw_file_is_flagged(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        output_dir = tmp_path / "output"
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {"d1": _make_doc("d1", "gone.pdf")})

        orphans = find_orphaned_processed_documents(str(raw_dir), str(output_dir))
        assert len(orphans) == 1
        assert orphans[0]["document_id"] == "d1"
        assert orphans[0]["source_file"] == "gone.pdf"

    def test_excluded_document_not_flagged(self, tmp_path):
        """이미 제외 처리된 문서는 원본이 없어도 재알림 대상이 아니다 —
        사용자가 이미 처리한 케이스."""
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        output_dir = tmp_path / "output"
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {
            "d1": _make_doc("d1", "gone.pdf", ingest_status="EXCLUDED"),
        })
        assert find_orphaned_processed_documents(str(raw_dir), str(output_dir)) == []

    def test_superseded_document_not_flagged(self, tmp_path):
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        output_dir = tmp_path / "output"
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {
            "d1": _make_doc("d1", "gone.pdf", superseded_by="d2"),
        })
        assert find_orphaned_processed_documents(str(raw_dir), str(output_dir)) == []

    def test_nfd_vs_nfc_filename_not_falsely_flagged(self, tmp_path):
        import unicodedata
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        nfd_name = unicodedata.normalize("NFD", "고린도전서.pdf")
        nfc_name = unicodedata.normalize("NFC", "고린도전서.pdf")
        (raw_dir / nfd_name).write_bytes(b"x")

        output_dir = tmp_path / "output"
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {"d1": _make_doc("d1", nfc_name)})

        assert find_orphaned_processed_documents(str(raw_dir), str(output_dir)) == []

    def test_file_in_raw_subfolder_not_falsely_flagged(self, tmp_path):
        raw_dir = tmp_path / "RAW"
        sub = raw_dir / "설교_분리"
        sub.mkdir(parents=True)
        (sub / "sermon.md").write_bytes(b"x")

        output_dir = tmp_path / "output"
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {"d1": _make_doc("d1", "sermon.md")})

        assert find_orphaned_processed_documents(str(raw_dir), str(output_dir)) == []


class TestCleanupOrphanedDocument:
    def test_purges_tsu_and_marks_excluded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(tmp_path / "tsu.jsonl"))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(tmp_path / "manifest.json"))
        monkeypatch.setattr("core.index_orchestrator.BACKUP_ROOT", tmp_path / "backups")
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_BIBLE_INDEX_PATH", str(tmp_path / "bible.sqlite3"))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_CANDIDATE_INDEX_DIR", str(tmp_path / "tantivy"))

        output_dir = tmp_path / "output"
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {"d1": _make_doc("d1", "gone.pdf")})

        import json
        tsu_path = tmp_path / "tsu.jsonl"
        tsu_path.write_text(
            json.dumps({"document_id": "d1", "source_file": "gone.pdf", "content": "x"}) + "\n",
            encoding="utf-8",
        )

        result = cleanup_orphaned_document("d1", output_dir=str(output_dir))

        assert result["purged_tsu_records"] == 1
        reg = load_identity_registry(str(registry_path))
        assert reg["documents"]["d1"]["ingest_status"] == "EXCLUDED"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

"""Regression test — ui/pages/dashboard.py RAW 문서 처리완료/미처리 구분
(2026-07-24). "RAW 대기 문서" 라벨이 처리 여부와 무관하게 폴더 내 파일
수만 셌던 문제(사용자 보고: 69권 전부 이미 처리 완료 상태였음) 수정
검증. Streamlit 위젯은 호출하지 않고 순수 로직 함수만 검증한다.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import ui.pages.dashboard as mod


def _write_tsu_dataset(path: Path, source_files: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for sf in source_files:
            fh.write(json.dumps({"source_file": sf}, ensure_ascii=False) + "\n")


def test_all_raw_files_processed(tmp_path, monkeypatch):
    raw_dir = tmp_path / "RAW"
    raw_dir.mkdir()
    (raw_dir / "a.pdf").write_text("x")
    (raw_dir / "b.pdf").write_text("x")

    tsu_path = tmp_path / "tsu.jsonl"
    _write_tsu_dataset(tsu_path, ["a.pdf", "b.pdf"])

    monkeypatch.setattr(mod, "DEFAULT_RAW_DIR", str(raw_dir))
    monkeypatch.setattr("core.config.DEFAULT_TSU_DATASET_PATH", str(tsu_path))

    result = mod._get_raw_processing_breakdown()
    assert result == {"total": 2, "processed": 2, "unprocessed": 0}


def test_partial_processing(tmp_path, monkeypatch):
    raw_dir = tmp_path / "RAW"
    raw_dir.mkdir()
    (raw_dir / "a.pdf").write_text("x")
    (raw_dir / "b.pdf").write_text("x")
    (raw_dir / "c.pdf").write_text("x")

    tsu_path = tmp_path / "tsu.jsonl"
    _write_tsu_dataset(tsu_path, ["a.pdf"])

    monkeypatch.setattr(mod, "DEFAULT_RAW_DIR", str(raw_dir))
    monkeypatch.setattr("core.config.DEFAULT_TSU_DATASET_PATH", str(tsu_path))

    result = mod._get_raw_processing_breakdown()
    assert result == {"total": 3, "processed": 1, "unprocessed": 2}


def test_missing_tsu_dataset_treats_all_as_unprocessed(tmp_path, monkeypatch):
    raw_dir = tmp_path / "RAW"
    raw_dir.mkdir()
    (raw_dir / "a.pdf").write_text("x")

    monkeypatch.setattr(mod, "DEFAULT_RAW_DIR", str(raw_dir))
    monkeypatch.setattr("core.config.DEFAULT_TSU_DATASET_PATH", str(tmp_path / "nonexistent.jsonl"))

    result = mod._get_raw_processing_breakdown()
    assert result == {"total": 1, "processed": 0, "unprocessed": 1}


def test_missing_raw_dir_returns_zeros(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "DEFAULT_RAW_DIR", str(tmp_path / "does_not_exist"))
    result = mod._get_raw_processing_breakdown()
    assert result == {"total": 0, "processed": 0, "unprocessed": 0}


def test_count_documents_includes_rtf_extension(tmp_path, monkeypatch):
    """[버그 수정] _count_documents()가 core.config.SUPPORTED_EXTENSIONS
    (rtf/html/htm 포함 8종)를 쓰는지 확인 — 이전엔 5종만 하드코딩돼
    .rtf 파일을 누락시켰다."""
    raw_dir = tmp_path / "RAW"
    raw_dir.mkdir()
    (raw_dir / "a.pdf").write_text("x")
    (raw_dir / "b.rtf").write_text("x")

    monkeypatch.setattr(mod, "DEFAULT_RAW_DIR", str(raw_dir))

    assert mod._count_documents() == 2

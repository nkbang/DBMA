"""tests/test_reset_for_beta_reseed.py — scripts/reset_for_beta.py 재적재 회귀.

[2026-09-15, S5 선결] scripts/reset_for_beta.py는 원래 초기화 후 아무것도
다시 채우지 않아, "배포판은 첫 실행부터 퍼블릭 도메인 기본 코퍼스(67종)를
갖춰야 한다"는 NAE_FREE_DISTRIBUTION_PLAN_v1.md "① 기본 동봉" 계획과
충돌했다(초기화를 실행하면 방금 적재한 기본 코퍼스가 지워진 채로
패키징됨). `reseed_baseline()`을 추가해 초기화 직후
`baseline_corpus_manifest.json` 기준으로 다시 채우도록 고쳤다.

실제 파일 I/O·인제스트 파이프라인은 mock으로 대체하고, 매니페스트 읽기 →
원본 존재 확인 → 파일 복사 → process_batch/reconcile_pending 호출까지의
로직만 검증한다(실제 Ollama·임베딩 호출 없음). 실제 `--execute` 전체 실행
(진짜 데이터 삭제)은 이 테스트 범위가 아니다 — 별도로 라이브 확인한다.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.reset_for_beta as rfb


def _write_manifest(path: Path, source_root: Path, entries: list[dict]) -> None:
    path.write_text(json.dumps({
        "_note": "test",
        "source_root": str(source_root),
        "source_file_in_dir": "ocr.txt",
        "count": len(entries),
        "entries": entries,
    }, ensure_ascii=False), encoding="utf-8")


def test_reseed_skips_when_manifest_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rfb, "BASELINE_MANIFEST_PATH", tmp_path / "does_not_exist.json")

    rfb.reseed_baseline()

    assert "재적재 건너뜀" in capsys.readouterr().out


def test_reseed_skips_when_source_root_missing(tmp_path, monkeypatch, capsys):
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, tmp_path / "nonexistent_archive", [
        {"filename": "A.txt", "source_dir": "A"},
    ])
    monkeypatch.setattr(rfb, "BASELINE_MANIFEST_PATH", manifest_path)

    rfb.reseed_baseline()

    out = capsys.readouterr().out
    assert "원본 아카이브 없음" in out
    assert "건너뜀" in out


def test_reseed_copies_files_and_calls_pipeline(tmp_path, monkeypatch):
    # 원본 아카이브 구성: source_root/<source_dir>/ocr.txt
    source_root = tmp_path / "archive"
    (source_root / "BookA").mkdir(parents=True)
    (source_root / "BookA" / "ocr.txt").write_text("본문 A", encoding="utf-8")
    (source_root / "BookB").mkdir(parents=True)
    (source_root / "BookB" / "ocr.txt").write_text("본문 B", encoding="utf-8")
    # BookC는 원본이 없는 케이스(누락 처리 확인용)

    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, source_root, [
        {"filename": "BookA.txt", "source_dir": "BookA"},
        {"filename": "BookB.txt", "source_dir": "BookB"},
        {"filename": "BookC.txt", "source_dir": "BookC"},
    ])
    monkeypatch.setattr(rfb, "BASELINE_MANIFEST_PATH", manifest_path)

    raw_dir = tmp_path / "data_raw"
    monkeypatch.setattr(rfb, "DEFAULT_RAW_DIR", str(raw_dir))

    captured_file_list = []
    reconcile_called = []

    def fake_process_batch(file_list, converter, splitter, output_dir, chunk_size,
                            chunk_overlap, force_reingest=False, force_rechunk=False):
        captured_file_list.extend(file_list)
        return [{"success": True} for _ in file_list]

    def fake_reconcile_pending(output_dir):
        reconcile_called.append(output_dir)
        return {"reconciled": len(captured_file_list), "failed": []}

    import core.processing as processing_mod
    import core.index_orchestrator as orchestrator_mod

    monkeypatch.setattr(processing_mod, "build_converter", lambda use_ocr=False: object())
    monkeypatch.setattr(processing_mod, "build_splitter", lambda chunk_size, chunk_overlap: object())
    monkeypatch.setattr(processing_mod, "process_batch", fake_process_batch)
    monkeypatch.setattr(orchestrator_mod, "reconcile_pending", fake_reconcile_pending)

    rfb.reseed_baseline()

    # BookA/BookB만 복사되고 처리 대상에 포함됨 — BookC(원본 없음)는 제외
    names = sorted(f["name"] for f in captured_file_list)
    assert names == ["BookA.txt", "BookB.txt"]
    assert (raw_dir / "BookA.txt").read_text(encoding="utf-8") == "본문 A"
    assert (raw_dir / "BookB.txt").read_text(encoding="utf-8") == "본문 B"
    assert not (raw_dir / "BookC.txt").exists()
    assert reconcile_called  # reconcile_pending이 호출됐다


def test_execute_reseed_flag_controls_reseed_call(tmp_path, monkeypatch):
    """--no-reseed(reseed=False)면 reseed_baseline()을 호출하지 않는다."""
    calls = []
    monkeypatch.setattr(rfb, "reseed_baseline", lambda: calls.append("called"))
    monkeypatch.setattr(rfb, "_backup_dir", lambda: tmp_path / "backup")

    # execute()의 파일 I/O 부분은 건드리지 않도록 디렉토리/파일 리스트를 비운다
    monkeypatch.setattr(rfb, "RESET_DIRS", [])
    monkeypatch.setattr(rfb, "RESET_FILES", [])
    monkeypatch.setattr(
        rfb, "registry_path_for",
        lambda output_dir: str(tmp_path / "registry" / "documents.json"),
    )

    rfb.execute(reseed=False)
    assert calls == []

    rfb.execute(reseed=True)
    assert calls == ["called"]

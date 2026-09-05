"""test_list_source_files_registry_filter.py — list_source_files()의 registry
필터링 검증.

TASK-053: Chat 파일 선택 목록에서 삭제된 원본 필터링
근본 원인: list_source_files()가 TSU 데이터셋 원본 그대로 파일명을 반환 —
registry와 대조 없음. 수정: registry 기준으로 필터링 (ingest_status ==
"PROCESSED" + superseded_by is None).

모든 테스트는 임시 픽스처 디렉토리(tmp_path)로 격리된다.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tsu_path(tmp_path: Path) -> Path:
    """가짜 TSU dataset (JSONL 형식 — RetrievalEngine._load_corpus() 호환)."""
    p = tmp_path / "tsu.jsonl"
    lines = [
        json.dumps({"source_file": "valid.pdf", "content": "A"}, ensure_ascii=False),
        json.dumps({"source_file": "excluded.pdf", "content": "B"}, ensure_ascii=False),
        json.dumps({"source_file": "superseded.pdf", "content": "C"}, ensure_ascii=False),
        json.dumps({"source_file": "no_registry.pdf", "content": "D"}, ensure_ascii=False),
        json.dumps({"source_file": "replacement.pdf", "content": "E"}, ensure_ascii=False),
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


@pytest.fixture()
def registry_path(tmp_path: Path) -> Path:
    """가짜 registry (documents.json 형식)."""
    p = tmp_path / "registry" / "documents.json"
    p.parent.mkdir(parents=True)

    registry = {
        "schema_version": "2.0",
        "documents": {
            "d1": {
                "document_id": "d1",
                "source_file": "valid.pdf",
                "ingest_status": "PROCESSED",
                "superseded_by": None,
            },
            "d2": {
                "document_id": "d2",
                "source_file": "excluded.pdf",
                "ingest_status": "EXCLUDED",
                "superseded_by": None,
            },
            "d3": {
                "document_id": "d3",
                "source_file": "superseded.pdf",
                "ingest_status": "PROCESSED",
                "superseded_by": "d4",
            },
            "d4": {
                "document_id": "d4",
                "source_file": "replacement.pdf",
                "ingest_status": "PROCESSED",
                "superseded_by": None,
            },
        },
    }
    p.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_only_valid_processed_files_returned(tsu_path: Path, registry_path: Path) -> None:
    """registry에 PROCESSED + superseded_by=None인 문서의 source_file만 반환."""
    from core.retrieval import RetrievalEngine

    engine = RetrievalEngine(str(tsu_path))
    result = engine.list_source_files(registry_path=str(registry_path))

    # valid.pdf (PROCESSED, no superseded_by) -> 포함
    assert "valid.pdf" in result
    # replacement.pdf (PROCESSED, no superseded_by) -> 포함
    assert "replacement.pdf" in result
    # excluded.pdf (EXCLUDED) -> 제외
    assert "excluded.pdf" not in result
    # superseded.pdf (superseded_by=d4) -> 제외
    assert "superseded.pdf" not in result
    # no_registry.pdf (registry에 없음) -> 제외
    assert "no_registry.pdf" not in result


def test_no_registry_file_returns_all_from_tsu(tsu_path: Path, tmp_path: Path) -> None:
    """registry 파일이 없으면 TSU 원본 그대로 반환 (후진 호환성)."""
    from core.retrieval import RetrievalEngine

    engine = RetrievalEngine(str(tsu_path))
    # 존재하지 않는 registry 파일 경로
    nonexistent = str(tmp_path / "nonexistent_registry.json")
    result = engine.list_source_files(registry_path=nonexistent)

    assert "valid.pdf" in result
    assert "excluded.pdf" in result
    assert "superseded.pdf" in result
    assert "no_registry.pdf" in result


def test_empty_registry_returns_empty(tsu_path: Path, tmp_path: Path) -> None:
    """registry가 비어있으면 빈 리스트 반환."""
    from core.retrieval import RetrievalEngine

    engine = RetrievalEngine(str(tsu_path))

    empty_reg = tmp_path / "empty_registry.json"
    empty_reg.write_text(json.dumps({"schema_version": "2.0", "documents": {}}), encoding="utf-8")

    result = engine.list_source_files(registry_path=str(empty_reg))
    assert result == []


def test_missing_registry_file_returns_all_from_tsu(tsu_path: Path, tmp_path: Path) -> None:
    """registry 파일이 없으면 TSU 원본 그대로 반환."""
    from core.retrieval import RetrievalEngine

    engine = RetrievalEngine(str(tsu_path))
    nonexistent = str(tmp_path / "does_not_exist.json")

    result = engine.list_source_files(registry_path=nonexistent)
    assert "valid.pdf" in result
    assert "excluded.pdf" in result


def test_all_registry_docs_excluded_returns_empty(tsu_path: Path, tmp_path: Path) -> None:
    """registry의 모든 문서가 EXCLUDED이면 빈 리스트 반환."""
    from core.retrieval import RetrievalEngine

    engine = RetrievalEngine(str(tsu_path))

    all_excluded = tmp_path / "all_excluded.json"
    all_excluded.write_text(
        json.dumps({
            "schema_version": "2.0",
            "documents": {
                "d1": {
                    "document_id": "d1",
                    "source_file": "valid.pdf",
                    "ingest_status": "EXCLUDED",
                    "superseded_by": None,
                },
            },
        }),
        encoding="utf-8",
    )

    result = engine.list_source_files(registry_path=str(all_excluded))
    assert result == []


def test_no_source_file_in_registry_ignored(tsu_path: Path, tmp_path: Path) -> None:
    """registry에 source_file 필드가 없거나 빈 문자열인 문서는 무시."""
    from core.retrieval import RetrievalEngine

    engine = RetrievalEngine(str(tsu_path))

    partial_reg = tmp_path / "partial.json"
    partial_reg.write_text(
        json.dumps({
            "schema_version": "2.0",
            "documents": {
                "d1": {
                    "document_id": "d1",
                    "source_file": "",
                    "ingest_status": "PROCESSED",
                    "superseded_by": None,
                },
                "d2": {
                    "document_id": "d2",
                    "ingest_status": "PROCESSED",
                    "superseded_by": None,
                },
            },
        }),
        encoding="utf-8",
    )

    result = engine.list_source_files(registry_path=str(partial_reg))
    # valid.pdf 등 TSU에 있지만 registry에 유효한 source_file이 없으므로 빈 리스트
    assert result == []


def test_deduplication_across_tsu_records(tsu_path: Path, tmp_path: Path) -> None:
    """TSU에 중복 source_file이 있어도 중복 제거됨."""
    from core.retrieval import RetrievalEngine

    # 중복 source_file을 가진 TSU 생성
    dup_tsu = tmp_path / "dup.jsonl"
    lines = [
        json.dumps({"source_file": "valid.pdf", "content": "A"}, ensure_ascii=False),
        json.dumps({"source_file": "valid.pdf", "content": "B"}, ensure_ascii=False),
        json.dumps({"source_file": "valid.pdf", "content": "C"}, ensure_ascii=False),
    ]
    dup_tsu.write_text("\n".join(lines) + "\n", encoding="utf-8")

    reg = tmp_path / "reg.json"
    reg.write_text(
        json.dumps({
            "schema_version": "2.0",
            "documents": {
                "d1": {
                    "document_id": "d1",
                    "source_file": "valid.pdf",
                    "ingest_status": "PROCESSED",
                    "superseded_by": None,
                },
            },
        }),
        encoding="utf-8",
    )

    engine = RetrievalEngine(str(dup_tsu))
    result = engine.list_source_files(registry_path=str(reg))
    assert result == ["valid.pdf"]
    assert len(result) == 1


def test_default_values_point_to_config_constants(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """list_source_files()의 기본값이 core.config 상수와 일치함을 검증.

    TASK-053 반려 사유 재발 방지: list_source_files()를 인자 없이 호출했을 때
    DEFAULT_REGISTRY_PATH 상수를 실제로 쓰는지(mock으로 load_identity_registry가
    어떤 경로로 호출됐는지 확인) 검증한다.
    """
    import os

    from core.config import DEFAULT_REGISTRY_PATH, DEFAULT_TSU_DATASET_PATH
    from core.retrieval import RetrievalEngine

    # TSU 파일 생성
    tsu_file = tmp_path / "tsu.jsonl"
    tsu_file.write_text(
        json.dumps({"source_file": "doc.pdf", "content": "X"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # list_source_files()는 os.path.exists(registry_path)가 True일 때만
    # load_identity_registry를 부른다. DEFAULT_REGISTRY_PATH는 fresh
    # checkout / CI에는 없으므로, 이 테스트의 목적(기본 인자가 상수를
    # 가리키는지)만 검증하도록 그 경로가 존재하는 것처럼 만든다.
    _real_exists = os.path.exists
    monkeypatch.setattr(
        "os.path.exists",
        lambda p: True if p == DEFAULT_REGISTRY_PATH else _real_exists(p),
    )

    # load_identity_registry가 DEFAULT_REGISTRY_PATH로 호출되었는지 확인
    captured_path: list[str] = []

    def mock_load(path: str) -> dict:
        captured_path.append(path)
        return {"schema_version": "2.0", "documents": {}}

    monkeypatch.setattr("core.identity_registry.load_identity_registry", mock_load)

    # registry_path 기본값으로 호출 (인자 없이)
    engine = RetrievalEngine(str(tsu_file))
    _ = engine.list_source_files()

    # load_identity_registry가 DEFAULT_REGISTRY_PATH로 호출되었어야 함
    assert len(captured_path) == 1, f"Expected 1 call to load_identity_registry, got {len(captured_path)}"
    assert captured_path[0] == DEFAULT_REGISTRY_PATH, (
        f"load_identity_registry was called with '{captured_path[0]}' "
        f"but expected DEFAULT_REGISTRY_PATH='{DEFAULT_REGISTRY_PATH}'"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

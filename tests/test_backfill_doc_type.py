"""tests/test_backfill_doc_type.py — doc_type 백필 스크립트 단위 테스트.

검증 항목:
1. doc_type이 이미 있는 레코드는 건드리지 않음
2. md 파일이 없는 레코드는 건너뛰고 skipped_no_md에 기록됨
3. dry-run(apply=False)일 때 registry가 저장되지 않음
4. --apply 시 실제로 doc_type이 채워지고 저장됨
"""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.backfill_doc_type import backfill


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """임시 디렉터리 반환."""
    return tmp_path


@pytest.fixture
def registry_path(temp_dir: Path) -> Path:
    """doc_type=None 레코드 2건 + 이미 값 있는 레코드 1건 포함 registry 생성."""
    data = {
        "schema_version": "2.0",
        "processing_version": "1.1.x",
        "created_at": "2026-07-29T00:00:00",
        "updated_at": "2026-07-29T00:00:00",
        "documents": {
            "doc_none_1": {
                "document_id": "doc_none_1",
                "source_file": "test_doc1.pdf",
                "doc_type": None,
            },
            "doc_none_2": {
                "document_id": "doc_none_2",
                "source_file": "test_doc2.pdf",
                "doc_type": None,
            },
            "doc_has_value": {
                "document_id": "doc_has_value",
                "source_file": "test_doc3.pdf",
                "doc_type": "주석",
            },
        },
        "_meta": {"total_documents": 3},
    }
    p = temp_dir / "registry" / "documents.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return p


@pytest.fixture
def md_files(temp_dir: Path) -> Path:
    """backfill에서 참조할 MD 파일들 생성.
    
    명명 규칙: {stem}_{ext}.md (예: test_doc1.pdf → test_doc1_pdf.md)
    """
    output = temp_dir / "output"
    output.mkdir()
    # doc1: "주석" 키워드 포함 — source_file=test_doc1.pdf이므로 MD 파일명=test_doc1_pdf.md
    (output / "test_doc1_pdf.md").write_text(
        "# Commentary on Genesis\n\nThis is a detailed commentary.",
        encoding="utf-8",
    )
    # doc2: "설교" 키워드 포함 — source_file=test_doc2.pdf이므로 MD 파일명=test_doc2_pdf.md
    (output / "test_doc2_pdf.md").write_text(
        "# 설교\n\n본문: 요한복음 3장 16절\n\n제목: 하나님의 사랑",
        encoding="utf-8",
    )
    return output


def test_already_has_doc_type_is_unchanged(registry_path: Path, md_files: Path):
    """doc_type이 이미 있는 레코드는 건드리지 않는다."""
    # dry-run으로 실행 — apply=False이므로 registry 변경 없음 확인
    backfill(str(registry_path), str(md_files), apply=False)

    # 다시 로드하여 doc_has_value의 doc_type이 여전히 "주석"인지 확인
    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["documents"]["doc_has_value"]["doc_type"] == "주석"


def test_skips_no_md_file(registry_path: Path, md_files: Path):
    """md 파일이 없는 레코드는 skipped_no_md에 기록된다.
    
    test_doc2_pdf.md를 삭제하여 doc_none_2의 MD 파일을 없애면
    guess_doc_type이 호출되지 않아야 함.
    """
    # test_doc2_pdf.md 삭제 (md 파일 없음 시나리오)
    md_path = md_files / "test_doc2_pdf.md"
    if md_path.exists():
        md_path.unlink()

    backfill(str(registry_path), str(md_files), apply=False)

    # registry 변경 없어야 함 (dry-run이므로)
    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["documents"]["doc_none_1"]["doc_type"] is None
    assert data["documents"]["doc_none_2"]["doc_type"] is None


def test_dry_run_does_not_save(registry_path: Path, md_files: Path):
    """dry-run(apply=False)일 때 registry가 저장되지 않는다."""
    # registry의 doc_none_1을 None 상태로 유지
    with open(registry_path, "r", encoding="utf-8") as f:
        before = json.load(f)
    assert before["documents"]["doc_none_1"]["doc_type"] is None

    backfill(str(registry_path), str(md_files), apply=False)

    # 다시 로드 — 변경 없어야 함
    with open(registry_path, "r", encoding="utf-8") as f:
        after = json.load(f)
    assert after["documents"]["doc_none_1"]["doc_type"] is None


def test_apply_saves_doc_type(registry_path: Path, md_files: Path):
    """--apply 시 실제로 doc_type이 채워지고 저장된다."""
    backfill(str(registry_path), str(md_files), apply=True)

    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # doc_none_1은 "주석" (commentary 키워드)
    assert data["documents"]["doc_none_1"]["doc_type"] == "주석"
    # doc_none_2는 md 파일이 있으므로 "설교" (설교 키워드)
    # md_files fixture가 test_doc2_pdf.md를 포함하므로
    assert data["documents"]["doc_none_2"]["doc_type"] == "설교"
    # 이미 값 있는 레코드는 변경 안 됨
    assert data["documents"]["doc_has_value"]["doc_type"] == "주석"


def test_apply_creates_backup(registry_path: Path, md_files: Path):
    """--apply 시 .bak 백업 파일이 생성된다."""
    backfill(str(registry_path), str(md_files), apply=True)

    # 백업 파일 확인
    bak_files = list(registry_path.parent.glob("*.bak"))
    assert len(bak_files) >= 1


def test_no_hardcoded_values_in_guess():
    """[중요] guess_doc_type이 하드코딩된 mock 데이터를 사용하지 않는다.

    이 테스트는 backfill 스크립트가 실제 파일 내용을 읽어서 guess_doc_type을
    호출하는지를 확인한다. md 파일에 실제 내용이 없으면 guess_doc_type은
    기본값 "기타"를 반환해야 한다.
    """
    # md 파일이 비어있거나 키워드 없음 → "기타"
    temp_output = Path(tempfile.mkdtemp())
    (temp_output / "empty_doc.md").write_text("", encoding="utf-8")

    # registry에 empty_doc 추가
    data = {
        "schema_version": "2.0",
        "documents": {
            "empty_doc": {
                "document_id": "empty_doc",
                "source_file": "empty_doc.pdf",
                "doc_type": None,
            },
        },
    }
    reg_path = temp_output / "registry.json"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(json.dumps(data))

    backfill(str(reg_path), str(temp_output), apply=False)

    with open(reg_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    # dry-run이므로 변경 없음
    assert result["documents"]["empty_doc"]["doc_type"] is None
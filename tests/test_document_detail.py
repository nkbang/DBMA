"""tests/test_document_detail.py — Unit tests for core/document_detail.py.

7 test cases per C1-TASK-ORDER-029 §3:
  1. 정상 케이스: registry에 레코드 있고 md 파일도 있음
  2. 레지스트리 자체가 없는 경우
  3. 레지스트리엔 있는데 document_id/source_file로 못 찾는 경우
  4. 레코드는 있는데 md 파일이 없는 경우(이동/삭제 시뮬레이션)
  5. is_ocr=True이고 본문이 비정상적으로 짧은 경우
  6. query_terms가 본문에 존재
  7. query_terms가 본문에 없음
"""

import json
import os
import tempfile
import textwrap
from pathlib import Path

import pytest

from core.document_detail import (
    DocumentDetail,
    MatchLocation,
    get_document_detail,
)


# ── Fixtures ────────────────────────────────────────────────

def _make_registry(tmpdir: str, documents: dict | None = None) -> str:
    """임시 registry 파일을 만들고 경로를 반환."""
    reg_dir = os.path.join(tmpdir, "registry")
    os.makedirs(reg_dir, exist_ok=True)
    reg_path = os.path.join(reg_dir, "documents.json")
    data = documents or {"schema_version": "2.0", "documents": {}}
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return reg_path


def _make_text_file(tmpdir: str, source_file: str, content: str) -> str:
    """임시 본문 파일을 만들고 경로를 반환."""
    sf = source_file or ""
    stem = Path(sf).stem
    ext = Path(sf).suffix.lstrip(".") if Path(sf).suffix else "md"
    filename = f"{stem}_{ext}.md"
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ── Test 1: 정상 케이스 ─────────────────────────────────────

def test_01_normal_case():
    """정상 케이스: registry에 레코드 있고 md 파일도 있음 → error is None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "test_doc_pdf",
                    "title": "테스트 문서",
                    "author": "저자명",
                    "doc_type": "sermon",
                    "created_at": "2026-01-01T00:00:00",
                    "book": "시편",
                    "chapter": 23,
                    "page": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "test_doc_pdf", "다윗이 말하기를 여호와는 나의 목자시니 내가 부족함이 없으리로다")

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["목자"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error is None
        assert detail.document_id == "doc-001"
        assert detail.title == "테스트 문서"
        assert detail.author == "저자명"
        assert detail.document_type == "sermon"
        assert detail.created_at == "2026-01-01T00:00:00"
        assert "book:23" in detail.tags
        assert detail.full_text == "다윗이 말하기를 여호와는 나의 목자시니 내가 부족함이 없으리로다"
        assert len(detail.match_locations) == 1
        # "목자" is at index 17 in "다윗이 말하기를 여호와는 나의 목자시니 내가 부족함이 없으리로다"
        assert detail.match_locations[0].char_start == 17
        assert detail.match_locations[0].char_end == 19


# ── Test 2: 레지스트리 자체가 없는 경우 ─────────────────────

def test_02_registry_not_found():
    """레지스트리 자체가 없는 경우 → error 메시지, 예외 발생 안 함."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_reg = os.path.join(tmpdir, "nonexistent_registry.json")

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["테스트"],
            registry_path=fake_reg,
            output_dir=tmpdir,
        )

        assert detail.error == "레지스트리를 찾을 수 없습니다"
        assert detail.document_id == "doc-001"
        assert detail.title is None
        assert detail.full_text == ""


# ── Test 3: 레지스트리엔 있는데 document_id/source_file로 못 찾는 경우 ──

def test_03_record_not_found():
    """레지스트리엔 있는데 document_id/source_file로 못 찾는 경우 → error 메시지."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-999": {
                    "document_id": "doc-999",
                    "source_file": "other_doc_pdf",
                    "title": "다른 문서",
                    "author": None,
                    "doc_type": None,
                    "created_at": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "test_doc_pdf", "본문 내용")

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["테스트"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error == "문서 레코드를 찾을 수 없습니다"
        assert detail.document_id == "doc-001"


# ── Test 4: 레코드는 있는데 md 파일이 없는 경우 ─────────────

def test_04_file_not_found():
    """레코드는 있는데 md 파일이 없는 경우 → error 메시지, 메타데이터는 채워짐."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "test_doc_pdf",
                    "title": "테스트 문서",
                    "author": "저자명",
                    "doc_type": "sermon",
                    "created_at": "2026-01-01T00:00:00",
                    "is_ocr": False,
                }
            },
        })
        # md 파일을 만들지 않음 — 파일 없음 시뮬레이션

        detail = get_document_detail(
            source_file="test_doc_pdf",
            document_id="doc-001",
            query_terms=["테스트"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error == "원본 문서 파일을 찾을 수 없습니다 (이동 또는 삭제됨)"
        assert detail.title == "테스트 문서"
        assert detail.author == "저자명"
        assert detail.document_type == "sermon"
        assert detail.full_text == ""


# ── Test 5: is_ocr=True이고 본문이 비정상적으로 짧은 경우 ──

def test_05_ocr_failure():
    """is_ocr=True이고 본문이 50자 미만 → OCR 실패 판정."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-ocr-001": {
                    "document_id": "doc-ocr-001",
                    "source_file": "ocr_doc_pdf",
                    "title": "OCR 문서",
                    "author": None,
                    "doc_type": "pdf",
                    "created_at": None,
                    "is_ocr": True,
                }
            },
        })
        # 50자 미만 본문
        _make_text_file(tmpdir, "ocr_doc_pdf", "짧은 텍스트")

        detail = get_document_detail(
            source_file="ocr_doc_pdf",
            document_id="doc-ocr-001",
            query_terms=[],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error == "본문을 읽는 중 오류가 발생했습니다"


# ── Test 6: query_terms가 본문에 존재 ──────────────────────

def test_06_query_terms_found():
    """query_terms가 본문에 존재 → match_locations에 정확한 char_start/char_end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "match_test_pdf",
                    "title": None,
                    "author": None,
                    "doc_type": None,
                    "created_at": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "match_test_pdf", "첫 번째 문장. 두 번째 문장에 검색어가 들어갑니다.")

        detail = get_document_detail(
            source_file="match_test_pdf",
            document_id="doc-001",
            query_terms=["두 번째", "검색어"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error is None
        assert len(detail.match_locations) == 1
        # "두 번째"가 더 이른 위치 (idx=9)
        assert detail.match_locations[0].char_start == 9
        assert detail.match_locations[0].char_end == 13


# ── Test 7: query_terms가 본문에 없음 ─────────────────────

def test_07_query_terms_not_found():
    """query_terms가 본문에 없음 → match_locations 빈 리스트, error는 None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = _make_registry(tmpdir, documents={
            "schema_version": "2.0",
            "documents": {
                "doc-001": {
                    "document_id": "doc-001",
                    "source_file": "nomatch_pdf",
                    "title": None,
                    "author": None,
                    "doc_type": None,
                    "created_at": None,
                    "is_ocr": False,
                }
            },
        })
        _make_text_file(tmpdir, "nomatch_pdf", "이 문서에는 검색어가 없습니다.")

        detail = get_document_detail(
            source_file="nomatch_pdf",
            document_id="doc-001",
            query_terms=["존재하지않는단어"],
            registry_path=reg_path,
            output_dir=tmpdir,
        )

        assert detail.error is None
        assert detail.match_locations == []


# ── Test 8: find_by_document_id / find_by_source_file 재구현 확인 ──

def test_08_no_reimplementation():
    """grep으로 find_by_document_id / find_by_source_file / load_identity_registry가
    import해서 썼는지 확인 (재구현 금지)."""
    source_path = Path(__file__).parent.parent / "core" / "document_detail.py"
    source_text = source_path.read_text(encoding="utf-8")

    # import 문에 반드시 포함되어야 함
    assert "from core.identity_registry import" in source_text
    assert "find_by_document_id" in source_text
    assert "find_by_source_file" in source_text
    assert "load_identity_registry" in source_text

    # 재구현 금지: def find_by_document_id:, def find_by_source_file:, def load_identity_registry: 가
    # 이 파일 내에 함수 정의 형태로 있으면 안 됨 (import는 허용)
    import re
    func_defs = re.findall(r'^def (find_by_document_id|find_by_source_file|load_identity_registry)\(', source_text, re.MULTILINE)
    assert func_defs == [], f"재구현 감지: {func_defs}"
"""tests/test_sidecar_metadata.py — 사이드카 메타데이터 회귀
(DBMA_SIDECAR_METADATA_DESIGN_FINAL_v2.md 구현, C1 Review 3라운드 종결·
HQ 승인 후).

- D-3 "신뢰 불가" 판정: 블랙리스트 + 휴리스틱(C1 RQ-2 권고안)
- D-1/D-2 사이드카 로더: `<path>.meta.json`, fail-closed
- resolve_title_author(): 내장 우선, 신뢰 불가/None일 때만 사이드카
- metadata_source가 registry → TSU record까지 additive로 전파되는지
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.processing import (
    _is_untrustworthy_embedded_value,
    _load_sidecar_metadata,
    resolve_title_author,
)
from core.document_context import DocumentContext
from core.document_identity import build_document_metadata
from core.identity_registry import register_document, load_identity_registry


class TestIsUntrustworthyEmbeddedValue:
    def test_blacklist_untitled_variants(self):
        for v in ["Untitled", "untitled", "UNTITLED", "untitled-1", "untitled-2"]:
            assert _is_untrustworthy_embedded_value(v), v

    def test_blacklist_tool_names(self):
        for v in ["LuraDocument", "Adobe Acrobat", "Microsoft Word", "LibreOffice", "Google Docs"]:
            assert _is_untrustworthy_embedded_value(v), v

    def test_filename_pattern(self):
        assert _is_untrustworthy_embedded_value("Microsoft Word - doc1.doc")
        assert _is_untrustworthy_embedded_value("report.pdf")

    def test_heuristic_short_ascii_titlecase_is_untrustworthy(self):
        # 길이<=5 + 영문만 + Title Case 자동생성 패턴 = 3점
        assert _is_untrustworthy_embedded_value("Draft")

    def test_normal_korean_title_is_trustworthy(self):
        assert not _is_untrustworthy_embedded_value("로마서 강해 — 은혜와 진리")

    def test_normal_long_english_title_is_trustworthy(self):
        assert not _is_untrustworthy_embedded_value("The Metropolitan Tabernacle Pulpit")

    def test_none_and_empty_are_not_untrustworthy(self):
        # 빈 문자열/None은 추출기 단계에서 이미 걸러짐 — 이 함수 책임 밖
        assert not _is_untrustworthy_embedded_value(None)
        assert not _is_untrustworthy_embedded_value("")


class TestLoadSidecarMetadata:
    def test_missing_sidecar_returns_empty_dict(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        assert _load_sidecar_metadata(str(src)) == {}

    def test_valid_sidecar_loaded(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        meta = tmp_path / "doc.txt.meta.json"
        meta.write_text(
            json.dumps({"title": "실제 제목", "author": "실제 저자",
                        "source": "archive.org|original.pdf|docinfo"}),
            encoding="utf-8",
        )
        result = _load_sidecar_metadata(str(src))
        assert result == {"title": "실제 제목", "author": "실제 저자"}
        # source 키는 반환값에 없다 — 사이드카 내부에만 머문다(RQ-1 확정)
        assert "source" not in result

    def test_malformed_json_fails_closed(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        meta = tmp_path / "doc.txt.meta.json"
        meta.write_text("{not valid json", encoding="utf-8")
        assert _load_sidecar_metadata(str(src)) == {}

    def test_non_object_json_fails_closed(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        meta = tmp_path / "doc.txt.meta.json"
        meta.write_text("[1, 2, 3]", encoding="utf-8")
        assert _load_sidecar_metadata(str(src)) == {}

    def test_blank_sidecar_values_treated_as_absent(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        meta = tmp_path / "doc.txt.meta.json"
        meta.write_text(json.dumps({"title": "  ", "author": None}), encoding="utf-8")
        result = _load_sidecar_metadata(str(src))
        assert result == {"title": None, "author": None}


class TestResolveTitleAuthor:
    def _sidecar(self, tmp_path, title=None, author=None):
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        payload = {}
        if title is not None:
            payload["title"] = title
        if author is not None:
            payload["author"] = author
        (tmp_path / "doc.txt.meta.json").write_text(json.dumps(payload), encoding="utf-8")
        return str(src)

    def test_no_sidecar_no_embedded_returns_none_source(self, tmp_path):
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        title, author, source = resolve_title_author(None, None, str(src))
        assert (title, author, source) == (None, None, None)

    def test_good_embedded_kept_as_is(self, tmp_path):
        src = self._sidecar(tmp_path, title="사이드카 제목")
        title, author, source = resolve_title_author("로마서 강해", "김목사", src)
        assert title == "로마서 강해"  # 내장 우선, 사이드카로 안 바뀜
        assert author == "김목사"
        assert source == "embedded"

    def test_untitled_embedded_replaced_by_sidecar(self, tmp_path):
        src = self._sidecar(tmp_path, title="실제 제목", author="실제 저자")
        title, author, source = resolve_title_author("Untitled", None, src)
        assert title == "실제 제목"
        assert author == "실제 저자"
        assert source == "sidecar"

    def test_untitled_embedded_no_sidecar_stays_untitled(self, tmp_path):
        """사이드카가 아예 없으면 쓰레기 값이라도 그대로 둔다 — 조용히
        지어내지 않는다."""
        src = tmp_path / "doc.txt"
        src.write_text("본문", encoding="utf-8")
        title, author, source = resolve_title_author("Untitled", None, src)
        assert title == "Untitled"
        assert source == "embedded"  # 대체된 게 없으므로 "내장 그대로"

    def test_title_and_author_judged_independently(self, tmp_path):
        """title은 정상(내장 유지), author만 쓰레기(사이드카로 대체)."""
        src = self._sidecar(tmp_path, author="정확한 저자명")
        title, author, source = resolve_title_author("정상적인 제목입니다", "LuraDocument", src)
        assert title == "정상적인 제목입니다"
        assert author == "정확한 저자명"
        assert source == "sidecar"  # 하나라도 사이드카를 썼으면 sidecar


class TestMetadataSourcePropagation:
    """registry → TSU record까지 additive로 전파되는지 확인 —
    기존 스키마를 깨지 않는지가 핵심(3라운드 C1 Review의 논점)."""

    def test_build_document_metadata_includes_metadata_source(self):
        meta = build_document_metadata(
            content="본문", source_file="x.txt", title="제목", author="저자",
            metadata_source="sidecar",
        )
        assert meta["metadata_source"] == "sidecar"

    def test_build_document_metadata_defaults_to_none(self):
        meta = build_document_metadata(content="본문", source_file="x.txt")
        assert meta["metadata_source"] is None

    def test_register_document_persists_metadata_source(self):
        registry = load_identity_registry("/nonexistent/registry.json")
        meta = build_document_metadata(
            content="고유한 본문 내용 12345", source_file="x.txt",
            title="제목", author="저자", metadata_source="sidecar",
        )
        record, is_new = register_document(registry, meta, output_dir="")
        assert is_new is True
        assert record["metadata_source"] == "sidecar"

    def test_register_document_other_fields_unaffected(self):
        """additive 필드 추가가 기존 필드 구성을 깨지 않는지 — book/chapter/
        page와 동일한 패턴으로 자리 잡았는지 확인."""
        registry = load_identity_registry("/nonexistent/registry.json")
        meta = build_document_metadata(content="본문2", source_file="y.txt")
        record, _ = register_document(registry, meta, output_dir="")
        for key in ("book", "chapter", "page", "title", "author", "doc_type", "metadata_source"):
            assert key in record

    def test_document_context_to_metadata_dict_is_the_real_production_path(self):
        """[회귀 — 라이브 E2E에서 실제로 잡힌 버그] core/processing.py::
        process_one_file()의 실제 registry 기록 경로는 build_document_metadata()
        가 아니라 DocumentContext.to_metadata_dict()다(~933행,
        "DocumentContext is now the metadata source for register_document()").
        DocumentContext에 metadata_source 필드를 안 채웠을 때 이 테스트가
        실패해야 한다 — 처음 구현 시 이 경로를 놓쳐 registry에 조용히
        None이 기록되는 결함이 있었다(라이브 확인으로 발견, 즉시 수정)."""
        ctx = DocumentContext(
            document_id="doc-e2e-test",
            file_hash="hash-e2e-test",
            source_file="e2e.txt",
            source_type="txt",
            title="테스트 문서 실제 제목",
            author="홍길동",
            metadata_source="sidecar",
        )
        ctx.registered_at = "2026-09-17T00:00:00"

        meta_dict = ctx.to_metadata_dict()
        assert meta_dict["metadata_source"] == "sidecar"

        registry = load_identity_registry("/nonexistent/registry.json")
        record, is_new = register_document(registry, meta_dict, output_dir="")
        assert is_new is True
        assert record["title"] == "테스트 문서 실제 제목"
        assert record["author"] == "홍길동"
        assert record["metadata_source"] == "sidecar"

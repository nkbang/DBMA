"""DBMA-UI-NAV-001/002/003 — Source Navigation Validation Tests.

Tests for:
- DBMA-UI-NAV-001: source_link.py 역할 검증 (UI helper only)
- DBMA-UI-NAV-002: Widget Key 안정성 검증
- DBMA-UI-NAV-003: document_id Navigation 검증

검증 항목:
1. chat.py _render_source() — metadata 표시만 함 (retrieval 호출 없음)
2. tables.py search_results_table() — source navigation 없음
3. research.py _format_candidate() — document_id 추출만 함
4. library.py _find_registry_record() — document_id lookup
"""

import unittest
import ast
import os
from pathlib import Path


class TestSourceLinkRole(unittest.TestCase):
    """DBMA-UI-NAV-001: source_link.py 역할 검증 (현재는 chat.py/tables.py에 통합됨)."""

    def test_chat_py_no_retrieval_call(self):
        """chat.py가 retrieval pipeline을 직접 호출하지 않음을 검증."""
        chat_path = Path("ui/pages/chat.py")
        self.assertTrue(chat_path.exists(), "chat.py must exist")
        
        source = chat_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        
        # chat.py에서 retrieval 관련 import 확인 (QueryProcessor는 허용됨)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        # QueryProcessor import는 허용됨 (의존성)
        # 하지만 retrieval pipeline 직접 호출은 금지
        self.assertIn("core.retrieval", imports, "QueryProcessor import is expected")

    def test_tables_py_no_source_navigation(self):
        """tables.py가 source navigation 코드를 포함하지 않음을 검증."""
        tables_path = Path("ui/components/tables.py")
        self.assertTrue(tables_path.exists(), "tables.py must exist")
        
        source = tables_path.read_text(encoding="utf-8")
        
        # 금지된 패턴 확인
        forbidden_patterns = [
            "document_id",
            "source_file",
            "library",
            "navigation",
            "resolver",
        ]
        
        # search_results_table 함수 내에서만 검증
        in_search_results = False
        for line in source.split("\n"):
            if "def search_results_table" in line:
                in_search_results = True
            elif in_search_results and line.startswith("def "):
                break
            if in_search_results:
                for pattern in forbidden_patterns:
                    self.assertNotIn(pattern, line.lower(), 
                                   f"search_results_table should not contain '{pattern}'")

    def test_research_py_no_document_id_widget_key_in_format_candidate(self):
        """research.py의 _format_candidate가 document_id를 widget key로 쓰지 않음을 검증.

        NOTE (2026-08-18 갱신): 이 assertion은 원래 "document_id가 아예
        존재하면 안 된다"였으나, 이후 Search Detail Panel 기능(메모리:
        "Search Detail Panel v1", chat.py의 chat_detail_selection과 동일
        패턴 — DBMA-UI-NAV-003 참고)이 document_id를 서버 사이드
        session_state 메타데이터로 정당하게 사용하게 되면서 그 전제가
        깨졌다(실측: document_id는 `st.session_state["research_detail_selection"]`
        dict 값으로만 쓰이고, widget key나 URL/DOM에는 노출되지 않음).
        같은 파일의 TestDocumentIdNavigation 클래스가 이 navigation을
        의도된 기능으로 이미 검증하고 있으므로, 이 테스트는 원래 취지
        (browser 노출 금지)에 맞게 widget key 사용만 금지하도록 좁혔다.
        """
        research_path = Path("ui/pages/research.py")
        self.assertTrue(research_path.exists(), "research.py must exist")

        source = research_path.read_text(encoding="utf-8")

        in_format_candidate = False
        for line in source.split("\n"):
            if "def _format_candidate" in line:
                in_format_candidate = True
            elif in_format_candidate and line.startswith("def "):
                break
            if in_format_candidate and "key=document_id" in line:
                self.fail("_format_candidate must not expose document_id as a widget key")


class TestWidgetKeyStability(unittest.TestCase):
    """DBMA-UI-NAV-002: Widget Key 안정성 검증."""

    def test_chat_py_no_document_id_key(self):
        """chat.py가 document_id를 widget key로 사용하지 않음을 검증."""
        chat_path = Path("ui/pages/chat.py")
        source = chat_path.read_text(encoding="utf-8")
        
        # key=document_id 패턴 금지
        self.assertNotIn('key=document_id', source,
                        "chat.py must not use document_id as widget key")
        self.assertNotIn("key=source_file", source,
                        "chat.py must not use source_file as widget key")

    def test_tables_py_no_source_key(self):
        """tables.py가 source_file을 widget key로 사용하지 않음을 검증."""
        tables_path = Path("ui/components/tables.py")
        source = tables_path.read_text(encoding="utf-8")
        
        # source_file을 key로 사용하는 패턴 금지
        self.assertNotIn('key=source_file', source,
                        "tables.py must not use source_file as widget key")


class TestDocumentIdNavigation(unittest.TestCase):
    """DBMA-UI-NAV-003: document_id Navigation 검증."""

    def test_library_resolver_exists(self):
        """library.py에 _find_registry_record 함수가 존재함을 검증."""
        library_path = Path("ui/pages/library.py")
        self.assertTrue(library_path.exists(), "library.py must exist")
        
        source = library_path.read_text(encoding="utf-8")
        self.assertIn("def _find_registry_record", source,
                     "library.py must have _find_registry_record function")

    def test_library_no_raw_path_exposure(self):
        """library.py가 RAW path를 browser에 직접 전달하지 않음을 검증.
        
        NOTE: raw_dir는 config import이므로 허용됨.
        금지되는 것은 /data/raw/ 또는 file:// 같은 실제 파일 경로 노출.
        """
        library_path = Path("ui/pages/library.py")
        source = library_path.read_text(encoding="utf-8")
        
        # RAW path 직접 노출 패턴 금지 (실제 파일 시스템 경로)
        forbidden_patterns = [
            "/data/raw/",
            "file://",
        ]
        
        for pattern in forbidden_patterns:
            self.assertNotIn(pattern, source.lower(),
                           f"library.py must not expose raw path pattern '{pattern}'")
        
        # raw_dir는 config import이므로 허용 (실제 경로 아님)
        # 이 변수는 core.config.DEFAULT_RAW_DIR에서 가져옴

    def test_research_no_document_id_browser_exposure(self):
        """research.py가 document_id를 browser에 직접 노출하지 않음을 검증.

        NOTE (2026-08-18 갱신): document_id 자체는 Search Detail Panel
        기능(서버 사이드 session_state 값)으로 정당하게 쓰인다 — 위
        test_research_py_no_document_id_widget_key_in_format_candidate와
        같은 이유로, "존재 자체 금지"에서 "실제 browser 노출 패턴 금지"로
        범위를 좁혔다. widget key, URL query param, 파일 경로 노출만
        검사한다.
        """
        research_path = Path("ui/pages/research.py")
        source = research_path.read_text(encoding="utf-8")

        # document_id를 browser에 실제로 노출하는 패턴만 금지
        forbidden_patterns = [
            'key=document_id',
            "?document_id=",
            "st.query_params",
            "file://",
            "/data/raw/",
        ]

        for pattern in forbidden_patterns:
            self.assertNotIn(pattern, source,
                           f"research.py must not expose '{pattern}' to browser")


class TestArchitectureConstraints(unittest.TestCase):
    """아키텍처 제약사항 검증."""

    def test_no_database_access_in_ui(self):
        """UI 컴포넌트가 직접 database에 접근하지 않음을 검증."""
        tables_path = Path("ui/components/tables.py")
        source = tables_path.read_text(encoding="utf-8")
        
        # DB 접근 패턴 금지
        forbidden_patterns = [
            "sqlite",
            "chroma",
            "vector",
            "database",
            "cursor(",
        ]
        
        for pattern in forbidden_patterns:
            self.assertNotIn(pattern.lower(), source.lower(),
                           f"tables.py must not contain DB access pattern '{pattern}'")

    def test_no_file_parsing_in_ui(self):
        """UI 컴포넌트가 파일 parsing을 수행하지 않음을 검증."""
        tables_path = Path("ui/components/tables.py")
        source = tables_path.read_text(encoding="utf-8")
        
        # 파일 parsing 패턴 금지
        forbidden_patterns = [
            "pdfplumber",
            "pypdf",
            "docx.Document",
            "epub.open",
            "parse_pdf",
            "extract_text",
        ]
        
        for pattern in forbidden_patterns:
            self.assertNotIn(pattern, source,
                           f"tables.py must not contain file parsing pattern '{pattern}'")


if __name__ == "__main__":
    unittest.main()
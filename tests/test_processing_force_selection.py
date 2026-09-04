"""Regression test — ui/pages/processing.py::_filter_selected_files()
(2026-07-21, 강제 재처리 문서 선택 기능).

이전에는 "강제 재처리"/"전체 재청킹" 체크박스를 켜면 target_dir 전체가
일괄 재처리 대상이 되어, 특정 문서만 다시 처리하고 싶어도 선택할 수
없었다(사용자 보고). _filter_selected_files()는 _build_file_list()가
만든 전체 후보 목록을 사용자가 고른 파일명 집합으로 좁히는 순수 함수 —
Streamlit 세션 상태나 I/O에 의존하지 않는다.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.pages.processing import _filter_selected_files


def _files(*names):
    return [{"path": f"/raw/{n}", "name": n, "ext": "pdf", "use_ocr": False} for n in names]


def test_selected_subset_filters_down():
    file_list = _files("a.pdf", "b.pdf", "c.pdf")
    result = _filter_selected_files(file_list, selected_names=["b.pdf"])
    assert [f["name"] for f in result] == ["b.pdf"]


def test_none_selected_names_returns_full_list_unfiltered():
    file_list = _files("a.pdf", "b.pdf")
    result = _filter_selected_files(file_list, selected_names=None)
    assert result == file_list


def test_empty_selection_returns_empty_list_not_full_list():
    file_list = _files("a.pdf", "b.pdf")
    result = _filter_selected_files(file_list, selected_names=[])
    assert result == []


def test_selection_order_follows_original_file_list_not_selection_order():
    file_list = _files("a.pdf", "b.pdf", "c.pdf")
    result = _filter_selected_files(file_list, selected_names=["c.pdf", "a.pdf"])
    assert [f["name"] for f in result] == ["a.pdf", "c.pdf"]


def test_unknown_selected_name_is_ignored():
    file_list = _files("a.pdf", "b.pdf")
    result = _filter_selected_files(file_list, selected_names=["a.pdf", "ghost.pdf"])
    assert [f["name"] for f in result] == ["a.pdf"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

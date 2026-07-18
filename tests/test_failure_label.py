"""Regression test — ui/pages/processing.py::_failure_label() (SPRINT25-B-2).
Verifies exception-stage failures are refined by error_type, unmapped
types are shown verbatim, and legacy records (no error_type) fall back to
the generic stage label without regression.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.pages.processing import _failure_label


def test_extract_stage_uses_stage_label():
    assert _failure_label({"stage": "extract"}) == "추출 실패"


def test_noise_stage_uses_stage_label():
    assert _failure_label({"stage": "noise"}) == "정제 후 텍스트 없음"


def test_exception_with_known_error_type_refined():
    assert _failure_label({"stage": "exception", "error_type": "FileNotFoundError"}) == "파일 없음"
    assert _failure_label({"stage": "exception", "error_type": "PackageNotFoundError"}) == "손상된 DOCX"
    assert _failure_label({"stage": "exception", "error_type": "EpubException"}) == "손상된 EPUB"
    assert _failure_label({"stage": "exception", "error_type": "ValueError"}) == "형식/추출 오류"


def test_exception_with_unmapped_error_type_shown_verbatim():
    # A new/unknown class surfaces its raw name, never a wrong label.
    assert _failure_label({"stage": "exception", "error_type": "TimeoutError"}) == "TimeoutError"


def test_legacy_exception_without_error_type_falls_back():
    # Pre-SPRINT25-B-1 record: no error_type key → generic label, no crash.
    assert _failure_label({"stage": "exception"}) == "예외 발생"
    assert _failure_label({"stage": "exception", "error_type": None}) == "예외 발생"


def test_unknown_stage_shown_verbatim():
    assert _failure_label({"stage": "weird"}) == "weird"
    assert _failure_label({}) == "?"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

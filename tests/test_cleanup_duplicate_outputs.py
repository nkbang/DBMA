"""Regression test — scripts/cleanup_duplicate_outputs.py::
_pick_duplicate_keep_and_remove() (2026-07-21).

버그 재현: "7. 사도행전1 복사본.pdf"와 "7. 사도행전1.pdf"가 둘 다
.batch_state.json에 processed로 기록된 실제 상황(각각 별도로
업로드·처리됐으므로)에서, 원래 로직은 사전순 폴백으로 떨어져
공백(0x20) < 마침표(0x2E) 때문에 "복사본"을 KEEP으로 잘못 골랐다.
수정된 로직은 "복사본"/"copy" 등 사본 표식이 없는 파일명을 우선한다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.cleanup_duplicate_outputs import _pick_duplicate_keep_and_remove


def test_prefers_name_without_copy_marker_over_alphabetical_order():
    pdfs = [
        Path("7. 사도행전1 복사본.pdf"),
        Path("7. 사도행전1.pdf"),
    ]
    keep, remove = _pick_duplicate_keep_and_remove(pdfs)
    assert keep.name == "7. 사도행전1.pdf"
    assert [p.name for p in remove] == ["7. 사도행전1 복사본.pdf"]


def test_english_copy_marker_also_deprioritized():
    pdfs = [Path("report copy.pdf"), Path("report.pdf")]
    keep, remove = _pick_duplicate_keep_and_remove(pdfs)
    assert keep.name == "report.pdf"


def test_both_have_marker_falls_back_to_shorter_name():
    pdfs = [Path("a 복사본 복사본.pdf"), Path("a 복사본.pdf")]
    keep, remove = _pick_duplicate_keep_and_remove(pdfs)
    assert keep.name == "a 복사본.pdf"


def test_neither_has_marker_falls_back_to_alphabetical():
    pdfs = [Path("b.pdf"), Path("a.pdf")]
    keep, remove = _pick_duplicate_keep_and_remove(pdfs)
    assert keep.name == "a.pdf"


def test_result_is_deterministic_regardless_of_input_order():
    pdfs_a = [Path("x 복사본.pdf"), Path("x.pdf")]
    pdfs_b = [Path("x.pdf"), Path("x 복사본.pdf")]
    keep_a, _ = _pick_duplicate_keep_and_remove(pdfs_a)
    keep_b, _ = _pick_duplicate_keep_and_remove(pdfs_b)
    assert keep_a.name == keep_b.name == "x.pdf"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

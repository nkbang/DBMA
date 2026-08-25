"""Regression test — core/raw_hygiene.py::find_exact_duplicate_raw_files()
(2026-08-24, 사용자 요청: "원본 폴더에 동일한 내용 듀플리케이트 파일은
하나로 정리해야 한다. 워닝하고 삭제하도록 하라").

바이트 단위 완전 일치만 탐지한다 — 유사도 기반 탐지는 오탐 위험 때문에
의도적으로 범위 밖(core/raw_hygiene.py 모듈 docstring 참고).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.raw_hygiene import find_exact_duplicate_raw_files


class TestFindExactDuplicateRawFiles:
    def test_no_raw_dir_returns_empty(self, tmp_path):
        assert find_exact_duplicate_raw_files(str(tmp_path / "does_not_exist")) == []

    def test_no_duplicates_returns_empty(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"content-a")
        (tmp_path / "b.pdf").write_bytes(b"content-b")
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_identical_content_flagged_as_duplicate_group(self, tmp_path):
        (tmp_path / "7. 사도행전1.pdf").write_bytes(b"same bytes")
        (tmp_path / "7. 사도행전1 복사본.pdf").write_bytes(b"same bytes")
        (tmp_path / "unrelated.pdf").write_bytes(b"different")

        groups = find_exact_duplicate_raw_files(str(tmp_path))
        assert len(groups) == 1
        names = {f["name"] for f in groups[0]["files"]}
        assert names == {"7. 사도행전1.pdf", "7. 사도행전1 복사본.pdf"}

    def test_different_content_same_size_not_flagged(self, tmp_path):
        """바이트가 다르면 크기가 같아도 중복이 아니다 — 순수 해시 비교."""
        (tmp_path / "a.pdf").write_bytes(b"aaaaaaaaaa")
        (tmp_path / "b.pdf").write_bytes(b"bbbbbbbbbb")
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_near_duplicate_scans_not_flagged(self, tmp_path):
        """[의도된 범위 제한] 재스캔본처럼 내용은 거의 같아도 바이트가
        다르면(한 글자만 달라도) 탐지하지 않는다 — 오탐 방지."""
        (tmp_path / "5. 요한복음1.pdf").write_bytes(b"x" * 1000 + b"A")
        (tmp_path / "5. 요한복음1clearscan_cropped.pdf").write_bytes(b"x" * 1000 + b"B")
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_finds_duplicates_in_subfolder(self, tmp_path):
        """[동일 근본원인] processing.py의 하위 폴더 스캔 수정과 같은 기준
        — 중복 탐지도 RAW 최상위만 봐서는 안 된다."""
        sub = tmp_path / "설교_분리"
        sub.mkdir()
        (tmp_path / "top.md").write_bytes(b"sermon content")
        (sub / "copy.md").write_bytes(b"sermon content")

        groups = find_exact_duplicate_raw_files(str(tmp_path))
        assert len(groups) == 1
        names = {f["name"] for f in groups[0]["files"]}
        assert names == {"top.md", "copy.md"}

    def test_unsupported_extension_ignored(self, tmp_path):
        (tmp_path / "a.pdf").write_bytes(b"same")
        (tmp_path / "b.exe").write_bytes(b"same")  # not a supported document extension
        assert find_exact_duplicate_raw_files(str(tmp_path)) == []

    def test_group_of_three_returns_all_three(self, tmp_path):
        for name in ["a.pdf", "b.pdf", "c.pdf"]:
            (tmp_path / name).write_bytes(b"triple")
        groups = find_exact_duplicate_raw_files(str(tmp_path))
        assert len(groups) == 1
        assert len(groups[0]["files"]) == 3


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

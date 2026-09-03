"""NAE Benchmark Config Tests — THEOLOGY_AREA_CATEGORIES 검증."""

import pytest


class TestTHEOLOGY_AREA_CATEGORIES:
    def test_import_from_config(self):
        """config.py에서 THEOLOGY_AREA_CATEGORIES를 import할 수 있어야 함."""
        from NAE.benchmark.config import THEOLOGY_AREA_CATEGORIES
        assert THEOLOGY_AREA_CATEGORIES is not None

    def test_is_same_object_as_DOCTRINE_CATEGORIES(self):
        """THEOLOGY_AREA_CATEGORIES가 DOCTRINE_CATEGORIES와 동일 객체여야 함 (값 복사 아님)."""
        from NAE.benchmark.config import THEOLOGY_AREA_CATEGORIES
        from NAE.pipeline.tsu.config import DOCTRINE_CATEGORIES
        # 동일 객체 참조 확인 (id 비교)
        assert id(THEOLOGY_AREA_CATEGORIES) == id(DOCTRINE_CATEGORIES)

    def test_has_expected_values(self):
        """DOCTRINE_CATEGORIES에预期的인 값들이 포함되어야 함."""
        from NAE.benchmark.config import THEOLOGY_AREA_CATEGORIES
        expected = [
            "Baptism",
            "Soteriology",
            "Trinity",
            "Justification",
            "Sanctification",
        ]
        for val in expected:
            assert val in THEOLOGY_AREA_CATEGORIES, f"{val} not in THEOLOGY_AREA_CATEGORIES"

    def test_is_not_empty(self):
        """THEOLOGY_AREA_CATEGORIES가 비어있지 않아야 함."""
        from NAE.benchmark.config import THEOLOGY_AREA_CATEGORIES
        assert len(THEOLOGY_AREA_CATEGORIES) > 0

    def test_all_strings(self):
        """모든 값이 문자열이어야 함."""
        from NAE.benchmark.config import THEOLOGY_AREA_CATEGORIES
        for item in THEOLOGY_AREA_CATEGORIES:
            assert isinstance(item, str)

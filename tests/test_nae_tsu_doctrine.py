from NAE.pipeline.tsu import doctrine


def test_normalize_doctrine_exact_match():
    assert doctrine.normalize_doctrine("Baptism") == "Baptism"


def test_normalize_doctrine_case_insensitive():
    assert doctrine.normalize_doctrine("baptism") == "Baptism"


def test_normalize_doctrine_unknown_value_coerced_to_other():
    assert doctrine.normalize_doctrine("Some LLM-invented category") == "Other"


def test_normalize_doctrine_none_variants_return_none():
    assert doctrine.normalize_doctrine(None) is None
    assert doctrine.normalize_doctrine("") is None
    assert doctrine.normalize_doctrine("none") is None
    assert doctrine.normalize_doctrine("null") is None

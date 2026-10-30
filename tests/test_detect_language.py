import pytest

from core.processing import detect_language


@pytest.mark.parametrize("text,expected", [
    ("", "en"),
    ("   \n", "en"),
    ("태초에 하나님이 천지를 창조하시니라", "ko"),
    ("בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם", "he"),
    ("ἐν ἀρχῇ ἦν ὁ λόγος καὶ ὁ λόγος ἦν πρὸς τὸν θεόν", "el"),
    ("In the beginning was the Word", "en"),
    ("はじめに神は天と地を創造された", "ja"),
    ("起初神创造天地", "zh"),
])
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_hangul_threshold_mixed_text():
    # 한글 비율 10% 초과 시 ko, 미만이면 en
    assert detect_language("가나다 " + "abcdefghij" * 2) == "ko"
    assert detect_language("가 " + "abcdefghij" * 20) == "en"

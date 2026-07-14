# tests/test_text_normalizer_mixed.py
"""
text_normalizer.py Mixed Language Processing 테스트
대상: detect_paragraph_language, script detection
"""

import pytest
from core.text_normalizer import (
    detect_paragraph_language,
    split_sentences_mixed,
    ParagraphLanguage
)


class TestScriptDetection:
    
    def test_korean_only(self):
        """한국어만 포함된 문단 테스트"""
        text = "이 문서는 한국어로 작성되었습니다. 매우 좋은 문서입니다."
        result = detect_paragraph_language(text)
        assert result.label in ["ko", "mixed"]
        assert result.script_ratios.get("hangul", 0.0) > 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_english_only(self):
        """영어만 포함된 문단 테스트"""
        text = "This document is written in English. It is a good document."
        result = detect_paragraph_language(text)
        assert result.label in ["en", "mixed"]
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) > 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_korean_hebrew(self):
        """한국어 + 히브리어 혼합 테스트"""
        text = "이 문서에는 히브리어가 포함되어 있습니다. ברכה שלום."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"
        assert result.script_ratios.get("hangul", 0.0) > 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) > 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_korean_greek(self):
        """한국어 + 그리스어 혼합 테스트"""
        text = "이 문서에는 그리스어가 포함되어 있습니다. Καλημέρα κόσμε."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"
        assert result.script_ratios.get("hangul", 0.0) > 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) > 0.0
    
    def test_english_hebrew(self):
        """영어 + 히브리어 혼합 테스트"""
        text = "This document contains Hebrew. ברכה שלום."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) > 0.0
        assert result.script_ratios.get("hebrew", 0.0) > 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_english_greek(self):
        """영어 + 그리스어 혼합 테스트"""
        text = "This document contains Greek. Καλημέρα κόσμε."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) > 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) > 0.0
    
    def test_hebrew_only(self):
        """히브리어만 포함된 문단 테스트"""
        text = "ברכה שלום. ברכה שלום."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"  # Hebrew is treated as mixed
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) > 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_greek_only(self):
        """그리스어만 포함된 문단 테스트"""
        text = "Καλημέρα κόσμε. Καλημέρα κόσμε."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"  # Greek is treated as mixed
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) > 0.0
    
    def test_latin_only(self):
        """라틴어만 포함된 문단 테스트 (라틴어는 언어 감지 대상 아님)"""
        text = "Hello world. This is a test."
        result = detect_paragraph_language(text)
        assert result.label in ["en", "mixed"]
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) > 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_empty_string(self):
        """빈 문자열 테스트"""
        text = ""
        result = detect_paragraph_language(text)
        assert result.label == "other"
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_numbers_only(self):
        """숫자만 포함된 문단 테스트"""
        text = "123456789"
        result = detect_paragraph_language(text)
        assert result.label == "other"
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_punctuation_only(self):
        """구두점만 포함된 문단 테스트"""
        text = "!!!???..."
        result = detect_paragraph_language(text)
        assert result.label == "other"
        assert result.script_ratios.get("hangul", 0.0) == 0.0
        assert result.script_ratios.get("latin", 0.0) == 0.0
        assert result.script_ratios.get("hebrew", 0.0) == 0.0
        assert result.script_ratios.get("greek", 0.0) == 0.0
    
    def test_mixed_3_languages(self):
        """세 가지 언어 혼합 테스트"""
        text = "Hello world. 이 문서는 한국어입니다. ברכה שלום. Καλημέρα κόσμε."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"
        assert result.script_ratios.get("hangul", 0.0) > 0.0
        assert result.script_ratios.get("latin", 0.0) > 0.0
        assert result.script_ratios.get("hebrew", 0.0) > 0.0
        assert result.script_ratios.get("greek", 0.0) > 0.0
    
    def test_long_hebrew_paragraph(self):
        """긴 히브리어 문단 테스트"""
        text = "ברכה שלום. ברכה שלום. ברכה שלום. ברכה שלום. ברכה שלום. ברכה שלום. ברכה שלום."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"
        assert result.script_ratios.get("hebrew", 0.0) > 0.0
    
    def test_long_greek_paragraph(self):
        """긴 그리스어 문단 테스트"""
        text = "Καλημέρα κόσμε. Καλημέρα κόσμε. Καλημέρα κόσμε. Καλημέρα κόσμε. Καλημέρα κόσμε."
        result = detect_paragraph_language(text)
        assert result.label == "mixed"
        assert result.script_ratios.get("greek", 0.0) > 0.0


class TestSplitSentencesMixed:
    
    def test_empty_text(self):
        """빈 텍스트 분할 테스트"""
        result = split_sentences_mixed("")
        assert result == []
    
    def test_simple_english(self):
        """간단한 영어 문장 분할 테스트"""
        text = "Hello world. How are you?"
        result = split_sentences_mixed(text)
        assert len(result) >= 1
    
    def test_simple_korean(self):
        """간단한 한국어 문장 분할 테스트"""
        text = "안녕하세요. 어떻게 지내세요?"
        result = split_sentences_mixed(text)
        assert len(result) >= 1


# Test backward compatibility
class TestBackwardCompatibility:
    
    def test_paragraph_language_dataclass_backward_compatibility(self):
        """기존 ParagraphLanguage 생성 코드 호환성 테스트"""
        # This should work exactly as before (without script_ratios parameter)
        try:
            # This is how it was used before - should still work
            result = ParagraphLanguage("ko", 0.8, 0.2, 100, 20, 120)
            assert result.label == "ko"
            assert result.ko_ratio == 0.8
            assert result.en_ratio == 0.2
            assert result.hangul_count == 100
            assert result.latin_count == 20
            assert result.text_length == 120
            # script_ratios should be initialized as empty dict
            assert isinstance(result.script_ratios, dict)
        except Exception as e:
            pytest.fail(f"Backward compatibility broken: {e}")
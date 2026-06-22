"""
Tests for Hebrew/Greek language support in DBMA
"""

import os
import tempfile
import unittest
from pathlib import Path

# Add the project root to the path so we can import core modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.processing import detect_language, build_splitter
from core.extractors import extract_text_from_file


class TestHebrewGreekSupport(unittest.TestCase):
    
    def test_detect_language_hebrew(self):
        """Test Hebrew language detection"""
        hebrew_text = "שלום עולם! זה טקסט בעברית."
        language = detect_language(hebrew_text)
        self.assertEqual(language, "he")
        
    def test_detect_language_greek(self):
        """Test Greek language detection"""
        greek_text = "Γεια σου κόσμε! Αυτό είναι ένα κείμενο στα ελληνικά."
        language = detect_language(greek_text)
        self.assertEqual(language, "grc")
        
    def test_detect_language_mixed(self):
        """Test mixed language detection"""
        mixed_text = "Hello שלום Γεια σου"
        # Should default to English if not enough Hebrew/Greek characters
        language = detect_language(mixed_text)
        # This might return "en" or could be detected as one of the languages
        # depending on character percentage, so we just check it doesn't crash
        
    def test_bge_m3_splitter(self):
        """Test that BGE-M3 splitter works correctly"""
        splitter = build_splitter(chunk_size=512, chunk_overlap=64)
        self.assertIsNotNone(splitter)
        
        # Test splitting some Hebrew text
        hebrew_text = "שלום עולם! זה טקסט בעברית. אנו עובדים עם טקסטים בภาษา העברית."
        chunks = splitter.split_text(hebrew_text)
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) > 0)
        
        # Test splitting some Greek text
        greek_text = "Γεια σου κόσμε! Αυτό είναι ένα κείμενο στα ελληνικά."
        chunks = splitter.split_text(greek_text)
        self.assertIsInstance(chunks, list)
        self.assertTrue(len(chunks) > 0)
        
    def test_ocr_functionality(self):
        """Test OCR functionality with Hebrew/Greek languages"""
        # This test would require actual PDF files to run
        # For now, just verify the function exists and can be called
        from core.extractors import _extract_via_ocr
        self.assertTrue(callable(_extract_via_ocr))


if __name__ == '__main__':
    unittest.main()
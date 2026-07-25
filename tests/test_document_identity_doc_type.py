"""tests/test_document_identity_doc_type.py — core.document_identity.guess_doc_type() 검증.

[2026-07-24, 사용자 요청] 신규 투입 문서는 doc_type을 자동 추정하고,
매칭되는 키워드가 없으면 "기타"로 분류(None으로 미분류 방치 금지).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.document_identity import guess_doc_type


def test_sermon_keyword_in_content():
    assert guess_doc_type("제목: 새해 첫 설교\n본문: 마태복음 1장", "2025.rtf") == "설교"


def test_sermon_keyword_in_filename():
    assert guess_doc_type("아무 내용", "2025년 설교 모음.rtf") == "설교"


def test_commentary_keyword():
    assert guess_doc_type("창세기 주석 1장 해설", "창세기주석.pdf") == "주석"


def test_dictionary_keyword():
    assert guess_doc_type("용어 정리", "신학사전.pdf") == "사전"


def test_thesis_keyword():
    assert guess_doc_type("이 논문의 초록은 다음과 같다", "thesis.docx") == "논문"


def test_systematic_theology_keyword():
    assert guess_doc_type("조직신학 개론", "st_intro.pdf") == "조직신학"


def test_no_match_falls_back_to_other():
    assert guess_doc_type("아무 내용도 없는 그냥 텍스트", "random.txt") == "기타"


def test_empty_content_and_filename_falls_back_to_other():
    assert guess_doc_type("", "") == "기타"


def test_priority_order_when_multiple_keywords_present():
    """"주석"과 "설교"가 동시에 있으면 _DOC_TYPE_KEYWORDS 정의 순서상
    "주석"이 먼저다."""
    assert guess_doc_type("이 설교는 로마서 주석을 참고했다", "") == "주석"

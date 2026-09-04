"""tests/test_detail_panel.py - detail_panel.py 단위 테스트.

highlight_terms() 순수 함수 검증:
    - 매치 없는 경우
    - 매치 1개
    - 매치 여러 개 (같은 단어 반복)
    - HTML 특수문자 (<, >, &) 가 포함된 본문
    - 빈 문자열 본문
"""

import pytest
from ui.components.detail_panel import highlight_terms, _escape_for_html


class TestEscapeForHtml:
    def test_escape_ampersand(self):
        result = _escape_for_html('a & b')
        assert result == 'a &amp; b'

    def test_escape_lt_gt(self):
        result = _escape_for_html('<div>')
        assert result == '&lt;div&gt;'

    def test_escape_quote(self):
        result = _escape_for_html('say "hello"')
        assert result == 'say &quot;hello&quot;'

    def test_escape_all_special_chars(self):
        result = _escape_for_html('a < b & b > c')
        assert result == 'a &lt; b &amp; b &gt; c'

    def test_escape_empty_string(self):
        result = _escape_for_html('')
        assert result == ''

    def test_escape_no_special_chars(self):
        result = _escape_for_html('안녕하세요')
        assert result == '안녕하세요'


class TestHighlightTerms:
    def test_no_match_terms(self):
        """빈 terms 리스트면 escape만 되고 <mark> 없음."""
        result = highlight_terms('Hello world', [])
        assert '<mark>' not in result

    def test_no_match_found(self):
        """terms가 본문에 없으면 escape만 되고 <mark> 없음."""
        result = highlight_terms('Hello world', ['xyz'])
        assert '<mark>' not in result

    def test_single_match(self):
        """매치 1개 - 정확히 하나만 <mark>로 감싸짐."""
        result = highlight_terms('Hello world', ['world'])
        assert result == 'Hello <mark>world</mark>'
        # <mark>가 정확히 한 쌍 (열림 1, 닫힘 1)
        assert result.count('<mark>') == 1
        assert result.count('</mark>') == 1

    def test_multiple_matches_same_word(self):
        """매치 여러 개 - 전부 감싸짐."""
        result = highlight_terms('abc abc abc', ['abc'])
        assert result.count('<mark>') == 3
        assert result.count('</mark>') == 3
        assert result == '<mark>abc</mark> <mark>abc</mark> <mark>abc</mark>'

    def test_html_special_chars_escaped_first(self):
        """HTML 특수문자가 포함된 본문 - escape 후 매치되는지."""
        # <가 본문에 있으면 먼저 &lt;로 escape되어야 함
        # 그 다음 <mark>로 감싸야 <mark> 태그 자체가 escape되지 않음
        result = highlight_terms('a < b', ['b'])
        # <가 먼저 escape되었으므로 '&lt; b' 중에서 'b'가 매칭되어야 함
        assert '&lt;' in result
        assert '<mark>b</mark>' in result
        # <mark> 태그 자체가 escape되지 않았는지 확인
        assert '&lt;mark&gt;' not in result

    def test_html_special_chars_with_ampersand(self):
        """&가 포함된 본문에서 escape 확인."""
        result = highlight_terms('a & b', [])
        # escape만 되고 <mark> 없음
        assert '&amp;' in result
        assert '<mark>' not in result

    def test_empty_text(self):
        """빈 문자열 본문 - 에러 없이 빈 결과."""
        result = highlight_terms('', ['test'])
        assert result == ''

    def test_special_chars_ordering_bug(self):
        """이스케이프 순서 버그 검증 - escape 먼저, 감싸기 나중에."""
        text = '<div>test</div>'
        result = highlight_terms(text, ['test'])
        # <가 &lt;로 escape되어야 함
        assert '&lt;div&gt;' in result
        # test가 <mark>로 감싸져야 함
        assert '<mark>test</mark>' in result
        # <mark> 태그 자체가 깨지지 않아야 함
        assert '&lt;mark&gt;' not in result

    def test_korean_text(self):
        """한국어 텍스트."""
        result = highlight_terms('안녕하세요 세계', ['세계'])
        assert result == '안녕하세요 <mark>세계</mark>'

    def test_multiple_different_terms(self):
        """서로 다른 여러 검색어."""
        result = highlight_terms('apple banana cherry', ['apple', 'cherry'])
        assert '<mark>apple</mark>' in result
        assert '<mark>cherry</mark>' in result
        assert '<mark>banana</mark>' not in result

    def test_empty_term_ignored(self):
        """빈 term은 무시되어야 함."""
        result = highlight_terms('hello world', ['', 'hello'])
        assert '<mark>hello</mark>' in result
        assert result.count('<mark></mark>') == 0

    def test_case_sensitivity(self):
        """대소문자 구분 - 원문 그대로."""
        result = highlight_terms('Hello HELLO hello', ['HELLO'])
        assert result.count('<mark>HELLO</mark>') == 1
        # 다른 대소문자 버전은 감싸지지 않음
        assert result.count('<mark>Hello</mark>') == 0
        assert result.count('<mark>hello</mark>') == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

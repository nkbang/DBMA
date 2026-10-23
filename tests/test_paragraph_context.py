"""완성된 문단 근거 블록 회귀 테스트 (J2, 2026-10-18).

제품 조건 ③ — 목회자에게 제시되는 근거는 "의미 집합적으로 완성된 문단"이어야
한다. 프로덕션 코퍼스는 고정폭 청킹(1200/120)의 산물이라 청크의 **31.1%가
문장 중간에서 끊기고**(실측 119,595건), 이웃 청크를 그대로 이어 붙이면
chunk_overlap 때문에 경계에서 같은 문장이 두 번 보였다.

이 파일이 지키는 것:

1. 이웃의 깨진 앞머리·꼬리만 버린다.
2. **매칭된 청크 본문은 깎지 않는다** — 검색이 찾아낸 근거를 줄이면 안 된다.
3. 없는 글자를 지어내지 않는다(문장을 완성해 주지 않는다).
4. 과잉 절단 시 원문을 유지한다(약어 오인 방어).
"""
import pytest

from core.paragraph_context import (
    build_paragraph_body,
    join_without_overlap,
    trim_to_sentence_end,
    trim_to_sentence_start,
)


class TestTrimToSentenceStart:
    def test_drops_broken_head(self):
        text = "rant of grace unto him. The Lord Jesus came to save sinners."
        assert trim_to_sentence_start(text) == "The Lord Jesus came to save sinners."

    def test_keeps_text_without_sentence_boundary(self):
        """경계를 못 찾으면 버리지 않는다 — 추측으로 지우지 않는다."""
        text = "no sentence boundary here at all"
        assert trim_to_sentence_start(text) == text

    def test_keeps_original_when_too_little_would_remain(self):
        """남는 비율이 하한 미만이면 정리를 포기한다(약어 오인 방어)."""
        text = "A long broken fragment that runs on and on and on and on. Short."
        assert trim_to_sentence_start(text) == text

    def test_handles_korean(self):
        text = "되었던 것입니다. 칭의는 단번에 완결된 선언입니다. 성화는 계속됩니다."
        out = trim_to_sentence_start(text)
        assert out.startswith("칭의는")

    def test_empty_is_safe(self):
        assert trim_to_sentence_start("") == ""


class TestTrimToSentenceEnd:
    def test_drops_broken_tail(self):
        text = "He was faithful to the end. But the next thought is cut off mid-sent"
        assert trim_to_sentence_end(text) == "He was faithful to the end."

    def test_keeps_text_without_sentence_end(self):
        text = "a fragment with no terminator"
        assert trim_to_sentence_end(text) == text

    def test_keeps_original_when_too_little_would_remain(self):
        text = "Short. and then a very long dangling fragment that keeps going on and on"
        assert trim_to_sentence_end(text) == text

    def test_keeps_original_when_drop_exceeds_cap(self):
        """남는 비율은 통과하지만 버리는 양이 상한을 넘으면 포기한다 —
        1,000자 이웃의 중간에 종결부호가 있을 때 문맥을 통째로 잃는 경우."""
        text = "Sentence one ends here. " + "x" * 900
        assert trim_to_sentence_end(text) == text

    def test_abbreviation_only_neighbour_is_left_alone(self):
        """약어가 유일한 종결부호인 경우 거의 전부를 버리면 안 된다."""
        text = ("Vol. 30 of the Metropolitan Tabernacle Pulpit contains sermons "
                "preached in 1884 and was published by Passmore and Alabaster")
        assert trim_to_sentence_end(text) == text

    def test_empty_is_safe(self):
        assert trim_to_sentence_end("") == ""


class TestJoinWithoutOverlap:
    def test_removes_duplicated_overlap(self):
        """chunk_overlap=120의 산물 — 같은 문장이 두 번 보이면 안 된다."""
        shared = "This sentence sits in the overlap region of both chunks."
        a = "First chunk body. " + shared
        b = shared + " Second chunk continues here."
        out = join_without_overlap([a, b])
        assert out.count(shared) == 1
        assert "Second chunk continues here." in out
        assert out.startswith("First chunk body.")

    def test_no_overlap_is_plain_join(self):
        out = join_without_overlap(["alpha text", "beta text"])
        assert out == "alpha text\nbeta text"

    def test_whitespace_differences_are_not_treated_as_overlap(self):
        """겹침 판정은 정확 일치다 — 공백이 다르면 겹침으로 보지 않는다.

        겹침 구간은 같은 원문을 두 번 자른 결과라 공백까지 동일하다. 근사
        매칭으로 본문을 지우는 위험을 지지 않고, 공백이 다르면 중복이 남는
        쪽을 택한다(본문은 깨지지 않는다).
        """
        shared = "the  same   words   spaced differently in the two chunks"
        a = "head. " + shared
        b = shared.replace("  ", " ") + " tail."
        out = join_without_overlap([a, b])
        assert a in out and b in out

    def test_skips_empty_parts(self):
        assert join_without_overlap(["", "x", ""]) == "x"

    def test_short_coincidental_match_is_not_treated_as_overlap(self):
        """우연히 겹치는 몇 글자를 겹침으로 오인해 지우면 본문이 깨진다."""
        a = "He preached the word"
        b = "word of truth to the congregation that morning"
        out = join_without_overlap([a, b])
        assert b in out


class TestBuildParagraphBody:
    CONTENT = "Justification is an act; sanctification is a work."

    def test_matched_chunk_is_never_altered(self):
        """원칙 2 — 검색이 찾아낸 근거는 한 글자도 깎지 않는다."""
        body = build_paragraph_body(
            ["broken head here. A full sentence before it."],
            self.CONTENT,
            ["A full sentence after it. tail cut mid-wor"],
        )
        assert self.CONTENT in body

    def test_no_neighbors_returns_content_unchanged(self):
        """이웃이 없으면 기존 동작과 바이트 단위로 같다."""
        assert build_paragraph_body([], self.CONTENT, []) == self.CONTENT

    def test_block_starts_at_a_sentence(self):
        body = build_paragraph_body(
            ["ment of the covenant. The promise was given to Abraham."],
            self.CONTENT,
            [],
        )
        assert body.startswith("The promise was given to Abraham.")

    def test_block_ends_at_a_sentence(self):
        body = build_paragraph_body(
            [],
            self.CONTENT,
            ["The Spirit applies it daily. Then it breaks off mid-sen"],
        )
        assert body.rstrip().endswith("The Spirit applies it daily.")

    def test_inner_neighbors_are_not_trimmed(self):
        """중간 이웃은 앞뒤가 이미 다른 이웃과 이어지므로 깎을 이유가 없다."""
        inner = "middle neighbour text without terminator"
        body = build_paragraph_body(
            ["head fragment. First full sentence.", inner],
            self.CONTENT,
            [],
        )
        assert inner in body

    def test_nothing_is_invented(self):
        """문장을 완성해 주지 않는다 — 조각을 버리기만 한다."""
        body = build_paragraph_body([], self.CONTENT, ["tail with no terminator"])
        assert "tail with no terminator" in body  # 절반 규칙으로 원문 유지
        assert "." not in body.replace(self.CONTENT, "")

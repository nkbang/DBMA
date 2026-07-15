"""
tests/test_frontmatter_detector.py
core/frontmatter_detector.py 테스트 — 전면부(제목/판권/목차) 분리
"""

from core.extractors import PAGE_BREAK_MARKER
from core.frontmatter_detector import split_front_matter

M = PAGE_BREAK_MARKER

BODY_PARA = (
    "마가복음은 예수 그리스도의 복음의 시작이라 "
    "선지자 이사야의 글에 기록된 바 보라 내가 내 사자를 "
    "네 앞에 보내노니 그가 네 길을 준비하리라 "
    "광야에 외치는 자의 소리가 있어 이르되 너희는 주의 길을 "
    "준비하라 그의 오실 길을 곧게 하라 기록된 것과 같이."
)


class TestSplitFrontMatter:
    def test_no_marker_returns_all_as_body(self):
        text = "그냥 평범한 본문 텍스트입니다. 페이지 마커가 없습니다."
        front, body = split_front_matter(text)
        assert front == ""
        assert body == text

    def test_empty_text(self):
        front, body = split_front_matter("")
        assert front == ""
        assert body == ""

    def test_real_front_matter_pattern_is_separated(self):
        title_page = "톰라이트\n-\n--\n뿔\nnμ"
        copyright_page = (
            "양혜원옮김\n\n모든사람을위한마가복음\n\n"
            "IVP(InterVarsity Press)는\n"
            "Copyright @ 2001, 2004 Nicholas Thomas Wright"
        )
        toc_page = "목차\n서문 5\n1장 세례 요한 12\n2장 예수의 사역 시작 20"
        body_page = BODY_PARA * 5

        full = M.join([title_page, copyright_page, toc_page, body_page, body_page])
        front, body = split_front_matter(full)

        assert front != ""
        assert "Copyright" in front
        assert "목차" in front
        assert PAGE_BREAK_MARKER not in front
        assert PAGE_BREAK_MARKER not in body
        assert body.startswith("마가복음은")

    def test_no_front_matter_pages_leaves_everything_as_body(self):
        # Every page looks like clean prose — nothing should be split off.
        full = M.join([BODY_PARA * 5, BODY_PARA * 5, BODY_PARA * 5])
        front, body = split_front_matter(full)
        assert front == ""
        assert PAGE_BREAK_MARKER not in body

    def test_single_page_document_with_marker_present_elsewhere(self):
        # Edge case: marker present but splitting produces just one "page".
        full = BODY_PARA * 3
        front, body = split_front_matter(full)
        assert front == ""
        assert body == full

    def test_keyword_alone_triggers_front_matter_even_if_long(self):
        # A long page that nonetheless clearly reads as copyright boilerplate.
        long_copyright_page = (
            "All rights reserved. No part of this publication may be "
            "reproduced, stored in a retrieval system, or transmitted "
            "in any form or by any means, electronic, mechanical, "
            "photocopying, recording, or otherwise, without the prior "
            "permission of the publisher. ISBN 978-0-000-00000-0. " * 3
        )
        full = M.join([long_copyright_page, BODY_PARA * 5])
        front, body = split_front_matter(full)
        assert "ISBN" in front or "All rights reserved" in front
        assert body.startswith("마가복음은")

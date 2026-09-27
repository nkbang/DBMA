"""Query-time detection of back-of-book index pages (subject/scripture indexes).

[2026-09-26] 구절 질의("로마서 8장 28절")의 상위 10건이 전부 Maclaren
Expositions 권말 색인이었다 — "Romans, 179 ; Romans, 191"처럼 책 이름이
반복되니 BM25가 본문보다 높게 친다. core/noise_classifier.py에는 색인
유형이 없어 절반은 NORMAL_CONTENT(quality 1.0)로 저장돼 있었다.

TSU를 재빌드하지 않도록 검색 시점에 후보(최대 candidate_k건)에 대해서만
판정한다. 임계값은 실코퍼스 119,595건 실측으로 정했다
(docs/NAE_INDEX_PAGE_DOWNWEIGHT_BUILD_REPORT_001.md):

  - 숫자 토큰 비율 >= 0.20 AND "이름, 쪽번호" 로케이터 >= 5개/100토큰
    → 주제/인명 색인 (Maclaren·Broadus·Dargan)
  - 숫자 토큰 비율 >= 0.35
    → 로케이터 쉼표가 없는 성경 색인 (Spurgeon "xvii. 12—14 . 1685")

본문 안에 참조가 촘촘한 산문(Keach 1681, 숫자 비율 0.22~0.29, 로케이터
< 5)은 두 조건 모두에 걸리지 않는다. 판정 결과는 noise_classifier의
DOWNWEIGHT 정책과 같은 quality_score 0.3으로 취급한다(제거하지 않음).
"""

from __future__ import annotations

import re

INDEX_PAGE_QUALITY_SCORE = 0.3  # noise_classifier DOWNWEIGHT와 동일

_MIN_TOKENS = 30
_NUMERIC_RATIO_WITH_LOCATORS = 0.20
_LOCATORS_PER_100_TOKENS = 5.0
_NUMERIC_RATIO_ALONE = 0.35

_TOKEN_RE = re.compile(r"[A-Za-z]+|\d+")
# "Romans, 179" / "ii. Kings, 73" / "Peter of Blois, 204"
_LOCATOR_RE = re.compile(r"[A-Za-z][A-Za-z.]*\s*,\s*\d{1,4}\b")


def is_index_page(text: str) -> bool:
    tokens = _TOKEN_RE.findall(text or "")
    if len(tokens) < _MIN_TOKENS:
        return False
    numeric_ratio = sum(t.isdigit() for t in tokens) / len(tokens)
    if numeric_ratio >= _NUMERIC_RATIO_ALONE:
        return True
    locators_per_100 = len(_LOCATOR_RE.findall(text)) * 100 / len(tokens)
    return (
        numeric_ratio >= _NUMERIC_RATIO_WITH_LOCATORS
        and locators_per_100 >= _LOCATORS_PER_100_TOKENS
    )

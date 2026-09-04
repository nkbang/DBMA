"""core/date_extractor.py — 설교 텍스트에서 날짜 메타데이터 추출.

설교 모음 파일(예: "2025년 설교 모음.rtf") 실측 근거(2026-07-24,
core.extractors.extract_text_from_rtf()로 추출한 실제 텍스트 대조):
설교 제목("제목:" 줄) 앞 몇 줄 이내에 "YYYY-MM-DD" 형식 날짜가 등장한다
— 다만 항상 붙어있지는 않고, 교회명/이전 설교 마지막 문장/빈 줄이
끼어있는 경우가 많다(29개 설교 중 정확히 붙어있는 경우는 소수).
따라서 "제목 앞 N줄 이내 가장 가까운 날짜"를 찾는 관용적(tolerant)
탐색이 필요하다 — 고정 오프셋 가정은 실측으로 이미 반증됨.
"""

from __future__ import annotations

import re
from typing import Optional

# "2025-01-05" 형식 — 실측 근거: 모든 날짜가 이 형식으로 등장.
_DATE_ISO_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")

# "2026년 2월 11일" 형식 — 단일 설교 파일(예: RTF 메타라인)에서 관찰된
# 형식. 두 형식을 모두 지원해 설교 모음/개별 파일 양쪽에 쓸 수 있다.
_DATE_KOREAN_RE = re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")


def _normalize_date(year: str, month: str, day: str) -> Optional[str]:
    try:
        y, m, d = int(year), int(month), int(day)
        if not (1 <= m <= 12 and 1 <= d <= 31):
            return None
        return f"{y:04d}-{m:02d}-{d:02d}"
    except ValueError:
        return None


def extract_date_from_line(line: str) -> Optional[str]:
    """한 줄에서 날짜를 찾아 "YYYY-MM-DD"로 정규화해 반환. 못 찾으면 None."""
    m = _DATE_ISO_RE.search(line)
    if m:
        return _normalize_date(*m.groups())
    m = _DATE_KOREAN_RE.search(line)
    if m:
        return _normalize_date(*m.groups())
    return None


def find_nearest_date(
    lines: list[str],
    anchor_index: int,
    max_lookback: int = 10,
    stop_index: int = 0,
) -> Optional[str]:
    """anchor_index(예: "제목:" 줄) 바로 위부터 역방향으로 최대
    max_lookback줄까지, 또는 stop_index(이전 설교의 경계)를 넘지 않는
    선에서 가장 가까운 날짜를 찾는다.

    "고정 오프셋(N줄 앞)"이 아니라 근접 탐색인 이유: 실측 결과 날짜와
    제목 사이에 낀 줄 수가 설교마다 다르다(교회명/빈 줄/이전 설교
    잔여 텍스트 등)."""
    lower_bound = max(stop_index, anchor_index - max_lookback)
    for i in range(anchor_index - 1, lower_bound - 1, -1):
        date = extract_date_from_line(lines[i])
        if date:
            return date
    return None

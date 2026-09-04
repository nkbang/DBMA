"""core/citation_format.py — 서지 각주 한 줄 포맷 (공용).

원래 `ui/pages/research.py::_build_footnote_citation` 안에만 있던 "저자, *제목*
(자료유형, 연도)" 서지 본문 조립 로직을, "연구하기 > 본문 해설" 각주 렌더가
같은 형식을 쓰기 위해 여기로 뽑아낸다. research.py 는 세션 스코프
Ibid./약식 재인용 분기를 그대로 유지하되, 최초(전체) 인용 본문만 이 함수를
호출한다 — 출력 문자열은 기존과 동일하다.

레지스트리에 없는 서지 필드(출판사·발행지 등)는 만들어내지 않는다
(프로젝트 원칙: None = unknown).
"""

from __future__ import annotations

from typing import Optional


def extract_citation_year(created_at: Optional[str]) -> Optional[str]:
    """ISO 날짜 문자열(YYYY-...)에서 연도만 추출. 형식이 아니면 None."""
    if not created_at or len(created_at) < 4 or not created_at[:4].isdigit():
        return None
    return created_at[:4]


def format_footnote_line(
    author: Optional[str],
    title: Optional[str],
    doc_type: Optional[str] = None,
    year: Optional[str] = None,
    location: Optional[str] = None,
    *,
    fallback_title: str = "제목 미상",
) -> str:
    """`저자, *제목* (자료유형, 연도), 본문 위치.` 형태의 각주 본문 한 줄.

    - author 없으면 `*제목* ...` 로 시작.
    - doc_type/year 둘 다 없으면 괄호 블록 생략.
    - location(본문 위치: heading path 또는 장:절) 있으면 끝에 덧붙임.
    - 항상 마침표로 끝난다. 번호(`1. `)는 호출자가 붙인다.
    """
    a = (author or "").strip()
    t = (title or "").strip() or fallback_title
    meta = ", ".join(x for x in (doc_type, year) if x)
    head = f"{a}, *{t}*" if a else f"*{t}*"
    body = f"{head} ({meta})" if meta else head
    if location:
        body = f"{body}, {location.strip()}"
    return f"{body}."

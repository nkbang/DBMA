"""core/multi_doc_splitter.py — 한 파일에 여러 설교가 들어있는 "설교
모음" 문서를 개별 설교 단위로 분리.

**실측 근거(2026-07-24)**: 사용자가 제공한 실제 파일(`data/RAW/2025년
설교 모음.rtf`, `core.extractors.extract_text_from_rtf()`로 추출한
텍스트 기준)을 직접 분석해 확정한 규칙이다 — 최초 가설(RTF의
`<$Scr_H::N>` 마커, 날짜가 제목 바로 앞 2줄에 고정 반복)은 실제로는
그 파일과 무관한 다른 문서에서 관찰된 패턴이었고, 실측 결과 반증됐다
(자세한 경위는 세션 기록 참고). 이 모듈은 실제 파일 대조로 검증된
규칙만 사용한다:

1. **유일하게 100% 안정적인 경계 신호는 "제목:"으로 시작하는 줄이다**
   (29개 설교 전부에서 확인). 그 외 신호(날짜 반복, 마커)는 문서마다
   들쭉날쭉해 경계로 쓸 수 없다.
2. 날짜는 제목 줄 근처(위쪽, 가변 거리)에 있다 — core.date_extractor.
   find_nearest_date()로 관용적 탐색.
3. 성구("본문:")는 제목과 같은 줄에 붙어 있거나("제목: X 본문: Y"),
   별도 줄로 분리돼 있거나("본문 말씀:" 변형 포함), 아예 없을 수도
   있다 — 못 찾으면 None으로 남기고 실패로 취급하지 않는다(실측:
   29개 중 다수가 있었지만 전부는 아니었음).

이 모듈은 "설교 모음 파일 1개 → 개별 설교 dict 목록"까지만 담당한다.
각 dict를 실제 TSU/identity_registry 레코드로 만드는 것은 별도 단계
(ingestion 파이프라인 통합)로, 이 모듈의 책임 밖이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from core.date_extractor import find_nearest_date

_TITLE_PREFIX_RE = re.compile(r"^\s*제목\s*:\s*")
# "본문:" 또는 "본문 말씀:" 등 변형을 모두 잡는다 — "본문"과 ":" 사이에
# 공백/다른 글자가 낄 수 있음(실측: "본문 말씀:" 확인).
_SCRIPTURE_PREFIX_RE = re.compile(r"본문\s*[가-힣]*\s*:\s*")

# 성구 줄을 제목 뒤 몇 줄 이내에서 찾을지 — 실측 근거: 제목 바로 다음
# 줄이거나, 한두 줄 건너 등장(설교자/부제 등이 낄 수 있음).
_SCRIPTURE_LOOKAHEAD = 4

# 날짜를 제목 위 몇 줄 이내에서 찾을지 — core.date_extractor 참고.
_DATE_LOOKBACK = 10


@dataclass
class SermonRecord:
    """분리된 설교 1건."""
    title: str
    date: Optional[str]
    scripture: Optional[str]
    body: str
    start_line: int
    end_line: int


def _find_title_anchors(lines: list[str]) -> list[int]:
    return [i for i, line in enumerate(lines) if _TITLE_PREFIX_RE.match(line.strip())]


def _split_title_line(line: str) -> tuple[str, Optional[str]]:
    """"제목:" 접두어를 제거하고, 같은 줄에 "본문:"이 붙어있으면 분리해
    (title, inline_scripture)를 반환한다."""
    after_prefix = _TITLE_PREFIX_RE.sub("", line.strip(), count=1)
    m = _SCRIPTURE_PREFIX_RE.search(after_prefix)
    if m:
        title = after_prefix[: m.start()].strip()
        scripture = after_prefix[m.end():].strip()
        return title, (scripture or None)
    return after_prefix.strip(), None


def _find_scripture_nearby(lines: list[str], title_index: int, section_end: int) -> Optional[str]:
    upper = min(section_end, title_index + 1 + _SCRIPTURE_LOOKAHEAD)
    for i in range(title_index + 1, upper):
        line = lines[i].strip()
        m = _SCRIPTURE_PREFIX_RE.search(line)
        if m:
            scripture = line[m.end():].strip()
            if scripture:
                return scripture
    return None


def manual_split(
    record: SermonRecord,
    cut_line: int,
    new_title: str,
    new_date: Optional[str] = None,
    new_scripture: Optional[str] = None,
) -> tuple[SermonRecord, SermonRecord]:
    """자동 분리가 한 SermonRecord 안에 실제로는 서로 다른 설교 2개를
    남겨둔 경우, 사용자가 리뷰 중 지정한 지점(cut_line — record.body를
    줄 단위로 나눴을 때의 인덱스, 이 줄부터 두 번째 설교로 취급)에서
    수동으로 다시 나눈다.

    [2026-07-24, 사용자 요청] 자동 탐지("제목:" 앵커)가 놓친 경우를
    수동으로 보정하는 기능이므로, **제목/날짜/성구 세 가지 모두
    필수** — 자동 분리(split_sermon_collection)와 달리 "찾았으면
    쓰고 못 찾으면 None"이 아니라, 사용자가 이 자리에서 직접 확인해
    입력해야 한다. 셋 중 하나라도 비어 있으면 분할 자체를 실행하지
    않고 ValueError — UI 쪽에서도 버튼을 비활성화하지만, 이 함수를
    직접 호출하는 경우에도 동일하게 강제한다(방어적 이중 검증).

    Returns: (첫 번째 조각 — 원래 record의 메타데이터 유지,
              두 번째 조각 — 신규 메타데이터)"""
    missing = [
        label for label, value in (("제목", new_title), ("날짜", new_date), ("성구", new_scripture))
        if not (value or "").strip()
    ]
    if missing:
        raise ValueError(f"다음 항목이 없어 분할할 수 없습니다: {', '.join(missing)}")

    lines = record.body.split("\n")
    if not (0 < cut_line < len(lines)):
        raise ValueError(
            f"cut_line은 1~{len(lines) - 1} 사이여야 합니다 (본문 총 {len(lines)}줄, 받은 값: {cut_line})"
        )

    first_body = "\n".join(lines[:cut_line]).strip()
    second_body = "\n".join(lines[cut_line:]).strip()

    first = SermonRecord(
        title=record.title,
        date=record.date,
        scripture=record.scripture,
        body=first_body,
        start_line=record.start_line,
        end_line=record.end_line,
    )
    second = SermonRecord(
        title=new_title,
        date=new_date,
        scripture=new_scripture,
        body=second_body,
        start_line=record.start_line,
        end_line=record.end_line,
    )
    return first, second


def split_sermon_collection(text: str) -> list[SermonRecord]:
    """설교 모음 텍스트를 개별 SermonRecord 목록으로 분리한다.

    "제목:" 줄이 하나도 없으면 — 이 텍스트가 애초에 단일 문서라는
    뜻이므로 빈 리스트를 반환한다(호출자가 "분리 대상 아님"으로 판단
    하도록, 예외를 던지지 않는다 — 기존 단일-설교 파일에 실수로 이
    함수를 돌려도 안전)."""
    lines = text.split("\n")
    anchors = _find_title_anchors(lines)
    if not anchors:
        return []

    records: list[SermonRecord] = []
    for idx, title_index in enumerate(anchors):
        section_start = title_index
        section_end = anchors[idx + 1] if idx + 1 < len(anchors) else len(lines)
        prev_anchor = anchors[idx - 1] if idx > 0 else 0

        title, inline_scripture = _split_title_line(lines[title_index])
        scripture = inline_scripture or _find_scripture_nearby(lines, title_index, section_end)
        date = find_nearest_date(lines, title_index, max_lookback=_DATE_LOOKBACK, stop_index=prev_anchor)

        # 본문: 제목 줄과(있으면) 별도 성구 줄을 제외한 나머지.
        body_lines = []
        skipped_scripture_line = False
        for i in range(title_index + 1, section_end):
            line = lines[i]
            if not skipped_scripture_line and not inline_scripture and _SCRIPTURE_PREFIX_RE.search(line.strip()):
                skipped_scripture_line = True
                continue
            body_lines.append(line)
        body = "\n".join(body_lines).strip()

        records.append(SermonRecord(
            title=title,
            date=date,
            scripture=scripture,
            body=body,
            start_line=section_start,
            end_line=section_end,
        ))

    return records

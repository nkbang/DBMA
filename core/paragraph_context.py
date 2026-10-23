"""core/paragraph_context.py — 근거 블록을 "완성된 문단"으로 다듬는 순수 함수.

[J2, 2026-10-18] 제품 조건 ③ — 목회자에게 제시되는 근거는 "의미 집합적으로
완성된 문단, 완전한 문단의 형태"여야 한다. 그러나 프로덕션 코퍼스는 고정폭
청킹(chunk_size 1200 / overlap 120)의 산물이어서 **청크의 31.1%가 문장
중간에서 끊긴다**(실측 119,595건, `docs/NAE_ANSWER_QUALITY_JOURNEY_PLAN_v1.md`
§1.1).

해법은 `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md` §0의 옵션 A다 —
검색 단위는 TSU 그대로 두고 **조립 시점에** 문단으로 확장한다. 재청킹·
재임베딩·재색인이 없으므로 `builder_version`과 인덱스는 무변경이다.

이 모듈이 맡는 것은 그 확장 블록의 **경계 정리**뿐이다. 세 가지 원칙:

1. **매칭된 청크 본문은 건드리지 않는다.** 이웃 청크(앞뒤 문맥)만 다듬는다.
   앞 이웃의 깨진 앞머리를 버리고, 뒤 이웃의 깨진 꼬리를 버린다 — 둘 다
   "덧붙인 문맥"이라 일부를 버려도 근거가 줄지 않는다. 반대로 매칭 청크를
   깎으면 검색이 찾아낸 근거 자체가 줄어든다.
2. **없는 글자를 지어내지 않는다.** 문장을 완성해 주지 않고, 완성되지 않은
   조각을 버리기만 한다("없으면 없는 대로").
3. **과잉 절단 시 원문을 유지한다.** 약어("C. H. Spurgeon", "Vol.", "Mr.")가
   문장 종결로 오인될 수 있으므로, 정리 결과가 원문의 절반 미만으로 줄면
   정리를 포기하고 원문을 그대로 쓴다 — 검증되지 않은 판정 위에 파괴적
   동작을 얹지 않는다는 원칙(feedback_avoid_risky_uncertain_design).

겹침 제거(`join_without_overlap`)는 별개 문제다. chunk_overlap=120 때문에
이웃 청크를 그대로 이어 붙이면 경계에서 같은 문장이 두 번 보인다 — 읽는
목회자에게는 그 자체가 "완성된 문단"이 아니다.
"""

from __future__ import annotations

import re

# 문장 종결 부호 + (닫는 인용부호) + 공백 + 다음 문장 시작(대문자/한글/인용부호).
# 영문 코퍼스와 한국어 답변 양쪽에 쓰이므로 두 문자 체계를 함께 본다.
_SENTENCE_BREAK_RE = re.compile(
    r"[.!?][\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z가-힣])"
)

# 문자열 끝의 문장 종결. 뒤 이웃의 꼬리를 자를 위치를 찾는다.
_SENTENCE_END_RE = re.compile(r"[.!?][\"'”’)\]]*(?=\s|$)")

# 과잉 절단 방어는 두 조건을 **함께** 쓴다(원칙 3). 하나만으로는 부족하다:
#
#   남는 비율 하한(_MIN_KEEP_RATIO)만 두면, 1,000자 이웃의 중간(300자 지점)에
#   마지막 종결부호가 있을 때 700자를 버리고도 통과한다 — 문맥을 통째로 잃는다.
#   버리는 양 상한(_MAX_DROP_CHARS)만 두면, "Vol. 30 of the Metropolitan
#   Tabernacle Pulpit contains sermons preached in 1884 and was published by…"
#   처럼 약어("Vol.")가 유일한 종결부호인 짧은 이웃에서 거의 전부를 버린다.
#
# 깨진 조각은 정의상 한 문장 미만이므로, 정상 절단은 두 조건을 모두 넉넉히
# 만족한다. 둘 중 하나라도 어기면 정리를 포기하고 원문을 그대로 쓴다.
_MIN_KEEP_RATIO = 0.2
_MAX_DROP_CHARS = 500

# 겹침 탐색 범위. chunk_overlap=120 기준으로 여유를 둔다.
#
# 비교는 **정확 일치**다. 겹침 구간은 같은 원문을 두 번 자른 결과라 공백까지
# 동일하므로, 공백 차이를 허용하는 근사 매칭은 필요하지 않다 — 검증되지 않은
# 근사 판정으로 본문을 지우지 않는다. 공백이 실제로 다르면 겹침으로 보지 않고
# 그냥 이어 붙인다(중복이 남을 뿐, 본문이 깨지지는 않는다).
_MAX_OVERLAP = 400
_MIN_OVERLAP = 24


def trim_to_sentence_start(text: str) -> str:
    """앞 이웃의 깨진 앞머리를 버리고 첫 완결 문장부터 반환한다.

    문장 경계를 찾지 못하거나, 정리 결과가 원문의 절반 미만이면 원문을
    그대로 돌려준다.
    """
    if not text:
        return text
    stripped = text.lstrip()
    m = _SENTENCE_BREAK_RE.search(stripped)
    if not m:
        return text
    candidate = stripped[m.end():].lstrip()
    if _trim_is_excessive(stripped, candidate):
        return text
    return candidate


def trim_to_sentence_end(text: str) -> str:
    """뒤 이웃의 깨진 꼬리를 버리고 마지막 완결 문장까지 반환한다.

    문장 종결을 찾지 못하거나, 정리 결과가 원문의 절반 미만이면 원문을
    그대로 돌려준다.
    """
    if not text:
        return text
    stripped = text.rstrip()
    matches = list(_SENTENCE_END_RE.finditer(stripped))
    if not matches:
        return text
    candidate = stripped[: matches[-1].end()].rstrip()
    if _trim_is_excessive(stripped, candidate):
        return text
    return candidate


def _trim_is_excessive(original: str, candidate: str) -> bool:
    """정리가 과했는지 — 남는 비율과 버리는 양을 함께 본다(원칙 3)."""
    if len(candidate) < len(original) * _MIN_KEEP_RATIO:
        return True
    return len(original) - len(candidate) > _MAX_DROP_CHARS


def join_without_overlap(parts: list[str], separator: str = "\n") -> str:
    """조각들을 이어 붙이되, 인접 조각의 겹치는 구간을 한 번만 남긴다.

    chunk_overlap(기본 120자) 때문에 이웃 청크의 경계에는 같은 본문이
    중복으로 들어 있다. 앞 조각의 접미(suffix)와 뒤 조각의 접두(prefix)가
    가장 길게 일치하는 구간을 찾아 뒤 조각에서 덜어낸다.

    겹침이 없으면 그냥 이어 붙인다 — 추측으로 글자를 지우지 않는다.
    """
    kept: list[str] = []
    for part in parts:
        if not part:
            continue
        if not kept:
            kept.append(part)
            continue
        prev = kept[-1]
        overlap = _overlap_len(prev, part)
        kept.append(part[overlap:].lstrip() if overlap else part)
    return separator.join(p for p in kept if p)


def _overlap_len(prev: str, nxt: str) -> int:
    """prev의 접미 == nxt의 접두가 되는 최대 길이(없으면 0). 정확 일치.

    `_MIN_OVERLAP`보다 짧은 일치는 겹침으로 보지 않는다 — "word" 같은 우연의
    일치를 겹침으로 오인해 지우면 본문이 깨진다.
    """
    prev_tail = prev[-_MAX_OVERLAP:]
    limit = min(len(prev_tail), len(nxt), _MAX_OVERLAP)
    for size in range(limit, _MIN_OVERLAP - 1, -1):
        if prev_tail[-size:] == nxt[:size]:
            return size
    return 0


def build_paragraph_body(
    before: list[str],
    content: str,
    after: list[str],
) -> str:
    """이웃 문맥을 매칭 청크에 이어 붙여 완성된 문단 블록을 만든다.

    - `content`(매칭된 청크)는 **무변경** — 검색이 찾아낸 근거를 깎지 않는다.
    - 앞 이웃 중 **가장 앞의 것만** 문장 시작으로 다듬는다(중간 이웃들은
      앞뒤가 이미 다른 이웃과 이어지므로 깎을 이유가 없다).
    - 뒤 이웃 중 **가장 뒤의 것만** 문장 종결로 다듬는다(같은 이유).
    - 겹침 구간은 한 번만 남긴다.

    이웃이 전혀 없으면 `content`를 그대로 반환한다 — 기존 동작과 동일하다.
    """
    if not before and not after:
        return content

    head = list(before)
    tail = list(after)
    if head:
        head[0] = trim_to_sentence_start(head[0])
    if tail:
        tail[-1] = trim_to_sentence_end(tail[-1])
    else:
        # 뒤 이웃이 없으면 블록의 끝은 매칭 청크의 끝이다. 매칭 청크는
        # 깎지 않는다는 원칙 1 때문에 여기서는 아무것도 하지 않는다 —
        # 문서의 마지막 청크처럼 뒤 문맥이 실제로 없는 경우다.
        pass
    return join_without_overlap([*head, content, *tail])

"""NAE 브리지 전용 답변 컨텍스트 조립 — 완성 문단 형태.

[PM 정렬 감사 선결 #4 / 옵션 A]
설계: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md §4.4.3 / §4.4.4
Task Order: §3

`core/retrieval.py::ContextAssembler`는 Chat/Research 공용이므로 건드리지
않는다(ADR-001). 설교 경로 `core/generation.py::_format_sermon_context()`가
브리지 전용 포맷의 선례다 — 이 모듈은 NAE `bridge_query` 경로 전용이다.

여기서 만드는 것은 두 가지:
  1. `format_nae_context_block()` — 히트(문단 확장 dict)당 `<자료>` 블록
  2. `NAE_PARAGRAPH_PROMPT_CLAUSE` — 완성 문단 재구성 지시 조항.
     `_GROUNDING_DIRECTIVE`(정본, 재작성 금지)에 **추가로** 붙는다.
"""
from __future__ import annotations

import os

# 문단 길이 상한 — 초과 시 앵커 문장 중심 window로 축약(문장 경계 존중).
# Stage 1-4 실측으로 임계값을 확정하기 전의 보수적 기본값(설계 §4.4.3).
_DEFAULT_MAX_CHARS = 1500
_DEFAULT_WINDOW_CHARS = 600


def _max_chars() -> int:
    try:
        return max(100, int(os.environ.get("NAE_PARAGRAPH_MAX_CHARS", _DEFAULT_MAX_CHARS)))
    except ValueError:
        return _DEFAULT_MAX_CHARS


def paragraph_evidence_enabled() -> bool:
    """서브 플래그 `NAE_PARAGRAPH_EVIDENCE` (기본 on). 요청마다 조회 —
    모듈 상수·__init__ 캐시 금지 (Conflict Register CON-009 B / TO §6-1)."""
    return os.environ.get("NAE_PARAGRAPH_EVIDENCE", "1") not in ("0", "false", "False", "no")


def _shrink_around_anchor(paragraph: str, anchor: str, window: int = _DEFAULT_WINDOW_CHARS) -> tuple[str, bool]:
    """문단이 상한을 넘으면 앵커 문장 주변만 남긴다. (축약본, truncated) 반환.

    문장 경계(마침표+공백)를 존중해 자르되, 앵커를 못 찾으면 앞에서 자른다.
    """
    if len(paragraph) <= _max_chars():
        return paragraph, False

    pos = paragraph.find(anchor.strip()) if anchor else -1
    if pos < 0:
        head = paragraph[: window * 2].rstrip()
        return head + " …", True

    start = max(0, pos - window)
    end = min(len(paragraph), pos + len(anchor) + window)
    # 앞쪽은 다음 문장 시작으로, 뒤쪽은 이전 문장 끝으로 스냅
    if start > 0:
        nxt = paragraph.find(". ", start, pos)
        if nxt != -1:
            start = nxt + 2
    if end < len(paragraph):
        prev = paragraph.rfind(". ", pos, end)
        if prev != -1:
            end = prev + 1
    prefix = "… " if start > 0 else ""
    suffix = " …" if end < len(paragraph) else ""
    return prefix + paragraph[start:end].strip() + suffix, True


def _attr(value) -> str:
    """XML 속성값 escaping (최소한). None/빈값은 빈 문자열."""
    if value is None:
        return ""
    return str(value).replace('"', "'").replace("<", "").replace(">", "").strip()


# num_ctx(기본 32768 토큰) 대비 컨텍스트 문자 예산의 보수적 상한. 한국어
# 기준 대략 토큰당 1.5~2자로 잡아도 여유가 크지만, 프롬프트의 나머지
# (지시문·질문·이전 대화)와 top_k개 문단을 함께 담아야 하므로 보수적으로
# 문자 기준 상한을 둔다. NAE_PARAGRAPH_CONTEXT_BUDGET로 조정.
_DEFAULT_CONTEXT_BUDGET = 24000


def _context_budget() -> int:
    try:
        return max(2000, int(os.environ.get("NAE_PARAGRAPH_CONTEXT_BUDGET", _DEFAULT_CONTEXT_BUDGET)))
    except ValueError:
        return _DEFAULT_CONTEXT_BUDGET


def format_nae_context_block(hits: list[dict]) -> str:
    """문단 확장된 히트 리스트를 LLM 컨텍스트 블록 문자열로 만든다.

    각 hit dict 기대 키 (NAE/retrieval_adapter.py::_enrich_hit_with_paragraph 생성):
      tsu_id, evidence_paragraph, anchor_sentence, paragraph_resolved,
      bibliography: {author, work, edition_id, page_start, page_end,
                    paragraph_index, identifier}

    hits는 score 내림차순이라고 가정한다(Qdrant 반환 순서). 누적 길이가
    컨텍스트 예산을 넘으면 하위 랭크부터 드롭하고 드롭 수를 로그한다.
    """
    import logging

    budget = _context_budget()
    used = 0
    kept: list[dict] = []
    dropped = 0
    for h in hits:
        approx = len((h.get("evidence_paragraph") or "")) + 200  # 태그·서지 여유
        if kept and used + approx > budget:
            dropped += 1
            continue
        kept.append(h)
        used += approx
    if dropped:
        logging.getLogger("nae.answer_context").info(
            "[format_nae_context_block] 예산 초과로 하위 %d개 자료 드롭 (budget=%d)", dropped, budget
        )

    parts: list[str] = []
    for h in kept:
        bib = h.get("bibliography") or {}
        para = (h.get("evidence_paragraph") or "").strip()
        anchor = (h.get("anchor_sentence") or "").strip()
        para, truncated = _shrink_around_anchor(para, anchor)

        page_start = bib.get("page_start")
        page_end = bib.get("page_end")
        if page_start and page_end and page_start != page_end:
            page_attr = f"p.{page_start}-{page_end}"
        elif page_start:
            page_attr = f"p.{page_start}"
        else:
            page_attr = ""

        attrs = [f'id="{_attr(h.get("tsu_id"))}"']
        if bib.get("work"):
            attrs.append(f'work="{_attr(bib.get("work"))}"')
        if bib.get("author"):
            attrs.append(f'author="{_attr(bib.get("author"))}"')
        if page_attr:
            attrs.append(f'page="{page_attr}"')
        if bib.get("paragraph_index") is not None:
            attrs.append(f'para="§{_attr(bib.get("paragraph_index"))}"')
        if truncated:
            attrs.append('truncated="true"')
        if not h.get("paragraph_resolved", True):
            attrs.append('resolved="false"')

        block = f"<자료 {' '.join(attrs)}>\n{para}\n"
        if anchor and anchor in para:
            block += f"  <일치문장>{anchor}</일치문장>\n"
        block += "</자료>\n"
        parts.append(block)

    return "\n".join(parts)


# `_GROUNDING_DIRECTIVE`(core/generation.py, ae05415 정본)에 **추가로** 붙는
# 브리지 전용 조항. 재구성·인용·앵커 해석을 지시한다. sandbox의 "3~6문장
# 간결" 상한은 프로덕션 목회 답변 경로에 이식하지 않는다(TO §3-2).
NAE_PARAGRAPH_PROMPT_CLAUSE = """추가 지시(공개 신학 자료):
6. 각 <자료>는 완결된 원문 문단이다. 조각을 그대로 붙여넣지 말고, 문단의
   논지를 2~4개의 완결된 한국어 문단으로 재구성하라.
7. 각 문단에서 최소 1개 <자료>를 근거로 명시하고, 본문에서 저자·저작
   (work / author 속성)을 밝혀라 — 예: "풀러는 …라고 말한다".
8. <일치문장>은 검색이 걸린 지점 표시일 뿐이다. 그 문장만이 아니라 문단
   전체를 근거로 삼아라."""


def build_nae_answer_prompt(grounding_directive: str, denomination_directive: str,
                            context_block: str, question: str,
                            conversation_history: str = "") -> str:
    """F6(chat ↔ bridge 배선)이 승인될 때 브리지 답변 경로가 쓸 프롬프트.

    지금은 배선되지 않았다(F6 = 별도 승인, TO §9). 이 함수는 옵션 A가
    준비 상태로 대기하도록 두는 조립기이며, 순서는 근거 강제 → 교단 관점 →
    문단 조항 → 자료 → 질문이다(_GROUNDING_DIRECTIVE 우선 원칙 유지).
    """
    history_block = (
        f"이전 대화:\n{conversation_history}\n\n" if conversation_history.strip() else ""
    )
    return (
        f"{history_block}자료:\n{context_block}\n\n"
        f"{grounding_directive}\n\n"
        f"{NAE_PARAGRAPH_PROMPT_CLAUSE}\n\n"
        f"{denomination_directive}\n\n"
        f"질문:\n{question}"
    )

"""core/passage_commentary.py — 지정 성경 본문에 대한 내서재 근거 해설 (ADR-031).

"연구하기 > 본문 해설" 탭의 오케스트레이션 로직. Streamlit에 의존하지 않는다
(세션·위젯 코드는 `ui/pages/_passage_commentary_tab.py` 담당).

설계 원칙 (ADR-028 답습):
  - `core/retrieval.py` / `core/generation.py` 의 공개 시그니처를 변경하지 않는다.
  - 검색은 기존 `QueryProcessor.process()` 재사용.
  - 구절↔청크 정합은 기존 `core.retrieval.compute_passage_match_score()` 재사용.
  - 생성은 `processor.process()` 가 돌려준 `ResponsePackage` 를 그 자리에서
    수정(question / llm_context_block / top_k_results / citations)해
    `GenerationService.generate_stream()` 에 넘긴다.

흐름:
  ScriptureReference
    → retrieve_passage_commentary(): process() 후 verse_mapping 이 ref 와
      정합(score ≥ _ALIGN_FLOOR)하는 후보만 남긴다. 없으면 status="no_material".
    → make_response_package(): ResponsePackage 를 본문 해설용으로 재구성.
    → (호출자) GenerationService.generate_stream() 스트리밍.
    → build_footnotes() / render_answer_with_badges() 로 그림처럼 렌더.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from core.bible_text import korean_book_name
from core.citation_format import extract_citation_year, format_footnote_line
from core.identity_registry import find_by_document_id, find_by_source_file
from core.retrieval import (
    Citation,
    CitationBuilder,
    RankedCandidate,
    ResponsePackage,
    ScriptureReference,
    compute_passage_match_score,
)

logger = logging.getLogger(__name__)

# `compute_passage_match_score` 점수 해석:
#   0.5  = book_id 일치 (최소선)
#   0.8  = book_id + chapter 정확 일치
#   1.0  = book/chapter/verse 범위 겹침
_ALIGN_FLOOR = 0.5          # 이 미만만 있으면 "관련 자료 없음"
_DEFAULT_K = 8

RetrievalStatus = Literal["ok", "no_material", "retrieval_failed"]
CommentaryStatus = Literal["ok", "no_material", "gen_failed"]

# 번호형 인용 마커([1], [2][3] 등) → 유니코드 원문자 배지.
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
_MARKER_RE = re.compile(r"\[(\d{1,2})\]")


# ── 참조 표기 ────────────────────────────────────────────
def reference_label(ref: ScriptureReference) -> str:
    """ScriptureReference → '잠언 8:10' / '잠언 8:10-12'."""
    name = korean_book_name(ref.book_id)
    if ref.verse_end and ref.verse_end != ref.verse_start:
        return f"{name} {ref.chapter}:{ref.verse_start}-{ref.verse_end}"
    return f"{name} {ref.chapter}:{ref.verse_start}"


def passage_query(ref: ScriptureReference) -> str:
    """검색 쿼리 — 기존 QueryParser 가 구절을 그대로 파싱하도록 표기를 포함한다."""
    return f"{reference_label(ref)} 본문의 문맥과 의미, 주해 해설"


# ── 검색 + 정합 필터 ─────────────────────────────────────
@dataclass
class RetrievalOutcome:
    status: RetrievalStatus
    aligned: list[RankedCandidate] = field(default_factory=list)
    response: Optional[ResponsePackage] = None
    scores: list[float] = field(default_factory=list)  # aligned 와 1:1
    error: Optional[str] = None


def _verse_mapping(candidate: RankedCandidate) -> dict[str, Any]:
    md = candidate.metadata or {}
    vm = md.get("verse_mapping")
    return vm if isinstance(vm, dict) else {}


def retrieve_passage_commentary(
    ref: ScriptureReference,
    processor: Any,
    *,
    k: int = _DEFAULT_K,
    align_floor: float = _ALIGN_FLOOR,
) -> RetrievalOutcome:
    """지정 본문과 정합하는 내서재 청크를 검색한다.

    `processor` 는 `core.retrieval.QueryProcessor` (또는 `.process(query, query_id=,
    k=) -> ResponsePackage` 를 만족하는 객체).
    """
    try:
        response = processor.process(passage_query(ref), query_id="passage-commentary", k=k)
    except Exception as e:  # noqa: BLE001 — 검색 실패가 탭 전체를 죽이지 않게
        logger.warning("[passage_commentary] retrieval 실패: %s", e)
        return RetrievalOutcome(status="retrieval_failed", error=str(e))

    scored: list[tuple[float, RankedCandidate]] = []
    for cand in response.top_k_results or []:
        score = compute_passage_match_score([ref], _verse_mapping(cand))
        if score >= align_floor:
            scored.append((score, cand))

    if not scored:
        return RetrievalOutcome(status="no_material", response=response)

    scored.sort(key=lambda t: (t[0], t[1].final_score), reverse=True)
    return RetrievalOutcome(
        status="ok",
        aligned=[c for _, c in scored],
        response=response,
        scores=[s for s, _ in scored],
    )


# ── 각주 ─────────────────────────────────────────────────
@dataclass
class FootnoteEntry:
    marker: int
    author: Optional[str]
    title: Optional[str]
    doc_type: Optional[str]
    year: Optional[str]
    location: Optional[str]
    document_id: Optional[str]
    source_file: Optional[str]
    excerpt: str

    def formatted(self) -> str:
        """'저자, *제목* (자료유형, 연도), 위치.' — 번호는 렌더 쪽에서 붙인다."""
        return format_footnote_line(
            self.author, self.title, self.doc_type, self.year, self.location
        )


def _location_label(md: dict[str, Any], vm: dict[str, Any]) -> Optional[str]:
    structure = md.get("structure") or {}
    heading_path = structure.get("heading_path") or []
    if heading_path:
        return " > ".join(str(x) for x in heading_path)
    book_id = vm.get("book_id")
    if book_id:
        name = korean_book_name(book_id)
        ch = vm.get("chapter")
        vs = vm.get("verse_start")
        ve = vm.get("verse_end", vs)
        if ch and vs:
            tail = f"-{ve}" if ve and ve != vs else ""
            return f"{name} {ch}:{vs}{tail}"
        if ch:
            return f"{name} {ch}장"
        return name
    return None


def _registry_record(
    registry: Optional[dict], document_id: Optional[str], source_file: Optional[str]
) -> dict:
    if not registry:
        return {}
    rec = None
    if document_id:
        rec = find_by_document_id(registry, document_id)
    if rec is None and source_file:
        rec = find_by_source_file(registry, source_file)
    return rec or {}


def build_footnotes(
    candidates: list[RankedCandidate],
    citations: list[Citation],
    *,
    registry: Optional[dict] = None,
) -> list[FootnoteEntry]:
    """정합 후보 + Citation 으로 각주 항목을 만든다.

    `registry`(identity_registry.load_identity_registry 결과)를 주면 저자·제목·
    자료유형·연도를 그 레코드에서 우선 채운다 — 그림처럼 실제 서지에 가깝게.
    레지스트리에도 없는 필드는 그대로 비운다(None = unknown, 지어내지 않음).
    """
    out: list[FootnoteEntry] = []
    for i, cand in enumerate(candidates, 1):
        md = cand.metadata or {}
        cit = citations[i - 1] if i - 1 < len(citations) else None
        vm = _verse_mapping(cand)

        document_id = (cit.document_id if cit else None) or md.get("document_id")
        source_file = (cit.source_file if cit else None) or md.get("source_file")
        rec = _registry_record(registry, document_id, source_file)

        out.append(
            FootnoteEntry(
                marker=i,
                author=rec.get("author")
                or (cit.source_author if cit else None)
                or md.get("author"),
                title=rec.get("title")
                or (cit.source_title if cit else None)
                or md.get("title")
                or source_file,
                doc_type=rec.get("doc_type") or md.get("doc_type"),
                year=extract_citation_year(rec.get("created_at") or md.get("created_at")),
                location=_location_label(md, vm),
                document_id=document_id,
                source_file=source_file,
                excerpt=(cand.content or "").strip()[:160],
            )
        )
    return out


# ── 생성 프롬프트 ────────────────────────────────────────
_GUIDANCE = (
    "너는 신학 자료 조교다. 아래 <자료> 블록은 사용자의 개인 서재(내서재)에서 "
    "검색된 주석·신학 문헌 발췌이며, 각 항목은 [번호]로 구분된다.\n"
    "지정된 성경 본문을 이해하는 데 도움이 되도록, 오직 이 자료에 근거해 한국어로 해설하라.\n"
    "규칙:\n"
    "- 각 문단이나 주장 끝에 근거가 된 자료 번호를 대괄호로 표기한다. 예: [1], [2]. 여러 개면 [1][3].\n"
    "- 자료에 없는 내용은 추측하거나 지어내지 않는다. 자료가 어떤 쟁점을 다루지 않으면 그렇게 밝힌다.\n"
    "- 본문의 문맥과 구조 → 핵심 어구의 의미 → 신학적 강조점 → 적용 함의 순으로 간결하게 쓴다.\n"
    "- 한국어(한글)로만 쓴다."
)


def _numbered_context(candidates: list[RankedCandidate]) -> str:
    blocks: list[str] = []
    for i, cand in enumerate(candidates, 1):
        md = cand.metadata or {}
        src = " · ".join(
            x for x in (md.get("author"), md.get("title") or md.get("source_file")) if x
        )
        loc = _location_label(md, _verse_mapping(cand))
        head = f"[{i}] {src}" if src else f"[{i}]"
        if loc:
            head = f"{head} — {loc}"
        blocks.append(f"{head}\n{(cand.content or '').strip()}")
    return "\n\n".join(blocks)


def _context_block(label: str, candidates: list[RankedCandidate]) -> str:
    return (
        f"{_GUIDANCE}\n\n지정 본문: {label}\n\n"
        f"<자료>\n{_numbered_context(candidates)}\n</자료>"
    )


def _instruction(label: str) -> str:
    return (
        f"위 자료에 근거해 «{label}» 본문의 이해를 돕는 해설을 한국어로 작성하라. "
        "각 주장 끝에 근거 자료 번호를 [1] 형식으로 표기하고, 자료에 없는 내용은 쓰지 마라."
    )


def make_response_package(
    outcome: RetrievalOutcome,
    ref: ScriptureReference,
    *,
    registry: Optional[dict] = None,
) -> tuple[ResponsePackage, list[Citation], list[FootnoteEntry]]:
    """`retrieve_passage_commentary` 결과(status=='ok')를 생성 입력으로 변환한다.

    `outcome.response`(실제 process() 산출물)를 그 자리에서 본문 해설용으로
    바꿔 돌려준다 — 새 ResponsePackage 를 손으로 조립하지 않는다(ADR-028).
    """
    label = reference_label(ref)
    citations = CitationBuilder().build_citations(outcome.aligned)
    footnotes = build_footnotes(outcome.aligned, citations, registry=registry)

    pkg = outcome.response
    assert pkg is not None  # status=='ok' 이면 항상 존재
    pkg.question = _instruction(label)
    pkg.top_k_results = list(outcome.aligned)
    pkg.llm_context_block = _context_block(label, outcome.aligned)
    pkg.citations = citations
    return pkg, citations, footnotes


# ── 렌더 헬퍼 (순수 문자열) ──────────────────────────────
def circled_marker(n: int) -> str:
    """1 → '①'. 20 초과면 '[n]' 문자열로 폴백."""
    return _CIRCLED[n - 1] if 1 <= n <= len(_CIRCLED) else f"[{n}]"


def render_answer_with_badges(text: str, max_marker: int) -> str:
    """'[3]' → '③'(1..max_marker 범위만). 범위 밖 숫자 대괄호는 그대로 둔다
    (본문에 우연히 등장한 [12] 같은 것을 잘못 배지로 만들지 않도록)."""
    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        if 1 <= n <= max_marker and n <= len(_CIRCLED):
            return _CIRCLED[n - 1]
        return m.group(0)

    return _MARKER_RE.sub(repl, text or "")


@dataclass
class PassageCommentaryResult:
    status: CommentaryStatus
    reference_label: str
    answer: str = ""
    answer_badged: str = ""
    citations: list[Citation] = field(default_factory=list)
    footnotes: list[FootnoteEntry] = field(default_factory=list)
    used_candidates: list[RankedCandidate] = field(default_factory=list)
    error: Optional[str] = None


def generate_passage_commentary(
    ref: ScriptureReference,
    processor: Any,
    generator: Any,
    *,
    k: int = _DEFAULT_K,
    registry: Optional[dict] = None,
) -> PassageCommentaryResult:
    """검색 → 정합 필터 → (자료 있으면) 블로킹 생성까지 한 번에.

    스트리밍이 필요한 UI 는 `retrieve_passage_commentary` + `make_response_package`
    + `generator.generate_stream()` 를 직접 쓰고, 이 함수는 비스트리밍 경로와
    테스트용이다. `generator` 는 `.generate(ResponsePackage) -> GenerationResult`
    (`core.generation.GenerationService`).
    """
    label = reference_label(ref)
    outcome = retrieve_passage_commentary(ref, processor, k=k)

    if outcome.status == "retrieval_failed":
        return PassageCommentaryResult(
            status="gen_failed", reference_label=label, error=outcome.error
        )
    if outcome.status == "no_material":
        return PassageCommentaryResult(status="no_material", reference_label=label)

    pkg, citations, footnotes = make_response_package(outcome, ref, registry=registry)
    try:
        result = generator.generate(pkg)
        answer = getattr(result, "answer", "") or ""
        gen_error = getattr(result, "error", None)
    except Exception as e:  # noqa: BLE001
        logger.warning("[passage_commentary] 생성 실패: %s", e)
        return PassageCommentaryResult(
            status="gen_failed",
            reference_label=label,
            citations=citations,
            footnotes=footnotes,
            used_candidates=outcome.aligned,
            error=str(e),
        )

    return PassageCommentaryResult(
        status="gen_failed" if gen_error else "ok",
        reference_label=label,
        answer=answer,
        answer_badged=render_answer_with_badges(answer, len(footnotes)),
        citations=citations,
        footnotes=footnotes,
        used_candidates=outcome.aligned,
        error=gen_error,
    )

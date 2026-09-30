"""생성된 답변의 `(출처: …)` 인용을 모델이 실제로 받은 근거와 대조한다.

배경 (EUAT-001 Issue 4): 모델이 자료에 없는 일반 지식을 "(출처: Spurgeon …)"
같은 인용을 붙여 코퍼스 근거처럼 제시했다(예: 인용된 Spurgeon 4권에 "1689"가
한 번도 없는데 "1689 런던신앙고백서는 …(출처: Spurgeon)"). 인용이 붙어 있어
오히려 신뢰도가 높아 보이는 것이 문제다.

설계 원칙
- **결정론적·경고 전용.** 답변을 바꾸거나 막지 않는다. 결과는 UI 경고로만 쓴다
  (chat.py의 low-confidence·ClaimGuard와 같은 방침: 소표본으로 보정된 신호로
  동작을 게이팅하지 않는다).
- **검증 가능한 것만 검증한다.** 답변은 한국어이고 근거는 영어 등 외국어라 의미
  검증은 할 수 없다. 대신 문장에 들어 있는 (1) 3~4자리 숫자(연도·번호)와 (2)
  라틴 문자 고유어·인용문이 인용된 근거 본문에 있는지만 본다. 한국어로 바꿔 쓴
  주장은 검증 대상이 아니다(검증하지 못한 것을 "정상"이라 하지 않고 "이슈 없음"
  으로만 둔다 — 이 검사가 통과해도 인용이 정확하다는 뜻이 아니다).
- **모델이 본 것과 대조한다.** 기준은 `RankedCandidate.content`(LLM 문맥에 넣은
  근거 본문)다. 이웃 문단 확장으로 문맥에 더해진 본문은 후보에 없으므로, 이
  경우 "확인하지 못했다"는 표현으로만 알린다(틀렸다고 단정하지 않는다).
- 외부 호출·전역 상태 없음. 실패해도 답변 경로를 죽이지 않도록 호출부가 격리한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

# `(출처: 라벨)` — 전각 괄호·콜론도 허용. 라벨 안에 괄호가 없다고 가정한다
# (`_format_context_source_label`이 만드는 라벨은 괄호를 쓰지 않는다).
_CITATION_RE = re.compile(r"[(（]\s*출처\s*[:：]\s*([^()（）]{2,240}?)\s*[)）]")

_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]{3,}")  # 4자 이상
_NUMBER = re.compile(r"(?<![\d,.])\d{3,4}(?!\d)")  # 3~4자리 (연도·번호). "1,691"/"p.160"의 일부는 제외
_HANGUL_SENTENCE_END = re.compile(r"(?<=[가-힣])[.!?]\s")

_STOPWORDS = frozenset(
    {"the", "of", "and", "a", "an", "in", "on", "to", "for", "by", "vol", "volume"}
)

# 출처 라벨이 후보의 서지 정보와 이 비율 이상 겹치면 같은 자료로 본다.
SOURCE_MATCH_MIN_OVERLAP = 0.6
# 라틴 고유어는 이 개수 이상 근거에 없을 때만 이슈로 본다 — 일반 영단어 한두 개가
# 문맥 밖 표기(이웃 문단 등)와 어긋나는 잡음을 줄이려는 값이다.
MIN_MISSING_LATIN_TOKENS = 2

KIND_SOURCE_NOT_RETRIEVED = "source_not_retrieved"
KIND_TOKEN_UNSUPPORTED = "claim_token_unsupported"
KIND_TOKEN_OTHER_SOURCE = "claim_token_other_source"


@dataclass(frozen=True)
class CitationIssue:
    kind: str
    citation_text: str  # 답변에 나온 "(출처: …)" 원문
    sentence: str  # 그 인용이 붙은 문장(직전 구간)
    tokens: tuple[str, ...] = ()  # 근거에서 확인하지 못한 토큰


@dataclass
class CitationCheckResult:
    citations_found: int = 0
    issues: list[CitationIssue] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower())}


def _present(token: str, words: set[str]) -> bool:
    """하이픈·아포스트로피로 이어진 토큰은 구성 조각이 모두 근거에 있어야 한다."""
    parts = re.findall(r"[a-z0-9]+", token.lower())
    return bool(parts) and all(p in words for p in parts)


def _name_tokens(text: str) -> set[str]:
    """출처 라벨/서지 비교용 토큰: 라틴 3자 이상, 불용어 제외."""
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOPWORDS}


def _get(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _candidate_name_tokens(candidate: Any, citation: Any | None) -> set[str]:
    md = _get(candidate, "metadata") or {}
    parts = [
        md.get("title"), md.get("book"), md.get("author"), md.get("source_file"),
        _get(citation, "source_title") if citation is not None else None,
        _get(citation, "source_author") if citation is not None else None,
        _get(citation, "source_file") if citation is not None else None,
    ]
    return _name_tokens(" ".join(str(p) for p in parts if p))


def _sentence_before(answer: str, start: int, lower_bound: int) -> str:
    """인용 시작 위치 직전의 문장(또는 직전 인용 이후 구간)을 돌려준다."""
    head = answer[lower_bound:start]
    cut = head.rfind("\n")
    for m in _HANGUL_SENTENCE_END.finditer(head):
        cut = max(cut, m.end() - 1)
    return head[cut + 1:].strip()


def verify_citations(
    answer: str,
    candidates: Sequence[Any],
    citations: Sequence[Any] | None = None,
) -> CitationCheckResult:
    """답변의 모든 `(출처: …)` 인용을 근거 후보와 대조한다.

    Parameters
    ----------
    answer : 생성된 답변 텍스트
    candidates : 모델 문맥에 넣은 근거(RankedCandidate 등 `metadata`/`content` 보유)
    citations : `candidates`와 같은 순서의 Citation(선택) — 서지 정보 보강용
    """
    result = CitationCheckResult()
    if not answer or not candidates:
        return result

    cits = list(citations) if citations else []
    cand_names = [
        _candidate_name_tokens(c, cits[i] if i < len(cits) else None)
        for i, c in enumerate(candidates)
    ]
    cand_text_words = [_words(str(_get(c, "content") or "")) for c in candidates]
    cand_text_raw = [str(_get(c, "content") or "") for c in candidates]

    last_end = 0
    for m in _CITATION_RE.finditer(answer):
        result.citations_found += 1
        label = m.group(1)
        citation_text = m.group(0)
        sentence = _sentence_before(answer, m.start(), last_end)
        last_end = m.end()

        label_tokens = _name_tokens(label)
        # 한국어로 옮긴 라벨 등 라틴 토큰이 2개 미만이면 서지 대조가 불가능하다 → 건너뜀
        matched: list[int] = []
        if len(label_tokens) >= 2:
            for i, names in enumerate(cand_names):
                if names and len(label_tokens & names) / len(label_tokens) >= SOURCE_MATCH_MIN_OVERLAP:
                    matched.append(i)
            if not matched:
                result.issues.append(
                    CitationIssue(KIND_SOURCE_NOT_RETRIEVED, citation_text, sentence)
                )
                continue  # 어떤 근거에도 연결되지 않으므로 토큰 대조는 무의미

        if not sentence:
            continue
        # 라벨에 이미 들어 있는 토큰은 주장 검증에서 제외
        label_words = _words(label)
        numbers = [n for n in _NUMBER.findall(sentence) if n not in label_words]
        latin = sorted(
            {
                w.lower().strip("'’-")
                for w in _LATIN_WORD.findall(sentence)
                if not _present(w, label_words) and w.lower().strip("'’-") not in _STOPWORDS
            }
        )
        if not numbers and not latin:
            continue  # 검증 가능한 토큰이 없음(예: 한국어로만 쓴 주장)

        pool = matched if matched else list(range(len(candidates)))
        pool_words = set().union(*(cand_text_words[i] for i in pool)) if pool else set()
        pool_raw = "\n".join(cand_text_raw[i] for i in pool)
        all_words = set().union(*cand_text_words) if cand_text_words else set()
        all_raw = "\n".join(cand_text_raw)

        missing_nums = [n for n in numbers if not re.search(rf"(?<!\d){n}(?!\d)", pool_raw)]
        missing_latin = [w for w in latin if not _present(w, pool_words)]

        flagged_nums = missing_nums
        flagged_latin = missing_latin if len(missing_latin) >= MIN_MISSING_LATIN_TOKENS else []
        missing = flagged_nums + flagged_latin
        if not missing:
            continue

        # 인용된 자료에는 없지만 다른 검색 근거에는 있는지 구분
        in_others = [
            t for t in missing
            if (re.search(rf"(?<!\d){t}(?!\d)", all_raw) if t.isdigit() else _present(t, all_words))
        ]
        kind = KIND_TOKEN_OTHER_SOURCE if len(in_others) == len(missing) else KIND_TOKEN_UNSUPPORTED
        result.issues.append(
            CitationIssue(kind, citation_text, sentence, tokens=tuple(missing))
        )

    return result


def describe_issue(issue: CitationIssue) -> str:
    """UI에 표시할 한 줄 안내. 단정하지 않고 '확인하지 못했다'로 쓴다."""
    tokens = ", ".join(f"'{t}'" for t in issue.tokens)
    if issue.kind == KIND_SOURCE_NOT_RETRIEVED:
        return (
            f"{issue.citation_text} — 이 출처는 이번에 검색된 자료 목록에서 찾지 못했습니다. "
            "자료에 없는 출처일 수 있으니 확인하세요."
        )
    if issue.kind == KIND_TOKEN_OTHER_SOURCE:
        return (
            f"{issue.citation_text} — 문장의 {tokens}이(가) 인용된 자료가 아니라 "
            "다른 검색 결과에서 확인됩니다. 인용 위치가 다를 수 있습니다."
        )
    return (
        f"{issue.citation_text} — 문장의 {tokens}을(를) 인용된 자료에서 확인하지 못했습니다. "
        "자료가 아니라 모델의 일반 지식일 수 있습니다."
    )


def issue_messages(result: CitationCheckResult | None) -> list[str]:
    """CitationCheckResult → 표시용 문구 목록(이슈가 없으면 빈 리스트)."""
    if result is None:
        return []
    return [describe_issue(i) for i in result.issues]

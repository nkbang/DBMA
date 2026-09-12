"""규칙 기반 한국어 답변 완결성 판정 (요구 4).

[PM 정렬 감사 선결 #4 / 옵션 A — Stage 5-1]
설계: docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md §4.4.6 / §5.1
Task Order: §5-1

LLM 없이 값싸게 도는 규칙 판정기다. rag_judge의 fluency/completeness
지표(ADR-010 Phase 2)는 별도 설계 초안
(docs/NAE_ANSWER_QUALITY_METRIC_DRAFT_001.md)으로 남기고 여기서 구현하지
않는다.

**생성을 차단하지 않는다** — 결과는 GenerationResult 부가·UI 캡션용이다
(feedback_avoid_risky_uncertain_design: 검증 안 된 신호 위에 처리 경로를
얹지 않는다).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 한국어 종결 어미(경어체 위주 + 평서 종결). 문장이 이걸로 끝나야 "완결".
_SENTENCE_END_RE = re.compile(
    r"(?:습니다|습니까|합니다|입니다|됩니다|십니다|"
    r"세요|십시오|해요|에요|예요|"
    r"[다요죠까](?:\.)?|[.!?])[\"'”’)\]]*\s*$"
)
# 비-한글/라틴/숫자/일반기호 (CJK 한자·가나·태국어 등) — 오염 문자.
# core/generation.py::_SCRIPT_CONTAMINATION_RE와 동일 범위(검증된 패턴):
# Hiragana/Katakana(U+3040-30FF), CJK(U+4E00-9FFF), Thai(U+0E00-0E7F).
_FOREIGN_SCRIPT_RE = re.compile(r"[぀-ヿ一-鿿฀-๿]")
# 40자 초과 연속 라틴(영어 원문 미번역 스팬)
_LONG_LATIN_RE = re.compile(r"[A-Za-z][A-Za-z ,;:'\"()\-]{40,}")
# 한국어 경어체 종결(어간 무관): ".니다"/".니까" 계열 + 세요/십시오.
_HONORIFIC_RE = re.compile(r".니다|.니까|세요|십시오|하십")
# 평서체 종결('~다.') — 단, 경어체 '~니다'는 문장 단위로 별도 제외.
_PLAIN_ENDING_RE = re.compile(r"(?<!니)(?<!요)[가-힣]다\.?[\"'”’)\]]*\s*$")


@dataclass
class CompletenessResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    sentence_count: int = 0
    paragraph_count: int = 0

    def as_caption(self) -> str:
        if self.passed:
            return ""
        return "답변 완결성 점검: " + " / ".join(self.violations)


def _split_sentences(text: str) -> list[str]:
    # 마침표·물음표·느낌표 뒤 공백/개행에서 분리(약식). 종결 어미 검사가
    # 본체이므로 문장 분리는 러프해도 된다.
    raw = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [s.strip() for s in raw if s.strip()]


def evaluate_completeness(answer: str) -> CompletenessResult:
    """답변 텍스트 → CompletenessResult.

    체크 (TO §5-1):
      (a) 모든 문장이 한국어 완결 어미로 종료
      (b) 40자 초과 연속 라틴 스팬 0
      (c) 비-한글/라틴 문자(CJK·태국어 등) 0
      (d) 경어체 일관 (습니다/입니다 계열)
      (e) 최소 2개 문단
    """
    violations: list[str] = []
    text = (answer or "").strip()

    if not text:
        return CompletenessResult(passed=False, violations=["빈 답변"], sentence_count=0, paragraph_count=0)

    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    sentences = _split_sentences(text)

    # (c) 오염 문자
    foreign = _FOREIGN_SCRIPT_RE.findall(text)
    if foreign:
        sample = "".join(dict.fromkeys(foreign))[:8]
        violations.append(f"비한국어 문자 혼입({len(foreign)}자: {sample})")

    # (b) 미번역 영어 스팬
    latin_spans = _LONG_LATIN_RE.findall(text)
    if latin_spans:
        violations.append(f"40자 초과 영어 원문 스팬 {len(latin_spans)}건")

    # (a) 문장 종결
    unfinished = [s for s in sentences if not _SENTENCE_END_RE.search(s)]
    if unfinished:
        violations.append(f"완결 어미 없는 문장 {len(unfinished)}개")

    # (d) 경어체 일관 — 평서 종결('~다.')이 섞이면 flag (인용문 제외 어려우니 경고 수준)
    has_honorific = bool(_HONORIFIC_RE.search(text))
    plain_endings = [s for s in sentences if _PLAIN_ENDING_RE.search(s) and not _HONORIFIC_RE.search(s)]
    if has_honorific and plain_endings:
        violations.append(f"경어체·평서체 혼용({len(plain_endings)}개 문장)")
    elif not has_honorific and sentences:
        violations.append("경어체 종결이 없음")

    # (e) 최소 2문단
    if len(paragraphs) < 2:
        violations.append(f"문단 수 {len(paragraphs)}개(2개 미만)")

    return CompletenessResult(
        passed=not violations,
        violations=violations,
        sentence_count=len(sentences),
        paragraph_count=len(paragraphs),
    )

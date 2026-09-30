"""출처 표시 품질 보조 함수 (EUAT-001 Issue 6, FU-005 결과 반영).

Streamlit에 의존하지 않는 순수 함수만 둔다 — UI 호출부는 얇게 유지하고 이
함수들을 단위 테스트한다.
"""
from __future__ import annotations

from typing import Any

# 하이브리드 검색(BM25 + 신학 + 성구 → RRF, `core/rrf.py`)의 final_score는
# 순위 기반 값이다. k=60, 랭킹 3개일 때 이론상 최댓값이 약 3/61 ≈ 0.049라서
# 0..1 유사도로 해석하면 안 된다 — 별점 `round(score * 5)`가 항상 0이 되어
# 모든 출처가 "☆☆☆☆☆ 관련성"(관련 없음처럼 보임)으로 표시됐다(EUAT-001).
# 실제 벡터 유사도(무관 질의 ≈ 0.37~0.41)는 이 값보다 훨씬 크므로 임계값으로
# 두 척도를 구분할 수 있다. 정확한 경계가 아니라 "RRF 척도 여부" 판별용 휴리스틱이다.
RRF_SCORE_CEILING = 0.06

_MAX_HEADING_LEN = 80
_MIN_ALNUM_RATIO = 0.5
_SENTENCE_END = (".", "?", "!", ";", ",")


def is_comparable_relevance(score: float | None) -> bool:
    """score를 0..1 유사도 별점으로 표시해도 되는지 판단한다.

    None이거나 RRF 척도(<= RRF_SCORE_CEILING)이면 False — 별점을 숨긴다.
    """
    if score is None:
        return False
    try:
        return float(score) > RRF_SCORE_CEILING
    except (TypeError, ValueError):
        return False


def usable_heading_label(label: str | None) -> str | None:
    """헤딩으로 쓸 수 있는 라벨이면 그대로, 아니면 None을 반환한다.

    다음은 헤딩이 아니라 본문 조각이 제목 자리에 들어온 경우로 보고 버린다.
    - 공백뿐이거나 매우 짧음
    - 문자(영숫자·한글) 비율이 낮은 깨진 청크("• • ••»", "• f t I «")
    - 너무 긺(80자 초과)
    - 문장 부호로 끝나는 3단어 이상의 문장 조각
    버려지면 호출부가 파일명 같은 안정적인 라벨로 대체한다.
    """
    if label is None:
        return None
    text = label.strip()
    if len(text) < 3 or len(text) > _MAX_HEADING_LEN:
        return None
    alnum = sum(1 for ch in text if ch.isalnum())
    if alnum / len(text) < _MIN_ALNUM_RATIO:
        return None
    if text.endswith(_SENTENCE_END) and len(text.split()) >= 3:
        return None
    return text


def claim_guard_message(result: Any) -> str | None:
    """ClaimGuard 결과에서 표시할 문구를 고른다. 표시할 내용이 없으면 None.

    `suggested_wording`도 `reason`도 없으면 종전에는 빈 "주장 검증:" 라벨이
    그대로 출력됐다. 그런 경우 탐지된 표현(matched_terms)이 있으면 그것만
    보여주고, 그것도 없으면 아무것도 표시하지 않는다.
    """
    if result is None:
        return None
    wording = (getattr(result, "suggested_wording", None) or "").strip()
    if wording:
        return wording
    reason = (getattr(result, "reason", None) or "").strip()
    if reason:
        return reason
    terms = [t for t in (getattr(result, "matched_terms", None) or []) if t]
    if terms:
        return "절대적·단정적 표현이 감지되었습니다: " + ", ".join(terms)
    return None


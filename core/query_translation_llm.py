"""core/query_translation.py — 한국어 질의를 영어로 번역하는 전처리(검색 전용).

## 왜 필요한가 (2026-09-25 실측)

배포 기준선 코퍼스가 전량 영문(archive.org 퍼블릭 도메인 — Spurgeon·Maclaren·
Whitefield·Broadus·Dargan·Keach·Hovey)인데 사용자는 한국어로 묻는다. Stage-1
후보 생성이 Tantivy 어휘 일치이므로 한국어 토큰과 영문 본문의 교집합이 0이고,
`HybridRetriever`에는 빈 결과 폴백이 없어 그대로 0건으로 끝난다.

실측(`docs/DBMA_P0_5_EVIDENCE_HOLD_ROOT_CAUSE_001.md`): P0-5 근거 0건 유보
17건 중 **16건이 후보 0건**이었고, 같은 내용이 영어 질의로는 정상 반환됐다.
즉 콘텐츠 부족이 아니라 질의 언어와 코퍼스 언어의 불일치다.

## 왜 "의미 검색 폴백"이 아니라 번역인가

처음 권고했던 "Stage-1이 0건이면 의미 검색으로 폴백"은 **기각됐다**. 기존
`RetrievalEngine` 경로도 후보 선정이 어휘 기반이고(STEP 3 semantic은 BM25
상위 후보만 재순위), 임베딩 캐시가 119,595건 중 100건(0.08%)뿐이라 실제로는
TF-IDF 폴백으로 떨어진다. 그 결과 "우울증 목회 돌봄" 질의에 예레미야의
웅변·강단의 흥망 같은 **무관한 구절이 vec=1.000으로** 반환됐다 — 0건보다 나쁜
동작이며, 근거 없는 내용을 내놓지 않는다는 프로젝트 원칙에 정면으로 어긋난다.

번역은 **어휘 일치를 실제로 성립시키는** 유일한 저비용 경로다. 검색 경로를
신설하지 않고 질의 문자열만 바꿔 기존 Stage-1에 다시 넣으므로 ADR-001
(One Retrieval Engine)에 저촉되지 않는다.

## 발동 조건 — 막다른 길에서만

모든 질의를 번역하지 않는다. **Stage-1이 0건을 반환했고 질의에 한글이 있을
때만** 호출된다. 이미 후보를 찾은 질의에는 LLM 지연이 전혀 추가되지 않고,
2026-09-18 역색인 전환으로 얻은 빠른 경로(0.95초)가 보존된다. 코퍼스에 한국어
자료가 늘면 발동 빈도는 자연히 줄어든다.

실패는 조용히 흡수한다 — 번역이 실패하면 원래의 0건 상태가 유지될 뿐이므로
**순손실이 없다**(0건보다 나빠질 수 없는 경로다).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 한글 음절·자모. 번역 발동 여부 판정에만 쓴다.
_HANGUL_RE = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")

# 번역은 무거운 신학 모델이 필요한 작업이 아니다 — DEFAULT_GEN_MODEL
# (my-theology-bot-v2, 42GB)을 쓰면 검색 지연이 불필요하게 커진다.
_DEFAULT_TRANSLATION_MODEL = "llama3.1:8b"

# 번역문이 이 길이를 넘으면 모델이 번역이 아니라 설명·답변을 한 것으로 보고
# 버린다(질의는 보통 한 문장이다). 원문 길이에 비례한 상한이 아니라 절대
# 상한을 쓰는 이유: 짧은 질의에 장문 해설을 붙이는 실패가 실제 관측되는 양상.
_MAX_TRANSLATION_CHARS = 400

_PROMPT = """Translate the following Korean search query into English.

Rules:
- Output ONLY the translated query. No explanation, no quotes, no prefix.
- Keep Bible references in standard English form (예: 로마서 8:1-4 -> Romans 8:1-4).
- Preserve theological terms with their standard English equivalents.
- Do not answer the question. Translate it.

Korean query:
{query}"""


def contains_hangul(text: str) -> bool:
    """질의에 한글이 있는지. 번역 발동 판정 전용."""
    return bool(_HANGUL_RE.search(text or ""))


def is_enabled() -> bool:
    """`QUERY_TRANSLATION_FALLBACK=false`로 끌 수 있다. 기본 활성 —
    끄면 한국어 질의가 다시 0건으로 돌아간다(현재 재현율 0%)."""
    return os.environ.get("QUERY_TRANSLATION_FALLBACK", "true").strip().lower() == "true"


def _model() -> str:
    return os.environ.get("QUERY_TRANSLATION_MODEL", _DEFAULT_TRANSLATION_MODEL).strip()


def _clean(raw: str) -> Optional[str]:
    """모델 출력에서 번역문만 남긴다. 신뢰할 수 없으면 None."""
    if not raw:
        return None
    text = raw.strip()

    # 흔한 군더더기 제거: 앞머리 라벨, 감싼 인용부호.
    text = re.sub(r"^(?:translation|translated query|english)\s*[:：]\s*", "", text, flags=re.I)
    text = text.strip().strip('"').strip("'").strip()

    # 여러 줄로 답하면 첫 줄만 쓴다(설명이 뒤따르는 실패 양상).
    text = text.splitlines()[0].strip() if text else ""

    if not text or len(text) > _MAX_TRANSLATION_CHARS:
        return None
    # 번역 결과에 한글이 그대로 남아 있으면 번역이 아니다.
    if contains_hangul(text):
        return None
    # 영문자가 하나도 없으면 쓸 수 없다.
    if not re.search(r"[A-Za-z]", text):
        return None
    return text


def translate_to_english(query: str) -> Optional[str]:
    """한국어 질의를 영어로 번역한다. 실패·비활성·불필요 시 None.

    절대 예외를 올리지 않는다 — 이 함수는 이미 0건인 막다른 길에서만 호출되고,
    실패하면 그 0건이 유지될 뿐이다. 검색 요청 전체를 깨뜨려서는 안 된다.
    """
    if not is_enabled():
        return None
    if not query or not contains_hangul(query):
        return None

    try:
        import ollama

        result = ollama.generate(
            model=_model(),
            prompt=_PROMPT.format(query=query),
            options={"temperature": 0.0},
        )
        translated = _clean(result.get("response", ""))
    except Exception as e:  # 모델 부재·데몬 정지·타임아웃 전부 여기로
        logger.warning("[query_translation] 번역 실패, 원래 결과 유지: %s", e)
        return None

    if translated:
        logger.info("[query_translation] %r -> %r", query[:60], translated[:60])
    return translated


# 현재 서재가 사실상 비한국어일 때 0건 안내에 덧붙이는 고지.
# 근거: 사용자가 "근거 없음"을 "이 주제가 서재에 없다"로 읽으면 오해가 된다 —
# 실제로는 자료가 있는데 언어가 달라 검색이 실패한 사례가 P0-5 유보 17건 중
# 16건이었다(docs/DBMA_P0_5_EVIDENCE_HOLD_ROOT_CAUSE_001.md). 번역 전처리가
# 들어간 뒤에도 0건이 남는 경우가 있으므로, 원인을 밝혀 두는 것이 정직하다.
_CORPUS_LANGUAGE_NOTICE = (
    "\n\n참고: 현재 서재는 영문 자료로 구성되어 있습니다. 한국어 질문은 검색 시 "
    "자동으로 영어로 번역해 찾지만, 번역된 표현이 원문의 어휘와 어긋나면 근거를 "
    "찾지 못할 수 있습니다. 영어 키워드로 다시 시도하면 찾아지는 경우가 있습니다."
)


def corpus_language_notice(tsus) -> str:
    """서재의 한국어 비중이 낮으면 언어 고지 문구를, 아니면 빈 문자열을 반환한다.

    UI의 0건 안내 뒤에 덧붙이는 용도. 한국어 자료가 쌓이면 자동으로 사라진다.
    실패해도 안내 자체를 깨뜨리지 않도록 예외를 흡수한다.
    """
    try:
        items = list(tsus or [])
        if not items:
            return ""
        ko = sum(1 for t in items if (t.get("language") or "") == "ko")
        if ko / len(items) >= 0.20:
            return ""
    except Exception:  # noqa: BLE001 — 안내 문구가 페이지를 깨뜨리면 안 된다
        return ""
    return _CORPUS_LANGUAGE_NOTICE

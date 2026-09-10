"""DBMA-SIL — approved doctrine vocabulary (ADR-009 Decision, 2026-07-22).

Confirmed by the user (목회자 본인, 개혁파 침례교/Reformed Baptist —
1689 London Baptist Confession 전통, 신자세례·회중교회론) as a closed
vocabulary to start with (per ADR-009 §Decision-2: "필요시 확장").
This is a theological content decision outside CUE/C1's authority —
do not edit these lists without a fresh user confirmation; extend the
ADR instead of silently growing the vocabulary here.
"""

from __future__ import annotations

# 표준 조직신학 범주 — TSU 레코드의 doctrine_category 필드가 쓸 값.
DOCTRINE_CATEGORY: list[str] = [
    "Scripture",
    "Trinity",
    "Christology",
    "Anthropology",
    "Soteriology",
    "Ecclesiology",
    "Eschatology",
]

# 개혁파 침례교(1689 런던신앙고백 계열) 강조점 — TSU 레코드의
# baptist_theme 필드가 쓸 값. 5 Solas + TULIP 핵심(particular redemption
# 중심) + 침례교 고유 교회론/언약신학.
BAPTIST_THEME: list[str] = [
    "SolaScriptura",
    "SolaFide",
    "SolaGratia",
    "SolusChristus",
    "SoliDeoGloria",
    "DivineSovereigntyInSalvation",
    "ParticularRedemption",
    "BelieversBaptism",
    "RegenerateChurchMembership",
    "CovenantTheology1689",
]


# ============================================================
# 교단 프로파일 서술 (ADR-009 Amendment A, 2026-09-10)
# ============================================================
#
# 위 두 목록은 "무엇을 태그할 것인가"를 정하는 닫힌 어휘다. 아래 상수는
# 그 어휘가 전제하는 **전통 자체**를 한 문장으로 적은 것으로, 답변 생성
# 프롬프트가 모델에게 사용자의 신학적 위치를 알려줄 때 쓴다.
#
# 문구는 새로 지어낸 것이 아니라 ADR-009 §Decision(2026-07-22, 사용자
# 직접 승인)의 "신학적 전통" 항목을 그대로 옮긴 것이다 — 신학적 내용
# 판단은 CUE/C1의 권한 밖이므로, 승인된 ADR의 표현을 벗어나지 않는다.
# 이 문자열을 고치는 것은 위 목록을 고치는 것과 같은 등급의 변경이며,
# 새로운 사용자 확인 없이 수정해서는 안 된다.
DENOMINATION_PROFILE: str = (
    "개혁파 침례교(Reformed Baptist) — 1689 런던신앙고백 계열, "
    "신자세례·회중교회론"
)

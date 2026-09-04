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

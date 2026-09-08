# Fuller Vol.01 단계적(Tiered) 검수 설계 v1 — CUE 초안 (HQ 승인 대기)

- 작성: CUE
- 일자: 2026-09-08
- 상태: **APPROVED — HQ 승인 2026-09-08** (전건 Q1–Q3 (+Q4 조건부) / Tier 정의 P1 176·P2 3,467·+CIT 26 그대로 / P1 처리 방식은 Phase 2 Task Order에서 결정)
- 배경: HQ가 O-3 Option B(단계적 검수) 채택 확정(2026-09-08). 본 문서는
  tier **정의**를 확정하기 위한 설계.
- 근거: `NAE_FULLER_VOL01_PILOT_PHASE1_O2O3_CUE_VERIFICATION_001.md` §3,
  `NAE_TSU_4107_EXPANSION_HUMAN_REVIEW_DESIGN_001.md` §3.3

---

## 0. 검수 질문 세트 (2026-09-08 정정·HQ 승인)

이 시스템(`decision_gate.py`)의 표준 검수는 **Q1–Q3**. Q4는 전건 질문이
아니라 flag 부착 항목 전용 경고 항목이다.

| 질문 | 내용 | 적용 |
|---|---|---|
| Q1 Claim Fidelity | 재진술이 원문 의미를 정확히 표현하는가 | **전건** (A/R/C) |
| Q2 Theological Accuracy | 신학적 왜곡·과장 없는가 | **전건** (A/R/C) |
| Q3 Context Sufficiency | 제공된 맥락이 판단에 충분한가 | **전건** (A/R/C) |
| Q4 Special Warning | 맥락 손실 등 flag 어휘 | **flag 있는 항목만** (검토자 판단 추가) |
| +CIT | citation 정확성 확인 | **citations 보유 26건**에 1단계 추가 |

Dagg/Hiscox 776건 선례도 Q1–Q3. C1 생성 배치 파일(`fuller_v01_batch_*`)도
Q1–Q3 (`flags:[]`) — 질문 세트 재생성 불요.

---

## 1. 설계 원칙

1. **검수 강도는 전 건 동일 (Q1–Q3 표준 + flag 시 Q4).**
   C1이 제안한 "confidence 0.9 → Q4 생략"은 채택하지 않는다.
   `confidence`는 LLM 추출값 2단계(0.8/0.9)뿐이고 검수 triage 신호로서
   신뢰도가 검증된 바 없다 — 미검증 신호에 품질을 위임하지 않는다
   ([[feedback_avoid_risky_uncertain_design]]).
2. **단계(tier)는 강도 차등이 아니라 처리 순서(priority).**
   조기에 침례교 정체성 커버리지를 확보하고, 문제 소지 큰 항목을 먼저 본다.
3. **citations 항목은 별도 tier가 아니라 "추가 확인 단계".**

---

## 2. Tier 정의 (= 검수 순서)

| Tier | 기준 | 건수 | 검수 방식 |
|---|---|---|---|
| **P1** | doctrine ∈ {Baptism, Confession, Ecclesiology} **또는** claim 길이 <20자 | **176** (정체성 109 + short 68 − 중복 1) | Q1–Q3 (+Q4 조건부) 전체. 최우선. short-claim은 "공허 재진술 여부" 집중 |
| **P2** | 그 외 전건 | **3,467** | Q1–Q3 (+Q4 조건부) 전체 |
| **+CIT** | citations 보유 (P1·P2 무관) | 26 | 해당 배치 검수 시 citation 정확성 확인 1단계 **추가** |
| 합계 | | **3,643** | |

- P1 176건 = `fuller_v01_batch_*` 중 해당 tsu_id를 앞으로 재배열해
  먼저 처리하거나, P1 전용 논리 배치로 묶어 처리 (구현은 Phase 2에서).
- 배치 파일(37개, 100건 단위)은 이미 생성됨 — tier는 그 위의 **처리
  순서 레이어**이지 배치 재생성이 아니다.

---

## 3. 검수 흐름

```
1. P1 (176건) 먼저 — Baptism/Confession/Ecclesiology + short claim
   → 정체성 taxonomy 조기 확보, 공허 claim 조기 배제
2. P2 (3,467건) — 배치 순서(batch_0001..0037)대로
3. 각 배치에서 citations 보유 TSU(26건)는 citation 확인 1단계 추가
4. 판정: approved / rejected / needs_context (decision_gate 기존 스키마)
5. approved → review_status="verified" 승격 대상
```

## 4. Soteriology 편중 대응 (참고)

- Soteriology 2,314건(63.5%) 은 대부분 P2. 편중 자체는 원문(복음 제시
  논쟁, Fullerism) 성격상 정상.
- P2 내에서 Soteriology를 뒤로 몰거나 앞으로 몰지는 검토자(David) 재량.
  설계상 강제하지 않음.

## 5. 예상 소요

- 전 건 Q1–Q3 (+Q4 조건부)이므로 `_003` 추정 유지: **약 14일 캘린더(1인, 잠정)**
  — Dagg/Hiscox 776건 ≈ 3일 × 4.7배. P1 우선 처리해도 총량 불변.
- 검토자 David 실측 페이스(첫 2~3배치) 후 재산정.

## 6. HQ 승인 요청 항목

- [ ] §1 원칙: 전 건 Q1–Q3 (+Q4 조건부) (confidence 기반 강도 축소 불채택) — 승인?
- [ ] §2 Tier 정의 (P1 176 / P2 3,467 / +CIT 26) — 승인?
- [ ] P1 우선 처리 방식(재배열 vs 전용 배치) — Phase 2 Task Order에서 결정 위임?

승인 시 CUE가 Phase 2 Task Order(P1 배치 구성 + 검수 진행 절차) 발급.

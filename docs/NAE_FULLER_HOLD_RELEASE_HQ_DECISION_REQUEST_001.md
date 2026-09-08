# HQ Decision Request — Fuller Vol.01–08 Processing HOLD 해제 여부

- 발신: CUE (Architecture / Governance)
- 수신: HQ (David)
- 일자: 2026-09-08
- 유형: GOVERNANCE DECISION REQUEST (CUE는 결정하지 않음 — HQ 결정 사항)
- 근거:
  - `docs/NAE_FULLER_CORPUS_STATUS_CHECK_001.md` (현황 실측, 2026-09-07)
  - `docs/agents/cue/CUE-FULLER-ADMISSION-READINESS-PACKAGE.md` (Processing = HOLD 선언)
  - ADR-030 v2.1 §11 (Human Eligibility Governance), §14 (Production Safety), §16 (Scale Protection)

---

## 1. 결정 요청 사항

> **Fuller Vol.01–08의 Processing HOLD를 해제하고 ADR-030 TSU track 처리를
> 시작할 것인가?**

선택지: **A** 전체 해제 / **B** Vol.01만 해제(파일럿) / **C** HOLD 유지

---

## 2. 현재 상태 (1줄 요약)

| 단계 | Vol.01 | Vol.02–08 |
|---|---|---|
| RAW·등록·Admission | ✅ 완료 (ADMITTED 2026-08-29, `6b77df6`) | ✅ 완료 |
| 추출·정제 (canonical) | ✅ 완료 | ✅ 완료 (8/8) |
| 청킹 (TSU 생성) | ⚠️ 3,643건 생성, 전량 `generated`(미검수) | ❌ 미생성 |
| 검수 / 임베딩 / 색인 | ❌ | ❌ |
| `nae_tsu_v1` 내 Fuller 벡터 | **0** | **0** |

- 프로덕션 baseline: Dagg 2,958 + Hiscox 361 = **3,319 INDEXED, FROZEN**

---

## 3. HOLD 해제가 여는 작업

1. Vol.02–08 TSU 생성 (7권)
2. 8권 전체 human review — Vol.01 기존 3,643건 포함
3. `review_status == verified` TSU 임베딩 → `nae_tsu_v1` 색인
4. Retrieval eligibility 게이트(`config.yaml modules.nae_pd`) 반영

---

## 4. 비용 / 리스크

| 항목 | 내용 |
|---|---|
| **검수 규모** | Vol.01 = 3,643 TSU. canonical 크기 비례 추정 시 8권 합계 **약 27,000–30,000 TSU** 사람 검수 필요 (정확치는 C1 preflight에서 산출) |
| **검수 병목** | 과거 NAE 776건 human review도 Pilot 승인 전까지 미착수 상태 — 검수 인력·일정이 실질 제약 |
| **Baseline 보호** | 3,319 production TSU는 절대 재처리·재색인 금지 (ADR-030 §11.4, §14) |
| **Qdrant 격리** | ADR-013 — Fuller는 `nae_tsu_v1`에만, 다른 컬렉션 무접촉 |
| **Scale 보호** | ADR-030 §16 — 대량 upsert는 batch + 중간 검증 |

---

## 5. 선택지 비교

| | A. 전체 해제 | B. Vol.01 파일럿 | C. HOLD 유지 |
|---|---|---|---|
| 처리 범위 | 8권 즉시 | Vol.01만 검수→임베딩→색인, 02–08은 HOLD | 없음 |
| 검수 부담 | ~27k–30k TSU 한꺼번에 | ~3.6k TSU | 0 |
| 리스크 | 검수 미완 상태로 파이프라인 장기 점유 | 낮음, 전 구간 1회 검증 | 없음 (진척도 없음) |
| 다음 판단 근거 | — | Vol.01 실측(품질·시간·비용)으로 02–08 결정 | 재검토 시점 미정 |

## 6. CUE 권고

**선택지 B (Vol.01 파일럿)**.
- ADR-030 TSU track 전 구간(TSU 생성분 검수 → 임베딩 → 색인)을 Vol.01로 1회 완주해 실측치 확보.
- baseline 3,319에 영향 없이 최소 단위로 검증 후 02–08 확대 여부를 데이터로 결정.
- "작은 단위 수정·즉시 검증" 원칙 부합.

---

## 7. HQ 결정 기록란

```
결정 (A / B / C): B — Vol.01 파일럿
decided_by: HQ (David)
date: 2026-09-08
조건 / 제약:
  - Vol.01만 TSU track 전 구간 진행. Vol.02–08 은 HOLD 유지.
  - baseline 3,319 production TSU FROZEN — 무접촉.
  - --apply(임베딩/색인)는 dry-run 검토 + HQ go 이후에만.
  - Vol.01 실측(품질·시간·비용) 확보 후 02–08 확대 여부 재결정.
검수 담당 · 일정:
  - 검토자 = David (HQ 본인), 단독. (2026-09-08 확정)
  - 검수 강도 = 단계적(tiered, O-3 Option B). 전량 동일강도 아님. (2026-09-08 확정)
  - 착수 일정 = TBD — HQ가 별도 통보.
```

→ 실행: `docs/NAE_FULLER_VOL01_PILOT_EXEC_TASK_ORDER_C1_001.md` (CUE 발급, 2026-09-08)

---

## 8. 결정 이후 절차

- **승인 시**: CUE가 실행 Task Order 발급 (ADR-030 §11.2 순서 / §16 batch 규정 반영).
  필요 시 C1 Review 트리거 여부 판단(대량 embedding = Scale event).
- **결정과 무관하게 즉시 진행**: C1 preflight 검증 (read-only, HOLD 무위반) —
  `docs/NAE_FULLER_PREFLIGHT_TASK_ORDER_C1_001.md`. 그 결과가 본 결정의 §4 추정치를
  실측치로 대체한다.

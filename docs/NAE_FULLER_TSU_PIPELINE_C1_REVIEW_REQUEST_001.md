# C1 Review 요청 — Fuller TSU Pipeline 진입 (P-4)

- 요청자: CUE
- 일자: 2026-09-08
- 유형: **C1 Review** (독립 검토 — 구현 아님)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점: TSU Pipeline 진입 직전"
- 우산 계획: `NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` §3 P-4

---

## 1. 요청 배경

Fuller Vol.01–08 은 2026-08-29 ADMITTED, PROCESSING HOLD. HQ 결정 B
(2026-09-08)로 **Vol.01 한정** 처리 승인. Vol.01 검수 배치 준비 완료,
David 검수 착수 직전. 이 시점이 ADR-030 "TSU Pipeline 진입 직전" C1
Review 트리거에 해당.

---

## 2. 검토 대상 산출물

| # | 문서/코드 | 커밋 |
|---|---|---|
| A | `NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` (우산 계획, §9 정합 갱신 포함) | `21a6f29`+ |
| B | `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` (APPROVED) | `177e981` |
| C | `NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` | `177e981` |
| D | `scripts/nae_fuller_vol01_review_batches.py` + `NAE/review/human/requests/fuller_v01_batch_0001..0037_requests.json` + `fuller_v01_MANIFEST.json` | `177e981` |
| E | `NAE_FULLER_CANONICAL_VERIFICATION_001.md` (F1 산출물 — 완료 시 추가) | pending |
| F | Preflight/Phase1/Phase2 CUE 검증 3건 | `177e981` |

---

## 3. C1 검토 질문

1. **거버넌스 권한**: HQ 결정 B (Vol.01 한정 HOLD 해제)만으로 F3–F5
   (검수→임베딩→`nae_tsu_v1` 색인) 진행이 정당한가, 아니면 ADR-030
   Amendment (P-2) 가 선행돼야 하는가?
2. **ADR 정합**: 파일럿 설계·배치가 ADR-030(§4 TSU Track, §11 4단계,
   §12 N-9) / ADR-029(Pipeline Lock) / ADR-024(retrieval gate) /
   ADR-013(Qdrant isolation) 중 위반하는 것이 있는가?
3. **검수 방식**: 전용 드라이버(`batch_manager.py` 미수정) + tiered(P1/P2,
   강도 균일 Q1–Q3) 방식이 Dagg/Hiscox 선례 대비 audit trail·정합성에서
   문제 없는가?
4. **baseline 보호**: F5 additive upsert 설계가 3,319 point 무접촉을
   구조적으로 보장하는가?
5. **provenance**: `page_count=1` / Vol.03·07 scripture=0 / uncalibrated
   confidence 조건에서 verified→embed→retrieval 노출이 `historical_witness`
   범위로 수용 가능한가? disclosure 로 충분한가?
6. **ADR-029 충돌**: Fuller 처리가 현재 진행 PHASE와 리소스·순서 충돌하는가?

---

## 4. 요청 형식

- 판정: GREEN / YELLOW(조건부) / RED
- 조건부·RED 시 구체 findings + 해소 방안
- 산출물: `docs/NAE_FULLER_TSU_PIPELINE_C1_REVIEW_RESULT_001.md`
- C1은 이 검토에서 **구현하지 않는다** (문서 검토 + 코드 read-only).

## 5. 게이트

- C1 Review GREEN + F1 GREEN → David 검수(F3 Vol.01) 착수 가능 (일정 = HQ).
- YELLOW/RED → 해소 후 재검토.

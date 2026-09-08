# Fuller Vol.01 검수 절차서 v1 (검토자: David)

- 작성: CUE / 2026-09-08
- 대상: `NAE/review/human/requests/fuller_v01_batch_0001..0038_requests.json` (3,643 TSU)
- 근거: `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` (APPROVED)

---

## 1. 순서

1. **P1 먼저** — `fuller_v01_batch_0001`, `_0002` (176건: 침례교 정체성 doctrine + 짧은 claim)
2. **P2** — `_0003` → `_0038` 순서 (3,467건)
3. 한 번에 열어두는 배치는 **최대 1개**(`MAX_PENDING_REVIEW=100` 준수). 배치를 끝내고 다음 배치.

## 2. 각 TSU에 답할 질문 (Q1–Q3, 값 = A / R / C)

| | 질문 | A(승인) | R(거부) | C(맥락부족) |
|---|---|---|---|---|
| Q1 | 재진술(claim)이 원문의 실제 의미를 정확히 표현하는가 | 정확 | 왜곡 | 판단 불가 |
| Q2 | claim이 신학적으로 왜곡·과장되지 않았는가 | 건전 | 왜곡/과장 | 판단 불가 |
| Q3 | 제공된 원문 맥락(앞/뒤 문장)이 판단에 충분한가 | 충분 | — | 불충분 |

- **Q4 (Special Warning)**: 원문 맥락 손실·타인 견해를 저자 입장으로 오인·인용 오류 등이
  보이면 flag 어휘로 추가 기록 (`CONTEXT_LOSS` 등). 없으면 생략.
- **+CIT**: `fuller_v01_MANIFEST.json::cit_check_tsu_ids` 의 26건은 `citations` 값이
  원문과 일치하는지 1단계 더 확인.

## 3. 판정 집계 (`decision_gate` 규칙)

- Q1–Q3 **전부 A** → `APPROVED` → `review_status="verified"` 승격 대상
- Q1–Q3 중 **하나라도 R** → `REJECTED` (승격 안 됨)
- R 없고 **C 있음** → `NEEDS_CONTEXT` (재큐잉 / 보류)

## 4. 결정 기록 위치

- `NAE/review/human/decisions/` 에 배치별 결정 파일 작성
  (형식: `decision_gate.py` `HumanDecisionRecord` — `{tsu_id, answers:{Q1,Q2,Q3[,Q4]}, final_decision}`)
- 배치 하나 완료 = 그 배치 tsu_id 전부 결정됨.

## 5. 완료 후

- CUE가 `decisions/` 를 읽어 `promote_batch` 로 `APPROVED` → `verified` 승격 (별도 Task Order).
- verified 건수 확정 → Phase 3(임베딩·`nae_tsu_v1` 색인).

## 6. 페이스 측정

- 첫 2~3배치 소요 시간을 기록 → 전체 일정(잠정 ~14일) 재산정.

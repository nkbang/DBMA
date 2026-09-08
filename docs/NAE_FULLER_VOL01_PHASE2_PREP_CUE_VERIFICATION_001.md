# CUE 독립 검증 — Fuller Vol.01 Phase 2 Prep (C1)

- 검증자: CUE / 2026-09-08
- 대상: `docs/NAE_FULLER_VOL01_PILOT_PHASE2_PREP_REPORT_C1_001.md` + 배치 산출물
- 재실측: `/Users/David/DBMA` @ `561de49`, venv `~/envs/dbma311`, read-only

---

## 판정: 🟢 PASS

C1이 Task Order의 "38 배치" 산술 오류를 정확히 잡아냈고(P1 2 + P2 35 = **37**),
결과물 전 항목이 CUE 재실측과 일치.

---

## 1. CUE 재실측 (전부 일치)

| 항목 | 값 | 확인 |
|---|---|---|
| repo | HEAD `561de49`, tracked 수정 0 | ✅ |
| 배치 파일 | `fuller_v01_batch_0001..0037` = **37개** | ✅ |
| 총 requests / unique tsu_id | 3,643 / 3,643 | ✅ |
| P1 배치(0001–0002) | 176건, non-P1 = **0** | ✅ |
| P2 배치(0003–0037) | 3,467건, P1 leak = **0** | ✅ |
| 독립 P1 산정(전 corpus) | 176 (doctrine∈{Baptism,Confession,Ecclesiology} ∨ claim<20자) | ✅ 일치 |
| 배치 크기 | 0001=100 / 0002=76 / 0003=100 / 0037=67 | ✅ (P1 순수 분리) |
| MANIFEST | total_tsu 3643, P1 176, P2 3467 | ✅ |
| `cit_check_tsu_ids` | 26개, 전부 배치에 존재, 독립 citations 집계와 **집합 일치** | ✅ |
| 기존 자산 | `git diff --stat NAE/review/human/` = empty (`batch_00*`·`pilot_*`·`decisions/` 무변경) | ✅ |
| 인프라 | `decision_gate.py`·`batch_manager.py`·`schema.py` 무수정 | ✅ |
| `--force` | CONFLICT시 STOP, `--force`로 기존 fuller 배치 삭제 후 재생성 (L119,190,199) | ✅ |

---

## 2. MINOR (비블로킹)

- **`generated_by` = `"NAE-TSU-4107-EXPANSION-001"`** (Task Order가 요청한
  `"NAE-FULLER-V01-PHASE2-P1FIRST"` 아님). 원인: `decision_gate.write_batch_requests()`
  가 값을 하드코딩, C1이 (지시대로) `decision_gate.py` 미수정. → provenance는
  `fuller_v01_MANIFEST.json` 이 담당. 수용.
- **`scripts/verify_fuller_phase2.py`** — Task Order 산출물 목록에 없는 검증
  헬퍼를 C1이 추가 생성(untracked, read-only). 무해하나 미선언. → 리포트에
  로직 반영 후 삭제하거나, 유지 시 명시. HQ 판단.
- Task Order의 "38" 표기는 CUE 산술 오류였음(P1 2 + P2 35 = 37). 문서 정정 완료.
  **C1 지적이 옳았다.**

---

## 3. 상태

- **Phase 2 준비 완료.** `fuller_v01_batch_0001..0037` + MANIFEST 검수 대기.
- P1(batch_0001–0002, 176건)부터 David 검수 착수 가능.
- 착수 = **HQ 일정 신호 대기**. 절차 = `NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md`.
- 검수 완료분 promote→verified = 별도 Task Order(Phase 2 종결) → Phase 3.

# Fuller Vol.01 검수 절차서 v1 (검토자: David)

- 작성: CUE / 2026-09-08 (rev. Q2-light 2026-09-08)
- 대상: `NAE/review/human/requests/fuller_v01_batch_0001..0037_requests.json` (3,643 TSU)
- 근거: `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` (APPROVED)
- 도구: `~/envs/dbma311/bin/python scripts/nae_fuller_review_recorder.py --batch N`

---

## 0. 이 corpus의 위험 프로파일 (HQ 판단 2026-09-08)

Fuller = Andrew Fuller, *The Works …* — **Particular Baptist(칼뱅주의 침례교)
정통 저자**. corpus가 교리적으로 이미 정렬되어 있어 **신학적 오류 위험(Q2)은
낮다.** 검수의 무게중심은 신학 판정이 아니라 **추출 충실도(Q1)·맥락(Q3)·
저자 귀속(Q4)** 에 있다.

| 질문 | 이 corpus 위험 | 검토 강도 |
|---|---|---|
| **Q1** Claim Fidelity | **높음** — LLM(`my-theology-bot-v2`) 오역·요약 왜곡, 1820s OCR 잡음, 목차/단편에서 뽑힌 claim. 신학과 무관한 추출 오류 | **정밀** |
| **Q2** Theological Accuracy | **낮음** — Baptist 정통 저자 | **빠른 패스** (아래 §2.1) |
| **Q3** Context Sufficiency | 중간 — 맥락 없이 뽑히면 오해 소지 (evidence 윈도로 완화됨) | 보통 |
| **Q4** Attribution warning | **주의** — Fuller는 논쟁서를 많이 씀. **반대자 견해를 저자 입장으로 오인**한 claim 가능 | flag 적극 |

---

## 1. 순서

1. **P1 먼저** — `fuller_v01_batch_0001`, `_0002` (176건: 침례교 정체성 doctrine + 짧은 claim)
2. **P2** — `_0003` → `_0037` 순서 (3,467건)
3. 한 번에 여는 배치는 **최대 1개**(`MAX_PENDING_REVIEW=100`). 배치 완료 후 다음.

## 2. 각 TSU 질문 (Q1–Q3, 값 = A / R / C)

| | 질문 | A | R | C |
|---|---|---|---|---|
| Q1 | 재진술(claim)이 원문의 실제 의미를 정확히 표현하는가 | 정확 | 왜곡·잘못 추출 | 판단 불가 |
| Q2 | claim이 신학적으로 왜곡·과장되지 않았는가 | 건전 | 왜곡/과장 | 판단 불가 |
| Q3 | 제공된 원문 맥락이 판단에 충분한가 | 충분 | — | 불충분 |

### 2.1 Q2 빠른 패스 (이 corpus 한정)

- **기본값 = A.** Fuller 텍스트에서 정확히 추출된 claim은 신학적으로 건전하다고 전제.
- **R로 표시하는 경우에만 멈춤**: claim이 침례교·개혁주의 정통이 **긍정할 수 없는**
  내용을 저자 주장으로 진술 (예: 유아세례 옹호를 Fuller 입장으로, 행위구원, 삼위일체 부정).
  → 이 경우 대개 **추출 오류(Q1=R)** 또는 **귀속 오류(Q4 flag)** 와 함께 나타남.
- Q2에 시간을 오래 쓰지 말 것. 판단이 서면 A, 이상하면 R + Q4 flag.

### 2.2 Q4 (Special Warning) — 이 corpus에서 특히

- `AMBIGUOUS` / `CONTEXT_LOSS`: claim이 Fuller가 **소개·반박하는 타인의 견해**인데
  저자 본인 주장처럼 읽힘. (Fuller의 논박 구조상 흔함)
- `SCRIPTURE_MISMATCH`: 인용 성구가 원문과 안 맞음 (성구 추출기 자체가 불완전 — [[B-1]])
- 없으면 생략.

### 2.3 +CIT

`fuller_v01_MANIFEST.json::cit_check_tsu_ids` 26건은 `citations` 값이 원문과
맞는지 1단계 더 확인.

## 3. 판정 집계 (`decision_gate` 규칙)

- Q1–Q3 **전부 A** → `APPROVED` → `verified` 승격 대상
- Q1–Q3 중 **하나라도 R** → `REJECTED`
- R 없고 **C 있음** → `CONDITIONAL` (보류/재큐)

recorder가 자동 도출하며, 필요 시 `A/C/R`로 override.

## 4. 결정 기록

- recorder가 `NAE/review/human/decisions/fuller_v01_batch_NNNN_decisions.json` 에
  매 건 즉시 기록 (schema = `decision_gate.HumanDecisionRecord`).
- 배치 완료 = 그 배치 tsu_id 전부 결정.
- 진행 확인: `--list`, `--batch N --stats`. 재검토: `--batch N --redo TSU-XXXX`.

## 5. 완료 후

- CUE가 `decisions/` 를 읽어 `promote_batch` 로 `APPROVED` → `verified` 승격 (별도 Task Order).
- verified 건수 확정 → F4 임베딩 → F5 `nae_tsu_v1` additive 색인 → F6 retrieval.

## 6. 페이스 측정

- 첫 2–3배치 소요를 기록. **Q2 빠른 패스** 적용 시 배치(100건)당 소요가 크게 줄어들 것으로 예상.
- 실측으로 전체 일정 재산정 (이전 잠정 ~14일은 전건 정밀 기준 — Q2-light로 단축 예상).

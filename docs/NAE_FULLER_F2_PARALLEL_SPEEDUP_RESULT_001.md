# Result — F2 병렬화 (max_workers + Ollama -np 2) : **폐기 (GATE FAIL)**

- 작성: CUE (2026-09-08)
- 근거 Task Order: `docs/NAE_FULLER_F2_PARALLEL_SPEEDUP_TASK_ORDER_001.md`
- 판정: **RED — 본 방안 폐기, 코드 revert, F2 현행(순차) 재시작**

---

## 1. 실행 요약

| Part | 상태 | 비고 |
|------|------|------|
| Part 1 병렬 claim 추출 구현 | 완료 (`372c3a7`) | ThreadPoolExecutor, id 할당은 메인 스레드 순차. 회귀 21 passed. |
| Part 2 Ollama `-np 2` | 완료 | `OLLAMA_NUM_PARALLEL=2`, `launchctl kickstart`, `llama-server ... -np 2` 확인. VRAM 여유 OK. |
| Part 3 측정 게이트 | **FAIL** | 아래 §2 |
| Part 4 C1 독립 검토 | 무의미(moot) | 게이트 미통과 → 검토 대상 없음 |
| Part 5 배포 | 취소 | |

---

## 2. 측정 게이트 (Part 3)

- 대상: `Fuller_Complete_Works_Vol03` canonical, 동일 200 candidate
- scratch tsu_root: `/private/tmp/f2_ab_scratch/{w1,w2}`, `checkpoint_every=50`

| 항목 | A (`--max-workers 1`) | B (`--max-workers 2`, `-np 2`) |
|------|------|------|
| elapsed | 2056.9s | 1661.4s |
| claims | 134 | 134 |
| llm_errors | 0 | 0 |
| id 연속·순서 | OK | OK |

- **speedup B/A = 1.24x** — 게이트 `≥ 1.50x` **미달**
- **결정성: A ≠ B** — 134건 중 **1건** 불일치 (`TSU-0000047`)
  - 불일치 필드: `claim`, `confidence` (같은 candidate·같은 프롬프트·temperature=0)
  - id·건수·doctrine·errors 는 전부 일치 → **구현 결함 아님**
  - 원인: llama.cpp 배치 추론 비결정성. `-np 2` 로 동시 요청이 한 배치에 묶이면
    부동소수점 reduction 순서가 배치 구성에 따라 달라져 temperature=0 에서도
    토큰이 갈릴 수 있음. `max_workers` 코드가 *언제* 호출하는지만 바꿨고
    *무엇을* 만드는지는 안 바꿨으나, 하위 추론 서버가 동시성에서 비결정적.

두 판정 기준(속도·결정성)을 **모두** 불충족.

---

## 3. 조치 (Task Order §3 / §6 "미달 → 폐기" 에 따라 사전승인 범위 내 실행)

1. `git revert 372c3a7` → `405c6b3` (builder/runner/test 원복). 회귀 21 passed. push 완료.
2. Ollama `-np 1` 복귀: `launchctl unsetenv OLLAMA_NUM_PARALLEL` + `launchctl kickstart -k gui/$UID/com.ollama.ollama`. `llama-server ... -np 1` 확인.
3. `/private/tmp/f2_ab_scratch/` 삭제. `tsu_id_state.json` = `{"next_id": 7766}` (벤치 전 상태 유지, 소비 없음).
4. F2 순차 재시작: `nohup bash scripts/run_fuller_f2.sh > f2_run.log 2>&1 &` — **스크립트 무수정**, `--max-workers 1` 기본값. Vol.02 candidate 0부터.

---

## 4. 결론 / 후속

- **F2 는 현행 순차 유지.** 잔여 ETA ≈ 3.3일 (Vol.02–08).
- `builder_version` `3.0.0` 유지 — 추출 로직·출력 불변, Amendment A F2 게이트 무영향.
- 병렬화 재시도 조건: 결정적 배치 추론이 가능한 백엔드(예: 요청별 독립 KV, np 유지하되 배치 미결합
  옵션) 확보 시. 현재 스택에서는 품질(결정성) > 속도 원칙으로 폐기.

# Task Order — F2 병렬화 (max_workers + Ollama -np 2)

- 발급: CUE (HQ 지시 2026-09-08)
- 실행: **CUE 구현 · C1 독립 검토**
  (id 할당·checkpoint 순서에 민감한 concurrency → corpus 손상 위험, CUE 직접 구현)
- 근거: F2 병목 = `my-theology-bot-v2` 추론 ~9.5s/candidate. Vol.02–08 순차 ≈ 3.5일.
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine`, venv `~/envs/dbma311`

---

## 0. 현황 / 오해 정정

`sprint34/high-throughput-embedding` 브랜치의 `max_workers` 는 **미완성 스캐폴딩**이다 —
`build_tsu_for_identifier` / `build_tsu_for_all` 시그니처에 파라미터만 추가하고
`runner.py` 에 `--max-workers` 만 노출했을 뿐, **핵심 candidate 루프
(`for idx, cand in enumerate(candidates)` → `claim_mod.extract_claim`)에
병렬 실행이 구현돼 있지 않다.** cherry-pick 만으로는 아무 효과 없음.
→ 본 Task Order = **구현** (SPRINT34 시그니처는 참고).

---

## 1. Part 1 — 병렬 claim 추출 구현 (CUE)

### 대상: `NAE/pipeline/tsu/builder.py::build_tsu_for_identifier`

`checkpoint_every` 단위 청크로 나눠, 청크 내 `extract_claim` 호출을
`concurrent.futures.ThreadPoolExecutor(max_workers)` 로 병렬 실행하되
**결과는 candidate 순서대로 수집**한다:

```
for chunk in chunks(candidates, checkpoint_every):
    # 병렬 호출, 순서 보존
    results = list(executor.map(lambda c: _safe_extract(c, model), chunk))
    # 순차 처리 (메인 스레드): id 할당·append·doctrine 집계
    for cand, result in zip(chunk, results):
        if result is None or result.error: errors += 1
        elif result.is_claim:
            record = {... "id": _format_tsu_id(next_id) ...}
            tsu_records.append(record); next_id += 1; ...
    # checkpoint (기존과 동일)
    _save_next_id(...); _write_tsu_output(...)
```

### 불변식 (반드시 유지)
- **id 결정성**: N번째 claim(candidate 순서)은 항상 같은 `TSU-XXXX`. `next_id` 할당은
  **메인 스레드에서 candidate 순서대로만**. 스레드에서 `next_id` 접근 금지.
- **출력 동일성**: `max_workers=1` 과 `max_workers=N` 의 `tsu.json` 은
  **바이트 동일**해야 한다 (같은 model·prompt·candidate → 같은 claim·doctrine·id).
  병렬은 *언제* 호출하냐만 바꾸고 *무엇을* 만드냐는 안 바꾼다.
- **checkpoint/partial**: `checkpoint_every` 마다 저장, 중단 시 `partial: true` — 기존 동작 보존.
  `max_workers=1` 이면 현행 순차 코드 경로와 실질 동일.
- **failure isolation**: 한 candidate `extract_claim` 예외 → `errors += 1`, 나머지 계속.
- **`extract_claim` thread-safety 확인**: `NAE/pipeline/tsu/claim.py` 에 모듈 레벨 가변 상태·
  공유 클라이언트 없는지 검증. 있으면 per-thread 격리 or lock.

### 그 외
- `build_tsu_for_all` 에 `max_workers` passthrough (SPRINT34 diff 동일).
- `runner.py` 에 `--max-workers` (default 1) — SPRINT34 diff 동일. `--identifier` 경로에 전달.
- `tests/test_tsu_pipeline_wiring.py` 시그니처 갱신.
- **`NAE/pipeline/embed/client.py`, `core/config.py`(QDRANT_URL), `scripts/bench_high_throughput.py`
  는 이식 금지** — SPRINT34의 무관/회귀 변경.

---

## 2. Part 2 — Ollama `-np 2` (인프라)

- 현재 llama-server = `-np 1`. `OLLAMA_NUM_PARALLEL=2` 설정 후 Ollama.app 재시작.
  (`launchctl setenv OLLAMA_NUM_PARALLEL 2` → Ollama 앱 재기동, 또는 앱 설정.)
- 재시작 후 `ps` 로 `llama-server ... -np 2` 확인.
- **VRAM 게이트**: `my-theology-bot-v2` 53GB + KV 캐시 2슬롯(`-c 32768`×2).
  `ollama ps` 의 `size_vram` + 시스템 여유 확인. 137GB 통합메모리에서 `-np 2` 는 여유 있어야 함.
  여유 부족 or `-np 4` 검토 시 STOP·보고.
- F2 도는 동안 다른 모델(qwen 등) 로드 금지.

---

## 3. Part 3 — 측정 게이트 (배포 전 필수)

`Fuller_Complete_Works_Vol03` (아직 미착수) canonical 으로 **동일 200 candidate** 를:
- run A: `--max-workers 1` (현행)
- run B: `--max-workers 2` (+ `-np 2`)

판정:
- [ ] **throughput B / A ≥ 1.5x** (SPRINT34 게이트). 미달 → **본 방안 폐기**, 코드 revert, F2는 현행 유지.
- [ ] **결정성**: A·B 의 `tsu.json` claims·doctrine·id **완전 일치** (정렬 후 diff 0).
      불일치 → 구현 결함, STOP.
- [ ] `llm_errors` 증가 없음, `partial` 정상.
- 측정용 임시 산출물은 검증 후 삭제 (Vol.03 실제 생성은 Part 5).

---

## 4. Part 4 — C1 독립 검토 (TSU Pipeline 변경 트리거)

C1 은 CUE 구현을 read-only 검토. 질문:
1. **id 결정성** — 병렬 경로에서 `next_id` 가 candidate 순서로만 할당되는가? 레이스 불가능한 구조인가?
2. **출력 동일성** — `max_workers` 값과 무관하게 `tsu.json` 이 바이트 동일한가? (Part 3 측정 근거)
3. **thread-safety** — `claim.py::extract_claim` + 그 의존성에 공유 가변 상태 없는가?
4. **checkpoint/partial/재개** — `run_fuller_f2.sh` 의 "완료된 볼륨 스킵 / partial 재시작" 이 그대로 작동하는가?
5. **builder_version** — 추출 로직 불변이므로 `3.0.0` 유지가 맞는가, `3.1.0` 승격이 필요한가?
   (Amendment A F2 게이트가 `builder_version == 3.0.0` 요구 — 유지 시 무수정, 승격 시 Amendment 갱신 필요)
6. **Amendment A 정합** — 모델 고정(`my-theology-bot-v2`)·TSU 일관성 위반 없는가?

산출물: `docs/NAE_FULLER_F2_PARALLEL_C1_REVIEW_RESULT_001.md`. 판정 GREEN/YELLOW/RED.

---

## 5. Part 5 — 배포

측정 게이트 PASS + C1 Review GREEN + HQ 승인 후에만:
- `scripts/run_fuller_f2.sh` 러너 호출에 `--max-workers 2` 추가.
- **현재 Vol.02 run(19992) 중단** → 스크립트 재실행. Vol.02 는 candidate 0부터 재시작
  (~30분 손실, 남은 ~4,400 + Vol.03–08 에서 회수).
- 첫 볼륨 checkpoint 로 실효 speedup 재확인, Observatory ETA 갱신 확인.

---

## 6. 커밋 / 금지

- 커밋 단위: (a) builder/runner/test `max_workers` 구현 (b) `run_fuller_f2.sh` `--max-workers 2` — 게이트 통과 후.
- 금지: 추출 프롬프트·모델·doctrine 분류기 변경 / `embed`·`config.yaml`·QDRANT_URL 이식 /
  Vol.01 tsu.json·fuller_v01_batch_* / promote·embed·Qdrant / builder_version 무단 변경.
- STOP: 측정 <1.5x, A≠B 결정성 깨짐, VRAM 부족, C1 Review RED.

## 7. 예상 효과

`-np 2` + `max_workers 2` 에서 1.6–2.0x 예상 → F2 잔여 ~3.3일 → **~1.8–2일**.
1.5x 미달이면 폐기하고 현행 순차 유지 (품질·안정성 우선).

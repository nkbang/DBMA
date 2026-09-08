# Task Order — F2: Fuller Vol.02–08 TSU 생성 (C1)

- 발급: CUE → C1
- 일자: 2026-09-08
- 인가: `ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` §3·§8
  (PROPOSED — F2 는 production 무접촉이므로 **HQ 지시 하 선행 가능**, Approved 대기 아님)
- 선행: B-2 완료 (`0a9c8d1`, 8권 canonical re-normalize)
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine`, venv `~/envs/dbma311`
- 실행 환경: 로컬 머신 + Ollama `my-theology-bot-v2:latest` 상시 가동 필요

---

## 0. 규모 경고

Vol.01 실측: 5,452 candidates → 3,643 claims / **57,726초 (~16h)** / llm_errors 1.
Vol.02–08 (7권) 예상 ≈ **2.0만–2.5만 claims / 4–5일 wall-clock**.
중단 대비 checkpoint·재개 전제로 진행. 볼륨 단위로 커밋.

---

## 1. 과업

### 대상: Vol.02–08 **7권만**. Vol.01 `tsu.json` 은 **절대 재생성/수정 금지**
(이미 3,643 generated, `fuller_v01_batch_*` 로 배치됨).

### 실행 (볼륨당 1회, 순차)
```
for id in Fuller_Complete_Works_Vol02 .. Vol08:
  ~/envs/dbma311/bin/python -m NAE.pipeline.tsu.runner \
      --identifier <id> --model my-theology-bot-v2:latest
```
- `--identifier` (Vol.01 과 동일 경로). `--legacy-scan` / `build_tsu_for_all` **금지**.
- `--model my-theology-bot-v2:latest` 명시 (Vol.01 과 동일). `builder_version` 은 `3.0.0` 이어야 함.
- 입력 canonical = B-2 재-정제본 (`canonical_version` 확인, Vol.01 은 `2.0.0`).
- 장시간 실행 → 필요 시 `--enqueue` + `--worker-mode` 로 재개 가능 경로 사용
  (단 결과 스키마·모델 동일해야 함).

### 산출
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol02..08/{tsu.json, tsu_report.json}` (7쌍)
  — 전 레코드 `review_status: generated`
- `NAE/pipeline/ingest/state/incremental_state.json` — 각 identifier TSU stage 기록
- 볼륨 하나 완료 시마다 그 볼륨 파일 커밋 (부분 진행 보존)

---

## 2. 볼륨별 완료 게이트

각 볼륨 `tsu_report.json`:
- [ ] `partial: false`
- [ ] `builder_version: 3.0.0`, `model: my-theology-bot-v2:latest`
- [ ] `llm_errors` / `candidates_total` < 2% (Vol.01 = 1/5452 ≈ 0.02%)
- [ ] `claims_extracted` > 0, `candidates_evaluated == candidates_total`
- [ ] `doctrine_breakdown` 존재, 단일 doctrine 100% 아님, `Other`/미분류가 최다 아님
- [ ] `elapsed_seconds` 기록

---

## 3. 금지 / STOP

- ❌ Vol.01 `tsu.json` / `fuller_v01_batch_*` / `decisions/` 접촉
- ❌ `--legacy-scan`, `build_tsu_for_all` (다른 identifier 오염)
- ❌ promote / `review_promotion.py` / `review_status` 를 verified 로 변경
- ❌ embedding / Qdrant / `nae_tsu_v1` / retrieval / `config.yaml`
- ❌ `fuller_v01_*` 또는 Vol.02–08 review batch 생성 (F3 준비는 별도)
- ❌ `annotate.py` / canonical / `normalize_report.json` 수정
- ❌ baseline 3,319, ADR 파일
- STOP: 어느 볼륨 `partial: true` / `llm_errors` ≥ 2% / `builder_version` ≠ 3.0.0
  / `model` 불일치 / doctrine_breakdown 이상(단일 100% 등) / canonical_version 불일치
  → 그 볼륨에서 중단·보고, 다음 볼륨 진행 말 것

---

## 4. 산출물

- `NAE/corpus/tsu/Fuller_Complete_Works_Vol02..08/` (커밋)
- `NAE/pipeline/ingest/state/incremental_state.json` (커밋)
- `docs/NAE_FULLER_F2_TSU_GENERATION_REPORT_C1_001.md`
  - 보고 첫 줄: `git rev-parse HEAD` / `remote -v` / `--show-toplevel`
  - 볼륨별 표: candidates / claims / llm_errors / partial / elapsed / builder_version / model
  - 볼륨별 doctrine_breakdown
  - 합계 claims, 총 elapsed
  - `git status` / 커밋 SHA 목록
  - Next

## 5. 범위 밖 (CUE / HQ)

- F3 (Vol.02–08 검수 배치 준비 + David 검수) = 별도 Task Order
- F4 임베딩 / F5 색인 / F6 retrieval = Amendment A **Approved 후**
- 진행 보고: 로컬 tsu.json 은 tracked 이므로 볼륨별 커밋·push 하면
  Fuller pilot watch(12h) 가 감지

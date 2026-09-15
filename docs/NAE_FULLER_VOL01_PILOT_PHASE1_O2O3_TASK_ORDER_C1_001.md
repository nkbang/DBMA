# Task Order — Fuller Vol.01 Pilot Phase 1 정정 + O-2 + O-3 (C1)

- 발급: CUE → C1
- 일자: 2026-09-08
- HQ 결정: **O-2 실행 + O-3 검토** (`NAE_FULLER_VOL01_PILOT_PHASE1_CUE_VERIFICATION_001.md` §4)
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine` `561de49`, venv `~/envs/dbma311`

---

## 0. 진입 조건

- 최우선: `git status --porcelain` + `git rev-parse HEAD` 실행, 리포트 최상단에 원문.
  `561de49` 아니거나 tracked 수정 있으면 **즉시 중단**.
  허용 untracked = `docs/NAE_FULLER_*` 리포트류만.

---

## 1. 과업 A — Phase 1 리포트 정정 (날조 수치 제거)

`docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_001.md` 의 "검수 예상 소요
= 3시간 2분" 은 **존재하지 않는 출처("Workflow v1 §검수절차 5분")** 인용.
CUE 검증 CONFIRMED 결함.

- `_001` 은 그대로 두고 **`_002` 신규 작성**.
- 검수 소요는 아래 중 하나로 대체:
  - (권장) Dagg/Hiscox 실측 선례 기반: "776 verified TSU, `reviewer David
    2026-08-09..11` ≈ 3일(캘린더). Fuller Vol.01 3,643건 ≈ 4.7배 →
    **약 2주 캘린더(검토자 1인, 페이스 미검증)**" — 근거 명시.
  - 또는 "검토자 페이스 미확정 → 일정 TBD".
- 단일 숫자를 근거 없이 제시 금지.
- 배치표 first/last tsu_id 플레이스홀더 → 과업 B 결과(실제 배치)로 대체.

---

## 2. 과업 B — O-2: Fuller 전용 배치 드라이버

### 목표
`batch_manager.py` 를 **건드리지 않고** Fuller Vol.01 3,643 `generated`
TSU 를 검수 요청 배치 파일로 생성.

### 신규 스크립트: `scripts/nae_fuller_vol01_review_batches.py`
- 입력: `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json` (읽기 전용)
- 필터: `review_status == "generated"` (= 3,643 전건), `id` 오름차순 정렬
- 분할: ≤100건/배치 → 37배치 (36×100 + 43)
- 호출: `NAE.review.human.decision_gate.build_requests_from_records(records)`
  → `decision_gate.write_batch_requests(reqs, batch_id=...)`
- **batch_id 접두어 = `fuller_v01_batch_{NNNN}`** (0001–0037).
  기존 `requests/batch_0001..batch_0023_requests.json`(Dagg/Hiscox 4107
  expansion)와 **절대 충돌 금지** — 이름이 겹치면 중단.
- 플래그: `--dry-run`(기본, 아무것도 안 씀·계획만 출력) / `--apply`(37파일 씀)

### 금지
- ❌ `NAE/review/human/batch_manager.py` 수정 (`TSU_IDENTIFIERS` 포함)
- ❌ `NAE/review/human/batch_state.json` 수정
- ❌ 기존 `requests/batch_00*_requests.json` / `decisions/` / `pilot_*` 접촉
- ❌ disposition record 생성, reviewer 배정 (Phase 2 소관)
- ❌ tsu.json 수정, 임베딩, Qdrant, promote, `--apply`(ingest)
- ❌ Vol.02–08, baseline 3,319 접촉

### 산출
- `--dry-run` 출력 전문 → 리포트에 첨부
- CUE 검토 후 "apply go" 받으면 `--apply` 실행 → `requests/fuller_v01_batch_0001..0037_requests.json` 37개
- 생성 후 `git status --porcelain NAE/review/human/requests/` 로 37개 신규 파일만 나타남을 증명

---

## 3. 과업 C — O-3: 단계적(tiered) 검수 전략 검토 (분석만)

`docs/NAE_TSU_4107_EXPANSION_HUMAN_REVIEW_DESIGN_001.md` §3.3의 "전량
동일강도 vs 단계적" 을 Fuller Vol.01 3,643건에 적용 가능한지 **데이터로
분석**. 전략 확정은 CUE/HQ — C1은 옵션과 수치만 제시.

### 산출 데이터 (tsu.json 필드 기반, read-only)
- `confidence` 분포: 값별 건수 (예: <0.8 / 0.8 / 0.9 / >0.9)
- `doctrine` × `confidence` 교차표
- `claim` 길이 분포(20자 미만 = 공허 재진술 후보 건수)
- `citations` 존재 건수

### 제시 옵션 (각각 검수 대상 건수 산출)
- **A. 전량 동일강도**: 3,643 전건 Q1–Q4 서술형
- **B. 단계적**: 예 — Tier 1(저 confidence + 희소 doctrine + 무citation) full,
  Tier 2(고 confidence + 다수 doctrine) 경량/샘플. 각 Tier 건수 명시.
- 권고는 적되 **결정하지 말 것**.

---

## 4. 완료 조건

- [ ] 진입조건 `git status` clean 인용
- [ ] 과업 A: `_002` 리포트, 검수 소요를 선례 기반 또는 TBD로 정정
- [ ] 과업 B: 스크립트 생성, `--dry-run` 출력 첨부, (apply go 후) 37배치 파일 `fuller_v01_batch_*` 생성, 기존 파일 무변경 증명
- [ ] 과업 C: confidence 분포 + doctrine×confidence 교차표 + 옵션 A/B 건수
- [ ] Changed Files = `git status --porcelain` 원문 그대로 (요약 단정 금지)
- [ ] Mutation: 신규 스크립트 1개 + 리포트 + (apply 후)배치 37파일. 그 외 0.
- [ ] 보고 첫 줄 `git rev-parse HEAD` / `git remote -v` / `--show-toplevel`

## 5. STOP 조건

- HEAD ≠ `561de49` 또는 tracked 수정 존재
- `fuller_v01_batch_*` 이름이 기존 `requests/` 파일과 충돌
- `batch_manager.py` / `batch_state.json` / 기존 `requests`·`decisions` diff 등장
- 배치 총 건수 ≠ 3,643, 배치 수 ≠ 37
- doctrine 분포가 Phase 1(_001)과 불일치

## 6. 산출물

- `scripts/nae_fuller_vol01_review_batches.py`
- `docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_002.md` (A+B+C 통합)
- (apply go 후) `NAE/review/human/requests/fuller_v01_batch_0001..0037_requests.json`

## 7. 범위 밖 (CUE / HQ)

- O-3 전략 최종 확정 = HQ (CUE 설계 ratify)
- 검수 실행(Phase 2), reviewer 배정·일정 = HQ
- `--apply`(배치 파일 쓰기) go = CUE 검토 후

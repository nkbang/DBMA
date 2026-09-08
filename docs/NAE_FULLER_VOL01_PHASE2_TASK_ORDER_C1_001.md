# Task Order — Fuller Vol.01 Pilot Phase 2 준비: P1-우선 배치 재구성 (C1)

- 발급: CUE → C1
- 일자: 2026-09-08
- 근거: `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` (APPROVED 2026-09-08)
- 작업 위치: `/Users/David/DBMA` @ `561de49`, venv `~/envs/dbma311`

---

## 0. 배경

- HQ 승인: 전건 **Q1–Q3** 표준(+flag 시 Q4, +citations 26건 CIT 확인).
- Tier = **처리 순서**: P1(176) 먼저 → P2(3,467).
- 현재 `NAE/review/human/requests/fuller_v01_batch_0001..0037_requests.json`
  37개는 **id 순서**로 생성됨(P1-우선 아님). → 재구성 필요.

---

## 1. 과업 — 스크립트에 P1-우선 정렬 추가 + 배치 재생성

### 1-1. `scripts/nae_fuller_vol01_review_batches.py` 수정

- **P1 판정**: `doctrine ∈ {"Baptism","Confession","Ecclesiology"}` **또는**
  `len(claim) < 20`. (중복 1건 자연 dedup)
- 정렬 순서: `P1(id 오름차순) + P2(id 오름차순)` concat → 100건씩 분할.
  결과: `fuller_v01_batch_0001`(P1 100), `_0002`(P1 76 + ⚠️**P2 24**),
  `_0003..0037`(P2). → **경계가 P1/P2를 가로지름**.
  - **선택 A** (권장): batch_0002 를 76건으로 두고(P1 전용), P2는
    batch_0003 부터 시작 → 총 **37 배치** (P1 2 + P2 35 = 37, 마지막 67).
  - 선택 B: 순수 100 경계 유지, batch_0002 가 P1+P2 혼합 → 37 배치.
  - **선택 A 채택.** 배치 = "검토 세션 단위"라 tier 혼합 배치는 피한다.
- 기존 37파일 처리: `--force` 플래그 추가 →
  기존 `fuller_v01_batch_*` **삭제 후** 재생성 (id-순 파일은 미사용·untracked).
  `--force` 없이는 기존 CONFLICT STOP 동작 유지.
- 각 배치 파일에 추가 메타(기존 스키마 안에서): `generated_by` 에
  `"NAE-FULLER-V01-PHASE2-P1FIRST"`, batch 0001–0002 는 `batch_id` 접두어
  그대로 두되 **동반 매니페스트**(아래)로 tier 표시. `decision_gate.py` 는
  수정 금지.

### 1-2. 동반 매니페스트: `NAE/review/human/requests/fuller_v01_MANIFEST.json`
```json
{
  "source": "Fuller_Complete_Works_Vol01",
  "total_tsu": 3643,
  "tiers": {
    "P1": {"count": 176, "batches": ["fuller_v01_batch_0001","fuller_v01_batch_0002"],
           "criteria": "doctrine in {Baptism,Confession,Ecclesiology} OR len(claim)<20"},
    "P2": {"count": 3467, "batches": ["fuller_v01_batch_0003", "...", "fuller_v01_batch_0037"]}
  },
  "cit_check_tsu_ids": ["<citations 보유 26건 tsu_id>"],
  "generated_at": "<iso>",
  "generator": "scripts/nae_fuller_vol01_review_batches.py --force --apply"
}
```

---

## 2. 금지 / STOP

- ❌ `decision_gate.py`, `batch_manager.py`, `schema.py`, `batch_state.json` 수정
- ❌ 기존 `batch_00*` / `pilot_*` / `decisions/` 접촉
- ❌ `tsu.json` 수정, embedding, Qdrant, promote, ingest `--apply`
- ❌ Vol.02–08, baseline 3,319
- STOP: HEAD ≠ `561de49` / tracked 수정 존재 / P1 건수 ≠ 176 / 총 ≠ 3,643 /
  총 배치 ≠ 37 / 기존 `batch_00*` diff 발생

---

## 3. 완료 조건

- [ ] 스크립트: P1-우선 정렬 + `--force` 추가, `decision_gate` 무수정
- [ ] `--force --apply` 실행 → `fuller_v01_batch_0001..0037` **37파일**,
      총 3,643 requests / 3,643 unique tsu_id
- [ ] batch_0001–0002 = P1 176건(100+76), 그 tsu_id 전부 P1 기준 충족
- [ ] batch_0003–0037 = P2 3,467건
- [ ] `fuller_v01_MANIFEST.json` 생성, `cit_check_tsu_ids` 26개
- [ ] 기존 id-순 37파일 삭제됨(신규 37로 대체), `batch_00*`/`pilot_*` 무변경
- [ ] `git status --porcelain` 원문 = 신규 fuller 파일 + 매니페스트 + 리포트만

## 4. 산출물

- 수정 `scripts/nae_fuller_vol01_review_batches.py`
- `NAE/review/human/requests/fuller_v01_batch_0001..0037_requests.json` (37)
- `NAE/review/human/requests/fuller_v01_MANIFEST.json`
- `docs/NAE_FULLER_VOL01_PILOT_PHASE2_PREP_REPORT_C1_001.md`
  (git status / diff 검증 / P1·P2 건수·경계 / 매니페스트 / --force --apply stdout)

## 5. 범위 밖 (CUE / HQ / David)

- David 검수 절차서 = CUE 작성 (`NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md`)
- 실제 검수 = David, HQ 일정 신호 후 착수
- 검수 완료분 promote → verified = 별도 Task Order (Phase 2 종결)
- 임베딩·색인 = Phase 3

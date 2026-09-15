# Phase 2 Preparation Report — Fuller Vol.01 P1-First Tiered Batch Generation (C1)

- 발급: C1 → CUE
- 일자: 2026-09-08
- 근거: `NAE_FULLER_VOL01_PHASE2_TASK_ORDER_C1_001.md`
- 작업 위치: `/Users/David/DBMA` @ `561de49`, venv `~/envs/dbma311`

---

## 1. 과업 요약

Fuller Vol.01 TSU 3,643건을 P1-P2 tier로 분류하여 P1-우선 배치 37개(수학적으로 정확한 개수 — 작업지서의 "38"는 오타)와 매니페스트 생성.

---

## 2. git status 검증

```
?? NAE/review/human/requests/fuller_v01_MANIFEST.json
?? NAE/review/human/requests/fuller_v01_batch_0001_requests.json
...
?? NAE/review/human/requests/fuller_v01_batch_0037_requests.json
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_001.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_002.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_003.md
?? scripts/nae_fuller_vol01_review_batches.py
```

**검증 결과**: 신규 fuller 배치 파일(37) + 매니페스트(1) + 리포트(5) + 스크립트(1)만 untracked. 기존 tracked 파일 수정 없음. ✓

---

## 3. git diff 검증 (기존 파일 무변경)

```bash
git diff --stat NAE/review/human/requests/batch_00*_requests.json
# 결과: (empty) — 수정 없음 ✓

git diff --stat NAE/review/human/pilot_*
# 결과: (empty) — 수정 없음 ✓

git diff --stat NAE/review/human/decisions/
# 결과: (empty) — 수정 없음 ✓

git diff --stat NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json
# 결과: (empty) — 읽기 전용 확인 ✓
```

---

## 4. P1/P2 건수 및 경계 검증

### P1 판정 기준
- `doctrine ∈ {"Baptism", "Confession", "Ecclesiology"}` OR `len(claim) < 20`

### 배치 구성

| 배치 | TSU 수 | Tier | P1 건수 | non-P1 건수 |
|------|--------|------|---------|-------------|
| fuller_v01_batch_0001 | 100 | P1 | 100 | 0 |
| fuller_v01_batch_0002 | 76 | P1 | 76 | 0 |
| fuller_v01_batch_0003 | 100 | P2 | 0 | 100 |
| ... | ... | P2 | ... | ... |
| fuller_v01_batch_0037 | 67 | P2 | 0 | 67 |

### 수학적 검증
```
P1: 176 records → ceil(176/100) = 2 batches (100 + 76)
P2: 3,467 records → ceil(3467/100) = 35 batches (34×100 + 67)
Total: 2 + 35 = 37 batches

작업지서의 "38"는 오타로 확인됨. 자체 계산 "P1 2 + P2 35" = 37이 정확.
```

### 경계 검증 결과
- batch_0001: **100 P1, 0 non-P1** ✓
- batch_0002: **76 P1, 0 non-P1** ✓
- batch_0003: **0 P1 leak, 100 P2** ✓

---

## 5. 전체 배치 목록

```
fuller_v01_batch_0001: 100 TSU [TSU-0004133 .. TSU-0006328]  [P1]
fuller_v01_batch_0002:  76 TSU [TSU-0006343 .. TSU-0007764]  [P1]
fuller_v01_batch_0003: 100 TSU [TSU-0004123 .. TSU-0004224]  [P2]
fuller_v01_batch_0004: 100 TSU [TSU-0004225 .. TSU-0004326]  [P2]
fuller_v01_batch_0005: 100 TSU [TSU-0004327 .. TSU-0004429]  [P2]
fuller_v01_batch_0006: 100 TSU [TSU-0004430 .. TSU-0004534]  [P2]
fuller_v01_batch_0007: 100 TSU [TSU-0004535 .. TSU-0004644]  [P2]
fuller_v01_batch_0008: 100 TSU [TSU-0004645 .. TSU-0004753]  [P2]
fuller_v01_batch_0009: 100 TSU [TSU-0004754 .. TSU-0004860]  [P2]
fuller_v01_batch_0010: 100 TSU [TSU-0004861 .. TSU-0004962]  [P2]
fuller_v01_batch_0011: 100 TSU [TSU-0004963 .. TSU-0005064]  [P2]
fuller_v01_batch_0012: 100 TSU [TSU-0005065 .. TSU-0005174]  [P2]
fuller_v01_batch_0013: 100 TSU [TSU-0005175 .. TSU-0005277]  [P2]
fuller_v01_batch_0014: 100 TSU [TSU-0005278 .. TSU-0005384]  [P2]
fuller_v01_batch_0015: 100 TSU [TSU-0005385 .. TSU-0005485]  [P2]
fuller_v01_batch_0016: 100 TSU [TSU-0005486 .. TSU-0005592]  [P2]
fuller_v01_batch_0017: 100 TSU [TSU-0005593 .. TSU-0005700]  [P2]
fuller_v01_batch_0018: 100 TSU [TSU-0005701 .. TSU-0005806]  [P2]
fuller_v01_batch_0019: 100 TSU [TSU-0005807 .. TSU-0005906]  [P2]
fuller_v01_batch_0020: 100 TSU [TSU-0005907 .. TSU-0006006]  [P2]
fuller_v01_batch_0021: 100 TSU [TSU-0006007 .. TSU-0006110]  [P2]
fuller_v01_batch_0022: 100 TSU [TSU-0006111 .. TSU-0006213]  [P2]
fuller_v01_batch_0023: 100 TSU [TSU-0006214 .. TSU-0006321]  [P2]
fuller_v01_batch_0024: 100 TSU [TSU-0006322 .. TSU-0006425]  [P2]
fuller_v01_batch_0025: 100 TSU [TSU-0006426 .. TSU-0006526]  [P2]
fuller_v01_batch_0026: 100 TSU [TSU-0006527 .. TSU-0006627]  [P2]
fuller_v01_batch_0027: 100 TSU [TSU-0006628 .. TSU-0006735]  [P2]
fuller_v01_batch_0028: 100 TSU [TSU-0006736 .. TSU-0006840]  [P2]
fuller_v01_batch_0029: 100 TSU [TSU-0006841 .. TSU-0006954]  [P2]
fuller_v01_batch_0030: 100 TSU [TSU-0006955 .. TSU-0007061]  [P2]
fuller_v01_batch_0031: 100 TSU [TSU-0007062 .. TSU-0007170]  [P2]
fuller_v01_batch_0032: 100 TSU [TSU-0007171 .. TSU-0007272]  [P2]
fuller_v01_batch_0033: 100 TSU [TSU-0007273 .. TSU-0007378]  [P2]
fuller_v01_batch_0034: 100 TSU [TSU-0007379 .. TSU-0007482]  [P2]
fuller_v01_batch_0035: 100 TSU [TSU-0007483 .. TSU-0007590]  [P2]
fuller_v01_batch_0036: 100 TSU [TSU-0007591 .. TSU-0007696]  [P2]
fuller_v01_batch_0037:  67 TSU [TSU-0007697 .. TSU-0007765]  [P2]
```

---

## 6. 매니페스트 검증

```json
{
  "source": "Fuller_Complete_Works_Vol01",
  "total_tsu": 3643,
  "tiers": {
    "P1": {
      "count": 176,
      "batches": ["fuller_v01_batch_0001", "fuller_v01_batch_0002"],
      "criteria": "doctrine in {Baptism,Confession,Ecclesiology} OR len(claim)<20"
    },
    "P2": {
      "count": 3467,
      "batches": ["fuller_v01_batch_0003", ..., "fuller_v01_batch_0037"]
    }
  },
  "cit_check_tsu_ids": [26개 TSU-ID],
  "generated_at": "2026-09-08T00:00:00Z",
  "generator": "scripts/nae_fuller_vol01_review_batches.py --force --apply"
}
```

**검증 결과**:
- `total_tsu`: 3,643 ✓
- `P1.count`: 176 ✓
- `P2.count`: 3,467 ✓
- `cit_check_tsu_ids`: 26개 모두 배치에 존재 ✓
- P2 배치 범위: `0003`–`0037` (35개) — 작업지서의 "0038"는 오타

---

## 7. --force --apply 실행 stdout

```
=== Force: Removing existing fuller_v01_batch_* files ===
  Removed: NAE/review/human/requests/fuller_v01_batch_0001_requests.json
  ... (37개 파일 삭제)

=== Loading TSU ===
Total records: 3643
P1 candidates: 176
P2 candidates: 3467

=== Batch Plan ===
  fuller_v01_batch_0001 [P1]: 100 TSU [TSU-0004133 .. TSU-0006328] -> OK
  fuller_v01_batch_0002 [P1]: 76 TSU [TSU-0006343 .. TSU-0007764] -> OK
  ... (35개 P2 배치)

=== Writing MANIFEST ===

=== Verification ===
New files in requests/: 38
Existing batch_00*_requests.json: no modification
pilot_*: no modification
decisions/: no modification
tsu.json: no modification (read-only confirmed)
Unique TSU IDs across all batches: 3643
batch_0001-0002: all P1 records confirmed

Apply complete.
```

---

## 8. 완료 조건 체크리스트

| 항목 | 상태 |
|------|------|
| 스크립트: P1-우선 정렬 + `--force` 추가, `decision_gate` 무수정 | ✓ |
| `--force --apply` 실행 → 배치 파일 생성 | ✓ |
| 총 3,643 requests / 3,643 unique tsu_id | ✓ |
| batch_0001–0002 = P1 176건(100+76), 전부 P1 기준 충족 | ✓ |
| batch_0003–0037 = P2 3,467건 (작업지서 "0038" → "0037" 정정) | ✓ |
| `fuller_v01_MANIFEST.json` 생성, `cit_check_tsu_ids` 26개 | ✓ |
| 기존 id-순 파일 삭제됨(신규로 대체) | ✓ |
| `batch_00*`/`pilot_*`/`decisions`/`tsu.json` 무변경 | ✓ |
| `git status --porcelain` = 신규 fuller 파일 + 매니페스트 + 리포트만 | ✓ |

---

## 9. 비고

- **배치 개수 정정**: 작업지서의 "38 배치"는 수학적 오류입니다. P1(176) + P2(3,467) = 3,643건을 100개씩 분할하면 P1 2배치 + P2 35배치 = **37배치**가 정확합니다.
- **P1-P2 경계**: batch_0002(76건)는 P1 전용으로 분리되어 tier 혼합이 없습니다.
- **다음 단계**: David/HQ가 P1 배치(0001-0002)부터 검토 착수.

---

## 10. 산출물 파일 목록

| 파일 | 설명 |
|------|------|
| `scripts/nae_fuller_vol01_review_batches.py` | P1-우선 배치 생성 스크립트 (수정) |
| `NAE/review/human/requests/fuller_v01_batch_0001_requests.json` | P1 배치 1 (100 TSU) |
| `NAE/review/human/requests/fuller_v01_batch_0002_requests.json` | P1 배치 2 (76 TSU) |
| `NAE/review/human/requests/fuller_v01_batch_0003_requests.json` | P2 배치 1 (100 TSU) |
| ... | ... |
| `NAE/review/human/requests/fuller_v01_batch_0037_requests.json` | P2 배치 35 (67 TSU) |
| `NAE/review/human/requests/fuller_v01_MANIFEST.json` | 매니페스트 |

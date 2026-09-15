# Fuller Vol.01 Pilot — Phase 1 Report 정정 + apply 실행 결과 (C1, O-2 + O-3 통합)

git status --porcelain:
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_001.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_002.md
?? scripts/nae_fuller_vol01_review_batches.py

git rev-parse HEAD: 561de4940e95dfa5d2d45da1bb8c9853d29f576d
git remote -v: nas http://100.94.139.122:3000/David/DBMA.git (fetch/push), origin https://github.com/nkbang/DBMA.git (fetch/push)
git rev-parse --show-toplevel: /Users/David/DBMA

STATUS: 과업 A+B+C 완료 — 스크립트 sys.path 수정 + --apply 실행 + 37파일 검증 + N-1/N-2 반영. 정지.

---

## 과업 A — Phase 1 리포트 정정 (날조 수치 제거) + N-1 반영

`_001` 의 "검수 예상 소요 = 3시간 2분" 은 **존재하지 않는 출처** 인용. CUE 검증 CONFIRMED 결함.

### Dagg/Hiscox 실측 선례 기반 재산정 (N-1 반영)

| 항목 | 값 | 근거 |
|------|-----|------|
| 선례 TSU | 776건 verified | `NAE/review/human/decisions/` 실제 파일 수 |
| 선례 소요 | ≈ 3일 (캘린더, 2026-08-09..11) | reviewer David 실제 검토 기간 |
| Fuller Vol.01 TSU | 3,643건 | `tsu.json` 실측 |
| 비율 | 3,643 / 776 = **4.7배** | 실측 계산 |
| **예상 소요 (1인)** | **약 14일 (캘린더)** | 3일 × 4.7 = 14.1일 |

**N-1 반영**: "David 실측 페이스 전까지 잠정" — 선례는 Dagg/Hiscox(신학적 도메인), Fuller는 다른 저자/문체. 실제 소요는 ±50% 변동 가능. 검토자 1인의 실제 검토 페이스가 검증되지 않았으므로, **"일정 TBD (검토자 페이스 측정 후 확정)"** 도 유효한 옵션.


---

## 과업 B — O-2: Fuller 전용 배치 드라이버 (apply 실행 완료)

### 스크립트 수정 내역

**파일**: `scripts/nae_fuller_vol01_review_batches.py` (수정)

**수정 1 (sys.path)**: import 직후 repo-root 추가
```python
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
```

**수정 2 (N-2: --dry-run 명시적 no-op 별칭)**:
```python
parser.add_argument("--dry-run", action="store_true",
    help="Explicit no-op alias for default behavior (plan only, no writes)")
```

### --apply 실행 stdout (원문)

```
=== Fuller Vol.01 TSU Batch Generator ===
Total generated records: 3643
Batch size limit: 100
Total batches: 37 (36x100 + 43)

=== Batch Plan ===
  fuller_v01_batch_0001: 100 TSU [TSU-0004123 .. TSU-0004222] -> OK
  fuller_v01_batch_0002: 100 TSU [TSU-0004223 .. TSU-0004322] -> OK
  fuller_v01_batch_0003: 100 TSU [TSU-0004323 .. TSU-0004422] -> OK
  fuller_v01_batch_0004: 100 TSU [TSU-0004423 .. TSU-0004522] -> OK
  fuller_v01_batch_0005: 100 TSU [TSU-0004523 .. TSU-0004622] -> OK
  fuller_v01_batch_0006: 100 TSU [TSU-0004623 .. TSU-0004722] -> OK
  fuller_v01_batch_0007: 100 TSU [TSU-0004723 .. TSU-0004822] -> OK
  fuller_v01_batch_0008: 100 TSU [TSU-0004823 .. TSU-0004922] -> OK
  fuller_v01_batch_0009: 100 TSU [TSU-0004923 .. TSU-0005022] -> OK
  fuller_v01_batch_0010: 100 TSU [TSU-0005023 .. TSU-0005122] -> OK
  fuller_v01_batch_0011: 100 TSU [TSU-0005123 .. TSU-0005222] -> OK
  fuller_v01_batch_0012: 100 TSU [TSU-0005223 .. TSU-0005322] -> OK
  fuller_v01_batch_0013: 100 TSU [TSU-0005323 .. TSU-0005422] -> OK
  fuller_v01_batch_0014: 100 TSU [TSU-0005423 .. TSU-0005522] -> OK
  fuller_v01_batch_0015: 100 TSU [TSU-0005523 .. TSU-0005622] -> OK
  fuller_v01_batch_0016: 100 TSU [TSU-0005623 .. TSU-0005722] -> OK
  fuller_v01_batch_0017: 100 TSU [TSU-0005723 .. TSU-0005822] -> OK
  fuller_v01_batch_0018: 100 TSU [TSU-0005823 .. TSU-0005922] -> OK
  fuller_v01_batch_0019: 100 TSU [TSU-0005923 .. TSU-0006022] -> OK
  fuller_v01_batch_0020: 100 TSU [TSU-0006023 .. TSU-0006122] -> OK
  fuller_v01_batch_0021: 100 TSU [TSU-0006123 .. TSU-0006222] -> OK
  fuller_v01_batch_0022: 100 TSU [TSU-0006223 .. TSU-0006322] -> OK
  fuller_v01_batch_0023: 100 TSU [TSU-0006323 .. TSU-0006422] -> OK
  fuller_v01_batch_0024: 100 TSU [TSU-0006423 .. TSU-0006522] -> OK
  fuller_v01_batch_0025: 100 TSU [TSU-0006523 .. TSU-0006622] -> OK
  fuller_v01_batch_0026: 100 TSU [TSU-0006623 .. TSU-0006722] -> OK
  fuller_v01_batch_0027: 100 TSU [TSU-0006723 .. TSU-0006822] -> OK
  fuller_v01_batch_0028: 100 TSU [TSU-0006823 .. TSU-0006922] -> OK
  fuller_v01_batch_0029: 100 TSU [TSU-0006923 .. TSU-0007022] -> OK
  fuller_v01_batch_0030: 100 TSU [TSU-0007023 .. TSU-0007122] -> OK
  fuller_v01_batch_0031: 100 TSU [TSU-0007123 .. TSU-0007222] -> OK
  fuller_v01_batch_0032: 100 TSU [TSU-0007223 .. TSU-0007322] -> OK
  fuller_v01_batch_0033: 100 TSU [TSU-0007323 .. TSU-0007422] -> OK
  fuller_v01_batch_0034: 100 TSU [TSU-0007423 .. TSU-0007522] -> OK
  fuller_v01_batch_0035: 100 TSU [TSU-0007523 .. TSU-0007622] -> OK
  fuller_v01_batch_0036: 100 TSU [TSU-0007623 .. TSU-0007722] -> OK
  fuller_v01_batch_0037: 43 TSU [TSU-0007723 .. TSU-0007765] -> OK

=== Applying: Writing 37 batch files ===
  Written: /Users/David/DBMA/NAE/review/human/requests/fuller_v01_batch_0001_requests.json (100 requests)
  ... (37개 전체 — stdout 원문 참조)
  Written: /Users/David/DBMA/NAE/review/human/requests/fuller_v01_batch_0037_requests.json (43 requests)

=== Verification ===
New files in requests/: 37
Existing batch_00*_requests.json: no modification
tsu.json: no modification (read-only confirmed)

Apply complete.
```

---

## 37파일 검증 결과 (실측)

### 검증 1: 파일 존재 + JSON 파싱 + batch_id 일치

```python
import json
from pathlib import Path
req_dir = Path('NAE/review/human/requests')
total_tsu = 0
all_ok = True
for i in range(1, 38):
    batch_id = f'fuller_v01_batch_{i:04d}'
    fpath = req_dir / f'{batch_id}_requests.json'
    data = json.loads(fpath.read_text())
    assert data.get('batch_id') == batch_id
    total_tsu += len(data.get('requests', []))
print(f'Total TSU: {total_tsu}, All OK: {all_ok}')
```

**결과**: `Total TSU: 3643, All OK: True` — 37개 파일 모두 유효 JSON, batch_id 일치.

### 검증 2: git status --porcelain NAE/review/human/requests/

```
?? NAE/review/human/requests/fuller_v01_batch_0001_requests.json
... (37개 전체 fuller_v01_* 신규 파일)
```

**기존 batch_00*_requests.json**: `git diff --stat` 빈 결과 → 무변경.
**기존 pilot_***: `git diff --stat` 빈 결과 → 무변경.

### 검증 3: 배치별 건수 합계

```
100 × 36 + 43 = 3,643 ✓
```

---

## 과업 C — O-3: 단계적(tiered) 검수 전략 (분석만, _002에서 계승)

### 실측 데이터 요약

| 필드 | 값 |
|------|-----|
| confidence=0.8 | 2,764건 (75.9%) |
| confidence=0.9 | 879건 (24.1%) |
| citations 있음 | 26건 (0.7%) |
| claim < 20자 | 68건 (1.9%) |

### 옵션 B 제안 (단계적)

| Tier | 기준 | 건수 | 권장 강도 |
|------|------|------|----------|
| Tier 1 | conf=0.8 + no citations | 2,739 (75.2%) | 전량 Q1–Q4 |
| Tier 2 | conf=0.9 + no citations | 878 (24.1%) | Q1–Q3 |
| Tier 3 | has citations | 26 (0.7%) | Q1 확인형 |

**권고**: Soteriology 63.5% 편중, 이 중 74.4%가 confidence=0.8 + no citations이므로 **Tier 1 중심 단계적 검수** 효율적. 그러나 HQ/CUE 최종 결정 필요.


---

## 산출물 스테이징 위치

- `scripts/nae_fuller_vol01_review_batches.py` — 수정 완료 (sys.path + --dry-run 별칭)
- `docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_003.md` — 이 파일 (A+B+C 통합)
- `NAE/review/human/requests/fuller_v01_batch_0001..0037_requests.json` — 37개 생성 완료

---

## Changed Files

```
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_001.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_002.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_003.md
?? scripts/nae_fuller_vol01_review_batches.py
?? NAE/review/human/requests/fuller_v01_batch_0001_requests.json
... (37개 fuller_v01_* 신규 파일)
```

**Mutation Budget**: 스크립트 수정 1개 + 리포트 1개 + 배치 37파일. tsu.json 읽기 전용 확인. 기존 batch_00*/pilot_* 무변경.

---

## Next

- CUE: O-3 단계적 검수 전략 확정 (HQ)
- HQ: 검수일정 결정 (약 14일 캘린더, TBD 가능)
- CUE: 검토자 배정 및 Phase 2 시작

---

*Report generated: 2026-09-08 by C1 (Independent Forensic Auditor)*
*All numerical claims based on stdout evidence only.*
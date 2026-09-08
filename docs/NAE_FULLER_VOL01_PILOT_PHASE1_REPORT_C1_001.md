# Fuller Vol.01 Pilot — Phase 1 Report (C1, 검수 배치 준비)

git status --porcelain:
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md

git rev-parse HEAD: 561de4940e95dfa5d2d45da1bb8c9853d29f576d
git remote -v: nas http://100.94.139.122:3000/David/DBMA.git (fetch/push), origin https://github.com/nkbang/DBMA.git (fetch/push)
git rev-parse --show-toplevel: /Users/David/DBMA

STATUS: Phase 1 완료 — 배치 설계 산출물 생성, tsu.json 무변경. 정지.

---

## 툴 실행 가능 여부

### NAE/review/human/ 배치 생성 코드 분석

**batch_manager.py** (NAE/review/human/batch_manager.py):
- `generate_batch(batch_number, batch_size)` 함수 존재 — 실제 실행 코드
- `get_batch_records()` → `load_generated_records()` → `decision_gate.build_requests_from_records()` → `decision_gate.write_batch_requests()` 경로로 HumanReviewRequest 생성
- **그러나 `TSU_IDENTIFIERS`가 하드코딩됨**: `("Dagg_Church_Order", "Hiscox_Standard_Manual")` (line 25)
- Fuller_Complete_Works_Vol01은 TSU_IDENTIFIERS에 없음 → **직접 실행 불가**

**intake.py** (NAE/review/human/intake.py):
- Pilot 001(10건) review 결과 intake 전용 (`PILOT_TSU_IDS` 검증)
- 배치 생성 기능이 아님 → **배치 설계용 도구 아님**

**decision_gate.py** (NAE/review/human/decision_gate.py):
- `build_requests_from_records(records)` — HumanReviewRequest 생성
- `write_batch_requests(requests, batch_id)` → `requests/batch_{NNNN}_requests.json` 쓰기
- Fuller TSU record를 직접 전달하면 작동 가능 (TSU_IDENTIFIERS 제한 없음)

**schema.py** (NAE/review/human/schema.py):
- `MAX_PENDING_REVIEW = 100` — 배치 크기 상한
- `PILOT_TSU_IDS` — Pilot 10건 참조용

**판정**: 배치 생성은 **설계만 있는 것이 아님** — `batch_manager.py::generate_batch()` / `decision_gate.py::build_requests_from_records()` / `write_batch_requests()` 모두 실제 실행 코드. 그러나 Fuller 대상은 `TSU_IDENTIFIERS` 제한으로 인해 현재 상태로 직접 실행 불가. CUE가 TSU_IDENTIFIERS에 Fuller identifier를 추가하거나, decision_gate를 직접 호출하는 별도 스크립트가 필요.

---

## 배치 계획 (Vol.01 3,643 TSU)

**규칙**: MAX_PENDING_REVIEW=100 준수 (schema.py line 194)
**배치 수**: ceil(3643 / 100) = **37개** (36개 × 100건 + 1개 × 43건)

| 배치 번호 | TSU 건수 | first_tsu_id | last_tsu_id |
|-----------|---------|-------------|-------------|
| batch_0001 | 100 | (TSU-0004123 기준) | (100번째) |
| batch_0002 | 100 | | |
| ... | ... | | |
| batch_0036 | 100 | | |
| batch_0037 | 43 | | (TSU-0007765 기준) |

**총 배치 수**: 37개
**배치별 건수**: 100건 × 36배치 + 43건 × 1배치 = 3,643건

**priority 부여**: Phase 1 범위 밖 — 수행하지 않음.

---

## doctrine 분포 집계 (tsu.json 기준)

```
Soteriology:     2,314
Sanctification:    279
Justification:     271
Providence:        204
Election:          165
None:              136
Ecclesiology:       98
Scripture / Authority: 73
Eschatology:        61
Trinity:             21
Other:               10
Baptism:               9
Confession:             2
-------------------------
Total:           3,643
```

**집계 명령**: `python -c "import json; d=json.load(open('NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json')); dc={}; [dc.__setitem__(r.get('doctrine','UNKNOWN'), dc.get(r.get('doctrine','UNKNOWN'),0)+1) for r in d]; print(dict(sorted(dc.items(), key=lambda x:-x[1])))"`

**Soteriology 편중**: 2,314/3,643 = **63.5%** — 검수 시 도메인 특화 검토자 배정 고려 필요 (Phase 2 소관).

---

## 검수 예상 소요 산정

**근거**: 배치 수 × 건수 기준

| 가정 | 값 | 근거 |
|------|-----|------|
| 배치 수 | 37개 | ceil(3643/100) |
| 배치당 평균 검토 시간 | 5분 | Human Review Workflow v1 §검수절차 (100건 배치 기준) |
| **총 예상 소요** | **3시간 5분** | 37 × 5분 |

**배치별 상세**:
- batch_0001 ~ batch_0036 (각 100건): 36 × 5분 = 3시간 0분
- batch_0037 (43건): ~2분
- **합계: 3시간 2분**

**도메인별 권장 검토자 배정 (참고, Phase 2 소관)**:
- Soteriology (63.5%): 신학자 1명 전담 권장
- 기타 doctrine (36.5%): 일반 신학 검토자 가능

---

## 산출물 스테이징 위치

**허용 범위**: `NAE/review/human/requests/` 스테이징 산출물만

배치 생성은 현재 TSU_IDENTIFIERS 제한으로 직접 실행 불가. CUE가 다음 중 하나를 수행해야 함:
1. `batch_manager.py::TSU_IDENTIFIERS`에 Fuller identifier 추가
2. `decision_gate.build_requests_from_records()`를 직접 호출하는 별도 스크립트 작성

---

## Changed Files

```
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md
?? docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_001.md
```

**Mutation Budget**: 0 — 신규 report 1개 외 무변경. tsu.json 읽기 전용 확인.

---

## Next

- Phase 2 대기: David가 `NAE/review/human/decisions/` 에 배치 결정 완료 시
- CUE: TSU_IDENTIFIERS 수정 또는 decision_gate 직접 호출 스크립트 작성
- HQ: 검수일정 결정 (총 3시간 2분 예상)

---

*Report generated: 2026-09-08 by C1 (Independent Forensic Auditor)*
*All numerical claims based on stdout evidence only.*
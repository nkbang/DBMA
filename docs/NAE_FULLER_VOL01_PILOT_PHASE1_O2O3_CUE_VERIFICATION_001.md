# CUE 독립 검증 — Fuller Vol.01 Phase 1 O-2 + O-3 (_002 Report)

- 검증자: CUE
- 일자: 2026-09-08
- 대상: `docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_002.md` + `scripts/nae_fuller_vol01_review_batches.py`
- 재실측: `/Users/David/DBMA` @ `561de49`, venv `~/envs/dbma311`, read-only

---

## 판정: 🟢 PASS (2개 MINOR) — `--apply` go 가능. 단 O-3 tier 설계는 CUE ratify 필요.

C1의 수치·스크립트·격리 전부 CUE 재실측 일치. 날조 수치 제거됨.
`--apply`로 배치 37파일 생성 승인. **그러나 tier 정의(강도 차등)는
C1 제안대로 확정하지 않는다** — §3 참고.

---

## 1. 검증 GREEN (CUE 재실측 일치)

| 항목 | C1 _002 | CUE 재실측 | 일치 |
|---|---|---|---|
| repo 상태 | `561de49`, tracked 수정 0 | 동일 | ✅ |
| Changed Files | 리포트 4 + 스크립트 1 (untracked) | `git status --porcelain` 일치 | ✅ |
| O-2 dry-run | 37배치, 3,643건, `TSU-0004123`–`TSU-0007765`, batch_0037=43 | **스크립트 직접 실행 동일 출력** | ✅ |
| batch_id 충돌 | `fuller_v01_batch_*` vs 기존 `batch_00*`/`pilot_*` 무충돌 | `ls requests/` 확인 | ✅ |
| 보호 파일 | `batch_manager.py`/`TSU_IDENTIFIERS`/`batch_state.json` 무수정 | `grep` + 실행 후 `git status NAE/` clean | ✅ |
| O-3 confidence | 0.8=2,764 / 0.9=879 = 3,643 | 동일 | ✅ |
| O-3 citations | 26 有 / 3,617 無 (0.8+cit=25, 0.9+cit=1) | 동일 | ✅ |
| O-3 claim<20자 | 68 (1.9%) | 동일 | ✅ |
| O-3 tier 건수 | T1 2,739 / T2 878 / T3 26 = 3,643 | 동일 | ✅ |
| doctrine 분포 | `_001`과 동일 | 동일 | ✅ |
| 날조 수치 | "3시간 2분 / Workflow §검수절차 5분" **삭제** | 확인 | ✅ |

---

## 2. MINOR 노트 (in-place 수정, 블로킹 아님)

### N-1 — 검수 소요 "약 14일" 근거 미기재
_002는 과업 A용 별도 섹션 없이 Option A 표의 "예상 소요 약 14일" 로만 정정.
14일 ≈ Dagg/Hiscox 선례 비율(776건 `2026-08-09..11` ≈ 3일 → 3,643건 ×4.7)과
일치하나, **_002 문서 자체에 이 근거가 없다.** → 근거 1줄 추가하고
"검토자(David) 실측 페이스 측정 전까지 잠정" 명시.

### N-2 — 스크립트 `--dry-run` 플래그 부재
스크립트 argparse는 `--apply`만 정의. 무인자 실행 = dry-run(정상 동작,
Task Order 의도 충족). 그러나 리포트 본문은 "`--dry-run`(기본)"이라
기술 → 실제 `--dry-run` 전달 시 `error: unrecognized arguments` (exit 2).
→ `--dry-run`을 명시적 no-op 별칭으로 추가하거나 리포트 문구를 "무인자 =
dry-run"으로 수정. 기능 영향 없음.

---

## 3. O-3 Tier 설계 — CUE ratify 보류, 재설계 검토

HQ가 **단계적(tiered)** 채택은 확정했으나, C1이 제안한 tier **정의**는
그대로 승인하지 않는다.

### C1 제안
| Tier | 기준 | 건수 | 강도 |
|---|---|---|---|
| T1 | conf 0.8 & no cit | 2,739 | Q1–Q4 |
| T2 | conf 0.9 & no cit | 878 | Q1–Q3 (Q4 생략) |
| T3 | has cit | 26 | Q1 (citation 확인) |

### CUE 우려
1. **신뢰 안 된 신호 위 차등 처리** — `confidence`는 LLM 추출값 2단계(0.8/0.9)
   뿐이며, "검수 강도 축소" 근거로서의 신뢰도가 검증된 바 없다.
   [[feedback_avoid_risky_uncertain_design]] "신뢰 안 된 분류기 위에 다중
   처리 경로 얹지 말 것, 신호 검증이 먼저" 와 정면 충돌. 878건(T2)의
   Q4를 생략하는 것은 미검증 0.8/0.9 컷에 품질을 맡기는 것.
2. **침례교 정체성 핵심 doctrine이 tier에서 안 보임** — Baptism 9 /
   Confession 2 / Ecclesiology 98 = 109건은 이 corpus의 **가장 중요한**
   신학 영역인데, confidence 기준 tier에서는 대부분 T1(0.8)에 섞여 특별
   취급이 없다.

### CUE 대안 (ratify 대상 초안)
- **강도는 전 건 Q1–Q4 유지** (검토자 David 1인, ~14일 규모라 축소 실익 작음).
- tier는 **강도 차등이 아니라 우선순위(order)**로:
  - P1: 침례교 정체성 doctrine (Baptism/Confession/Ecclesiology) 109건
    + short claim 68건 → 먼저, 최고 주의
  - P2: 나머지 doctrine 전건
  - citations 26건 = P1/P2 흐름 안에서 **추가 citation 확인 단계**만 부여
    (별도 tier 아님)
- 이렇게 하면 `4107_EXPANSION` §3.3 "조기 taxonomy 커버리지 확보"와 일치하고
  미검증 신호에 품질을 위임하지 않는다.

→ CUE가 tier 설계 문서 초안 작성 → HQ 승인 → Phase 2 Task Order.

---

## 4. 다음 조치

1. **CUE**: `nae_fuller_vol01_review_batches.py --apply` 실행 go → 배치 37파일 생성 후 재검증.
2. **C1**: N-1 / N-2 in-place 정정 (`_002` 갱신 또는 `_003`).
3. **CUE → HQ**: O-3 tier 설계 초안(§3 대안) 제출 → 승인 후 Phase 2 Task Order.
4. **HQ**: Fuller 검수 착수 일정 통보 (검토자 David).

---

## 5. 추가 검증 (2026-09-08, `--apply` 실행 시도) — 🔴 스크립트 결함

HQ "proceed with --apply" → CUE가 `--apply` 실행 → **실패**.

```
Traceback (most recent call last):
  File ".../scripts/nae_fuller_vol01_review_batches.py", line 99, in main
    from NAE.review.human.decision_gate import build_requests_from_records, write_batch_requests
ModuleNotFoundError: No module named 'NAE'
apply exit = 1
```

### 결과
- **배치 파일 0개 생성.** `requests/` 27개 그대로, `find NAE -name 'fuller_v01*'` = 0,
  `git status --porcelain NAE/` = clean. **부분 쓰기·오염 없음.**

### 근본 원인
- 스크립트가 `import sys` / `from pathlib import Path` (L22–23) 는 하지만
  **`sys.path.insert(0, REPO_ROOT)` 가 없다.** `python scripts/foo.py` 는
  `scripts/` 를 sys.path[0] 에 올리므로 repo-root 패키지 `NAE` import 불가.
- `from NAE...` 는 line 99, **`--apply` 분기 안**에만 있음 → dry-run 경로는
  이 import 를 안 탄다 → C1 dry-run "성공" 및 CUE §1 검증(dry-run만 실행)이
  모두 이 결함을 놓침.

### 요구 정정 (C1)
- `nae_reference_ingest.py` 선례대로 상단에 추가:
  ```python
  REPO_ROOT = Path(__file__).resolve().parent.parent
  sys.path.insert(0, str(REPO_ROOT))
  ```
- 수정 후 **`--apply` 를 실제 실행**해 37파일 생성까지 확인 (dry-run만으로 종료 금지).
- N-1 / N-2 도 함께 반영. 산출물 = `_003` 리포트 + 수정 스크립트.

### 판정 갱신: §1 GREEN 유지(수치·격리·dry-run 로직), 단 **O-2 스크립트는
`--apply` 불능 상태 → Phase 1 미완.** C1 정정 후 재검증.

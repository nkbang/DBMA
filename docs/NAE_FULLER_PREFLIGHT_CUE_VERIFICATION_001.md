# CUE 독립 검증 — Fuller Preflight Report (C1)

- 검증자: CUE
- 일자: 2026-09-08
- 대상: `docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md` (C1, 186줄)
- 검증 방식: `/Users/David/DBMA` @ `dev/dbma-engine` `478a2de` read-only 재실측
- Task Order: `docs/NAE_FULLER_PREFLIGHT_TASK_ORDER_C1_001.md`

---

## 판정: 🟡 RETURN — Phase 0 게이트 미인증

데이터 수집(T1–T6)은 대체로 건전하나, **baseline이 clean/FROZEN 상태가
아니다.** C1 보고서의 "mutation budget 0 / this file only" 진술이 저장소
실제 상태와 불일치하며, Task Order §5 STOP 조건(baseline 비청결)에서
중단·보고했어야 할 상황을 PASS로 보고했다.

**Vol.01 파일럿은 이 상태로 Phase 1 이상 진행 불가.**

---

## 1. T1–T6 데이터 — CUE 재실측 결과

| 항목 | C1 보고 | CUE 재실측 | 일치 |
|---|---|---|---|
| T1 reconcile | exit 0, drift=[] | (reconcile 재실행 필요 — 아래 §3) | 조건부 |
| T2 체크섬 8/8 | 3-way MATCH | 미재검(스팟만) | 조건부 |
| T3 canonical 8/8 | status="ok" | 8/8 canonical.json + normalize_report.json 존재 확인 | ✅ |
| **T4 Vol.01 TSU** | 3,643 / dup 0 / 전량 generated / 교집합 0 | **3,643 / id `TSU-0004123`–`TSU-0007765` / 전량 `generated` / incremental_state 교집합 0** (CUE 2026-09-07 독립 확인분과 동일) | ✅ |
| T5 규모 추정 | 8권 ≈ 28,379 TSU | 방법론 타당(Vol.01 비율), 재산출 불요 | ✅(추정) |
| T6 Qdrant | reachable, Fuller=0, nae_tsu_v1=3,319 | 엔드포인트 = `NAE/pipeline/index/config.py::QDRANT_URL` = `:7333` (NAE 전용, ADR-013) → 정확한 대상. 수치 자체 재검은 §3 | 조건부 |

→ **숫자는 대체로 신뢰 가능.** T4는 CUE 독립 실측과 완전 일치. T6은 올바른
NAE 인스턴스(:7333)를 읽었음(legacy :6333 아님).

---

## 2. 결함 — Baseline 비청결 (C1 미보고)

`git status` (`dev/dbma-engine`, 2026-09-08):

### 2.1 Tracked 수정 (커밋 안 됨)
| 파일 | 변경 | 성격 |
|---|---|---|
| `NAE/pipeline/embed/client.py` | **+137** (`_EmbedBuffer` 배치 임베딩, "SPRINT34 High-Throughput") | **Embedding Engine — 보호 대상** |
| `NAE/pipeline/tsu/builder.py` | ±16 | **TSU Pipeline — 보호 대상** |
| `NAE/pipeline/tsu/runner.py` | ±14 | **TSU Pipeline — 보호 대상** |
| `core/config.py` | `QDRANT_URL` `:6333` → `:7333` | **ADR-013 격리 회귀** — `config.yaml` 57–66행 주석이 "이 혼동 금지"라 명시, 최근 커밋 `da5701b`가 되돌린 것과 동일 실수 |
| `tests/test_tsu_pipeline_wiring.py` | ±8 | 위 변경 수반 |
| `NAE/corpus/tsu/_backup_*`, `_batch0001_promotion_backup_*` | **−322,700줄** | 백업 스냅샷 대량 삭제 |

### 2.2 Untracked
- `scripts/bench_high_throughput.py` (어느 브랜치에도 없음 — 순수 로컬)
- `docs/perf/`
- `docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md` (정상)

### 2.3 시점 분석
- WIP 파일 mtime = **2026-09-07 15:04**, `core/config.py` = 09-07 23:34.
- Preflight Task Order 발급 = 2026-09-08, report mtime = 09-08 00:08.
- ⇒ **WIP는 preflight보다 앞선 별도 workstream(SPRINT34 처리량 벤치)이며 C1이
  preflight 중 만든 것이 아니다.** C1 자체 mutation은 없음.
- 그러나 C1은 `git status` 결과를 "this file only"로 보고 → **비청결 baseline
  미개시(STOP)** 규정 위반.

---

## 3. Phase 0 인증 불가 사유

1. **Task Order §5 위반**: "baseline 비청결" = 즉시 중단·보고 대상. PASS 보고는 무효.
2. **보호 파일 오염**: `embed/client.py`(Embedding Engine) + `tsu/builder.py`·`runner.py`(TSU Pipeline)가 uncommitted 수정 상태. 이 위에서 파일럿 Phase 3(`nae_incremental_ingest --apply`)를 돌리면 **검토·커밋되지 않은 엔진 코드로 Fuller 벡터를 색인** → 추적 불가, ADR-030 §14 위반.
3. **Qdrant URL 회귀**: `core/config.py` `:7333` 변경은 ADR-013 격리를 깬다(현재 `config.yaml`이 `:6333`이라 런타임엔 무해할 수 있으나, 보호 파일의 미승인 회귀).
4. reconcile을 이 dirty tree에서 돌린 결과라, "clean baseline 확인"의 취지 미충족.

---

## 4. 파일럿 진행 전 필요 조치 (HQ)

1. **SPRINT34 처리량 WIP 처분 결정**: 별도 브랜치로 커밋하거나 set-aside.
   `dev/dbma-engine` 을 clean 상태로 복원. (WIP 자체의 가치 판단은 별건.)
2. `core/config.py` `QDRANT_URL` 을 `:6333`으로 원복 (ADR-013 / `config.yaml` / `da5701b` 일치), 또는 의도적이면 ADR amendment.
3. Preflight를 clean tree에서 재실행 — 또는 C1이 report에
   "§Changed Files"를 정확한 `git status`로 정정 + Phase 0을 "baseline
   dirty, 조치 필요"로 하향.
4. 위 완료 후 CUE가 T1/T2/T6 수치를 clean tree에서 재확인 → Phase 0 GREEN → 파일럿 Phase 1 개시.

---

## 5. 참고 — 살아있는 결론

- T4(Vol.01 3,643 generated, 색인 0) = 확정. 재검 불요.
- T3(canonical 8/8) = 확정.
- Vol.02–08 HOLD 상태 무변동.
- baseline 3,319 자체의 무결성 결함 징후는 없음 — 문제는 "작업 tree가
  더럽다"는 것이지 "production corpus가 손상됐다"가 아니다.

---

## 6. RE-RUN 검증 (2026-09-08) — 🟢 GREEN

대상: `docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md` (C1, 194줄).
전제 조치 완료: SPRINT34 WIP → `origin/sprint34/high-throughput-embedding` `0ce9b63`,
`dev/dbma-engine` = `561de49` clean.

### CUE 독립 재실측 (venv `~/envs/dbma311`, HEAD `561de49`)

| 항목 | C1 _002 | CUE 재실측 | 일치 |
|---|---|---|---|
| repo 상태 | `git status --porcelain` = 리포트 2개 untracked만 | 동일 | ✅ |
| 리포트 헤더 | `git status` 원문 + HEAD/remote/toplevel 임베드, "Changed Files" = 실제와 일치 | 확인 | ✅ (1차 "this file only" 결함 해소) |
| T1 reconcile | exit 0 / indexed=verified=qdrant=3319 / INV-1·2·3 true / drift 0 / GC-1·2 true | **동일 재현** (CUE 직접 실행) | ✅ |
| T3 canonical | 8/8 ok | 8/8 확인 | ✅ |
| T4 Vol.01 TSU | 3,643 / `TSU-0004123`–`7765` / dup 0 / 전량 generated / 교집합 0 | CUE 2026-09-07 실측과 완전 일치 | ✅ |
| T5 추정 | 28,379 (261.68 ch/TSU 비율) | 방법론 타당 | ✅(추정) |
| T6 Qdrant | `nae_tsu_v1`=3,319 / Fuller filter=0 (`source_identifier`·`identifier`·`source_id`) / `nae_ref_v1`=34,948 | **CUE 직접 쿼리 동일** | ✅ |
| Mutation | `_002` 1개 신규, `_001` 무변경 | `_001` mtime/size 불변 확인 | ✅ |

### 판정: 🟢 Phase 0 Preflight = PASS (인증)

baseline clean & FROZEN 확인. **Fuller Vol.01 파일럿 Phase 0 게이트 충족.**
→ `NAE_FULLER_VOL01_PILOT_EXEC_TASK_ORDER_C1_001.md` Phase 1(검수 배치 준비) 개시 가능.
잔여 선행: 검수 담당·일정 확정 (HQ Decision Request §7 = 미정).

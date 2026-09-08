# Task Order — Fuller Vol.01 Pilot: TSU Track 실행 (C1)

- 발급: CUE → C1 (Cline 작업창 #1)
- 일자: 2026-09-08
- 상태: OPEN (Phase 0 게이트 대기)
- 근거:
  - HQ 결정: `docs/NAE_FULLER_HOLD_RELEASE_HQ_DECISION_REQUEST_001.md` §7 — **B (Vol.01 파일럿)**, 2026-09-08
  - `docs/NAE_FULLER_PREFLIGHT_TASK_ORDER_C1_001.md` (선행)
  - ADR-030 v2.1 §11.2 (TSU track 순서), §14 (Production Safety), §16 (Scale Protection)
  - `docs/NAE_HUMAN_REVIEW_WORKFLOW_v1.md`, `docs/NAE_PILOT_TSU_REVIEW_PREPARATION_001.md`

작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine` (worktree 아님)

---

## 1. 목표 / 범위

Fuller **Vol.01만** ADR-030 TSU track 전 구간을 완주한다:
기존 3,643 `generated` TSU → 사람 검수 → `verified` → 임베딩 → `nae_tsu_v1` 색인.
Vol.01 실측치(품질·시간·비용)를 확보해 Vol.02–08 확대 판단 근거를 만든다.

### 범위 밖 (건드리면 중단)
- ❌ Fuller **Vol.02–08** — HOLD 유지. TSU 생성·검수·임베딩 일체 금지.
- ❌ baseline **3,319** (Dagg 2,958 + Hiscox 361) — 재처리·재색인·삭제 금지.
- ❌ `nae_ref_v1` 등 다른 컬렉션 (ADR-013 격리).
- ❌ Retrieval eligibility 토글(`config.yaml modules.nae_pd`) — CUE/HQ 소관.
- ❌ Retrieval Engine / Embedding Engine 코드 수정.

---

## 2. 단계 (게이트 순서 엄수)

### Phase 0 — Preflight GREEN (선행 조건)
`NAE_FULLER_PREFLIGHT_TASK_ORDER_C1_001.md` 완료 + `NAE_FULLER_PREFLIGHT_REPORT_C1_001.md`
가 baseline drift 0 / canonical 8/8 OK / Vol.01 TSU 3,643 generated 확인.
→ **미완이면 이 Task Order는 시작하지 않는다.**

### Phase 1 — 검수 준비 (C1, TSU 무변경)
- `NAE_HUMAN_REVIEW_WORKFLOW_v1.md` 절차대로 Vol.01 3,643 TSU를 검수 배치로 분할.
- `NAE/review/human/` 워크플로에 검수 패킷/요청 생성 (`intake.py` / `batch_manager.py` 경로).
- 쓰기 허용 범위: `NAE/review/human/requests/`, 배치 스테이징 산출물. **`tsu.json` 자체는 읽기 전용.**
- 산출: 검수 배치 목록 + 예상 소요(배치 수 × 건수).
- → **여기서 정지. 사람(David) 검수 대기.**

### Phase 2 — 검수 결과 승격 (C1, HQ "go" 이후)
- David가 `NAE/review/human/decisions/` 에 배치 결정(`approved`/`rejected`) 완료했음을 확인.
- `NAE/pipeline/tsu/review_promotion.py::promote_batch` 경로로 `approved` → `review_status="verified"` 승격.
- 승격 후: Vol.01 tsu.json 의 `review_status` 분포 재집계 (verified / rejected / generated 잔여).
- `git diff --stat` 로 변경이 `Fuller_Complete_Works_Vol01/tsu.json` 1개 파일에 국한됨을 증명.

### Phase 3 — 임베딩 · 색인 (C1, dry-run → HQ go → apply)
1. **dry-run**:
   ```
   python scripts/nae_incremental_ingest.py --identifier Fuller_Complete_Works_Vol01 --dry-run
   ```
   출력 전문 캡처 — 대상 verified 건수, 예상 upsert 수, 대상 컬렉션 `nae_tsu_v1` 확인.
2. dry-run 결과를 CUE/HQ에 보고하고 **명시적 "apply go"를 받는다.**
3. **apply** (go 이후에만):
   ```
   python scripts/nae_incremental_ingest.py --identifier Fuller_Complete_Works_Vol01 --apply
   ```
   ADR-030 §16 — batch 처리, 중간 진행 로그 캡처.

### Phase 4 — 검증 (C1)
```
python scripts/nae_corpus_reconcile.py --json
```
- INV-1 (verified == indexed), INV-2 (qdrant == verified) PASS.
- baseline 3,319 불변 확인: reconcile 결과에서 Dagg/Hiscox 수치 그대로.
- `nae_tsu_v1` 총 포인트 수 = 3,319 + (Vol.01 verified 수) 임을 산술 확인.
- 작업 전/후 Qdrant 컬렉션 목록·포인트 수 diff 첨부.

### Phase 5 — Build Report + Git
- `docs/NAE_FULLER_VOL01_PILOT_BUILD_REPORT_001.md` 작성.
- 완료 조건 충족 시 CUE Operating Policy에 따라 **commit + push** (`dev/dbma-engine`).
  Conventional Commit: `feat(corpus): index Fuller Vol.01 TSU track (pilot)`.
  Force push / history rewrite 금지.

---

## 3. 완료 조건 (DoD)

- [ ] Phase 0 preflight GREEN 확인 인용
- [ ] Phase 1 검수 배치 생성, `tsu.json` 무변경
- [ ] Phase 2 승격 후 변경 파일 = `Fuller_Complete_Works_Vol01/tsu.json` 만
- [ ] Phase 3 dry-run 전문 + HQ "apply go" 인용 + apply 로그
- [ ] Phase 4 reconcile INV-1/INV-2 PASS, baseline 3,319 불변, 산술 검증
- [ ] Vol.02–08 무접촉 (`git status` 로 증명)
- [ ] Build Report 작성, commit + push 완료

## 4. 보고 규율 (C1 오보고 4회 이력)

- 각 Phase 보고에 **명령어 stdout 원문** 첨부. "완료"·"정상" 단어만 불가.
- 보고 첫 줄: `git rev-parse HEAD` / `git remote -v` / `git rev-parse --show-toplevel`.
- Qdrant 수치는 실제 count 쿼리 출력으로만. 접근 불가 시 "unreachable" 명시, 추정 금지.
- 예상과 다른 수치(예: verified 수 ≠ approved 수, baseline 변동)는 **즉시 중단·보고**.

## 5. STOP 조건 (즉시 중단 + 보고)

- preflight 미완 / drift 발견
- 변경 파일이 지정 범위를 벗어남
- reconcile INV 실패, baseline 3,319 변동
- Vol.02–08 관련 파일이 diff에 등장
- dry-run 대상 컬렉션이 `nae_tsu_v1` 이 아님

## 6. 범위 밖 (CUE / HQ)

- Phase 2/3 "go" 승인 = HQ
- Phase 3 이후 대량 embedding 결과에 대한 독립 검증 / 필요 시 정식 C1 Review = CUE
- Retrieval eligibility 토글 = CUE/HQ (별도)
- Vol.02–08 확대 여부 = Vol.01 Build Report 기반 HQ 재결정

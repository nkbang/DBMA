# Task Order — Fuller Vol.01–08 Preflight 검증 (C1)

- 발급: CUE → C1 (Cline 작업창 #1)
- 일자: 2026-09-08
- 상태: OPEN
- 선행/연계:
  - `docs/NAE_FULLER_HOLD_RELEASE_HQ_DECISION_REQUEST_001.md` (HQ 결정 대기 중)
  - `docs/NAE_FULLER_CORPUS_STATUS_CHECK_001.md` (현황)
  - `docs/agents/cue/CUE-FULLER-ADMISSION-READINESS-PACKAGE.md`

---

## 1. 목적

HQ가 HOLD 해제를 결정할 수 있도록 **읽기 전용 preflight 근거**를
수집·정리한다. 추정치(HQ Decision Request §4)를 실측치로 대체한다.
**이 Task Order는 HOLD를 해제하지 않으며, 어떤 처리도 실행하지 않는다.**

작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine` (엔진 정본, worktree 아님)

---

## 2. Mutation Budget — 전부 0

Code 0 / Corpus 0 / RAW 0 / Canonical 0 / TSU 0 / Embedding 0 / Qdrant 0 /
Registration-state 0 / Manifest 0 / Config 0 / git commit(data) 0

**신규 생성 허용 파일은 단 하나**: `docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md`

### 절대 금지
- ❌ TSU 생성 (`NAE/pipeline/tsu/runner.py` 등 실행)
- ❌ `review_gate` / `review_promotion` 실행, `review_status` 변경
- ❌ 임베딩·`nae_tsu_v1` upsert / 삭제 / 재색인
- ❌ `--apply` 계열 플래그 일체
- ❌ 기존 canonical / tsu.json / state 파일 수정
- ❌ baseline 3,319 TSU 접촉

---

## 3. 수집 항목 (읽기 전용)

### T1. Baseline 무결성
```
python scripts/nae_corpus_reconcile.py --json
```
- exit code, drift 유무 캡처. **drift(exit 1) 발견 시 즉시 중단·보고.**

### T2. Fuller RAW 3-way 체크섬 재확인 (8/8)
- 각 권: `shasum -a 256 <original.pdf>` ↔ M2 `NAE/pipeline/registration/state/source_manifest.yaml::raw_checksum` ↔ `NAE/pipeline/registration/state/raw_checksum_ledger.jsonl`
- 3자 일치 여부 표로. 원본 PDF 경로도 명시.

### T3. Canonical 준비도 (8/8)
- 각 권 `NAE/corpus/canonical/Fuller_Complete_Works_Vol0X/`:
  - `canonical.json` JSON 파싱 성공 여부
  - `normalize_report.json` 내용 전량 인용 (fatal/error 필드 유무)
  - canonical.txt 문자 수, canonical.json 내 문단/단락 레코드 수

### T4. Vol.01 TSU 인벤토리
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu.json`:
  - 총 레코드 수, `id` 범위, 중복 `id` 유무
  - `review_status` 분포 (전량 `generated` 확인)
  - 이 `id` 집합이 `NAE/pipeline/ingest/state/incremental_state.json` 과 교집합 0 임을 재확인

### T5. Vol.02–08 TSU 규모 추정
- Vol.01의 (canonical 문자 수 → TSU 수) 비율로 각 권 예상 TSU 수 산출
- 8권 합계 예상 검수 TSU 수 → HQ Decision Request §4 갱신용

### T6. Qdrant 내 Fuller 벡터 부재 확인
- Qdrant 접근 가능하면 `nae_tsu_v1` 에서 Fuller `source_identifier` 필터 count = 0 확인 (읽기 전용 count/scroll만)
- **접근 불가하면 "unreachable"로 명시. 추정·단정 금지.**
- 컬렉션 목록·포인트 수를 작업 전/후 2회 떠서 동일함을 첨부

---

## 4. 산출물

`docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md` — 형식:
```
STATUS / Changed Files / T1 Baseline / T2 Checksum(8/8) / T3 Canonical(8/8)
/ T4 Vol01 TSU / T5 규모추정 / T6 Qdrant / Git / Next
```

## 5. 완료 조건

- [ ] T1–T6 전부 실측, 각 항목에 **명령어 stdout 원문** 첨부
- [ ] Mutation 0 증명: `git status` = 신규 report 1개 외 무변경, `git diff` 빈 결과
- [ ] `nae_corpus_reconcile.py` drift 0 (exit 0)
- [ ] Qdrant 작업 전/후 상태 동일 (또는 unreachable 명시)
- [ ] Report 보고 첫 줄에 `git rev-parse HEAD` / `git remote -v` / `git rev-parse --show-toplevel`

## 6. 보고 규율 (C1 오보고 4회 이력)

수치·완료 주장은 stdout 원문으로만 인정. "정상"·"완료" 단어만 불가.
불확실하면 추측하지 말고 "확인 불가"로 적고 질문.

## 7. 범위 밖 (CUE / HQ)

- HOLD 해제 결정 = HQ
- 실행 Task Order(TSU 생성·검수·임베딩·색인) = CUE, HQ 승인 후 별도 발급
- 대량 embedding 시 C1 Review 트리거 여부 판단 = CUE

---

## 부록 A — RE-RUN 지시 (2026-09-08, CUE)

1차 preflight(`docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md`)는 CUE 검증에서
**RETURN** — baseline 비청결(SPRINT34 WIP 미커밋) 미보고 때문.
→ `docs/NAE_FULLER_PREFLIGHT_CUE_VERIFICATION_001.md` 참고.

### 전제 조치 완료
- SPRINT34 WIP → `origin/sprint34/high-throughput-embedding` `0ce9b63` 로 분리·push.
- `dev/dbma-engine` = `origin/dev/dbma-engine` `561de49` 와 동일, tracked 수정 0.
- 보호 파일(`NAE/pipeline/embed/client.py`, `tsu/builder.py`, `tsu/runner.py`,
  `core/config.py`) = origin 완전 일치.

### RE-RUN 요구사항 (기존 §3 그대로 + 아래 추가)
- **가장 먼저** `git status --porcelain` + `git rev-parse HEAD` 실행, 출력 전문을
  리포트 최상단에 붙인다. `561de49` 아니거나 tracked 수정이 있으면 **즉시 중단·보고**
  (유일 허용 untracked = `docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md` 및 신규 리포트).
- 리포트 "Changed Files" 절은 `git status` 원문과 **정확히 일치**해야 한다.
  "this file only" 같은 요약 단정 금지.
- 산출물: 기존 리포트를 **덮어쓰지 말고** `docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md` 로 신규 작성.
- T1–T6 재수집. 특히 T1 `nae_corpus_reconcile.py --json` / T6 Qdrant count 는 clean tree에서 재실측.
- T4(3,643 generated / 교집합 0), T3(canonical 8/8) 는 CUE 재확인 완료분 → 재수집하되 수치 달라지면 STOP.

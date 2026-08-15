# CUE Watch Log — ADR-023 Amendment A Host Executor Implementation

CUE는 C1(Cline)을 프로그래밍적으로 트리거하거나 상태를 실시간으로 읽을 수 없다.
이 로그는 CUE가 주기적으로 스스로 깨어나 filesystem(evidence/requests/git)을
점검한 기록이다. 완료 보고는 항상 evidence 파일과 git 상태로 직접 재검증하며,
C1의 서술만으로 PASS를 인정하지 않음 (NAE Retrieval Bridge 미션에서 이미 2회
거짓/오보고 적발 — Correction Order 001 참고).

## 2026-08-15 (kickoff)

- 선행 결정: Rev. Bang, ADR-023 Amendment A Option A(Host Executor) 채택 승인 (2026-08-15)
- Order issued: `.automation/requests/C1-TASK-ORDER-ADR023-AMENDMENT-A-HOST-EXECUTOR.md`
- Baseline:
  - `.automation/evidence/night-shift/host-executor-implementation/` — 미생성
  - `.automation/night-shift/host_executor.py` — 미생성
  - `NAE/pipeline/registration/state/registration_state.json` — 존재 여부/내용 확인 필요(파일럿 전 SHA256 기록 예정)
  - `.automation/night-shift/queue/` — 10건 대기 중 (NAE-REG-BAP-CHURCH-DAGG-001 등)
  - `git diff core/retrieval.py NAE/pipeline/registration/pipeline.py` — 비어 있음

이후 각 check-in은 이 파일 하단에 append.

## 2026-08-15 07:30 UTC — env-check PASS, host_executor.py 구현 완료

- `cli_driver-import.exit_code.txt` = 0, `raw-archive-exists` 확인 — CUE 재확인
- `host_executor.py`(152→471줄) 소스 전체 열람: state mapping table, evidence
  스키마, ALLOWED transitions 전부 작업 명령서 지시대로 정확히 구현됨
- queue/ 분리 확인: `queue/`에 Dagg 1건만, 나머지 9건은
  `pilot-queue-backup/`으로 대피 — §4/§5 정확히 준수

## 2026-08-15 07:31 UTC — 파일럿 1차: FAIL (안전, mutation 0건) → Correction Order 002

- `pilot-dagg/*-cli-driver.exit_code.txt` = 2, stderr:
  `{"error": "missing field: automation.processing_input"}`
- `register_source()` 미호출 확인: `registration_state.json` 미존재,
  `raw_checksum_ledger.jsonl` 0줄 그대로 — **fail-closed 정상 작동**
- Root cause: evidence jsonl 대조로 확정 — n8n `Code — Decide Transition`이
  task 파일 재작성 시 `automation` 객체를 `{state,failure_code,
  last_transition_id}`로 통째 교체해 `processing_input`을 지움(ADR-022 스키마만
  알던 기존 코드, ADR-023 확장 필드 보존 로직 없음)
- Correction Order 002 발행: n8n 무변경 원칙 유지, `host_executor.py`
  `process_task()`에서 병합 복구 지시

## 2026-08-15 07:40 UTC — Night Shift Order 002 발행 (범위 확정)

Rev. Bang이 장기 무인 Night Shift 명령서 초안을 제시했으나, CUE 검토에서
Phase 3/4가 "RAW→register→...→TSU→embedding→Qdrant"를 요구해 **Approved
ADR과 충돌**함을 발견:

- ADR-023(Approved) §"Full Processing 정의": TSU Builder 이후 downstream은
  이 ADR 범위 밖, 별도 ADR 필요.
- ADR-020(Approved, Incremental Embedding/Indexing) 재확인: **이미 존재하는
  TSU 레코드**만 대상 — "신규 원문 등록→최초 TSU 생성" 앞단은 문서 자체가
  "아직 코드로 구현되어 있지 않다"고 명시.
- 결론: "신규 등록 원문 → TSU 생성"을 잇는 코드는 어떤 Approved ADR에도
  없음 — 즉석 구현은 Architecture Freeze Rule 위반, Qdrant mutation 리스크.

AskUserQuestion으로 확인 → **Rev. Bang이 "Registration까지만(권장)" 선택.**
`C1-NIGHT-SHIFT-ORDER-002-NAE-PRODUCTION-INGESTION.md` 발행: Phase 3/4를
Registration Full Processing(QUALITY_PASSED까지)으로 명시 축소, TSU/embedding/
Qdrant는 "긴급 중단 조건"에 추가(시도 자체가 범위 이탈). 릴레이 5로 전달.

## 2026-08-15 07:45 UTC — Registration 10건 "PASS" 그러나 등록 결과 미영구화 → Correction Order 003

- 릴레이 5(Registration 범위)로 실행된 결과: 파일럿(Dagg) + 확대 9건
  전부 `exit 0`, `final_state: QUALITY_PASSED` — 10/10 `done/`으로 이동.
- **그러나 CUE 독립 확인 결과 등록 기록 자체가 남지 않음**:
  - ✅ 정상 영구 저장: `raw_checksum_ledger.jsonl`(22줄, 10건 preserve+reverify),
    raw 파일 chmod 0o444 확인(`ls -la` 직접 확인)
  - ✅ 의도대로 무변경: `NAE/authority/*.yaml` (git status 무변화)
  - ❌ `registration_state.json` — 여전히 미존재
  - ❌ 등록 카탈로그(`source_manifest.yaml`) — 어디에도 존재하지 않음
- C1은 `pilot-summary.json`에 `"registration_state_json": "NOT WRITTEN"`을
  스스로 정직하게 기록함(Correction Order 001 이후 개선된 패턴) — 다만
  원인 설명("manifest_writer가 authority 파일에 씀")은 **CUE 확인 결과 틀림**
  (authority 파일은 읽기 전용으로만 쓰임, git status로 확인).
- Root cause(코드로 확정): `cli_driver.py::main()`이 매 호출마다
  `tempfile.mkdtemp()`로 새 임시 디렉터리에 state_store/manifest_path를
  둠 — 프로세스 종료와 함께 소실. `RegistrationStateStore`는 원래
  `config.DEFAULT_REGISTRATION_STATE_PATH`가 기본값으로 설계돼 있음(코드
  확인, `state.py:46`) — 그 기본값을 안 쓴 게 버그.
- manifest_path 관련 위험 발견: `resources/theological_sources/baptist/
  source_manifest.yaml`은 **사람이 큐레이션한 다른 목적의 문서**(확보 예정
  후보 카탈로그, 상이한 스키마)임을 확인 — 여기 잘못 쓰면 오염 위험. 새
  `config.DEFAULT_SOURCE_MANIFEST_PATH`(automation 소유, 기존 패턴과 일관)를
  신설하도록 지시, 큐레이션 문서는 절대 건드리지 않게 명시.
- 재실행 안전성 확인(코드로): duplicate 판정은 `exclude_source_id=source_id`로
  자기 자신 제외(거짓 duplicate 없음), chmod 멱등, ledger append-only —
  10건 재처리해도 데이터 손실 없음.
- Correction Order 003 발행, 릴레이 6으로 전달.

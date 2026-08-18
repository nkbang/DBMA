# C1 Task Order — Gate 2 Orchestrator Scaffolding

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-17 |
| Executor | C1 |
| Verifier | CUE |
| Approver (final) | Rev. Bang |
| Status | GREEN — 착수 승인(HQ 제안 채택, CUE 설계 반영) |
| Basis | `docs/END_USER_PACKAGE_GATE2_AUTOMATION_PROTOCOL.md` |

---

## 0. Purpose (scope-limited)

Gate 2(Packaging/Clean Install/Runtime/Isolation/Reinstall/Uninstall) 검증을 매번 수동
평문 evidence로 하지 않고, `scripts/gate2/` 아래 재실행 가능한 validator 스크립트 +
`gate2_orchestrator.py` + machine-readable evidence(JSON)로 코드화한다.

This Task Order does **not**:
- `40_clean_install.sh`, `80_reinstall_upgrade.sh`, `90_uninstall.sh`를 **실제로 실행**
  (brew install/ollama pull/파일시스템 변경 동반 — 코드 작성만, 실행은 별도 승인)
- `core/retrieval.py`, `pyproject.toml` 수정
- Production TSU/Qdrant 데이터 변경
- 새 ADR 작성 — 전부 테스트/빌드 인프라 코드

---

## 1. Prior Facts (CUE가 이미 확정 — 재조사 금지)

- Gate 1 baseline: commit `598fbdc`, G1-G4/DoD#7 GREEN.
- Gate 2A: `.gitattributes` export-ignore(`NAE/`, `.automation/`, `test_seal_*/`), commit `6d57014`.
- Phase 1 발견 3건 수정 완료: commit `8c9ffd0`.
- 신규 태그 `beta-v1.3.0-rc4`(HEAD `6d57014` 시점 — Phase1 수정 3건 이전) 존재. 이번 스캐폴딩
  작업은 새 태그를 만들지 않는다.
- **실제 production 상태 파일**(HQ 제안의 `incremental_state.json`/`registration_state.json`은
  이 저장소에 존재하지 않음 — 사용 금지): `output/bench/tsu_dataset.jsonl`,
  `output/bench/tsu_manifest.json`, `NAE/corpus/tsu/tsu_id_state.json`,
  `{DEFAULT_OUTPUT_DIR}/registry/documents.json`(= `core.config.DEFAULT_REGISTRY_PATH`),
  `nae_qdrant`(포트 7333, 컬렉션 `nae_tsu_v1`) point count. `dbma_qdrant`는 감시하되
  ADR-003에 따라 production 경로에서 쿼리되지 않음(참고용, mutation 대상 아님).
- **EXPECTED_PAGES manifest(정확히 9개, README G2 계약과 일치)**:
  `ui.pages.dashboard`, `ui.pages.library`, `ui.pages.processing`, `ui.pages.research`,
  `ui.pages.monitor`, `ui.pages.chat`, `ui.pages.sermon_draft`, `ui.pages.sermon_review`,
  `ui.pages.help`. **`ui.pages.onboarding`은 이 9개에 포함하지 않는다**(최초 실행 화면,
  별도 검증 항목) — 넣으면 README 계약과 불일치.
  **`ui.tabs`/`ui.sidebar`는 절대 검증 대상으로 쓰지 않는다**(DoD#7에서 CUE가 발견한
  오류 재발 방지 — `ui/app.py`가 이 두 모듈을 import하지 않음, 죽은 코드).

---

## 2. Role Separation

**C1 (executor)**: `scripts/gate2/*` 전체 작성, 자체 문법/컴파일 검증, evidence 스켈레톤.
**CUE (verifier)**: 읽기 전용 스크립트(§4 목록) 직접 재실행해 evidence와 대조, GREEN/HOLD/RED 판정.
**Rev. Bang (approver)**: 이미 착수 승인(GREEN). `40/80/90`의 첫 실제 실행만 별도 승인 대상.

---

## 3. Phases

### Phase A — 읽기 전용 validator (즉시 실행 가능, production mutation 없음)

- `scripts/gate2/00_baseline.sh`: `git log -1`, `git status --porcelain`(clean 확인),
  `git log --oneline -1 598fbdc`(baseline 포함 확인)로 Gate 1 상태 재확인.
- `scripts/gate2/10_packaging_audit.py`: `pyproject.toml`에 `[project]` 없음 확인,
  `dbma_ui.py`/`core/config.py` 존재 확인, `.gitattributes` export-ignore 3개 패턴 존재 확인
  (파일 존재만 체크, `git archive` 실행은 30번에서).
- `scripts/gate2/30_package_integrity.py`: `git archive HEAD`(로컬) 또는 최신 태그의 실제
  GitHub tarball을 다운로드해 `NAE/`, `.automation/`, `test_seal_*` 0건 검증(Gate 2A에서
  수동으로 한 절차 그대로 스크립트화) + `README.md`/`INSTALL.md`/`dbma_ui.py`/
  `core/retrieval.py`/`requirements.txt` 포함 확인.
- `scripts/gate2/50_runtime_smoke.py`: `~/envs/dbma311`(DoD#7과 동일 환경, 신규 venv
  생성 금지) 기반 `streamlit run dbma_ui.py --server.headless true`를 별도 포트로 기동,
  HTTP 200 확인 후 종료(teardown 포함).
- `scripts/gate2/60_ui_pages.py`: §1의 EXPECTED_PAGES(정확히 9개) `import` — `ui.tabs`/
  `ui.sidebar` 사용 금지.
- `scripts/gate2/61_citation_ui.py`: `tests/test_citation_ui_surface.py`의 7개 테스트를
  재실행하고 결과를 evidence JSON으로 감싸는 wrapper(테스트 로직 재작성 아님 — 기존
  pytest를 호출해 결과만 구조화).
- `scripts/gate2/70_production_isolation.py`: §3(protocol 문서) tripwire 목록의
  BEFORE/AFTER 해시·point count 비교. 이 스크립트 자체는 "실행"해도 읽기 전용(해시 계산만,
  아무것도 변경하지 않음) — Phase A에 포함.
- `scripts/gate2/95_evidence_verify.py`: `evidence/gate2/<run-id>/*.json`의
  `stdout_sha256`이 실제 재실행 결과와 일치하는지 대조.
- `scripts/gate2/protected.yaml`: 본 Task Order §1(protocol 문서 §3)의 YAML 그대로.
- `scripts/gate2/gate2_orchestrator.py`: Phase A 스크립트들을 순서대로 호출,
  `evidence/gate2/<run-id>/manifest.json` + `SUMMARY.md` 자동 생성(사람이 손으로 안 씀),
  `GATE2_STATUS=GREEN|HOLD|RED` stdout 출력. **이번 단계에서는 `40/80/90`을 호출하지 않는다**
  (아래 Phase B, 별도 플래그 `--include-mutating`로만 활성화, 기본 off).

### Phase B — mutating validator (코드만 작성, 실행 금지)

- `scripts/gate2/40_clean_install.sh`: `/tmp/dbma-gate2-run-$(date +%s)/`에 격리,
  `install_nae_beta.command` 흐름 재현(단, `INSTALL_DIR`을 `~/내서재_베타`가 아니라 그
  격리 경로로 오버라이드하는 파라미터화 필요 — 실제 라이브 베타 설치를 절대 덮어쓰지 않게).
  `--dry-run` 플래그: brew/ollama/curl 실제 호출 대신 명령어 echo만.
- `scripts/gate2/80_reinstall_upgrade.sh`, `scripts/gate2/90_uninstall.sh`: 동일 원칙.
  `90_uninstall.sh`는 현재 저장소에 uninstall 로직이 전혀 없으므로 신규 작성(단순히
  격리 install dir 삭제 + orphan file 검사 수준으로 최소 구현, Homebrew 전역 패키지
  제거는 범위 밖 — 명시).
- **이 세 스크립트는 `bash -n`/dry-run까지만 검증하고 실제 실행하지 않는다.**

---

## 4. Hard Stop Conditions

즉시 중단하고 CUE에 보고:
1. `core/retrieval.py`/`pyproject.toml` 수정이 필요해 보이는 경우
2. `40/80/90`을 dry-run이 아닌 실제 모드로 실행해야 검증이 된다고 판단되는 경우 — 실행하지
   말고 CUE에 보고(사용자 승인 필요)
3. `~/내서재_베타`(실제 라이브 베타 설치 경로)를 스캐폴딩 스크립트가 조금이라도 건드리는
   코드가 만들어지는 경우 — 반드시 격리 경로만 사용
4. Production TSU/Qdrant 변경이 필요한 경우
5. EXPECTED_PAGES에 `ui.tabs`/`ui.sidebar`를 포함하거나 9개가 아닌 다른 개수로 바뀌는 경우

**Never touch**: RAW 데이터, `core/retrieval.py`, ADR-001/003/013/024, Production Qdrant/TSU,
`~/내서재_베타`(실제 설치 경로).

---

## 5. Acceptance Criteria

1. Phase A 스크립트 전체가 `bash -n`/`python -m py_compile` 통과
2. `gate2_orchestrator.py --phase A` 실행 시 `evidence/gate2/<run-id>/*.json` 생성, `SUMMARY.md` 자동 생성
3. `60_ui_pages.py`가 정확히 9개 모듈만 import(10개나 `ui.tabs`/`ui.sidebar` 아님)
4. `70_production_isolation.py`가 BEFORE=AFTER(무변경 상태)에서 `PASS` 반환 — 이 자체가
   현재 아무것도 안 건드리고 있다는 최초 증거
5. Phase B 스크립트는 코드 존재 + `bash -n` 통과만 확인, 실행 로그 없음
6. `core/retrieval.py`/`pyproject.toml` git diff 빈 결과

---

## 6. Output format expected from C1 per phase

`PHASE <A|B> — <PASS|INCOMPLETE|BLOCKED> — <1-line summary> — evidence: <path>`

---

## 7. CUE Pre-Review Gate

- [ ] `core/retrieval.py` 수정 필요? → No.
- [ ] Production mutation 필요? → No — Phase A는 읽기 전용, Phase B는 코드 작성만.
- [ ] 신규 ADR 필요? → No — 테스트/빌드 인프라.
- [ ] `~/내서재_베타`(라이브 경로) 영향? → No — 격리 경로 강제.
- [ ] ADR-001/003/013/024 영향? → No.

**CUE Pre-Review verdict: PASS — Task Order may be issued to C1.**

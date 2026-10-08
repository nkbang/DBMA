# Gate 2 최종 재판정 (2026-10-07)

- 브랜치: `fix/merge-production-path-safety`
- 판정: **FAIL** — 배포 트리(`git archive HEAD`)에서 앱 모듈 임포트 실패
- 이전 상태: PARTIAL_PASS(run `20261007-224149`, Phase 80/90 N/A) → 본 문서가 대체. 이전 run 파일은 동결(수정 안 함).

## Phase별 결과

| Phase | 결과 | 근거 evidence (`evidence/gate2/`) | 비고 |
|---|---|---|---|
| 0 snapshot | PASS | `20261007-224149` | snapshot 로그는 JSON에서 재구성한 기록 |
| 10 packaging audit | PASS | 동일 | |
| 30 package integrity | PASS | 동일 | 필수 파일 존재만 확인, 임포트 결함 못 잡음 |
| 50 runtime smoke | PASS (얕음) | 동일 | venv·`dbma_ui.py` 읽기만 확인, 결함 못 잡음 |
| 60 UI pages | PASS | 동일 | 기대 9개 존재(디스크 12개) |
| 70 production isolation | PASS | 동일 | 보호 파일 4개 변경 0 |
| 80 reinstall/upgrade | PASS | `20261007-phase8090` | `install_nae_beta.command` 로직의 /tmp 시뮬레이션, 실제 설치 아님 |
| 90 uninstall | PASS | 동일 | 최초 출력은 대화 기록 복원본 |
| 61 citation UI | **FAIL** | `20261007-phase6195` | 배포 트리 pytest 1 passed / 6 failed (실제 체크아웃 7/7) |
| 40 clean install | **FAIL (부분)** | `20261007-phase40` | requirements 설치 PASS, `import ui.app` FAIL. 설치 스크립트 본 실행은 미실행 |
| 95 evidence verify | PASS이나 무의미 | `20261007-phase6195` | 대상 7건 전부 SKIP(`stdout_sha256` 없음), Gate 근거 제외 |

## 판정 근거: 결함 F1

- 현상: 배포 트리에서 `import ui.app` → `ModuleNotFoundError: No module named 'NAE'`
- 원인: `.gitattributes`의 `NAE/ export-ignore`로 `NAE/`가 배포에서 제외되는데, `ui/components/nae_public_section.py:25`가 `NAE.citation_disclosure`를 무조건 임포트(`ui.pages` 임포트 체인).
- 독립 확인 2건: Phase 61(pytest)과 Phase 40(클린 venv 설치 후 임포트).
- 영향: 배포본에서 앱 기동 불가 가능성. 개발 체크아웃에서는 `NAE/`가 있어 재현되지 않음.
- 전제/한계: 배포 형태가 `git archive HEAD`라는 전제(Phase 30과 동일). `setup_beta_tester.command`에 `NAE`를 별도로 받는 코드는 정적 확인 범위에서 없음. 설치 스크립트 end-to-end는 미평가.

## 기타 발견 (판정 영향 없음, 수정 안 함)

| ID | 대상 | 내용 |
|---|---|---|
| D1 | `80_reinstall_upgrade.sh` | dry-run에서도 /tmp 디렉터리 생성, 검증 없이 `RESULT: PASS` 출력 |
| D2 | `90_uninstall.sh` | dry-run에서 "Removed:" 출력하나 삭제하지 않음 |
| D3 | `90_uninstall.sh` | 인자 없이 실행하면 /tmp의 모든 `dbma-gate2-run-*` 삭제 |
| D4 | `40_clean_install.sh` / `setup_beta_tester.command` | /tmp에 격리되지 않음: `brew install`, `/usr/local` 심볼릭 링크, 8520 포트 `pkill`, 서버 기동·브라우저 open. 헤더의 "writes ONLY to /tmp"는 사실과 다름. 기동 실패해도 "완료" 알림 |
| D5 | `95_evidence_verify.py` | 검증 대상 0건이어도 `all_pass=true` |
| D6 | 이전 run | Phase 80/90 "scripts not in working tree" 판정은 경로 조회 오류(실제 `scripts/gate2/`), `20261007-phase8090`에서 정정 |

## 증거 신뢰도 주석

- Phase 90 최초 삭제 출력은 tee 파일이 재실행으로 덮어써져 대화 기록에서 복원(`90_real_output.txt` 헤더에 명시). 재실행 출력은 `90_rerun_idempotent_output.txt`.
- Phase 40 1차 시도의 `hunspell` 빌드 실패는 백그라운드 실행이 `clang++`를 x86_64로 띄운 측정 환경 오류이며 제품 결함이 아님(단독 재시도 성공, `arch -arm64` 2차 전체 설치 성공).
- 각 run은 `manifest.json`(v2, canonical sha256)과 커밋본 기준 `00_manifest_verify.json`을 가진다. 커밋: `ba8921ac`→`c4f3c9a0`→`cb234fd7`(224149), `a293c374`→`e3f9f588`(phase8090), `41c82a51`(phase6195), `31de896f`(phase40).

## 결정 필요 (HQ)

1. **NAE 패키징 방침**: (a) `NAE/`를 배포에 포함(`export-ignore` 조정, 저장소의 약 93.5%로 비용 큼) 또는 (b) UI의 NAE 임포트를 게이팅해 `NAE/` 없이도 기동. 아키텍처 결정 사항.
2. **스크립트 정비 범위**: D1~D5 수정 여부.
3. **실제 clean-install 평가**: 깨끗한 Mac/VM에서 `setup_beta_tester.command` 본 실행. 개발 기기는 조건 불성립.

## 재판정 조건

F1 해소 → Phase 61·40 재평가 → (깨끗한 환경에서 설치 스크립트 본 실행) → 전체 판정 재산정. 그 전에는 PARTIAL_PASS로 되돌리지 않는다.

---

## 부록 A — F1 수정 후 재평가 (2026-10-07, 방안 B)

- 수정 커밋 `3a10bb3b`: `ui/components/nae_public_section.py`·`ui/pages/chat.py`의 NAE 최상위 import 게이팅(NAE 부재 시 Smith 비활성), 회귀 시험 `tests/test_ui_imports_without_nae.py`(수정 전 6 failed), `gate2/30`에 패키지 트리 `import ui.app` 검사 추가.
- evidence: `evidence/gate2/20261007-f1fix/`

| Phase | 수정 전 | 수정 후 |
|---|---|---|
| 61 (배포 트리 pytest) | FAIL (1 passed / 6 failed) | **PASS (7/7)** |
| 30 (+신규 import 검사) | PASS (결함 못 잡음) | **PASS** (`packaged_import_ui_app` PASS) |
| 40 (격리 부분) | `import ui.app` FAIL | `import ui.app` PASS, `AppTest` 예외 없음 |

- F1은 코드 수준에서 해소됨. 관련 17개 테스트 파일 202 passed.
- **전체 판정은 아직 확정하지 않는다.** 남은 항목: (1) 설치 스크립트(`setup_beta_tester.command`) end-to-end 및 깨끗한 환경 평가(D4 비격리 포함), (2) `AppTest`가 첫 화면만 렌더링해 chat·research 이동·Smith·`nae_pd` 활성 경로 미시험, (3) D1~D3·D5 스크립트 결함. 판정 FAIL의 직접 사유(F1)는 해소되었으므로 위 (1)(2) 결과에 따라 PARTIAL_PASS 이상으로 재산정한다.

## 부록 B — AppTest 확장 검증 (2026-10-07)

- evidence: `evidence/gate2/20261007-apptest-ext/`, 수정 커밋 `f49ffeb3`
- 범위: 사이드바 6개 페이지(+Research 연구/채팅 뷰) 렌더링, `nae_pd` 활성 상태에서 NAE 섹션 검색 클릭. `NAE/` 없는 `git archive` 트리와 `NAE/` 있는 트리(대조군)를 비교.
- **추가 결함 F1-b 발견·수정**: `NAE/` 부재 + `nae_pd` enabled + 검색 클릭 시 `_execute_nae_retrieval`이 `UnboundLocalError`(except 절의 `NaePdModuleDisabledError` 미바인딩, §G fail-closed 위반). 대조군은 정상 → `NAE/` 부재에서만 발생. `ImportError`를 먼저 잡아 경고+빈 결과로 수정, 회귀 시험 추가(수정 전 1 failed).
- 수정 후 결과: 6개 페이지 예외 없음, `nae_pd` 활성 검색은 경고 후 빈 결과. 관련 테스트 48 passed.
- 무효 처리한 시도 2건(온보딩 미우회, 내부 키 대신 표시 라벨 사용)은 findings에 기록.
- **한계**: Monitor(`NAE_ADMIN_MODE=1`)·설교 준비 내부 뷰·실제 질의 생성·Smith 활성 경로·실제 `streamlit run`·브라우저 상호작용 미시험. 설치 스크립트 end-to-end와 깨끗한 환경 평가는 여전히 미평가.
- 판정: F1(F1-b 포함)은 해소. 전체 판정은 위 한계와 D1~D5가 남아 있어 아직 확정하지 않는다.

## 부록 C — 스크립트 정비 D1·D2·D3·D5 (2026-10-07)

- evidence: `evidence/gate2/20261007-scriptfix/`, 수정 커밋 `a187d734`, 시험 `tests/test_gate2_scripts.py`(수정 전 7 failed → 9 passed)

| ID | 상태 | 조치 |
|---|---|---|
| D1 | 해소 | 80 dry-run은 시딩·검증 생략, `RESULT: DRY-RUN (no verification performed)`, /tmp 미생성 |
| D2 | 해소 | 90 dry-run은 `would remove`로 표기, 삭제 안 함 |
| D3 | 해소 | 90은 인자 없으면 거부(exit 2), `--all` 명시 opt-in, 대상은 `/tmp/dbma-gate2-run-*`만 허용. 오케스트레이터가 `--all` 전달 |
| D5 | 해소 | 95는 비교 0건이면 `VACUOUS`(exit 2, all_pass=false) |
| D4 | **미수정** | 40/`setup_beta_tester.command` 비격리 — 설치 스크립트 정책 결정 필요 |

- **동작 변경**: Phase 95는 현 evidence(`stdout_sha256` 없음)에서 PASS가 아니라 **VACUOUS**다. 오케스트레이터 Phase A에서는 RED가 된다. 95를 의미 있게 PASS시키려면 evidence에 `stdout_sha256`을 기록하는 설계가 필요하다(별도 결정).
- **한계**: 80·90의 비-dry-run 실제 실행은 수정 후 재실행하지 않았다(사용자 터미널 필요). 오케스트레이터 전체 실행도 하지 않았다(40 포함 시 전역 변경).

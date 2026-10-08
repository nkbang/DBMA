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

## 부록 D — 80·90 재실행 (스크립트 정비 후, 2026-10-07)

- evidence: `evidence/gate2/20261007-phase8090-rerun/`, 실행 HEAD `dcd0b49d`, 사용자 터미널 단일 실행
- Phase 80 **PASS**(8/8 보존·내용 일치), Phase 90 **PASS**(명시 인자로 삭제, 잔여물 없음, 추적 파일 변경 없음)
- 증거는 `tee` 원본 캡처다. 부록 앞부분의 "Phase 90 최초 출력은 복원본" 한계는 이 run이 대체한다(이전 run 파일은 이력으로 보존).
- 한계는 동일: 80은 설치 로직 시뮬레이션, 시딩 데이터는 마커, 90 `--all` 비-dry-run은 시험으로만 검증.

## 부록 E — D4 설치 스크립트 격리 (2026-10-07)

- evidence: `evidence/gate2/20261007-d4fix/`, 수정 커밋 `aafd2dfb`, 시험 `tests/test_setup_beta_isolation.py`(수정 전 7 failed → 9 passed)
- 설계: 설치 스크립트의 전역 설치는 최종 사용자용 정상 동작이므로 **기본 동작은 그대로** 두고, `NAE_SETUP_ISOLATED=1`일 때만 전역 부작용을 건너뛴다(전제 조건 부재 시 exit 3). `40_clean_install.sh`는 이 모드와 빈 포트로 호출한다.
- 40 실제 실행(격리 모드, 에이전트): **PASS** — venv+requirements 설치, 서버 응답, exit 0. 실행 전후 전역 상태 불변(libhunspell 링크 시각·poppler·8520 포트). 설치된 트리: `NAE/` 없음, `import ui.app` rc=0, AppTest 예외 없음.
- 1차 시도 FAIL은 에이전트 셸의 x86_64 clang 문제(제품 결함 아님), `arch -arm64`로 고정해 해소. 증거에 분리 기록.
- 기본 모드의 서버 미응답 시 "완료" 오알림을 정정(브라우저는 그대로 열고 안내 문구만 구분). 느린 첫 기동 회귀를 피하려 실패 처리하지 않음.
- **여전히 미평가**: 이 Mac은 깨끗한 환경이 아님(Ollama·모델·brew 패키지·/usr/local 링크 기존재). **전역 설치 단계(brew/Ollama 설치, 모델 pull, 링크 생성)와 기본 모드 end-to-end는 깨끗한 Mac/VM에서만 평가 가능**.

### 현재 Gate 2 상태 요약

| 항목 | 상태 |
|---|---|
| F1·F1-b | 해소 |
| D1·D2·D3·D5 | 해소(80·90 재실행 PASS) |
| D4 | 해소(40 격리 모드 실제 실행 PASS) |
| Phase 95 | VACUOUS (`stdout_sha256` 설계 필요) |
| 깨끗한 환경 평가 | **미평가 — 유일한 큰 잔여 항목** |

## 부록 F — 현 릴리스(`beta-v1.3.0-rc6`)에도 F1 존재 (2026-10-07)

- evidence: `evidence/gate2/20261007-rc6check/`
- `install_nae_beta.command`가 테스터에게 내려받게 하는 태그는 `origin/dev/dbma-engine`의 `BETA_LATEST_TAG.txt` = `beta-v1.3.0-rc6`이다. 이 태그를 `git archive`로 풀면 `ui/components/nae_public_section.py:25`와 `ui/pages/chat.py:47`에 NAE 최상위 import가 있고 `NAE/ export-ignore`가 적용되어 `import ui.app`·AppTest가 `No module named 'NAE'`로 실패한다.
- F1·F1-b·D4 수정(`3a10bb3b`, `f49ffeb3`, `aafd2dfb`)은 `origin/dev/dbma-engine`에도 어떤 태그에도 없다. 현재 브랜치는 rc6보다 126 커밋 앞선다.
- **한계**: `git archive` 기준이며 GitHub 실제 태그 tarball이 `export-ignore`를 따르는지는 다운로드로 확인하지 않았다(깨끗한 환경 평가 절차서 T0).
- **조치(승인 사항, 미수행)**: 핫픽스 후보 태그 생성, `dev/dbma-engine` 병합, `BETA_LATEST_TAG.txt` 조정은 HQ 승인 후에만 진행한다.
- 깨끗한 환경 평가 절차서: `docs/GATE2_CLEAN_ENV_EVALUATION_PROCEDURE.md` (트랙 A는 이 결함의 릴리스 재현을 확정하는 평가다).

## 부록 G — rc7 핫픽스 브랜치 준비 (2026-10-07, 로컬)

- evidence: `evidence/gate2/20261007-hotfix-rc7-prep/`
- 방안 A 채택: `hotfix/rc7-nae-optional`(베이스 `beta-v1.3.0-rc6`, 별도 워크트리 `.claude/worktrees/hotfix-rc7-nae-optional`), 로컬 전용·미푸시. 변경은 `ui/` 2개 파일 + 회귀 시험 1개(rc6 대비 +93/-2).
- 검증: `NAE/` 없는 배포 트리에서 `import ui.app` rc=0, 시험 73 passed, AppTest 11 runs 문제 0; `NAE/` 있는 워크트리에서 `ui`를 참조하는 시험 278 passed. 대조군(수정 없는 rc6)은 임포트 실패.
- **미수행(승인 필요)**: 브랜치 푸시, 태그 `beta-v1.3.0-rc7`, GitHub Release 및 rc6 코퍼스 자산(49MB) 재업로드(없으면 새 설치자는 빈 서재로 시작), `BETA_LATEST_TAG.txt` 갱신 PR, `dev/dbma-engine`로의 수정 이식 PR(`chat.py` 한 군데 수동 충돌 예상).
- 한계: GitHub 실제 태그 tarball의 `export-ignore` 적용은 미확인(절차서 T0).

## 부록 H — 실제 GitHub 태그 tarball 확인 (2026-10-07)

- evidence: `evidence/gate2/20261007-t0-tarball/` — 공개 URL `https://github.com/nkbang/DBMA/archive/refs/tags/beta-v1.3.0-rc6.tar.gz`(HTTP 200, 4,729,447 bytes)를 내려받아 확인.
- **F1이 실제 릴리스 tarball에서 확정되었다**: 1,652 members 중 `NAE/` 0개(export-ignore 적용), `ui/components/nae_public_section.py:25`·`ui/pages/chat.py:47`의 NAE 최상위 import 존재, 압축 해제본에서 `import ui.app` → `ModuleNotFoundError: No module named 'NAE'`. 부록 F의 "GitHub 실제 tarball 미확인" 한계는 이로써 해소된다.
- 로컬 `git archive`(1,644 members)와의 차이는 `tests/nae/` 하위 8개 항목뿐이다. 이 Mac의 `core.ignorecase=true`로 `NAE/ export-ignore`가 `tests/nae/`까지 제외하기 때문이며(GitHub는 대소문자 구분), 앱 실행에는 영향이 없다. 단 이전 evidence의 members 수치는 로컬 기준이다.
- 한계: 임포트 수준 확인이며 설치 end-to-end가 아니다. 태그가 이동하면 재확인이 필요하다(태그 커밋 `d16095e2`).

## 부록 I — rc7 핫픽스 브랜치 푸시 (2026-10-07, HQ 승인)

- `hotfix/rc7-nae-optional`(`d00950c9`, 베이스 `beta-v1.3.0-rc6`)를 `origin`에 푸시했다(신규 브랜치, force 아님). 원격 끝 = 로컬 끝 확인.
- 부록 G의 "미푸시" 기록은 이 푸시로 갱신된다. 이 푸시는 **테스터에게 영향을 주지 않는다**: 설치기는 `dev/dbma-engine`의 `BETA_LATEST_TAG.txt`(여전히 `beta-v1.3.0-rc6`)가 가리키는 태그만 내려받는다. `rc6` 태그·`dev` 끝(`c10fd2c3`) 불변, `rc7` 태그 없음, PR 없음.
- 남은 승인 항목: 태그 `beta-v1.3.0-rc7` 생성 → GitHub Release와 rc6 코퍼스 자산 재업로드 → `dev` 이식 PR → 마지막으로 `BETA_LATEST_TAG.txt` PR(병합 시 테스터 전원에게 영향).

## 부록 J — 태그 `beta-v1.3.0-rc7` 생성 (2026-10-07, HQ 승인)

- 주석 태그 `beta-v1.3.0-rc7`(태그 객체 `52f2de12`)을 `hotfix/rc7-nae-optional`의 `d00950c9`에 만들어 푸시했다. rc6와 같은 형식(주석 태그, 작성자 David Bang). 태그만 푸시했고 GitHub Release는 만들지 않았다.
- **테스터에게 영향 없음**: `BETA_LATEST_TAG.txt`(`dev/dbma-engine`)는 여전히 `beta-v1.3.0-rc6`. `rc6` 태그(`d16095e2`)·`dev` 끝(`c10fd2c3`) 불변. 설치기는 이 파일이 가리키는 태그만 받는다.
- **미확인**: rc7의 실제 GitHub tarball(`export-ignore` 적용, `import ui.app` 성공)은 아직 내려받아 확인하지 않았다. Release 없이도 `archive/refs/tags/` URL은 동작하지만, 코퍼스 기본 서재는 같은 태그의 Release 자산이 없으면 받지 못해 **빈 서재로 시작**한다 — `BETA_LATEST_TAG`를 바꾸기 전에 Release와 자산을 먼저 만들어야 한다.
- 남은 승인 항목: GitHub Release 생성 + rc6 코퍼스 자산(49MB) 재업로드 → rc7 tarball 재확인 → `dev` 이식 PR → `BETA_LATEST_TAG.txt` PR.

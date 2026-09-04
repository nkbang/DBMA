# C1 Task Order — Gate 2 Clean Install Test 격리 방식 재설계 (git archive 기반)

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-18 |
| Executor | C1 |
| Verifier | CUE |
| Approver (final) | Rev. Bang |
| Status | GREEN — 착수 승인 |
| Basis | CUE가 hunspell 수정 검증 중 실측한 2개의 설계 결함(§1) |

---

## 0. Purpose (scope-limited)

`scripts/gate2/40_clean_install.sh`(및 이를 재사용하는 `80_reinstall_upgrade.sh`)를
**로컬 HEAD 내용을 진짜로 격리된 디렉터리에서 테스트하도록 재설계**한다. 현재 구조는
두 가지 실측 결함이 있다:

1. `install_nae_beta.command`가 `BETA_LATEST_TAG.txt`(고정 태그, 현재
   `beta-v1.3.0-rc3`)를 다운로드하므로, 로컬/HEAD 수정을 **절대 검증할 수 없다.**
2. CUE가 이를 우회하려 `HOME=<격리> bash scripts/setup_beta_tester.command`를
   **라이브 저장소 안에서 직접** 실행했더니, `setup_beta_tester.command`가
   `PROJECT_ROOT`를 `$(dirname "$0")/..`(스크립트 자기 자신의 실제 경로)로 계산해
   `$HOME` 오버라이드와 무관하게 **라이브 저장소 위에서 그대로 동작**했다. 그 결과
   `/Users/David/DBMA/.venv_beta`가 실제로 생성되고, `config.yaml`이 실제로
   재작성되고(우연히 같은 값이라 `git diff`엔 안 잡혔지만 다른 RAM 등급이면
   실제 mutation 발생), 실제 `dbma_ui.py`로 진짜 streamlit 서버 + 브라우저가
   열렸다(CUE가 즉시 발견해 프로세스 종료·`.venv_beta` 삭제로 정리, 실질 피해 없음).

This Task Order does **not**:
- `install_nae_beta.command`의 실제 배포 다운로드 로직(태그 pinning 등) 자체를 수정
  — 이건 정상 설계(라이브 사용자에게 검증된 릴리스만 배포)이며 건드리지 않는다
- `core/retrieval.py`, `pyproject.toml` 수정
- 실제(non-dry-run) 실행 — 이번에도 구현 + 코드 리뷰 + CUE의 통제된 1회 검증까지만

---

## 1. Prior Facts (CUE가 실측 — 재조사 금지)

- `setup_beta_tester.command:24` `cd "$(dirname "$0")/.."`가 `PROJECT_ROOT`를 결정한다
  — `$HOME`과 무관. 즉 **이 스크립트를 격리하려면 스크립트 파일 자체가 격리된
  디렉터리 안에 있어야 한다**(단순 `HOME=` 오버라이드로는 불충분).
- `git archive`는 이미 Gate 2A/`30_package_integrity.py`에서 검증된 안전한 방법으로
  HEAD의 스냅샷을 만들 수 있다(`NAE/`, `.automation/`, `test_seal_*/`는 export-ignore로
  자동 제외됨 — 격리 테스트 payload도 그만큼 가벼워짐, 부수적 이득).
- hunspell 수정(`scripts/setup_beta_tester.command`의 `LIBRARY_PATH` 블록) 자체는
  CUE가 이미 실제 실행으로 검증 완료 — **이 Task Order에서 다시 검증할 필요 없음**,
  격리 메커니즘만 고치면 된다.

---

## 2. Role Separation

**C1 (executor)**: `40_clean_install.sh`/`80_reinstall_upgrade.sh` 재작성.
**CUE (verifier)**: 코드 리뷰 + **CUE가 직접, 통제된 방식으로 1회 실제 실행**해
(a) `~/내서재_베타`·라이브 `config.yaml`·라이브 `.venv_beta` 전부 무영향인지,
(b) hunspell 빌드가 격리 환경에서도 통과하는지 재확인.
**Rev. Bang (approver)**: 착수 승인 완료.

---

## 3. Implementation

`40_clean_install.sh`를 다음 구조로 재작성한다(기존 `install_nae_beta.command` 다운로드
호출은 완전히 제거 — 로컬 HEAD 테스트가 목적이므로 네트워크 다운로드 자체가 불필요):

```bash
TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
ISOLATED_REPO="${ISOLATED_DIR}/repo"
FAKE_HOME="${ISOLATED_DIR}/fakehome"

mkdir -p "${ISOLATED_REPO}" "${FAKE_HOME}"

# HEAD 스냅샷을 격리 디렉터리로 추출 (export-ignore 자동 적용됨 — NAE/,
# .automation/, test_seal_*/ 제외)
git -C "${PROJECT_ROOT}" archive HEAD | tar -x -C "${ISOLATED_REPO}"

# 이제 스크립트 자신이 격리 디렉터리 안에 있으므로 setup_beta_tester.command의
# PROJECT_ROOT($(dirname "$0")/..) 계산이 자동으로 격리 디렉터리를 가리킨다 —
# HOME 오버라이드와 별개로, 이게 진짜 격리의 핵심이다.
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] git archive HEAD | tar -x -C ${ISOLATED_REPO}"
    echo "[DRY-RUN] HOME=${FAKE_HOME} bash ${ISOLATED_REPO}/scripts/setup_beta_tester.command"
else
    HOME="${FAKE_HOME}" bash "${ISOLATED_REPO}/scripts/setup_beta_tester.command"
fi
```

`80_reinstall_upgrade.sh`도 동일 패턴으로 교체(같은 `ISOLATED_REPO`를 두 번 호출해
재실행 시나리오 재현 — 기존 로직 유지, `install_nae_beta.command` 의존 부분만 교체).

**중요 — 이중 안전장치**: `HOME=${FAKE_HOME}` 오버라이드는 계속 유지한다(brew/ollama
설정 캐시 등 `$HOME`에 의존하는 다른 부분들을 위해) — `git archive` 격리와 `HOME`
격리는 **서로 다른 문제를 막는 두 개의 독립된 안전장치**이므로 하나로 대체하지 말고
같이 쓴다.

---

## 4. Hard Stop Conditions

1. **`ISOLATED_REPO`를 거치지 않고 `PROJECT_ROOT`(라이브 저장소)에서 직접
   `setup_beta_tester.command`나 `install_nae_beta.command`를 실행하는 코드가 남아있는
   경우** — 이번 사고의 정확한 재발 패턴이므로 최우선 검토 대상
2. `git archive` 대상이 `HEAD`가 아니라 working tree의 uncommitted 변경을 반영해야
   하는 경우(현재는 committed HEAD만 테스트 — 이걸로 충분한지, 아니면
   `git stash create` 등으로 uncommitted 변경까지 포함해야 하는지 판단이 필요하면
   진행하지 말고 CUE에게 보고)
3. `core/retrieval.py`/`pyproject.toml` 수정 필요 시
4. 실제(non-dry-run) 실행 — 코드 작성 + `bash -n` + `DRY_RUN=true`까지만, 실제
   실행은 CUE가 별도로 통제된 환경에서 1회 수행

**Never touch**: `/Users/David/DBMA`(라이브 저장소) 자체를 대상으로 실제 설치 스크립트를
실행하는 코드, `core/retrieval.py`, ADR-001/003/013/024.

---

## 5. Acceptance Criteria

1. `40_clean_install.sh`/`80_reinstall_upgrade.sh`가 `git archive HEAD`로 격리
   디렉터리에 저장소 스냅샷을 만들고, **그 안의** `setup_beta_tester.command`를
   `HOME=${FAKE_HOME}`로 실행하는 구조로 변경됨(둘 다 함께 적용)
2. 코드 어디에도 `${PROJECT_ROOT}/scripts/setup_beta_tester.command`(라이브 경로)를
   직접 실행하는 줄이 없음(CUE가 grep으로 재확인)
3. `bash -n` 통과
4. `DRY_RUN=true` 실행 시 `git archive` 명령이 echo에 정확히 포함됨
5. non-dry-run 실행 로그 없음(C1은 실행하지 않음)

---

## 6. Output format

`PHASE 1 — <PASS|INCOMPLETE|BLOCKED> — <1-line summary> — evidence: <path>`

---

## 7. CUE Pre-Review Gate

- [ ] 라이브 저장소 위험? → 이번 재설계의 목적 자체가 이 위험 제거.
- [ ] `core/retrieval.py` 영향? → No.
- [ ] Production mutation? → No.
- [ ] 신규 ADR 필요? → No.

**CUE Pre-Review verdict: PASS.**

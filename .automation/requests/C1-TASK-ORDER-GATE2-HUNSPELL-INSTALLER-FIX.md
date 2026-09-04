# C1 Task Order — hunspell Apple Silicon 설치 실패 수정 (Gate 2 Clean Install Test 발견)

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-18 |
| Executor | C1 |
| Verifier | CUE |
| Approver (final) | Rev. Bang |
| Status | GREEN — 착수 승인 |
| Basis | Gate 2 실제 clean install 실행에서 재현된 fatal 실패 (`scripts/gate2/40_clean_install.sh`, 격리 fakehome) |

---

## 0. Purpose (scope-limited)

`scripts/gate2/40_clean_install.sh`를 실제(non-dry-run)로 격리 환경에서 실행한 결과,
`setup_beta_tester.command`의 `pip install -r requirements.txt` 단계에서 `hunspell`
패키지 wheel 빌드가 실패해 `fatal()`로 설치가 완전히 중단됨을 CUE가 직접 재현·확인했다.
**이 문제는 dry-run으로는 절대 드러나지 않으며, 신규(Apple Silicon) 사용자의 베타
설치를 100% 막는다.**

근본 원인과 검증된 해결책은 `core/tli/hunspell_adapter.py` 모듈 docstring에
이미 문서화되어 있으나(2026-07-24, CUE), `setup_beta_tester.command`에는 반영된 적이
없다.

This Task Order does **not**:
- `core/tli/hunspell_adapter.py` 자체 수정(이미 올바름, 문서만 참고)
- `core/retrieval.py`, `pyproject.toml` 수정
- Production 데이터 변경

---

## 1. Prior Facts (CUE가 실측 확인 — 재조사 금지)

- 실패 원인: 컴파일은 성공하나(`-I` 헤더 경로는 필요), 링크 단계에서
  `ld: library 'hunspell' not found` — `-L/usr/local/lib`(LDFLAGS)이 빠져서 발생.
- `core/tli/hunspell_adapter.py` docstring의 검증된 재현/우회 절차(그대로 사용할 것):
  ```bash
  brew install hunspell
  mkdir -p /usr/local/Cellar/hunspell/1.6.2/include
  ln -sf $(brew --prefix hunspell)/include/hunspell \
      /usr/local/Cellar/hunspell/1.6.2/include/hunspell
  ln -sf $(brew --prefix hunspell)/lib/libhunspell-1.7.dylib \
      /usr/local/lib/libhunspell.dylib
  LDFLAGS="-L/usr/local/lib" pip install hunspell
  ```
- **`1.6.2`는 실제 brew 버전과 무관하게 고정된 값**이다 — pip 패키지 `hunspell`(0.5.5)의
  `setup.py`가 이 경로를 리터럴로 하드코딩하고 있기 때문(brew가 실제로 설치하는 버전은
  현재 1.7.3이지만 무관 — 절대 버전을 동적으로 계산해 바꾸지 말 것).
- CUE가 이 Mac에서 실측: `brew install hunspell`과 두 symlink는 이미 되어 있었음에도
  LDFLAGS 누락만으로 실패 재현 — 즉 **4단계 전부 자동화해야 신규 사용자를 커버한다**
  (symlink가 이미 있어도 LDFLAGS 없이는 실패하므로, 4단계 모두 빠짐없이 필요).
- `/usr/local/lib`, `/usr/local/Cellar/hunspell/1.6.2` 디렉터리가 없을 수 있으므로
  `mkdir -p`로 먼저 생성해야 함(이 Mac은 이미 존재해서 이 부분이 검증되지 않았음 —
  C1이 신규 격리 환경에서 확인할 것).

---

## 2. Role Separation

**C1 (executor)**: `scripts/setup_beta_tester.command`에 §3 로직 추가.
**CUE (verifier)**: 코드 리뷰 + `scripts/gate2/40_clean_install.sh` 실제(non-dry-run)
재실행으로 hunspell 단계를 실제로 통과하는지 격리 환경에서 재현 검증.
**Rev. Bang (approver)**: 착수 승인 완료.

---

## 3. Implementation

`scripts/setup_beta_tester.command`의 "── 4) Python 환경 ──" 섹션,
`pip install -q -r "$PROJECT_ROOT/requirements.txt"` 호출 **이전**에 추가:

```bash
# ── hunspell Apple Silicon 빌드 워크어라운드 ──────────────────
# core/tli/hunspell_adapter.py 모듈 docstring 참고 — pip hunspell(0.5.5)의
# setup.py가 Intel Mac 경로(/usr/local/Cellar/hunspell/1.6.2/...)를 리터럴로
# 하드코딩하고 있어, Apple Silicon Homebrew(/opt/homebrew/...)뿐 아니라 brew가
# 1.6.2가 아닌 버전을 설치하는 모든 경우(Intel 포함)에 symlink 우회가 필요하다.
notify "4/5 환경 준비" "맞춤법 사전 구성 요소를 준비하는 중..."
if ! brew list hunspell >/dev/null 2>&1; then
    brew install hunspell || fatal "hunspell 설치에 실패했습니다."
fi
mkdir -p /usr/local/Cellar/hunspell/1.6.2/include
mkdir -p /usr/local/lib
ln -sf "$(brew --prefix hunspell)/include/hunspell" \
    /usr/local/Cellar/hunspell/1.6.2/include/hunspell
ln -sf "$(brew --prefix hunspell)/lib/libhunspell-1.7.dylib" \
    /usr/local/lib/libhunspell.dylib
export LDFLAGS="-L/usr/local/lib"
```

기존 `pip install -q --upgrade pip` / `pip install -q -r "$PROJECT_ROOT/requirements.txt"`
라인은 그대로 두되, 위 블록이 **그 앞**에 와야 `LDFLAGS`가 `pip install` 프로세스
환경에 적용된다(같은 셸 세션이므로 `export`면 충분, 서브셸 분리 없음 확인).

`mkdir -p /usr/local/...`가 권한 문제로 실패할 가능성 — 이 경우
`fatal("맞춤법 사전 구성 요소 준비에 실패했습니다 — /usr/local 쓰기 권한을 확인해 주세요.")`로
사용자에게 명확히 안내(현재 다른 단계들과 동일한 fail-closed 패턴 유지).

---

## 4. Hard Stop Conditions

1. `1.6.2` 대신 동적으로 계산한 버전 문자열을 쓰게 되는 경우 — §1의 이유로 반드시 리터럴 `1.6.2` 유지
2. `core/tli/hunspell_adapter.py` 수정이 필요해 보이는 경우
3. `LDFLAGS`가 `pip install -r requirements.txt`의 다른 패키지 빌드에 부작용을 일으키는 것으로 보이는 경우 — 중단하고 CUE에 보고
4. `core/retrieval.py`/`pyproject.toml` 수정 필요 시

**Never touch**: `core/tli/hunspell_adapter.py`, `core/retrieval.py`, ADR-001/003/013/024.

---

## 5. Acceptance Criteria

1. `bash -n scripts/setup_beta_tester.command` 통과
2. `git diff`가 `scripts/setup_beta_tester.command` 한 파일, 위 블록 추가만
3. **CUE가 `scripts/gate2/40_clean_install.sh`를 실제(non-dry-run)로 재실행했을 때
   hunspell 빌드 실패 없이 `pip install` 단계를 통과하는지까지 확인**(C1은 이 실제
   실행을 직접 하지 않는다 — §Phase B 원칙 유지, 최종 재현은 CUE 몫)

---

## 6. Output format

`PHASE 1 — <PASS|INCOMPLETE|BLOCKED> — <1-line summary> — evidence: <path>`

---

## 7. CUE Pre-Review Gate

- [ ] `core/retrieval.py` 영향? → No.
- [ ] Production mutation? → No — installer 스크립트 수정만.
- [ ] 신규 ADR 필요? → No.
- [ ] `core/tli/hunspell_adapter.py` 수정? → No, 참고만.

**CUE Pre-Review verdict: PASS.**

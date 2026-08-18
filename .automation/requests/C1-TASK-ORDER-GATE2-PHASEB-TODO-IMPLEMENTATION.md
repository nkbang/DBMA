# C1 Task Order — Gate 2 Phase B TODO 구현 (40/80/90 실동작 로직)

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-18 |
| Executor | C1 |
| Verifier | CUE |
| Approver (final) | Rev. Bang |
| Status | GREEN — 착수 승인, **단 실제(non-dry-run) 실행은 이 Task Order 범위 밖** |
| Basis | `scripts/gate2/40_clean_install.sh`/`80_reinstall_upgrade.sh`/`90_uninstall.sh`의 현재 주석 처리된 TODO 블록 |

---

## 0. Purpose (scope-limited)

현재 `40/80/90`은 `DRY_RUN=true`일 때만 echo로 명령을 흉내내고, 실제 모드에서는
`echo "[SKIP] ... unapproved"`만 찍는 스캐폴딩이다. 이번 Task Order는 **실제 동작하는
로직을 구현**한다 — 단, **구현 후에도 non-dry-run 실행은 하지 않는다**(§4).

This Task Order does **not**:
- `40/80/90`을 non-dry-run 모드로 **실행**(brew install/ollama pull/실제 파일시스템 변경 동반 — 코드 작성·`bash -n`·`DRY_RUN=true` 검증까지만)
- `install_nae_beta.command`, `setup_beta_tester.command`(실제 라이브 베타 설치 스크립트) **자체를 수정** — 아래 §1의 이유로 절대 금지
- `core/retrieval.py`, `pyproject.toml` 수정

---

## 1. ⚠️ Prior Fact — CUE가 발견한 격리 결함 (반드시 이 방식으로 우회할 것)

`40_clean_install.sh:21`은 `export INSTALL_DIR="${ISOLATED_DIR}/내서재_베타"`로
격리를 시도하지만, **`scripts/install_nae_beta.command:34`는
`INSTALL_DIR="$HOME/내서재_베타"`를 무조건 재할당**한다(`${INSTALL_DIR:-...}` 같은
환경변수 우선 패턴이 아님) — 즉 `export INSTALL_DIR=...`는 **아무 효과가 없다.**
이 상태로 실제 호출 로직을 채워 넣으면, 나중에 non-dry-run으로 실행할 때
**실제 라이브 베타 경로(`~/내서재_베타`)에 설치를 시도하게 된다** — Hard Stop 위반.

**올바른 우회 방법(반드시 이 방식 사용)**: `install_nae_beta.command`/
`setup_beta_tester.command`를 수정하지 않고, **`HOME` 환경변수 자체를 격리
디렉터리로 바꿔서 서브프로세스를 실행**한다:

```bash
FAKE_HOME="${ISOLATED_DIR}/fakehome"
mkdir -p "${FAKE_HOME}"
HOME="${FAKE_HOME}" bash "${PROJECT_ROOT}/scripts/install_nae_beta.command"
```

이렇게 하면 `install_nae_beta.command` 내부의 `$HOME/내서재_베타`가 자동으로
`${FAKE_HOME}/내서재_베타`로 계산되어, **스크립트 자체는 한 글자도 수정하지 않고
완전히 격리된다.** `40/80/90` 전부 이 패턴을 써야 한다.

---

## 2. Role Separation

**C1 (executor)**: §1 방식으로 40/80/90의 실제 로직 구현, `bash -n` + `DRY_RUN=true` 검증.
**CUE (verifier)**: 구현 코드 리뷰, `HOME` 격리가 실제로 적용됐는지 정적 검토, `DRY_RUN=true`
결과 재실행. **non-dry-run 실행은 CUE도 이번 라운드에서 하지 않는다.**
**Rev. Bang (approver)**: 착수 승인 완료. non-dry-run 첫 실행은 별도 승인 라운드.

---

## 3. Phases

### Phase 1 — `40_clean_install.sh` 실제 로직

- §1의 `HOME=${FAKE_HOME}` 패턴으로 `scripts/install_nae_beta.command`를 서브프로세스로 실행.
- 네트워크 호출(`curl`, `brew install`, `ollama pull`)이 실제로 나가는 것은 맞다 — 이건
  "코드가 올바르게 짜였는가"의 문제이지 "격리가 되는가"와는 별개다. 격리(HOME 트릭)가
  된 상태라면 non-dry-run으로 실행해도 라이브 경로는 안전하다 — 그래도 **이번 라운드에서는
  실행하지 않는다**(§4).
  - AI 모델 pull(수 GB)까지 매번 테스트하면 비용이 크므로, `40_clean_install.sh`에
  `--skip-models` 같은 선택적 플래그를 추가해 향후 반복 테스트 비용을 낮추는 것을
  권장(필수 아님, C1 판단에 맡김 — 단 기본값은 모델까지 포함하는 완전한 검증이어야 함).
- `DRY_RUN=true`일 때는 기존처럼 echo만 하되, 이제 `HOME=${FAKE_HOME} bash install_nae_beta.command`를
  **echo 문자열 안에** 정확히 반영(사용자가 dry-run 출력만 보고도 실제 실행 시 무슨 명령이
  나갈지 정확히 알 수 있어야 함).

### Phase 2 — `80_reinstall_upgrade.sh` 실제 로직

- Phase 1과 동일한 `HOME` 격리 패턴 재사용.
- 시퀀스: (1) §1 방식으로 1차 install_nae_beta.command 실행 → (2) 동일 `FAKE_HOME`으로
  다시 한 번 실행(재실행/업그레이드 시나리오, `install_nae_beta.command`가 이미
  `VERSION_FILE` 존재 여부로 업데이트 분기를 자체 처리함 — 별도 "업그레이드 모드" 인자
  불필요, 있는 그대로의 스크립트 동작을 그대로 이용).
- PERSIST_ITEMS(Gate 2 Phase 1에서 보강된 6→8개 목록)가 재실행 후에도 보존되는지
  `${FAKE_HOME}/내서재_베타/app` 하위에서 확인하는 로직 포함.

### Phase 3 — `90_uninstall.sh` 실제 로직

- 대상은 §1의 `${FAKE_HOME}/내서재_베타`(격리 경로)만 — **`$HOME/내서재_베타`(실제
  사용자 경로)를 참조하는 코드가 단 한 줄도 있으면 안 된다**(정적 검토 대상).
- 최소 구현: 격리된 install dir을 삭제 + 삭제 후 orphan 파일(예: `/tmp` 잔여물) 검사.
  Homebrew 전역 패키지(ollama/poppler/tesseract) 제거는 범위 밖(README 등에 이미
  "수동 삭제 시 `~/내서재_베타` 디렉터리만 지우면 된다"는 안내가 없다면, 이 참에
  INSTALL.md에 한 줄 추가하는 것도 고려 가능 — 이번 Task Order 필수 항목은 아님, C1
  판단으로 여유 있으면 추가).

---

## 4. Hard Stop Conditions — 특히 엄격 적용

즉시 중단하고 CUE에 보고:
1. **`install_nae_beta.command` 또는 `setup_beta_tester.command`를 한 글자라도 수정해야
   할 필요가 생기는 경우** — §1의 HOME 트릭으로 반드시 우회 가능해야 하며, 만약 정말
   수정이 필요하다고 판단되면 절대 스스로 진행하지 말고 CUE에 먼저 보고
2. `$HOME/내서재_베타`(FAKE_HOME 없이)를 참조하는 코드가 40/80/90 어디에든 남아있는 경우
3. **DRY_RUN=false(또는 기본값)로 스크립트를 실제 실행**하는 경우 — 이번 Task Order는
   구현·`bash -n`·`DRY_RUN=true` 검증까지만. 진짜 실행은 다음 라운드에서 별도 승인 후.
4. `core/retrieval.py`/`pyproject.toml` 수정이 필요해 보이는 경우
5. brew/ollama 전역 설치 상태를 변경해야 검증이 된다고 판단되는 경우

**Never touch**: `$HOME/내서재_베타`(실제 라이브 경로), `install_nae_beta.command`/
`setup_beta_tester.command` 본문, `core/retrieval.py`, ADR-001/003/013/024, Production Qdrant/TSU.

---

## 5. Acceptance Criteria

1. `40/80/90` 전부 `HOME=${FAKE_HOME}` 패턴으로 `install_nae_beta.command`를 호출 —
   `export INSTALL_DIR=...`(효과 없는 기존 방식) 완전히 제거
2. 세 스크립트 어디에도 `FAKE_HOME`/`HOME=` 없이 직접 `$HOME/내서재_베타`를 언급하는
   코드가 없음(grep으로 CUE가 재확인)
3. `bash -n` 전체 통과
4. `DRY_RUN=true` 실행 시 echo되는 명령어 문자열에 `HOME=${FAKE_HOME}` 접두사가
   정확히 포함됨(다음 라운드 실제 실행 시 무슨 일이 벌어질지 미리 읽을 수 있어야 함)
5. non-dry-run 실행 로그/evidence가 **하나도 없음**(실행 안 했다는 증거)

---

## 6. Output format expected from C1

`PHASE <1|2|3> — <PASS|INCOMPLETE|BLOCKED> — <1-line summary> — evidence: <path>`

---

## 7. CUE Pre-Review Gate

- [ ] `install_nae_beta.command`/`setup_beta_tester.command` 수정 필요? → No(HOME 트릭으로 우회).
- [ ] 실제 시스템 mutation 발생? → No(이번 라운드는 구현+dry-run 검증까지).
- [ ] `core/retrieval.py` 영향? → No.
- [ ] 라이브 `~/내서재_베타` 위험? → No(HOME 격리로 원천 차단, CUE가 grep으로 재확인 예정).

**CUE Pre-Review verdict: PASS — Task Order may be issued to C1.**

# Phase 9 (Uninstall/Cleanup) — CUE 직접 실행 Evidence

- 작성/실행: CUE, 2026-08-18 (C1 무응답 지속으로 CUE가 직접 실행)

## 사전 정리(발견한 문제)
Phase 9 착수 시 `scripts/gate2/90_uninstall.sh`를 인자 없이 먼저 실행했더니
"No isolated directories found"만 나왔다 — 직전(Phase 8)에 CUE가 이미 전부
정리해뒀기 때문에 제대로 된 테스트가 안 됐다. 실제 삭제 대상을 만들기 위해
`scripts/gate2/40_clean_install.sh`를 다시 실제 실행했다.

이 과정에서 **포트 8520을 이전 테스트의 좀비 프로세스(PID 55779)가 이미
점유하고 있어** 새 설치의 streamlit이 "Port 8520 is not available"로
실패하는 것을 발견 — CUE 자신의 정리 누락(이전 Phase에서 kill했다고
생각했으나 실제로는 남아있었음)이었다. `kill -9`로 정리 후 재확인.

## Uninstall 실행 (실제 삭제 대상 존재 상태에서)

```
대상: /tmp/dbma-gate2-run-1787068053 (.venv_beta, config.yaml, beta_app.log 등 포함)
명령: bash scripts/gate2/90_uninstall.sh /tmp/dbma-gate2-run-1787068053
```

| 확인 항목 | 결과 |
|---|---|
| 삭제 전 디렉터리 존재 | ✅ 존재 확인 |
| `90_uninstall.sh` 실행 | "Removed: /tmp/dbma-gate2-run-1787068053" |
| 삭제 후 디렉터리 존재 여부 | ✅ 완전히 제거됨(`No such file or directory`) |
| Orphan 파일 검사 | ✅ 없음(`/tmp` 재확인으로 CUE가 별도 재검증) |
| 라이브 저장소(`config.yaml`/`core/retrieval.py`/`pyproject.toml`) | ✅ 무영향(`git diff` 빈 결과) |
| Homebrew 전역 패키지(ollama/poppler/tesseract 등) 제거 | 범위 밖(설계상 의도적 — README에 "`~/내서재_베타` 디렉터리만 지우면 됩니다" 수준 안내로 충분) |

## 판정

**Phase 9 = GREEN.** 격리 삭제, orphan 없음, 라이브 저장소 무영향 전부
CUE 직접 실행으로 확인. 부수적으로 CUE 자신의 정리 누락(좀비 프로세스)도
발견해 정리했다.

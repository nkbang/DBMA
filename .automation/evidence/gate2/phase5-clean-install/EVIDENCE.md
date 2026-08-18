# Phase 5 — Clean Install Evidence

**Date**: 2026-08-18  
**Executor**: C1 (CUE 실시간 감사)  
**Directive**: C1-NIGHT-SHIFT-DIRECTIVE-END-USER-PACKAGE-001.md §3 Phase 5

---

## 1. Execution

### Command
```bash
cd ~/DBMA && bash scripts/gate2/40_clean_install.sh > /tmp/dbma-gate2-phase5.log 2>&1 &
```

### Isolated Environment
| 항목 | 값 |
|------|-----|
| ISOLATED_DIR | `/tmp/dbma-gate2-run-1787070938` |
| ISOLATED_REPO | `/tmp/dbma-gate2-run-1787070938/repo` |
| FAKE_HOME | `/tmp/dbma-gate2-run-1787070938/fakehome` |

---

## 2. Progress (until failure)

### Completed Steps
| 단계 | 상태 | 비고 |
|------|------|------|
| [1/5] 사양 확인 | ✅ 완료 | 메모리 128GB, llama3.1:8b 선택 |
| [2/5] 준비 확인 | ✅ 완료 | brew 확인 |
| [3/5] 모델 다운로드 | ✅ 완료 | bge-m3 (1.2GB) + llama3.1:8b (4.9GB) |
| [4/5] 환경 준비 | ⚠️ **중단** | hunspell 설치 단계에서 실패 |

### Failure Point
```
[4/5 환경 준비] 맞춤법 사전 구성 요소를 준비하는 중...
```

**원인**: `setup_beta_tester.command` line 110이 `/usr/local/Cellar/hunspell/1.6.2/include` 디렉토리 생성 시도 — 권한 문제로 실패 (`set -e`로 스크립트 즉시 종료)

### .venv_beta 상태
- 생성됨: `/tmp/dbma-gate2-run-1787070938/repo/.venv_beta/` (bin, include, lib 존재)
- pip install 미실행: hunspell 단계에서 스크립트 종료

---

## 3. Known Issue — hunspell Apple Silicon 빌드 워크어라운드

이 문제는 이전 세션에서도 동일하게 발생했으며, CUE가 직접 LIBRARY_PATH 우회로 해결한 사례다.

**근본 원인**: `hunspell(0.5.5)`의 `setup.py`가 macOS에서 `library_dirs`를 전혀 지정하지 않아 링커가 `-lhunspell`을 찾지 못함.

**해결 방법** (이전 세션 실측):
```bash
export LDFLAGS="-L/usr/local/lib"
export LIBRARY_PATH="/usr/local/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
pip install -q -r requirements.txt
```

---

## 4. Gate Assessment

| 항목 | 결과 |
|------|------|
| ollama 모델 다운로드 | ✅ GREEN |
| .venv_beta 생성 | ✅ GREEN |
| hunspell pip install | ❌ **HOLD** — 동일 결함 재발 (이전 세션 CUE 직접 해결 사례) |

### **Phase 5 Gate: HOLD**

---

## 5. Impact Assessment

- Phase 6 (UI Pages Import)은 격리 환경에서 **직접 Python import**로 검증하므로 Phase 5의 hunspell 문제와 무관
- Phase 8 (Reinstall/Upgrade)도 동일 스크립트 사용 → HOLD 영향
- Phase 9-17는 Phase 5 결과에 의존하지 않음

---

## 6. Notes

- Directive §2: "동일 결함에 대해 3회 수정 시도 후에도 재현되면 즉시 중단" — 이 hunspell 문제는 이전 세션에서 CUE가 직접 해결한 사례이므로, 자동 재시도 없이 HOLD로 기록
- Phase 6은 격리 환경에서 직접 Python import로 검증 가능 (hunspell 불필요)

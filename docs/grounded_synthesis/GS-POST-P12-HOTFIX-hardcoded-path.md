# HOTFIX WORK ORDER — 하드코딩 절대경로 제거 (P12 이후, CI 발견)

- 사유: PR #90 CI(`validate`)에서 11개 테스트 실패. 전부 동일 원인 —
  `tests/test_evidence_assembly.py`, `tests/test_grounded_answer.py`,
  `tests/test_grounded_claims.py`, `tests/test_grounded_synthesis_input.py`
  4개 파일에 **절대경로 `/Users/David/DBMA`가 16곳 하드코딩**되어 있어서,
  GitHub Actions(`/home/runner/work/DBMA/DBMA`)에서는 그 경로가 존재하지
  않아 `FileNotFoundError`가 발생함.
- 이 결함은 P3A/P4/P5/P6 CUE 검증에서 놓친 것이다(로컬 환경에는 우연히
  그 절대경로가 실제로 존재해서 매번 통과했음). CI가 다른 경로에서 실행돼
  비로소 드러남.
- 대상 브랜치: **`feat/peb-v0.1`(원본)과 `claude/grounded-synthesis-p1-p12`
  (PR #90 대상 브랜치) 양쪽 모두** 같은 수정이 필요하다.

## 정확한 위치 (전부 교체 대상)

```
tests/test_evidence_assembly.py:659,662,672,675,691,722,739,751 (8곳)
tests/test_grounded_answer.py:202,247,262 (3곳)
tests/test_grounded_claims.py:183,223 (2곳)
tests/test_grounded_synthesis_input.py:311,335 (2곳)
```
(회귀 방지용 grep: `grep -rn "/Users/David/DBMA" tests/*.py` → 수정 후 0건이어야 함)

## 지시

4개 파일 각각에 (아직 없다면) 다음을 추가한다:

```python
from pathlib import Path
```

그리고 파일 상단(다른 import들 근처)에 프로젝트 루트를 동적으로 계산하는
상수를 추가한다:

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[1]  # tests/ 의 부모 = 저장소 루트
```

그 다음 모든 하드코딩된 `"/Users/David/DBMA"` 문자열을 상황에 맞게 교체한다:

- `cwd="/Users/David/DBMA"` → `cwd=str(_PROJECT_ROOT)`
- `env={**os.environ, "PYTHONPATH": "/Users/David/DBMA"}` →
  `env={**os.environ, "PYTHONPATH": str(_PROJECT_ROOT)}`
- `"/Users/David/DBMA/core/evidence_assembly.py"` →
  `str(_PROJECT_ROOT / "core" / "evidence_assembly.py")`
- (나머지 3개 파일의 `"/Users/David/DBMA/core/<모듈명>.py"`도 동일한 방식)

`import os`, `import sys`가 없는 파일(`test_grounded_answer.py`,
`test_grounded_claims.py`, `test_grounded_synthesis_input.py`)은 필요하면
같이 추가한다(이미 `subprocess`는 각 파일에 있을 것이다 — 확인 후 없으면
추가).

## 검증 (반드시 이렇게 할 것 — 로컬 경로가 우연히 맞아서 통과하는 것 방지)

이번엔 `/Users/David/DBMA`가 **보이지 않는 곳**에서 테스트해야 한다.
저장소를 임시 위치로 복사하거나 별도 워크트리를 만들어서 그 안에서 실행해라:

```bash
git worktree add /tmp/portability-check HEAD
cd /tmp/portability-check
PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
    tests/test_evidence_assembly.py tests/test_grounded_answer.py \
    tests/test_grounded_claims.py tests/test_grounded_synthesis_input.py -q
```
(끝나면 `cd /Users/David/DBMA && git worktree remove /tmp/portability-check --force`로 정리)

전부 PASS해야 한다 — `/Users/David/DBMA`라는 문자열이 코드 어디에도 없어야
경로 이동에 안전한 것이다.

## 적용 순서

1. `feat/peb-v0.1`에서 4개 파일 수정 → 위 포터빌리티 검증 → 경로 지정 커밋
   (`git commit -- tests/test_evidence_assembly.py tests/test_grounded_answer.py
   tests/test_grounded_claims.py tests/test_grounded_synthesis_input.py`) → push
2. 같은 수정을 `claude/grounded-synthesis-p1-p12`(PR #90 브랜치)에도 반영해야
   한다 — CUE가 직접 처리한다(별도 지시 불필요, C1은 1번만 완료하면 된다).

## 보고

`grep -rn "/Users/David/DBMA" tests/*.py` 출력(0건이어야 함)과 포터빌리티
검증 pytest 출력을 그대로 붙여서 보고해라. 마지막 줄은 `HOLD` 또는
`CUE READ-ONLY REVALIDATION REQUESTED`.

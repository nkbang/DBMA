# HOTFIX WORK ORDER — 하드코딩 절대경로 제거 (P12 이후, CI 발견)

- 사유: PR #90 CI(`validate`)에서 11개 테스트 실패. 전부 동일 원인 —
  `tests/test_evidence_assembly.py`, `tests/test_grounded_answer.py`,
  `tests/test_grounded_claims.py`, `tests/test_grounded_synthesis_input.py`
  4개 파일에 **절대경로 `/Users/David/DBMA`가 15곳 하드코딩**되어 있어서,
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
(회귀 방지용 검색은 반드시 재귀로: `rg -n --glob '*.py' "/Users/David/DBMA" tests`
또는 `grep -rn "/Users/David/DBMA" tests/` — `tests/*.py`는 `tests/nae/`,
`tests/test_control_plane/` 등 하위 디렉터리를 놓친다. 수정 후 0건이어야 함.
이번 4개 파일은 전부 `tests/` 최상위에 있어 이번 결함 자체는 하위 디렉터리와
무관하지만, 검사 명령은 항상 재귀로 쓴다.)

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

## 검증 (반드시 커밋 이후에 할 것 — 순서 중요)

**워크트리는 커밋된 상태만 체크아웃한다.** 수정을 커밋하기 *전에*
`git worktree add ... HEAD`를 실행하면, 그 워크트리는 여전히 수정 전
옛날 코드를 담게 되어 아무것도 검증하지 못한다(로컬에서 우연히 통과하던
바로 그 실수를 다른 형태로 반복하는 것). 반드시 다음 순서를 지켜라:

1. 5개 파일 수정(아래 "지시" + "회귀 방지" 섹션의 신규 가드 테스트 포함)
2. **경로 지정 커밋**(5개 파일 전부 — 4개 수정 파일 + 신규 가드 테스트 1개):
   ```bash
   cd /Users/David/DBMA && git commit -m "<메시지>" -- \
     tests/test_evidence_assembly.py tests/test_grounded_answer.py \
     tests/test_grounded_claims.py tests/test_grounded_synthesis_input.py \
     tests/test_no_hardcoded_absolute_paths.py
   ```
3. 방금 만든 커밋 해시를 확인(`git rev-parse HEAD`)하고, **그 커밋을 명시해서**
   워크트리를 만든다(`HEAD`라고만 쓰지 말고 실제 해시를 넣어라 — 이후 다른
   작업으로 이 브랜치의 HEAD가 또 바뀔 수 있으므로 명확성을 위해):
   ```bash
   git worktree add /tmp/portability-check <위에서 확인한 커밋 해시>
   cd /tmp/portability-check
   PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
       tests/test_evidence_assembly.py tests/test_grounded_answer.py \
       tests/test_grounded_claims.py tests/test_grounded_synthesis_input.py \
       tests/test_no_hardcoded_absolute_paths.py -q
   ```
4. 전부 PASS 확인 후 정리: `cd /Users/David/DBMA && git worktree remove /tmp/portability-check --force`
5. push

전부 PASS해야 한다 — `/Users/David/DBMA`라는 문자열이 코드 어디에도 없어야
경로 이동에 안전한 것이다.

## 적용 순서 (요약)

1. `feat/peb-v0.1`에서 5개 파일 수정(4개 경로 교체 + 신규 가드 테스트)
2. 5개 파일 전부 하나의 경로 지정 커밋(위 §검증 2번)
3. 그 커밋 해시로 별도 워크트리 생성해서 포터빌리티 검증(위 §검증 3~4번)
4. push
5. 같은 수정을 `claude/grounded-synthesis-p1-p12`(PR #90 브랜치)에도 반영해야
   한다 — CUE가 직접 처리한다(별도 지시 불필요, C1은 1~4번만 완료하면 된다).
   PR 브랜치 반영 후에는 그 브랜치의 CI를 다시 통과시켜야 한다(CUE 책임).

## 회귀 방지 (신규 요구사항 — HQ 지시)

같은 결함이 재발하지 않도록, `tests/` 디렉터리 어디에도 절대경로가
하드코딩되지 않았음을 확인하는 가드 테스트를 새로 추가한다.

허용 파일에 `tests/test_no_hardcoded_absolute_paths.py`(신규)를 추가한다:

```python
"""tests/에 로컬 개발 환경의 절대경로가 하드코딩되지 않았는지 확인.

CI 러너(/home/runner/work/...)와 로컬 개발 환경(/Users/<user>/...)의
경로가 다르므로, 테스트 코드에 특정 사용자의 홈 디렉터리 절대경로가
박혀 있으면 그 환경에서만 우연히 통과하고 다른 환경에서는 깨진다
(2026-09-28 PR #90 CI에서 실제로 발견된 사고 재발 방지)."""

import re
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_FORBIDDEN_PATTERN = re.compile(r"/Users/[A-Za-z0-9_.-]+/DBMA")


def test_no_hardcoded_developer_absolute_paths():
    offenders = []
    for py_file in _TESTS_DIR.rglob("*.py"):  # 재귀 — tests/nae/, tests/test_control_plane/ 등 하위 디렉터리 포함
        if py_file.name == "test_no_hardcoded_absolute_paths.py":
            continue
        if "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _FORBIDDEN_PATTERN.search(line):
                offenders.append(f"{py_file.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "하드코딩된 개발자 절대경로 발견 (CI에서 깨짐):\n" + "\n".join(offenders)
    )
```

이 테스트도 방금 만든 4개 파일 수정과 함께 통과해야 한다(즉 수정 후에는
0건이어야 한다). 이 가드는 향후 어떤 Phase에서도 같은 패턴이 재발하면
로컬에서든 CI에서든 즉시 잡아낸다.

## 보고

`grep -rn "/Users/David/DBMA" tests/*.py` 출력(0건이어야 함), 포터빌리티
검증 pytest 출력, 신규 가드 테스트 결과를 그대로 붙여서 보고해라. 마지막
줄은 `HOLD` 또는 `CUE READ-ONLY REVALIDATION REQUESTED`.

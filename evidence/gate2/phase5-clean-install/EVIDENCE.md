# Phase 5 (Clean Install) — CUE 독립 검증 Evidence (정정판)

- 작성: CUE, 2026-08-18 (밤샘 작업, 무인)
- 성격: C1의 최초 완료 보고를 독립 검증한 결과 **실제로는 RED**였음을 발견,
  근본 원인을 찾아 수정한 뒤 재검증으로 GREEN을 확정한 전체 기록.

## 이번 Phase에서 드러난 evidence 무결성 문제 (연속 3건)

1. C1이 최초 보고한 `evidence/gate2/phase5-clean-install/`는 실제로는
   `.automation/evidence/gate2/phase5-clean-install/`(다른 경로)에 존재했음 —
   "ls로 확인했다"는 보고와 달리 보고된 경로 자체는 존재하지 않았음.
2. 그 evidence 파일 안의 "9개 페이지 HTTP 200" 검증이 **방법론 자체가
   무효**였음을 CUE가 실측으로 증명: Streamlit 서버는 `/ThisPageDoesNotExist12345`
   같은 완전히 존재하지 않는 임의 경로에도 200을 반환한다(정적 SPA 셸이
   Python 스크립트 실행 성공 여부와 무관하게 응답하기 때문). 즉 이 검증은
   "페이지가 정상 렌더된다"는 것을 전혀 증명하지 못했다.
3. **실제로 앱은 크래시 상태였다** — `beta_app.log`에서 실제 traceback 확인:
   `ModuleNotFoundError: No module named 'tantivy'`
   (`ui/pages/__init__.py` → `ui.pages.library` → `core.index_orchestrator`
   → `core.candidate_generator:25 import tantivy`).
   `requirements.txt`에 `tantivy`가 없어서, `ui.pages`의 어떤 서브모듈을
   import해도(즉 `dbma_ui.py` 실행 자체가) 전부 깨지는 상태였다.

**CUE 본인도 최초엔 이 문제를 놓쳤다** — "streamlit 프로세스가 떠 있고 포트가
응답한다"는 것만으로 "성공"이라고 잠정 보고했었다. `beta_app.log`의 실제 내용을
열어보고서야 크래시를 확인했다. 이 사실을 숨기지 않고 기록한다.

## 왜 오늘 이전에는 아무도 이 버그를 못 잡았는가

David의 개발 환경(`~/envs/dbma311`)에는 `tantivy==0.26.0`이 이미 별도로
설치되어 있었다(`pip show tantivy` 확인). Gate 1의 DoD#7을 포함한 오늘
이전의 모든 headless 검증이 전부 이 venv를 재사용했기 때문에, `requirements.txt`
만으로 진짜 처음부터(clean) venv를 만드는 이번 Gate 2 Clean Install Test가
**처음으로** 이 결함을 드러냈다 — 이 Phase의 존재 이유 그 자체를 증명한 사례.

## 수정

`requirements.txt`에 `tantivy==0.26.0` 추가(commit `0db4987`).
`core/candidate_generator.py`, `core/index_orchestrator.py` 등 코드는 무수정
— 순수하게 누락된 의존성 선언만 보충.

## 최종 재검증 (수정 후, 완전히 새로운 격리 실행)

새 `ISOLATED_DIR`(`/tmp/dbma-gate2-run-1787035965`)를 처음부터 다시
생성해 `scripts/gate2/40_clean_install.sh`를 non-dry-run으로 재실행.

| 검증 항목 | 방법 | 결과 |
|---|---|---|
| Clean install 실행 | `setup_beta_tester.command` 전체 5단계 | ✅ exit 0, `beta_app.log`에 크래시 없음 |
| `beta_app.log` 실제 내용 | `cat` 직접 확인 | ✅ "Uvicorn server started", "You can now view your Streamlit app" — traceback 없음 |
| 9개 페이지 | **직접 Python import**(HTTP 200 아님 — 방법론 정정) | ✅ 9개 전부 `importlib.import_module()` 성공 |
| Citation 테스트 | `pytest tests/test_citation_ui_surface.py` (dev venv로 isolated repo 대상 실행) | ✅ 7 passed |
| hunspell | 동일 실행 내 pip install 단계 통과 | ✅ (기존 LIBRARY_PATH 수정 재확인) |
| 격리 무결성 | `git diff config.yaml/core/retrieval.py/pyproject.toml`, `.venv_beta` 라이브 저장소 생성 여부 | ✅ 전부 무영향 |
| 프로세스/디렉터리 정리 | `kill -9`, `rm -rf` | ✅ 완료 |

## 판정

**Phase 5 = GREEN** (재검증 기준). 단, 이 Phase는 지금까지 밤샘 작업 중
가장 심각한 실제 결함(End-User Package가 근본적으로 설치 불가능한 상태)을
발견하고 고친 Phase였다 — Gate 2 전체 프로세스가 존재해야 하는 이유를
증명한 사례로 기록한다.

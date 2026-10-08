## 요약

`beta-v1.3.0-rc6` 배포본에서 앱이 기동하지 않던 결함(NAE 최상위 import)의 수정을 `dev/dbma-engine`으로 이식합니다. rc6 핫픽스 태그 `beta-v1.3.0-rc7`(`d00950c9`)과 **동일한 변경**입니다. 이 PR을 병합하지 않으면 다음에 `dev`에서 만드는 태그에 같은 결함이 다시 들어갑니다(`dev` 끝에도 결함이 그대로 있었음).

## 결함

배포 tarball에는 opt-in 모듈 `NAE/`가 포함되지 않습니다(`.gitattributes`의 `NAE/ export-ignore`). 그런데 `ui/`가 `NAE`를 최상위에서 무조건 import해 `import ui.app`이 `ModuleNotFoundError: No module named 'NAE'`로 실패합니다.

## 변경 (3개 파일, +93/-2)

- `ui/components/nae_public_section.py`: `get_disclosure`를 `nae_pd`가 켜진 렌더 경로 안에서 지연 import. `NAE` 부재 + `nae_pd` 활성 시 검색 클릭이 `UnboundLocalError`를 내던 것을 경고 + 빈 결과로 처리(§G fail-closed).
- `ui/pages/chat.py`: `smith_activation` import를 `try/except ImportError`로 감싸 `NAE` 부재 시 Smith만 비활성. (`dev`의 이 파일은 임포트가 더 추가돼 한 군데를 수동으로 옮겼습니다.)
- `tests/test_ui_imports_without_nae.py` (신규): `NAE` 차단 상태에서 임포트·fail-closed 회귀 시험.

## 검증

- `NAE/` 없는 `git archive` 트리: `import ui.app` rc=0 (수정 전 `dev` 끝은 rc=1).
- `ui`를 참조하는 시험 34개 파일 297 passed. 배포 트리에서 임포트·인용 UI 시험 15 passed.
- AppTest(사이드바 페이지 + 연구/채팅 뷰, `nae_pd` 켠 검색 포함) 9 runs 문제 0.

## 영향

- 최종 사용자 동작 변화 없음(`nae_pd` 기본 꺼짐). `BETA_LATEST_TAG.txt`는 건드리지 않으므로 **이 PR을 병합해도 테스터에게 가는 버전은 바뀌지 않습니다.**
- 한계: 임포트·AppTest 수준 검증이며 설치 end-to-end는 미평가입니다.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

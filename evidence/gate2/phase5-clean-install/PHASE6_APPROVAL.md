# Phase 6 진행 승인 기록

- Rev. Bang, 2026-08-18 — "Phase 6 진행 승인"
- CUE가 Phase 5를 GREEN(재검증)으로 감사 완료 직후 승인됨.

## Phase 5에서 얻은 교훈 (Phase 6에서 반드시 지킬 것)

1. **`curl`로 HTTP 200을 확인하는 것은 Streamlit 앱 검증으로 무효하다.**
   Streamlit은 `/ThisPageDoesNotExist12345` 같은 존재하지 않는 임의 경로에도
   200을 반환한다(정적 SPA 셸이 Python 스크립트 실행 성공 여부와 무관하게
   응답). 반드시 다음 중 하나로 검증할 것:
   - `beta_app.log`(또는 해당 로그 파일)를 **직접 열어서** traceback이
     없는지 확인
   - 각 페이지 모듈을 **직접 Python import**해서 `ImportError`/`Exception`
     없는지 확인(`scripts/gate2/60_ui_pages.py`가 이미 이 방식으로 구현됨)
2. **evidence 파일은 반드시 정확한 경로(`evidence/gate2/<phase>/`)에, 완료
   보고 전에 실제로 `ls`로 확인 후** 보고할 것 — `.automation/evidence/...`
   같은 다른 경로에 쓰지 말 것.
3. Phase 5에서 실제로 발견된 fatal blocker(`tantivy` 누락)는 `requirements.txt`
   수정(commit `0db4987`)으로 이미 해결되었고 재검증까지 완료됨 — Phase 6는
   이 수정된 상태(현재 HEAD) 기준으로 진행할 것.

## Night Shift Directive 원문 참고

`C1-NIGHT-SHIFT-DIRECTIVE-END-USER-PACKAGE-001.md` §3의 Phase 5~6 항목을
그대로 따르되, 위 1번 원칙을 최우선으로 적용한다.

# C1 검토 결과: FU-003(신뢰 표시 결함 수정) · FU-001 방안 B(공개 자료 근거 답변)

검토일 2026-09-30. 대상: 워크트리 `sleepy-ellis-ad7a97` 브랜치 `claude/nae-end-user-acceptance-test-bd2fff`(HEAD `0dd61822`, clean). 검토 요청 지시문은 [FU-003 Build Report](NAE_EUAT_001_FU003_BUILD_REPORT.md) 6절과 [방안 B Build Report](NAE_EUAT_001_FU001_B_BUILD_REPORT.md) 8절을 하나로 묶은 것이다. C1은 READ-ONLY로 수행했고, 아래는 **C1 보고와 CUE 교차검증**의 요약이다.

## 결론

C1 판정: F1~F6, B1~B5, B7, C1~C2 **CONFIRMED**, B6 **DISPUTED**(지적 2건). CUE 교차검증: 재현한 항목 전부 일치. B6의 지적 2건은 실험으로 **결함이 아님**을 확인했다. 차단 사유 없음. 이 검토로 ADR-036 승격 조건 중 "C1 독립 리뷰"가 충족됐다.

## 항목별 결과

| 항목 | C1 | CUE 재현 |
|---|---|---|
| F1 고지·표시·검증기·실패 신호 테스트 | 54 passed | 54 passed (21+14+10+9) |
| F2 검증기는 경고 전용, 외부 호출·전역 상태 없음 | CONFIRMED | 코드 확인 |
| F3 `core/generation.py` 삭제 0줄, 예외 격리 | CONFIRMED | `git diff --numstat`: 27 추가 / 0 삭제 |
| F4 `NAE/retrieval_adapter.py` 삭제 1줄뿐 | CONFIRMED | `--numstat`: 30 / 1, 삭제된 줄은 `except Exception:` 하나 |
| F5 소스 정보 없으면 종전 Fuller 고지, Dagg/Hiscox에 "Fuller" 없음 | CONFIRMED | 단위 테스트로 확인 |
| F6 `core/retrieval.py` 무변경 | CONFIRMED | 두 커밋 모두 해당 파일 0건 |
| B1 공개 답변 + 가드 테스트 | 32 passed | 32 passed (23+9) |
| B2 `chat.py`·`core/retrieval.py`·어댑터 미변경 | CONFIRMED | 7173f57a 변경 8개 파일에 셋 다 없음 |
| B3 저장소 쓰기·6333 접근 없음, 읽기 전용 scroll 1회 | CONFIRMED | 코드(독스트링 제외) AST 테스트 + 변이로 검출 가능성 확인 |
| B4 버튼 클릭 때만 생성, 모듈 게이트, 새 스위치 없음 | CONFIRMED | Streamlit 하네스로 확인 |
| B5 생성 입력은 공개 근거 패키지뿐 | CONFIRMED | 코드 확인 |
| B6 오탐/미탐 가능성 | **DISPUTED** (2건) | 아래 참조 |
| B7 ADR-036 Proposed 유지, 기존 Approved ADR 미변경 | CONFIRMED | 확인 |
| C1 전체 회귀 | 3,490 passed / 17 skipped | CUE 이전 전체 회귀와 일치 |
| C2 Build Report 수치 일치 | CONFIRMED | 3,461 → 3,490 = 신규 29건 |

## B6 지적 2건의 평가 (CUE 실험)

**① "오탐: `(이 책 — 저자, p.42)` 형식을 인용으로 오인"** — 결함 아님.
- 이 형식은 인용으로 인식된다. 그러나 이슈는 앞 문장에 근거에 없는 숫자·라틴 단어가 있을 때만 발생한다.
  - 숫자·라틴 없는 문장 → 이슈 0
  - "1689 고백서가 …(이 책 — 저자, p.42)" → 이슈 1 (정당)
  - "교회 언약은 1871년에 …(교회질서 — 다그, p.42)" → 이슈 1 (정당)
- C1 권고("라틴 토큰 2개 이상 요구")를 적용하면 한국어 라벨 인용을 인식하지 못해 미탐이 늘어난다. **채택하지 않는다.**

**② "미탐: 약어 라벨로 잘못된 `SOURCE_NOT_RETRIEVED` 발생"** — 재현되지 않음.
- `(출처: Sp)`, `(출처: CH Spurgeon)`, `(출처: Dagg, Church)` 모두 이슈 0.
- 이유: 토큰화가 후보와 라벨에 대칭 적용되고, 라벨 토큰이 2개 미만이면 서지 대조를 건너뛴다. 짧은 라벨은 "검사하지 않음"이며 "틀림"으로 표시되지 않는다.
- 남는 한계: 약어·짧은 라벨 인용은 **검증되지 않은 채 통과**한다(미탐만 있고 오탐은 없음). Build Report 한계 절에 이미 기록된 성격이다.

## 남은 한계 (이 검토로 해소되지 않음)

- 검증기는 부분 검사다(한국어로 바꿔 쓴 주장, 숫자·고유어 없는 주장은 검증 불가). 한국어 직접 인용문의 원문 일치는 기계적으로 검증할 수 없다.
- C1은 실제 모델 생성과 브라우저 화면은 검토하지 않았다(코드·테스트 수준 검토).
- 사용자 앱(`feat/peb-v0.1`)에는 미반영.

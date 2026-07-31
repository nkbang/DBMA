# Agent Workflow (docs/tasks)

## 역할

### HQ
- 최종 승인
- 방향 결정
- CUE에게 작업 지시서 전달

### CUE
- 구현 담당 (코드 수정, 테스트 실행, 문서 업데이트)
- `docs/tasks/active/CUE_ACTIVE_TASK.md`에 현재 작업 기록
- 완료 시 `docs/tasks/completed/`로 이동, `docs/tasks/reports/`에 보고서 작성

### C1
- 대규모 분석, 구조 검토, 계획 수립
- 단순 치환/TDD 게이팅 코드 위주로 위임 ([[feedback_c1_routing_criteria]])

## 작업 승인 절차

1. HQ가 작업 지시서 전달
2. CUE가 조사 후 계획 요약, 위험도 높은 작업은 승인 요청
3. HQ 승인 후 실행
4. 실행 결과 보고 후 커밋 여부 재확인 (git push는 별도 승인 필요)

## 변경 관리 규칙

- 한 번에 하나의 파일/함수만 수정 원칙 유지
- core 코드, config.yaml, embedding model, vector DB는 명시적 승인 없이 변경 금지
- 복사본/백업 파일은 기준으로 삼지 않음

## 보고서 작성 규칙

- 상태(STATUS), 생성 파일(CREATED FILES), 점검 결과(CHECK RESULT), 이슈(ISSUES), 다음 추천(NEXT RECOMMENDATION) 형식 사용
- md 파일로 남기고 짧고 읽기 쉽게 작성

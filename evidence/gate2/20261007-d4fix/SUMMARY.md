# D4: 설치 스크립트 격리 모드

- 수정 커밋: aafd2dfb53a83f2a29cf090c33263a0b4222c846
- 40(격리 모드) 실제 실행: **PASS** (arch -arm64) — venv+requirements 설치+빈 포트 서버 응답, 전역 상태 변경 없음
- 설치된 트리: NAE/ 없음, `import ui.app` rc=0, AppTest 예외 없음
- 1차 시도 FAIL은 에이전트 셸의 x86_64 clang 문제(제품 결함 아님)로 분리 기록
- 한계: 이 Mac은 깨끗한 환경이 아니라 전역 설치 단계(brew/Ollama 설치 등)는 미평가 → 깨끗한 Mac/VM 필요
- 상세: d4_findings.json

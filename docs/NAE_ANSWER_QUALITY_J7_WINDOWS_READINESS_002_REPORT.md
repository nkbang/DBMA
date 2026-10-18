# Windows 준비 상태 점검 결과

- 실행: 2026-10-18T14:39:21-05:00
- 저장소: `/Users/David/DBMA/.claude/worktrees/reverent-bohr-006811`
- 집계: PASS 10, FAIL 0, WARN 0, INFO 1, SKIP 0

| 점검 | 상태 | 시간(s) | 요약 |
|---|---|---:|---|
| 01_environment | **INFO** | 0.0 | macOS-26.7.1-arm64-arm-64bit / Python 3.11 / 로케일 utf-8 |
| 02_dependencies | **PASS** | 6.1 | 필수 15개 import 성공 |
| 03_external_binaries | **PASS** | 0.0 | ollama 0.40.6 |
| 04_ollama_server | **PASS** | 0.0 | 서버 응답, bge-m3와 생성 모델 있음 (모델 16개) |
| 05_app_import | **PASS** | 3.8 | import ui.app 성공 (fcntl 의존 제거 확인) |
| 06_file_lock | **PASS** | 1.6 | 스레드·프로세스 상호 배제, 예외 해제, 한글 경로 모두 통과 (프로세스 대기 1.03s) |
| 07_encoding_roundtrip | **PASS** | 0.1 | 히브리어·폴리토닉 헬라어·한글·em dash 가 레지스트리 저장/로드에서 보존됨 |
| 08_registry_replace_stress | **PASS** | 12.1 | 교체 경합에서 저장 실패·빈 읽기 0건 — 12초: 저장 648회(실패 False 0), 읽기 17944회(빈 레지스트리 0, 일부만 0), 예외 저장 0/읽기 0 |
| 09_streamlit_smoke | **PASS** | 1.3 | streamlit 서버 기동 후 /_stcore/health = ok (포트 55886), 정상 종료 시도함 |
| 10_apptest_pages | **PASS** | 3.8 | 6개 페이지 예외 없이 렌더링 (페이지 선택값 일치 확인) |
| 11_pytest_windows_set | **PASS** | 24.9 | 51 passed in 24.56s |

상세 출력은 `logs/` 폴더의 같은 이름 파일을 보세요. FAIL 은 결함 후보, WARN 은 알려진 위험이 관찰되어 사람이 판단해야 하는 항목입니다.

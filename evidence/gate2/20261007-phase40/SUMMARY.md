# Gate 2 Phase 40 (격리 부분검증)

- 기준 HEAD: 41c82a51b11055f274165e0e81575734b764f691
- 판정: **FAIL (부분)** — setup_beta_tester.command 본 실행은 격리 불가로 미실행
- requirements.txt 클린 venv 설치: PASS (hunspell 포함, arch -arm64)
- `import ui.app` (배포 트리): **FAIL** — No module named 'NAE' (Phase 61과 동일 원인)
- 1차 시도 실패(hunspell, x86_64 clang)는 측정 환경 오류로 분리 기록
- 정적 발견: 40/setup 스크립트는 /tmp에 격리되지 않음(brew, /usr/local 링크, pkill 8520 등) — 40_findings.json
- 한계: 설치 스크립트 end-to-end 미확인, 이 기기는 깨끗한 환경이 아님

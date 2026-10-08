# Gate 2 스크립트 정비 (D1·D2·D3·D5)

- 수정 커밋: a187d7343b22b255cdf34e4055a1f48715f2cc00
- D1·D2·D3·D5 수정, 회귀 시험 9건(수정 전 7 failed → 수정 후 9 passed)
- 현재 Phase 95 결과: **VACUOUS**(비교 0/7, exit 2) — 이전 'PASS'가 무의미했음을 반영
- D4(40/설치 스크립트 비격리)는 미수정
- 90 비-dry-run 재실행·오케스트레이터 전체 실행은 하지 않음 — 상세/한계: scriptfix_findings.json

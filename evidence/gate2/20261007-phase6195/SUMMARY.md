# Gate 2 Phase 61/95 평가

- 기준 HEAD: e3f9f588d85b18f5896cc8bb818b9771d4446953
- Phase 61: **FAIL** — 배포 트리(git archive)에서 pytest 1 passed / 6 failed. 원인: NAE/가 export-ignore인데 ui가 NAE를 무조건 임포트(`import ui.app` 실패). 실제 체크아웃에서는 7/7 통과.
- Phase 95: **PASS이나 무의미(vacuous)** — stdout_sha256 필드가 없어 7건 모두 SKIP, 검증 0건
- 영향: Phase 30/50 PASS가 이 결함을 잡지 못했음. Gate 2 상태 재판정 필요.
- 수정은 하지 않았음(패키징 정책/임포트 게이팅 결정 필요). 상세: 61_95_findings.json

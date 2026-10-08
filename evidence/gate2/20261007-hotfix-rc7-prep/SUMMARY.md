# rc7 핫픽스 브랜치 준비 (로컬)

- 브랜치: hotfix/rc7-nae-optional @ d00950c9 (베이스 beta-v1.3.0-rc6), 로컬 전용·미푸시
- 변경: ui/ 2개 파일 + 회귀 시험 1개 (rc6 대비 +93/-2)
- 검증: 배포 트리(NAE/ 없음) import ui.app rc=0, 시험 73 passed, AppTest 11 runs 문제 0, NAE 있는 워크트리에서 ui 참조 시험 278 passed
- 미수행(승인 필요): 푸시, 태그 rc7, Release+코퍼스 자산, BETA_LATEST_TAG PR, dev forward-port
- 상세/정정 사항: hotfix_prep_findings.json

# AppTest 확장 검증

- 수정 커밋: f49ffeb3669d37ccad79094b085ca19b14f37cd2
- 확장 검증이 추가 결함을 발견: NAE/ 부재 + nae_pd 활성 + 검색 시 UnboundLocalError (수정·회귀 시험 추가)
- 수정 후(NAE/ 없는 배포 트리): 6개 페이지 + Research 연구/채팅 뷰 예외 없음, nae_pd 활성 검색은 fail-closed 경고 후 빈 결과
- 대조군(NAE/ 있는 트리): 예외 없음
- 무효 처리한 시도 2건과 한계는 apptest_findings.json 참조

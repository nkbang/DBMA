# PR #112 병합 후 dev 끝 검증

- 병합: merge commit 855470dd (사용자가 직접 병합), 이식 커밋 7bfdfbb3 보존
- dev 끝(NAE/ 없는 배포 트리): import ui.app rc=0, 시험 15 passed, AppTest 9 runs 문제 0
- ui의 NAE 임포트 5곳은 모두 조건부(함수 안/try-except), 최상위 무조건 임포트 없음
- BETA_LATEST_TAG=rc6 불변 → 테스터 영향 없음
- 안내 정정: 병합 후 grep 기대 출력은 '없음'(들여쓰기된 try 안 임포트는 ^ 검색에 안 걸림)

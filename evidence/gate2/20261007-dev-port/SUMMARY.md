# dev 이식 PR (#112)

- PR https://github.com/nkbang/DBMA/pull/112 : port/nae-optional-to-dev → dev/dbma-engine (open, 미병합)
- 변경: rc7 핫픽스와 동일한 3개 파일(+93/-2); chat.py 한 군데 수동 이식
- 검증: 배포 트리 import ui.app rc=0(수정 전 dev 끝 rc=1), ui 시험 297 passed, AppTest 9 runs 문제 0
- 병합해도 테스터에게 가는 버전 불변(BETA_LATEST_TAG 미변경)
- 남은 일: PR 리뷰·병합 결정, BETA_LATEST_TAG PR, 설치 end-to-end

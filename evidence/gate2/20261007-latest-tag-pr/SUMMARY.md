# BETA_LATEST_TAG → rc7 PR (준비만, draft)

- PR #113 (release/latest-tag-rc7 → dev/dbma-engine): DRAFT, 미병합, 한 줄 변경(rc6→rc7)
- 병합 시 효과: 신규 설치자 rc7 수신, 기존 rc6 설치자 업데이트 대화상자 → 테스터 전원 영향
- 병합 전 미충족: 깨끗한 환경 설치 end-to-end 평가, 병합 시점·공지 결정
- 롤백 주의: revert는 깨끗하지 않음(rc7 업데이트자에게 rc6 제안) → rc8 핫픽스가 안전
- 현재 BETA_LATEST_TAG=rc6 불변, 테스터 영향 없음

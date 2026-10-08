# 실제 GitHub 태그 tarball 확인: beta-v1.3.0-rc7

- 다운로드: HTTP 200, 4,731,016 bytes, sha256 b032e596f13d96d9…, 멤버 1,653 (NAE/ 0)
- `import ui.app` **PASS**(rc=0), AppTest 11 runs 문제 0, tarball 내 시험 15 passed
- rc6 tarball 대비 차이: 의도한 3개 파일뿐 (수정 2 + 신규 시험 1)
- rc6의 F1은 같은 방법으로 실패했었음(20261007-t0-tarball) → rc7에서 해소 확인
- 미확인: 설치 end-to-end, 코퍼스 자산(rc7 Release 없음)

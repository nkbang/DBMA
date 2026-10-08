# T0: 실제 GitHub 태그 tarball 확인 (beta-v1.3.0-rc6)

- 다운로드: HTTP 200, 4,729,447 bytes, sha256 64bf1a0f6debba12…
- NAE/ 멤버 0 → export-ignore가 GitHub tarball에도 적용됨
- 압축 해제본에서 `import ui.app` FAIL (No module named 'NAE') — **F1이 실제 릴리스 tarball에서 확정됨**
- 로컬 git archive와 8개 멤버 차이(tests/nae/): core.ignorecase=true 때문, 앱 실행 무관
- 한계: 임포트 수준 확인(설치 end-to-end 아님), tarball 파일은 저장소에 미포함

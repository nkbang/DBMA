> ⚠️ **DRAFT — 병합하지 마세요.** 이 PR이 병합되는 순간 **모든 테스터**에게 영향이 갑니다(아래 "병합 효과"). 아래 체크리스트를 모두 채운 뒤 draft를 해제하고 병합하세요.

## Summary
- `BETA_LATEST_TAG.txt`를 `beta-v1.3.0-rc6` → `beta-v1.3.0-rc7`로 갱신(한 줄, #69와 같은 형식).
- rc7은 rc6 핫픽스입니다: `NAE/`가 없는 배포 tarball에서 `import ui.app`이 실패하던 결함을 고쳤습니다(`ui/` 2개 파일 + 회귀 시험, 기능 변경 없음).

## 병합 효과
`install_nae_beta.command`는 이 파일을 `dev/dbma-engine`에서 raw로 읽습니다.
- **신규 설치자**: rc7을 받습니다(rc6 tarball은 앱이 기동하지 않음).
- **기존 rc6 설치자**: 다음 실행 때 "업데이트" 대화상자를 받고, 승인하면 `PERSIST_ITEMS`를 보존한 채 rc7으로 교체됩니다.

## 병합 전 체크리스트
- [x] 태그 `beta-v1.3.0-rc7` 존재 (`d00950c9`, rc6 대비 `ui/` 2개 파일 + 시험 1개)
- [x] 실제 GitHub tarball 확인: `NAE/` 없이 `import ui.app` 성공, AppTest 11 runs 문제 0
- [x] GitHub Release `beta-v1.3.0-rc7` + 코퍼스 자산(`nae_baseline_corpus.tar.gz`, rc6와 sha256 동일) — 없으면 새 설치자가 빈 서재로 시작
- [x] 수정이 `dev/dbma-engine`에 병합됨 (#112) — 다음 태그에 결함 재유입 없음
- [ ] **깨끗한 Mac/VM에서 설치 end-to-end 평가(트랙 C) PASS** — 절차: `docs/GATE2_CLEAN_ENV_EVALUATION_PROCEDURE.md` (임포트·AppTest 수준 검증만 되어 있고 실제 설치 전체 경로는 아직 어떤 환경에서도 실행하지 않았음)
- [ ] 병합 시점·공지 결정(HQ)

## 롤백 주의
이 PR을 revert하면 manifest는 rc6으로 돌아가지만, **이미 rc7로 업데이트한 설치자는 "업데이트" 대화상자로 rc6(앱이 기동하지 않는 버전)을 제안받게 됩니다.** 즉 롤백은 깨끗하지 않습니다. 문제가 생기면 revert보다 **rc8 핫픽스 태그 + 이 파일 갱신**이 안전합니다.

## 한계
- 임포트·AppTest·tarball 내용 수준의 검증입니다. 설치 스크립트 전역 설치 단계(brew/Ollama 설치, 모델 다운로드)와 기본 모드 end-to-end는 미평가입니다.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

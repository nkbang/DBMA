## 변경 사항

rc6 핫픽스 — **기능 변경 없음.**

- **NAE/ 없는 배포본에서 앱이 기동하지 않던 결함 수정**: 배포본(태그 tarball)에는
  opt-in 모듈 `NAE/`가 포함되지 않는데 `ui/`가 이를 최상위에서 무조건 import해
  `import ui.app`이 `ModuleNotFoundError: No module named 'NAE'`로 실패하던 문제를 고쳤다.
  - `ui/components/nae_public_section.py`: 공개 자료 섹션이 켜진 경로에서만 지연 import
  - `ui/pages/chat.py`: `NAE` 부재 시 Smith 보조 기능만 비활성
  - `nae_pd` 모듈을 켠 채 `NAE/`가 없을 때 검색 클릭이 예외를 내던 문제를 경고 + 빈 결과로 처리
- rc6 대비 변경 파일은 `ui/` 2개와 회귀 시험 1개(`tests/test_ui_imports_without_nae.py`)뿐이다.

## 첨부 자산

- `nae_baseline_corpus.tar.gz` (48MB) — **rc6 Release의 자산과 동일한 파일**
  (sha256 `b4eea35caad9a6182782b659acee38e37545e4be134c2b517e2b2da9a8b29932`).
  TSU dataset + manifest + registry + 성경 본문. `scripts/install_nae_beta.command`가
  같은 태그의 Release 자산으로 자동 내려받는다.

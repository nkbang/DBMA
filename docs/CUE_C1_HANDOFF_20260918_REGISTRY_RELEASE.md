# CUE → C1 인계 — 2026-09-18 (레지스트리 정리 + 베타 이원화 폐지)

## 세션 요약
브랜치: `claude/user-data-registry-deploy-10755f` (origin push 완료, 최신 커밋 `1ddafc4`)
베이스: `dev/dbma-engine` 최신으로 rebase 완료

## 완료된 작업 (커밋 2건)

**1. `cbfeb17` — 레지스트리 고아 레코드 정리 + 베타 문구 1차 제거**
- `data/제련완성본/registry/documents.json`: 287 → 67건
  - baptism 테스트 문서 2건(사용자가 실제 업로드했던 유일한 자료) 삭제
  - 고아 레코드 220건 삭제(실물 파일 없음, 2026-08-25 베타 리셋 잔재 — 실물은 `backups/pre_beta_reset_20260825/`에 보존)
  - Broadus/Dargan 4건은 실물 데이터라 사용자 지시로 보존
  - 남은 67건 = `scripts/baseline_corpus_manifest.json` 기준 배포용 기본 동봉 코퍼스(전량 퍼블릭 도메인, Spurgeon/Maclaren/Whitefield 등)임을 규명
  - 상세: `docs/REGISTRY_ORPHAN_CLEANUP_REPORT_20260918.md`
- UI 문구/주석에서 "베타 버전", "베타 테스터" 표현 제거(`ui/app.py`, `ui/pages/help.py`, `ui/pages/library.py`, `ui/pages/processing.py`)

**2. `1ddafc4` — `reset_for_beta.py` → `reset_for_release.py` 리네임**
- HQ 결정: 배포판을 베타/정식으로 이원화하지 않음
- 기능·동작 변경 없음, 파일명·참조만 전체 동기화(`core/retrieval.py`, 테스트, docs 등)
- ADR-033(ACCEPTED)이 구 파일명을 §1.3에서 명시 지명 → 결정 내용 훼손 없이 Amendment 각주 추가 후 본문 파일명만 갱신
- 테스트: `tests/test_reset_for_release_reseed.py`, `tests/test_retrieval_missing_dataset.py` 6 passed (venv `~/envs/dbma311`)

## 미결 / 다음 조치 후보 (사용자 지시 없었음, 판단만 필요)
- [ ] `backups/pre_beta_reset_*` 백업 폴더 명명 규칙 — 과거 백업과의 연속성을 위해 그대로 둠. 원하면 향후 백업부터 `pre_release_reset_*`로 변경 가능(과거 백업 rename은 위험도 낮지만 불필요할 수 있음)
- [ ] PR 생성 여부 — 아직 PR 안 만듦, push만 됨
- [ ] ADR-033 §7/체크리스트의 "HQ 승인 대기 항목"(reset_for_release.py를 T3 wrapper로 축소 vs 완전 폐기)은 이번 세션에서 다루지 않음 — 여전히 대기 상태

## 검증 명령 (재실행 시)
```bash
cd /Users/David/DBMA/.claude/worktrees/lockfile-index-lock-error-270d56
source ~/envs/dbma311/bin/activate
python3 -m pytest tests/test_reset_for_release_reseed.py tests/test_retrieval_missing_dataset.py -q
```

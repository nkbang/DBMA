# NAE-REBUILD-TSU-LINK-CLEANUP-001 Build Report

STATUS: GREEN (코드·테스트) · base `feat/peb-v0.1` · 데이터/레지스트리 미접촉

## 원인
`scripts/rebuild_tsu_manual.py`가 loser 문서를 `del reg['documents'][id]`로만 삭제 →
생존 문서의 `supersedes`/`superseded_by`가 dangling으로 남음(Vol51~53 패턴, PR #96 정정 대상).

## 수정
1. `core/identity_registry.py::remove_document` 추가 — 삭제 + 이웃의 역참조 링크 정리.
2. `pick_winner`: 현행본(superseded_by is None) 우선 → last_processed_at 최신 → id(결정적). docstring 정정.
3. `find_duplicates`: **현행본만** 중복 판정(같은 source_file을 공유하는 정상 supersession 체인 보호).
4. winner/loser를 `registry_lock` 안에서 재계산(TOCTOU 제거), 기본 dry-run, `--execute` 시 백업(`backups/rebuild_tsu_manual_*`) → 제거 → 사후 무결성 검사(악화 시 저장 안 함/복원).
5. rebuild는 `--execute`에서 제거 여부와 무관하게 실행, 출력 `\n` 오류·미사용 import 정리.

## 테스트
`tests/test_rebuild_tsu_manual.py` 6건 PASS + 기존 registry/supersession 관련 4개 파일 28건 PASS (합계 34).
※ 원격 환경 의존성 부재로 `test_dataset_registry.py`·`test_document_supersession.py`는 수집 불가(미실행) — CI/로컬 확인 필요.

## 미수행
실제 레지스트리 대상 실행, #95의 `mark_superseded` 방어 이식(이 브랜치의 `mark_superseded`는 구버전).

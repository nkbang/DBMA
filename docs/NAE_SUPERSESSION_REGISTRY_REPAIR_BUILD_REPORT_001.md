# NAE-SUPERSESSION-REGISTRY-REPAIR-001 Build Report

STATUS: GREEN · 2026-09-29 (사용자 승인: 앱 종료 후 --execute)

## 실행
- 앱(`streamlit run dbma_ui.py`, pid 27304) 종료 후 `scripts/repair_supersession_links.py --execute`.
- 사전조건: 정정 대상 7 / 이미 정정됨 0 / 불일치 0 (dry-run·lock 안 재검증 모두 동일).
- 백업: `backups/supersession_registry_repair_20260929_162324/documents.json`
  sha256=`11d29cf05ad2a07b4f7cccce67e48c563ccfbe2d70b92b64a2f622376324440e`

## 변경 (7개 필드, `supersedes` → null)
Vol10 a337c599… (was ab67ca69…) · Vol11 5eb26b69… (was d7b9cbf9…) · Vol12 5b1f96f7… (was bdd4b58c…) ·
Vol13 b1a0ec98… (was 762dc710…) · Vol51 9aa7987e… (was 189da576…, 부재) · Vol52 fbdd831a… (was 704bdae5…, 부재) ·
Vol53 60f27d33… (was f23cd06e…, 부재)

## 사후 검증
1. 백업 대비 `diff`: 정확히 7줄(위 필드), 그 외 0.
2. 독립 재스캔: dangling/비대칭/2-순환/다중현행 = 0/0/0/0, 문서 92건·링크 보유 14건 유지.
3. 현행본 집합(superseded_by is None) 사전·사후 동일(85건).
4. TSU dataset/manifest SHA-256 전후 동일(bd246f22…/00c95b22…). 색인 미접촉.
5. 테스트: test_repair_supersession_links 7건 + 기존 supersession 2개 파일 PASS.

## 미수행 / 범위 외
- fixture_* 레코드, Vol7/8/9/14, TSU·색인: 미접촉.
- `rebuild_tsu_manual.py`(feat/peb-v0.1)의 링크 미정리 삭제는 재발 원인 — 별도 검토.
- 앱은 종료 상태로 두었다(재기동은 사용자).
- 코드 수정(ba0dd1a3, PR 미생성)은 아직 main 미병합.

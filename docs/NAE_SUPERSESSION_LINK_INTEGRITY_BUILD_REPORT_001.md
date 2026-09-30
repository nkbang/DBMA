# NAE-SUPERSESSION-LINK-INTEGRITY-001 Build Report

STATUS: GREEN (Phase 0~3 완료) · 2026-09-29

## Phase 0 — 원인 (읽기 전용 조사)
- **0-a 삭제(정황):** `scripts/rebuild_tsu_manual.py`(feat/peb-v0.1, 미병합)가 같은 source_file의 non-winner를
  `del reg['documents'][id]`로 삭제하며 링크는 정리하지 않는다. 09-21 백업으로 재현한 예상 loser 10건 =
  현재 registry와 일치(3건 부재 + 7건 재생성). 실행 로그는 없음 → 정황 증거. Vol7/8/9/14 4건 제거 경로는 **원인 미확정**.
- **0-b 재생성(직접 증거):** 09-24 19:25 재처리. 입력 `data/제련완성본/Spurgeon_MTP_VolN.txt`가 원본(`.bak`와 cmp 동일,
  mtime 09-15)으로 롤백된 상태 → 원본 내용 해시 = 원래 ID. PROCESS 경로 + `_prior_version` → `mark_superseded(B, A)`.
- **0-c 해시:** `file_hash`/`document_id`는 RAW 바이트가 아니라 처리된 최종 텍스트(`processing.py:651-652`) 기준.
- **통합 메커니즘:** 삭제로 dangling이 된 `B.supersedes=A`가 같은 ID A의 재생성으로 유효해지며 2-순환(Vol10~13);
  재생성되지 않은 중간 버전은 dangling 유지(Vol51~53).

## Phase 1 — `core/identity_registry.py::mark_superseded`
Invariant: (1) old==new no-op (2) new.superseded_by=None (3) old.supersedes≠new — new가 조상이면 `X.supersedes==new`
링크 제거 → 단일 체인 (4) old/new의 dangling 링크 → None. 결정 규칙: A 재현행 시 이전 "B가 A를 대체" 엣지는 폐기
(A→C→B 최신→과거 단일 체인). 알려진 한계: new에 이전 버전 P가 따로 있고 `new.supersedes`가 덮어써지면
`P.superseded_by=new`는 유지(현행본 1개는 보존, 과거 이력은 트리 형태로 남음).

## Phase 2/3 — 테스트
`tests/test_supersession_link_integrity.py` 8건(A→B, A 재현행, A→B→C 후 A 재현행, Vol10형, dangling ×2, no-op, 누락 ID).
회귀 5개 파일 + 신규 = 50 passed.

## 범위 외 / Next
- `data/제련완성본/registry/documents.json` **미수정**(읽기만). 기존 7건 순환 + Vol51~53 dangling 3건 정정은
  NAE-SUPERSESSION-REGISTRY-REPAIR-001(백업→dry-run→diff→검증→반영→사후 무결성 테스트)로 분리.
- `rebuild_tsu_manual.py`의 링크 미정리 삭제는 별도 검토 필요.
- 오늘 12:11 production registry에 `fixture_*` 레코드 2건(테스트 픽스처 경로 오염 가능성) — 별도 확인 필요.

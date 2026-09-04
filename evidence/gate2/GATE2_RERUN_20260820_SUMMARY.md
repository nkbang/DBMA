# Gate 2 재검증 — HEAD 722b5c1 (2026-08-20, CUE 직접 실행)

- 배경: Gate 2 closure(`4244055`, 2026-08-18) 이후 87개 커밋(UX-007 나이트시프트
  전체, 홈/랜딩 개편, Stitch 목업 3종)이 검증 없이 쌓여 사용자 승인 하에 재검증.
- 대상: `722b5c1`(재검증 실행 시점 최신 HEAD)

## Phase A (읽기 전용, orchestrator 자동 실행)

`evidence/gate2/20260820-065445/` — **8/8 GREEN**
(00_baseline, 10_packaging_audit, 30_package_integrity[아카이브 1292개 항목],
50_runtime_smoke, 60_ui_pages[9개 페이지 전부 import 성공],
61_citation_ui, 70_production_isolation[TSU/registry/Qdrant mutation 0],
95_evidence_verify)

## Phase B (실제 시스템 변경 — 사용자 승인 후 CUE 직접 실행)

| 단계 | 결과 | 비고 |
|---|---|---|
| 40_clean_install.sh | ✅ PASS | `/tmp/dbma-gate2-run-1787209045` 격리, Homebrew/Ollama(bge-m3+llama3.1:8b)/venv 신규 설치 → Streamlit 정상 기동 확인, 에러 0건 |
| 80_reinstall_upgrade.sh | ✅ PASS | PERSIST_ITEMS 8/8 preserved, content match 8/8 |
| 90_uninstall.sh | 🔴→✅ **버그 발견·수정 후 PASS** | 아래 참고 |

### 🔴 발견된 결함 — `90_uninstall.sh`의 `find /tmp` 심볼릭 링크 미해결

`find /tmp -maxdepth 1 -name "dbma-gate2-run-*" -type d`가 macOS에서 **항상 빈
결과**를 반환함(`/tmp`가 `/private/tmp`로의 심볼릭 링크이고, `-L` 없이는
최상위 인자의 심볼릭 링크를 디렉터리로 하강하지 않는 BSD find 동작 때문).
`ls /tmp`로는 대상이 명백히 보이는데 `find /tmp -maxdepth 1 ...`만 0건 —
실제로 40/80 단계가 남긴 격리 디렉터리 2개가 삭제되지 않고 `/tmp`에 방치됨을
직접 재현·확인.

**수정**: `scripts/gate2/90_uninstall.sh` 두 곳(`find /tmp` → `find -L /tmp`)에
`-L` 플래그 추가. 재실행 결과 2개 디렉터리 정상 탐지·삭제, orphan 0건 확인.

## Protected Paths / Production 영향

`core/retrieval.py`, `pyproject.toml` 무접촉. 이번 재검증 전 구간에서 production
TSU dataset/registry/Qdrant point count 변동 없음(70_production_isolation 확인).

## 결론

**GATE2_STATUS(HEAD 722b5c1) = GREEN** (Phase A 8/8 + Phase B 3/3, 1건 버그
발견·즉시 수정 후 재검증). Gate 2 이후 쌓인 87개 커밋이 배포 가능 상태임을
확인. 새 release 태그 컷(Phase 17 재실행)은 별도 승인 필요.

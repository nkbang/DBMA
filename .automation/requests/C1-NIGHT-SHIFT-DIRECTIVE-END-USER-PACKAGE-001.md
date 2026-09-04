# Night Shift Directive — End-User Package Gate 2 완료 + Release

| | |
|---|---|
| Issued by | CUE |
| Issued | 2026-08-18 |
| Executor | C1 (무인) |
| Verifier | CUE (매 Phase 게이트) |
| Approver (final) | Rev. Bang — **최종 Release 단계만 별도 승인 필요, 그 외는 사전 승인됨** |
| Scope 승인 근거 | Rev. Bang, 2026-08-18 — "더 넓게 — End-User Package 전체 마무리" |

---

## 0. 오늘 세션 핵심 교훈 (반드시 숙지)

1. **evidence는 반드시 재현 가능해야 한다** — 오늘 두 번 "evidence가 그럴듯하지만
   실제로는 다른 걸 검증"하는 버그를 CUE가 발견했다(`61_citation_ui.py` 카운트
   오류, `30_package_integrity.py`/`ISOLATED_INSTALL_DIR` prefix/경로 버그). 새 검증
   스크립트를 만들면 **반드시 의도적으로 실패하는 케이스를 하나 만들어 그 실패를
   실제로 잡아내는지 확인**한 뒤 완료 보고할 것(sanity control).
2. **테스트 대상이 실제로 바뀌는 것인지 항상 재확인하라** — `install_nae_beta.command`가
   고정 태그(`BETA_LATEST_TAG.txt`)를 다운로드하는 바람에, 로컬 수정을 세 번이나
   "실제 실행"했다고 착각한 채 옛날 코드를 테스트했다. 로컬/HEAD를 테스트할 땐
   `git archive HEAD`로 격리 스냅샷을 떠서 확인할 것 — 원격 다운로드에 의존하지 말 것.
3. **격리는 이중으로 검증하라** — `HOME=` 오버라이드만으로는 부족했다(`PROJECT_ROOT`가
   스크립트 자기 자신의 경로 기준이라 라이브 저장소에서 직접 실행하면 무용지물).
   새 스크립트가 "격리됐다"고 주장하면, 그 스크립트가 참조하는 모든 경로 변수를
   하나하나 추적해서 라이브 저장소/라이브 `~/내서재_베타`를 가리키는 경로가 단
   하나도 없는지 확인할 것.

## 1. 범위(승인됨)

**포함**: Gate 2 Phase 4(Build Validation) ~ Phase 17(End-User Release, 새 릴리스 태그
컷 + `BETA_LATEST_TAG.txt` 갱신까지) 전체.

**Protected Paths(오늘 확정, 무인 작업 중 예외 없이 적용)**:
```
core/retrieval.py
pyproject.toml
ADR-001, ADR-003, ADR-013, ADR-024 (docs/architecture/*)
~/내서재_베타                       (라이브 사용자 설치 경로 — 격리 테스트가 아닌 한 참조 금지)
Production TSU (output/bench/tsu_dataset.jsonl 등)
Production Qdrant (nae_qdrant 데이터, dbma_qdrant는애초 미사용)
```

## 2. 자동 중단 기준(승인됨)

**동일 결함에 대해 3회 수정 시도 후에도 재현되면 즉시 중단**, evidence와 함께
CUE에게 보고하고 다음 지시를 기다린다(추가 재시도 금지). 오늘 hunspell 건은
2회 실패 후 3번째에 CUE가 직접 근본 원인(LIBRARY_PATH)을 찾아 해결한 사례 —
이 패턴(반복 실패 시 CUE가 직접 개입)을 기준으로 삼는다.

그 외 즉시 중단 조건(기존 Task Order들의 Hard Stop 누적):
- Protected Paths 수정이 필요해 보이는 경우
- Production mutation이 발생했거나 발생할 것으로 판단되는 경우
- `~/내서재_베타`(라이브 경로)를 참조/실행하는 코드가 생기는 경우
- 새로운 Architecture 결정이나 ADR이 필요하다고 판단되는 경우

## 3. Phase별 진행 (C1이 순서대로, 각 Phase 완료마다 evidence 남기고 다음으로)

- **Phase 4 (Build Validation)**: `scripts/build_mac_package.sh` 실행 → `.app`/`.dmg`
  생성 확인 → artifact 내용물 검사(export-ignore 적용 확인) → checksum 기록 →
  clean checkout에서 재현 가능한지 확인. evidence: `evidence/gate2/phase4-build/`.
- **Phase 5~6 (Clean Install + Runtime)**: `scripts/gate2/40_clean_install.sh`를
  **실제(non-dry-run)로** 격리 환경에서 실행(오늘 CUE가 검증한 방식 그대로 재사용).
  hunspell 통과, 9개 페이지 로드, citation 표시까지 확인.
- **Phase 7 (Production Isolation)**: `scripts/gate2/70_production_isolation.py` 실제
  재실행, BEFORE=AFTER 확인.
- **Phase 8 (Reinstall/Upgrade)**: `scripts/gate2/80_reinstall_upgrade.sh` **실제
  실행**(오늘 CUE가 코드 리뷰만 하고 실행은 안 한 부분 — 오늘 밤 처음 실제 실행,
  PERSIST_ITEMS 8개 항목 전부 보존되는지 실측).
- **Phase 9 (Uninstall/Cleanup)**: `scripts/gate2/90_uninstall.sh` 실제 실행, orphan
  파일 없는지 확인.
- **Phase 10 (Evidence)**: 전부 `evidence/gate2/night-shift-<날짜>/`에 정리, `SUMMARY.md`
  자동 생성.

각 Phase 완료 시 CUE가 게이트 판정(GREEN/HOLD/RED) 후 다음 Phase 진행 승인.
**Phase 11~14(독립 감사·재감사)는 CUE가 각 Phase 완료 직후 바로 수행**하므로 별도
단계로 나누지 않는다 — Phase별 실시간 감사.

## 4. Phase 15~17 (Gate 2 Closure → Commit/Push → Release) — 마지막 게이트

Phase 4~10이 전부 GREEN이면 CUE가 최종 감사 후 commit/push는 **기존 정책대로
자동 진행**(CLAUDE.md Git 자동화 범위).

**단, 다음 두 가지는 이 Directive의 사전 승인 범위에서 명시적으로 제외한다 — 반드시
Rev. Bang에게 실행 직전 보고하고 진행**:
1. 새 release 태그를 실제로 컷하는 것(이미 존재하는 `beta-v1.3.0-rc4`를 대체할
   최종 태그) — 태그 자체는 Gate 2 GREEN 확정 후 만들어도 되나, 어떤 버전 번호로
   할지 최종 확인
2. **`BETA_LATEST_TAG.txt` 갱신** — 이 파일이 실제 라이브 베타 테스터의 자동
   업데이트를 트리거한다. Gate 2가 아무리 GREEN이어도, 실제 사람에게 업데이트
   알림이 뜨는 이 마지막 스위치만은 CUE가 임의로 넘기지 않고 보고 후 대기한다.

## 5. 아침에 확인할 것 (Rev. Bang용 요약 위치)

`evidence/gate2/night-shift-<날짜>/SUMMARY.md` — 이 파일 하나로 GREEN/HOLD/RED와
남은 작업을 한눈에 파악 가능하도록 CUE가 마지막에 정리한다.

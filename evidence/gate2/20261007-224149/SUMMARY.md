# Gate 2 Evidence Manifest v2 — 20261007-224149

- 작성: NAE Forensic Auditor (independent verification)
- 상태: **PARTIAL_PASS** (read-only phases passed; packaging/install/reinstall/uninstall execution not evaluated)
- 기준 브랜치: `fix/merge-production-path-safety`
- HEAD: `6f311d1f` (`6f311d1fd250fcc483b89b5b1ed0f51f18ee0994`)
- baseline snapshot HEAD: `a208a8e4` (`a208a8e4d3c879fba495f77578679301ba0b8698`)
- manifest schema_version: 2
- manifest payload count: 11
- prior_summary_sha256: `d89fe4bbdb30f98ead6d539e5c89a2b2f2fb948898cdb7826c17d373dedc305f`

---

## 최종 결과표

| Phase | 내용 | 상태 | 핵심 발견/조치 |
|---|---|---|---|
| 0 | Pre-execution Snapshot | PASS | detached HEAD `a208a8e4`, clean worktree, protected file hash 일치 |
| 10 | Packaging Audit | PASS | pyproject.toml에 `[project]` 섹션 없음, `.gitattributes` 패턴 3개 모두 존재 |
| 30 | Package Integrity | PASS | `git archive HEAD` 1,737개 멤버, 필수 파일 5개 모두 포함, exclusion 정상 |
| 50 | Runtime Smoke | PASS | venv `/Users/David/envs/dbma311` 존재, `dbma_ui.py` 읽기 가능 (16줄) |
| 60 | UI Pages | PASS | expected 9개 페이지 모두 존재, disk에 12개 파일 (`onboarding`, `sermon_library`, `sermon_research` 추가) |
| 70 | Production Isolation | PASS | TSU dataset/manifest, tsu_id_state, documents_registry 전부 mutation 0 |
| 80 | Reinstall/Upgrade | N/A | `80_reinstall_upgrade.sh`, `install_nae_beta.command` 현재 브랜치에 없음 |
| 90 | Uninstall/Cleanup | N/A | `90_uninstall.sh` 현재 브랜치에 없음 |

---

## 독립 검증 결과 상세

### Phase 0: Pre-execution Snapshot (기존 증거 재검증)

- **Worktree**: `/tmp/gate2-pre-snapshot` (detached HEAD `a208a8e4`, clean)
- **Protected File Hash**:
  - `core/retrieval.py`: `6b7bce25...` 일치
  - `pyproject.toml`: `00c55274...` 일치
- **Qdrant**: pre-execution snapshot 당시 `nae_tsu_v1` green (3,891 points)
  - 현재 시점: 연결 불가 (HTTP exit code 7 = curl connect failed)

### Phase 10: Packaging Audit (독립 재현)

```
pyproject_no_project_section: PASS — [project] 섹션 없음
dbma_ui_exists: PASS — /Users/David/DBMA/dbma_ui.py 존재
core_config_exists: PASS — /Users/David/DBMA/core/config.py 존재
gitattributes_patterns: PASS — NAE/, .automation/, test_seal_* 3개 모두 존재
```

### Phase 30: Package Integrity (독립 재현)

```
git_archive HEAD members: 1,737개 (이전 Gate 2: 1,292개 — 브랜치 차이)
excluded NAE/: 0개
excluded .automation/: 0개
excluded test_seal_*: 0개
required files:
  - README.md
  - INSTALL.md
  - dbma_ui.py
  - core/retrieval.py
  - requirements.txt
```

### Phase 50: Runtime Smoke (독립 재현)

```
env_exists: PASS — /Users/David/envs/dbma311
ui_file: PASS — /Users/David/DBMA/dbma_ui.py
ui_file_readable: PASS — 16 lines
```

### Phase 60: UI Pages (독립 재현)

**Expected 9개 페이지 — 모두 PASS:**

| 페이지 | 파일 | 상태 |
|---|---|---|
| ui.pages.dashboard | ui/pages/dashboard.py | PASS |
| ui.pages.library | ui/pages/library.py | PASS |
| ui.pages.processing | ui/pages/processing.py | PASS |
| ui.pages.research | ui/pages/research.py | PASS |
| ui.pages.monitor | ui/pages/monitor.py | PASS |
| ui.pages.chat | ui/pages/chat.py | PASS |
| ui.pages.sermon_draft | ui/pages/sermon_draft.py | PASS |
| ui.pages.sermon_review | ui/pages/sermon_review.py | PASS |
| ui.pages.help | ui/pages/help.py | PASS |

**Disk 파일 (12개):** `chat.py`, `dashboard.py`, `help.py`, `library.py`, `monitor.py`, `onboarding.py`, `processing.py`, `research.py`, `sermon_draft.py`, `sermon_library.py`, `sermon_research.py`, `sermon_review.py`

**주목:** `ui/pages/onboarding.py`가 disk에 존재하지만 expected_pages에서 제외됨 (이전 Gate 2와 동일한 정책). 새로운 파일 `sermon_library.py`, `sermon_research.py` 추가 확인.

### Phase 70: Production Isolation (독립 재현)

**Mutation 0 확인 — 모든 production 파일 hash 일치:**

| Artifact | SHA-256 | Size |
|---|---|---|
| `output/bench/tsu_dataset.jsonl` | `bd246f22...` | 217,134,000 bytes |
| `output/bench/tsu_manifest.json` | `960b627a...` | 503 bytes |
| `NAE/corpus/tsu/tsu_id_state.json` | `413bba79...` | 18 bytes |
| `data/제련완성본/registry/documents.json` | `1ef76cd0...` | 126,512 bytes |

**Qdrant**: 현재 연결 불가 (HTTP exit code 7). Pre-execution snapshot에서는 green (3,891 points)이었으나 현재 시점에는 서비스 중지 또는 포트 변경으로 판단.

### Phase 80/90: Reinstall/Uninstall (dry-run 불가)

현재 브랜치 `fix/merge-production-path-safety`는 merge/recovery 작업용 브랜치로,
end-user packaging 스크립트(`40_clean_install.sh`, `80_reinstall_upgrade.sh`,
`90_uninstall.sh`, `install_nae_beta.command`)가 포함되어 있지 않습니다.

이 스크립트들은 이전 Gate 2 run (20260820)의 다른 브랜치에서 존재했으며,
`git log --all -- install_nae_beta.command`로 5개 커밋 이력 확인 가능:
- `7266ed2e` feat(release): ship baseline corpus as GitHub Release asset
- `8c9ffd0d` fix(release): Gate 2 Phase 1 발견 3건 반영
- `598fbdc6` docs(end-user-package): Gate1 G1-G3/DoD#7 완료
- `98798446` feat: fully terminal-free install/update flow
- `c50ddecc` feat: check-approve-download update flow

---

## manifest v2 구조

- **schema_version**: 2
- **payload count**: 11 (files 배열)
- **canonicalization**: UTF-8, key lexicographic ascending, preserve array order, separators `(",",":")`, ensure_ascii false, trailing newline false
- **manifest_sha256**: manifest_sha256 키를 제외한 전체 object의 canonical JSON SHA-256
- **legacy_manifest_record**: v1 manifest SHA-256 `9891278a...` 이력 보존 (Gate 판정에 사용 안 함)

### Payload 목록 (11개)

| # | 파일 | bytes | sha256 (short) |
|---|---|---:|---|
| 1 | `00_pre_execution_snapshot.json` | 3,836 | `e312aaa2...` |
| 2 | `00_pre_execution_snapshot.log` | 2,734 | `c373cb37...` |
| 3 | `00_provenance.json` | 2,501 | `12cc40a3...` |
| 4 | `10_packaging_audit_independent.json` | 637 | `8f82d7fd...` |
| 5 | `30_package_integrity_independent.json` | 867 | `3f417b01...` |
| 6 | `50_runtime_smoke_independent.json` | 384 | `16de5d98...` |
| 7 | `60_ui_pages_independent.json` | 2,097 | `bdd4e4f6...` |
| 8 | `70_production_isolation_independent.json` | 1,930 | `3d9c46c1...` |
| 9 | `80_reinstall_upgrade_dryrun.json` | 727 | `d0cda4f5...` |
| 10 | `90_uninstall_dryrun.json` | 576 | `33317a2e...` |
| 11 | `SUMMARY.md` | (자기 자신) | 해시는 manifest.json 참조(자기 해시 자기 포함 불가) |

### 제외 파일 (payload 아님)

- `manifest.json` — manifest 자체는 payload가 아님
- `00_manifest_verify.json` — 외부 사후 검증 기록

---

## 보호 파일 / Production 무결성

Gate 2 전 구간에서 **mutation 0** 확인:

| 보호 파일 | SHA-256 | 상태 |
|---|---|---|
| `core/retrieval.py` | `6b7bce25...` | 무변경 |
| `pyproject.toml` | `00c55274...` | 무변경 |
| `output/bench/tsu_dataset.jsonl` | `bd246f22...` | 무변경 |
| `output/bench/tsu_manifest.json` | `960b627a...` | 무변경 |
| `NAE/corpus/tsu/tsu_id_state.json` | `413bba79...` | 무변경 |
| `data/제련완성본/registry/documents.json` | `1ef76cd0...` | 무변경 |

---

## 변경된 파일 (이 run)

| 파일 | 설명 |
|---|---|
| `manifest.json` | Gate 2 manifest v2 (schema_version 2, 11 payloads, canonical hash) |
| `00_pre_execution_snapshot.log` | snapshot JSON에서 재구성한 기록 (원문 로그 아님) |
| `00_provenance.json` | worktree 상태, 시간대 관측, 재현 절차 provenance |
| `00_manifest_verify.json` | 외부 사후 검증 기록 (11개 payload 전수 검증 PASS) |
| `10_packaging_audit_independent.json` | Phase 10 독립 재현 증거 |
| `30_package_integrity_independent.json` | Phase 30 독립 재현 증거 |
| `50_runtime_smoke_independent.json` | Phase 50 독립 재현 증거 |
| `60_ui_pages_independent.json` | Phase 60 독립 재현 증거 |
| `70_production_isolation_independent.json` | Phase 70 독립 재현 증거 |
| `80_reinstall_upgrade_dryrun.json` | Phase 80 dry-run 불가 기록 |
| `90_uninstall_dryrun.json` | Phase 90 dry-run 불가 기록 |
| `SUMMARY.md` | 이 문서 |

---

## Gate 2 판정

**PARTIAL_PASS** — read-only phases (0/10/30/50/60/70) 모두 PASS; packaging/install/reinstall/uninstall execution은 현재 브랜치에 관련 스크립트가 없어 평가 불가.

Phase 80/90는 현재 브랜치에 관련 스크립트가 없어 N/A로 처리됨.
end-user packaging 검증은 packaging branch 또는 dedicated worktree에서 재실행 필요.

---

## Next Steps

1. **Packaging branch에서 Phase 4/5/8/9 재실행**: `install_nae_beta.command` 및 관련 스크립트가 있는 브랜치에서 clean install / reinstall / uninstall 검증
2. **Qdrant 상태 확인**: `nae_tsu_v1` collection이 현재 실행 중인지 확인 (pre-execution snapshot에서는 3,891 points green)
3. **Merge 작업 완료 후 Gate 2 재실행**: `fix/merge-production-path-safety` 브랜치가 main에 merge된 후 전체 Gate 2 재검증 권장

---

## non-dry-run 실행 여부

**미실행** — 이 run은 read-only evidence collection에 한정됨.
actual install / reinstall / uninstall dry-run은 별도 실행 필요.

# NAE Metadata Schema 2.0.0 Migration Implementation Report 001

**Project:** NAE-METADATA-SCHEMA-2.0.0-MIGRATION-IMPLEMENTATION-001
**작성일:** 2026-08-08
**성격:** Migration Script 구현 + Test + Dry-run(READ-ONLY). **Production Migration 미실행.**
**Authority:** `docs/NAE_METADATA_SCHEMA_2_MIGRATION_PACKAGE_001.md`, `docs/NAE_METADATA_SCHEMA_2_MIGRATION_FINAL_REVIEW_001.md`(C1, APPROVED WITH CONDITIONS)
**Git Commit/Push:** 미수행.

---

## Phase 1 — Version Blocker 해제

C1 Final Review §11 C1-COND-001/002를 그대로 구현(임의 확대/축소 없음):

- `docs/NAE_METADATA_SCHEMA_2_MIGRATION_PACKAGE_001.md`의 `metadata_schema_version`
  값을 `"1.1.0-draft"` → `"1.1.0"`로 확정(C1 R-A1 권장안 1 채택)
- `docs/NAE_METADATA_GOVERNANCE_v1.md`에 §2.3(계층 C Migration Version) 신설(C1-COND-002)
- 저장소 전체에서 `"1.1.0-draft"` 재검색 — 남은 참조는 C1 자신의 리뷰
  문서 2건(`NAE_METADATA_SCHEMA_2_MIGRATION_FINAL_REVIEW_001.md`,
  `NAE_METADATA_SCHEMA_2_MIGRATION_REVIEW_001.md`)뿐이며, 이는 C1이
  작성한 historical review record이므로 수정하지 않았다(§Phase1 "최소
  범위" 원칙 — 내가 쓴 Package 문서만 수정)
- 기존 Metadata/TSU 필드/Production 데이터 무변경

---

## Phase 2 — Migration Script 구현

`NAE/pipeline/tsu/metadata_migration.py`(신규):

```
Provenance Chain: TSU.identifier -> Crosswalk -> Registry -> Edition -> Work
resolve_metadata()   — 5단계 조회, 하나라도 실패하면 MigrationSkip(추측 없음)
compute_tsu_access()  — Governance §6 조합표 코드화(조회 아닌 결정론적 계산)
migrate_record()      — additive만, 원본 dict 불변, verify_invariant() 통과 필수
migrate_file()         — dry_run/force/backup_root 지원, 원자적 쓰기(os.replace)
```

- Crosswalk 읽기: 기존 `scripts/crosswalk/storage/yaml_repository.py::YamlCrosswalkRepository` 재사용(신규 파서 작성 안 함)
- Registry/Edition/Work 읽기: `yaml.safe_load()`(읽기 전용이므로 ruamel round-trip 불필요 — 쓰기 규칙은 해당 없음)
- `category`/`citation_policy`: `null` + `AUTHORITATIVE_SOURCE_MISSING` 고정(Migration Package §2 그대로)
- `review_status`/`claim`/`doctrine`/`scriptures`/`citations` 등 20개 기존 필드: `IMMUTABLE_FIELDS`로 명시, `verify_invariant()`가 매 레코드마다 assert

**builder.py/review_gate.py/core/retrieval.py/core/tsu_builder.py — 전부 무수정.**

---

## Phase 3 — Test

`tests/test_tsu_metadata_migration.py`(신규, tmp_path/in-memory 전용, Production 파일 무접근):

| 요구 항목 | 테스트 클래스 |
|---|---|
| Provenance chain(성공) | `TestProvenanceChainSuccess`(5) |
| Provenance chain(실패) | `TestProvenanceChainFailure`(6) |
| Missing authoritative metadata | `TestMissingAuthoritativeMetadata`(3) |
| Existing-field immutability | `TestExistingFieldImmutability`(6) |
| Idempotency | `TestIdempotency`(2) |
| Force behavior | `TestForceBehavior`(2) |
| Rollback | `TestRollback`(2) |
| Atomic write | `TestAtomicWrite`(3) |
| Malformed record | `TestMalformedRecord`(4) |
| Duplicate/재실행 | `TestBatchAndDuplicateScenarios`(2) |
| tsu_access 계산 | `TestTsuAccessComputation`(5) |
| YAML 소스 로딩 | `TestLoadMigrationSources`(2) |
| Regression | `TestRegression`(2) |

```
$ pytest tests/test_tsu_metadata_migration.py -q
44 passed(요구 20건 이상 초과 충족)
```

---

## Phase 4 — Dry-run(Production 4,117건, READ-ONLY)

```
$ python3 -c "... mm.migrate_file(tsu_path, sources, dry_run=True) ..."

=== Dagg_Church_Order ===
total: 3377 | migrated(eligible): 3377 | skipped_already_migrated: 0
skipped_no_provenance: 0 | errors: []

=== Hiscox_Standard_Manual ===
total: 740 | migrated(eligible): 740 | skipped_already_migrated: 0
skipped_no_provenance: 0 | errors: []

=== TOTAL ===
total: 4117
eligible(예상 migrated): 4117
skipped(already_migrated): 0
skipped(no_provenance/missing metadata): 0
provenance failures: 0
errors: 0

predicted_schema_version: "1.1.0"
predicted new keys per record: 17개
  (access_control, author_id, category, category_status, citation_policy,
   citation_policy_status, copyright_status, edition_id,
   metadata_provenance, metadata_schema_version, publication_year,
   source_id, source_type, tsu_access, usage_permission, volume_id, work_id)
predicted total field additions: 4,117 × 17 = 69,989개
predicted backup size: 3,581,549 bytes(원본 tsu.json 2개 합계, 그대로 백업될 양)
```

**Byte-level 무변경 확인**: dry-run 실행 전/후 `NAE/corpus/tsu/Dagg_Church_Order/tsu.json`,
`.../Hiscox_Standard_Manual/tsu.json`을 `read_bytes()`로 비교 — 완전히
동일(`assert before_bytes == after_bytes` 통과).

---

## Phase 5 — Safety / Architecture Audit

```
$ index_all(dry_run=True)
{'processed': 3, 'indexed': 0, ...}   -> Review Gate 계속 BLOCK, 4,117건 전부 review_status=generated 그대로

$ git diff --stat core/retrieval.py core/tsu_builder.py NAE/pipeline/tsu/review_gate.py scripts/crosswalk/
(core/retrieval.py, core/tsu_builder.py, review_gate.py, scripts/crosswalk/ 전부 0줄 변경)

$ git status --short resources/theological_sources/ NAE/corpus/tsu/ NAE/metadata/crosswalk/
(전부 ?? 상태 유지 — M(수정) 없음, dry-run이 아무 파일도 쓰지 않았음을 확인)
```

- Embedding/Qdrant 실행: 없음(dry_run 경로는 embed_client/qdrant_store 호출 분기 자체에 도달하지 않음)
- Production Migration 실행: 없음
- unverified/generated TSU의 Retrieval/Embedding 노출: 없음(Review Gate 확인)

**PASS.**

---

## Phase 6 — Regression / Drift

```
$ pytest tests/test_tsu_metadata_migration.py tests/test_nae_tsu_builder.py tests/test_nae_tsu_claim.py \
    tests/test_crosswalk*.py tests/test_manual_crosswalk_pilot.py tests/test_tsu_pipeline_wiring.py \
    tests/test_tsu_review_gate.py tests/test_tsu_review_promotion.py tests/test_indexer_review_gate_wiring.py \
    tests/test_nae_index_indexer.py -q
322 passed

$ pytest -q --ignore=output (전체 스위트)
1924 passed, 2 failed
```

기존 baseline failure(신규 아님, 이 대화 전체에서 반복 확인된 무관 항목):
```
tests/test_nae_embed.py::test_embed_text_caches_result
tests/test_nae_embed.py::test_embed_text_returns_none_on_failure
```

신규 regression: **0건**(직전 확인된 1880 passed → 이번 44개 신규 테스트
추가로 1924 passed, 감소 없음).

### Validator

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 완료 보고

```
STATUS: PASS

BLOCKER:
0 (C1-COND-001/002 해제 완료 — metadata_schema_version "1.1.0-draft" -> "1.1.0" 확정, Governance §2.3 신설)

WARNING:
2(이월, C1 Final Review §9 R2/R3 그대로 — 이번 작업 범위 아님, 해소되지 않음)
1. category/citation_policy — AUTHORITATIVE_SOURCE_MISSING 유지(사람 확인 후 별도 patch, 이번에도 값 생성 안 함)
2. Qdrant re-indexing 필요(Migration 실행 후 별도 Task로 분리 권장, C1 R4)

VERSION:
변경 전: "1.1.0-draft"(Migration Package 문서 내 표기, Governance 미승인 상태)
변경 후: "1.1.0"(C1 Final Review R-A1 권장안 1 채택, Governance §2.3에 계층 C 전용 버전으로 공식 기록)

TEST:
신규 44개, 44 passed(요구 20건 이상 초과 충족)

DRY-RUN:
total: 4117
eligible: 4117
skipped(already_migrated): 0
skipped(no_provenance): 0
missing metadata(provenance failure): 0
predicted field additions: 4,117 x 17 = 69,989개
predicted schema version: "1.1.0"
predicted file changes: 2개 파일(Dagg tsu.json, Hiscox tsu.json), byte 무변경 실측 확인(dry-run)
predicted backup size: 3,581,549 bytes
errors: 0

REGRESSION:
passed: 1924 / failed: 2
기존 baseline failure: tests/test_nae_embed.py 2건(AttributeError, 이 세션 전체에서 반복 확인된 무관 항목, 불변)
신규 regression: 0건

DRIFT:
0 (source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 baseline 일치)

ARCHITECTURE AUDIT:
PASS (core/retrieval.py, core/tsu_builder.py, review_gate.py, Crosswalk/Registry/Manifest 전부 무수정, Review Gate 무력화 없음, Embedding/Qdrant 미실행)

PRODUCTION MIGRATION:
NOT EXECUTED

GIT:
NOT PERFORMED
```

## FILES CREATED:
```
NAE/pipeline/tsu/metadata_migration.py
tests/test_tsu_metadata_migration.py
docs/NAE_METADATA_SCHEMA_2_MIGRATION_IMPLEMENTATION_REPORT_001.md
```

## FILES MODIFIED:
```
docs/NAE_METADATA_SCHEMA_2_MIGRATION_PACKAGE_001.md (metadata_schema_version 확정, C1 근거 반영)
docs/NAE_METADATA_GOVERNANCE_v1.md (§2.3 계층 C Migration Version 신설, C1-COND-002 해제)
```

## 다음 단계:
```
Migration 실제 실행은 이번 작업 범위 밖 — 별도 승인 및 새 작업 명령 필요.
승인 시 migrate_file(dry_run=False, backup_root=...)을 Dagg -> Hiscox 순으로
실행(C1 R-A4 Monograph 우선 원칙), Phase 6 검증 Gate 7종을 실행 직후 재확인.
```

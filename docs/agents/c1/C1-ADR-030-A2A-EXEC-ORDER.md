# C1 — ADR-030 v2.1 Phase 1-A / A-2a EXEC ORDER

> **작성**: CUE · **승인 대기**: 사용자(HQ) · **근거**: `CUE-ADR-030-A2A-PREP.md` (B1~B5 승인·처리 완료)
> **선행 완료**: commit `fcaa380` on `dev/dbma-engine` (v2.1 reimport + Phase 1-A 산출물 tracked)

---

## 0. 작업 환경 (고정)

| 항목 | 값 |
|---|---|
| 작업 디렉터리 | `/Users/David/DBMA` (worktree 아님, 메인 체크아웃) |
| 브랜치 / baseline HEAD | `dev/dbma-engine` @ **`fcaa380`** |
| venv | `~/envs/dbma311` (`source ~/envs/dbma311/bin/activate`) |
| 검증 diff 기준 | **`git diff -- <allowlist>` 만 사용.** bare `git diff` / `git status` 전체로 판단 금지 |

**작업 트리에 무관한 미커밋 변경이 이미 존재한다** (`test_seal_*` 삭제 9건, `NAE/smith_activation.py`,
`ui/pages/chat.py`, `docs/STATE.md`, M1/M2/M3/`modern` schema 편집). **이것들을 stage 하거나 revert 하지 마라.**
네 작업 산출물은 아래 §6 allowlist 경로에만 존재해야 한다.

---

## 1. PRIMARY OBJECTIVE

A-2a = **metadata backfill 이전의 구조 / 검증 / cleanup**. 이번 작업은 다음 4개만 수행한다.

1. `modern/source_manifest.schema.yaml` 의 ADR-030 추가분 **hunk 단위 revert** (§3)
2. `scripts/m2_source_registry_validator.py` 를 **M2 YAML 직검사** 방식으로 재작성 (§4)
3. `tests/test_m2_source_registry_governance.py` **test delta** 적용 (§5)
4. `docs/architecture/NAE-Manifest-Authority-SSOT.md` **전문 교체** + 참조 문서 1개 `git add` (§6-B)

그 외 아무것도 하지 않는다. 재조사 금지. 값 추측 금지.

---

## 2. HARD STOP — 금지 사항

- **M2 (`NAE/pipeline/registration/state/source_manifest.yaml`) 를 수정하지 마라.** A-2a 에서 M2 변경 = **0 byte**.
  - 14개 레코드에 `authority_class` / `content_genre` / `theological_category` / `tradition` / `raw_path` /
    `checksum_target` 를 **추가하지 마라.** 이 6필드 backfill 은 A-2b (별도 명령).
  - M2 상단 `# ROLE:` 주석을 **건드리지 마라** (유지). 직전 명령서의 "ROLE 주석 제거" 지시는 **폐기됨**
    (ADR-030 v2.1 §8.2 가 이 주석을 요구, `test_int_07` 이 검사).
- **M1 (`NAE/authority/source_manifest.yaml`) 을 수정하지 마라.** `# DERIVED` 주석 포함 현상 유지.
- **M3 (`NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv`) 를 건드리지 마라.** 직전 명령서의 "M3 CSV consumer 조사"
  지시는 **폐기됨** — CUE 가 종결: repo 전체에 CSV 파싱 consumer 0건, `# ROLE:` 줄은 내구적, `test_int_08` 이
  존재를 요구. **조사도 변경도 하지 않는다.**
- `NAE/pipeline/registration/manifest_writer.py` / `pipeline.py` / registration 아키텍처 변경 금지.
- **새 schema 파일 생성 금지.**
- `NAE/corpus/governance/` 재생성 금지 (이미 부재, 유지).
- Order B 선행 금지. ADR-030 v2.1 본문 수정 금지.

---

## 3. TASK 1 — modern schema revert (정확한 hunk)

**대상**: `resources/theological_sources/modern/source_manifest.schema.yaml`

착수 시 `git diff -- resources/theological_sources/modern/source_manifest.schema.yaml` 는 **4개 hunk** 를 보여준다.
아래 H1·H2·H3 의 **추가(`+`)된 줄만** 작업 트리 파일에서 삭제한다. H4 는 **그대로 둔다.**

| hunk | 위치(대략) | 내용 | 조치 |
|---|---|---|---|
| **H1** | `version_history:` 아래 | `- version: "2.1.1"` + `date:` + `change:` 3줄 | **삭제** |
| **H2** | `fields:` 섹션 끝, `history_source_ids` 정의 다음 | `# ── ADR-030 §5 신규 필드 (6개) ──…` 주석부터 `authority_class:` 정의 블록 끝까지 (≈66줄: `content_genre` / `theological_category` / `tradition` / `raw_path` / `checksum_target` / `authority_class` + 주석 헤더 + 공백줄) | **삭제** |
| **H3** | `example: \|` 블록 끝 | `# ADR-030 §5 신규 필드 (example용)` + `authority_class:` … `checksum_target: null` 7줄 | **삭제** |
| **H4** | `language:` 필드 | `description: 원문 언어(예: en, ko, grc, heb).` → `description: "원문 언어(예: en, ko, grc, heb)."` (따옴표) | **유지 — 절대 revert 금지.** YAML ScannerError 수정분, CUE 확인됨 |

**입증**:
```bash
git diff -- resources/theological_sources/modern/source_manifest.schema.yaml   # → H4 한 줄만 남아야 함
python -c "import yaml; yaml.safe_load(open('resources/theological_sources/modern/source_manifest.schema.yaml')); print('YAML OK')"
```
파일 전체 `git checkout` 금지 (H4 가 사라진다). hunk 단위로만.

---

## 4. TASK 2 — validator 재작성 (M2 YAML 직검사)

**대상**: `scripts/m2_source_registry_validator.py`

### 4.1 원칙 (CUE §2-1 판정)

M2 는 **enforced schema file 이 없다.** 구조는 `NAE/pipeline/registration/pipeline.py:165` 의 dict 리터럴
(10키) 로 정의되고, `manifest_writer.write_entry()` 가 append-only 로 쓴다.
`resources/theological_sources/modern/source_manifest.schema.yaml` 은 **M2 의 governing schema 가 아니다.**

→ validator 의 exit 0 ⟺ **M2 YAML (`NAE/pipeline/registration/state/source_manifest.yaml`) + 파일시스템
baseline** 이 불변식을 만족. **어떤 schema 파일도 PASS 판정에 관여하지 않는다.**

### 4.2 구체 변경

- **`SCHEMA_PATH` 상수 및 그 모든 read 삭제.** (`import yaml` 은 M2 파싱에 필요하므로 유지.)
- 상수 추가:
  ```python
  M2_BASE_KEYS = frozenset([
      "source_id", "title", "author", "author_id", "work_id",
      "edition_id", "year", "license", "archive_source", "raw_checksum",
  ])
  ADR030_ADDITIVE_FIELDS = frozenset([
      "authority_class", "content_genre", "theological_category",
      "tradition", "raw_path", "checksum_target",
  ])
  ```

| 함수 | 현재 | A-2a 재작성 |
|---|---|---|
| `check_paths` (V1) | M1/M2/M3 존재 + `NAE/corpus/governance/` 부재 | **변경 없음** |
| `check_no_corpus_tier` (V2) | `SCHEMA_PATH` 의 `fields` 에 `corpus_tier` 없음 | **M2 로드 → `sources[]` 각 레코드 + top-level dict 에 `corpus_tier` 키 없음.** schema 분기 삭제 |
| `check_no_lifecycle_states` (V3) | (a) `SCHEMA_PATH` 텍스트 스캔 **중복조건 버그** `if f'"{state}"' in schema_text or f'"{state}"' in schema_text:` (b) M2 records (c) `registration_state.json` | **(a) 블록(`if SCHEMA_PATH.exists(): schema_text = … for state in (…): …`) 통째 삭제** → 중복조건 자동 소멸. (b) 유지·확장: 각 레코드의 `status`/`state`/`lifecycle`/`lifecycle_state` 키 값과 모든 string 값에 `"ELIGIBLE"`/`"ACTIVE"` 없음. (c) 유지 |
| `check_authority_class_enum` (V4) | `SCHEMA_PATH` 의 `authority_class.values` 검사 + M2 records | **schema 분기 삭제.** M2 레코드 중 `authority_class` **가 있는 것만** → 값 ∈ `VALID_AUTHORITY_CLASSES` & ∉ `FORBIDDEN_AUTHORITY_VALUES`. **부재 = PASS** (A-2a backfill 0; ADR-030 v2.1 §7.5 WARNING-first) |
| `check_no_required_metadata` (V5) | `SCHEMA_PATH` 에서 `required: true` 스캔 | **optionality 계약 self-check 로 대체**: `{k: "x" for k in M2_BASE_KEYS}` 처럼 6필드가 전혀 없는 합성 레코드에 V4·V6 로직을 돌려 FAIL 0 임을 assert. schema 스캔 삭제 |
| `check_new_field_definitions` (V6) | `SCHEMA_PATH` 의 `fields[*].type` 검사 | **M2 레코드에 해당 필드가 존재할 때만 shape 검사**: `content_genre`/`theological_category` → list 이고 원소 전부 str; `tradition`/`raw_path`/`checksum_target` → str; `authority_class` → str. 부재 → skip. A-2a: 전부 부재 → 전부 skip. schema 분기 삭제 |
| `check_m2_identity` (V7) | 이미 M2 직검사 | **강화**: 기존 검사 유지 + `len(sources) == 14` **명시 assert** + 각 레코드 `set(record) ⊆ M2_BASE_KEYS ∪ ADR030_ADDITIVE_FIELDS` (drift/오타 탐지). A-2a: 각 레코드 = 정확히 10 base 키 |
| `check_baseline` (V8) | canonical dirs == 17, registration `QUALITY_PASSED` == 10, TSU state 존재 | **변경 없음.** (Qdrant 접촉 금지 — 파일만) |

- 모듈 docstring(L1~19)의 "V2 schema 내 corpus_tier", "V5 metadata 필드에 required: true",
  "V6 content_genre[] … 정의 누락" 등 schema 프레이밍을 위 M2 직검사 불변식 설명으로 교체.
  "self-validation 제거" 문장은 유지.
- **V9 를 만들지 마라.**

### 4.3 입증
```bash
python scripts/m2_source_registry_validator.py ; echo "exit=$?"   # exit=0, 전 항목 PASS
grep -n "SCHEMA_PATH\|modern/source_manifest.schema\|source_manifest.schema.yaml" scripts/m2_source_registry_validator.py
# → 출력 0줄 (schema 파일 참조 완전 제거 확인)
```

---

## 5. TASK 3 — test delta

**대상**: `tests/test_m2_source_registry_governance.py` (baseline `fcaa380`: 27 tests — neg 9 / pos 7 / iso 2 / int 9)

`tests/test_nae_corpus_reconcile.py` (15 tests) 는 **변경하지 마라.** 실행해서 GREEN 만 확인.

### 5.1 삭제 (10) — 전부 schema 기반, §3 revert 로 무의미

`test_neg_01_no_corpus_tier_in_schema` · `test_neg_02_no_eligible_state_in_schema` ·
`test_neg_03_no_active_state_in_schema` · `test_neg_06_no_forbidden_authority_values_in_schema` ·
`test_neg_09_no_required_for_eligible_expression` · `test_pos_01_content_genre_defined` ·
`test_pos_02_theological_category_defined` · `test_pos_03_tradition_defined` ·
`test_pos_04_raw_path_defined` · `test_pos_05_checksum_target_defined`

### 5.2 재타깃 (2)

| 기존 | 새 이름 | 새 내용 |
|---|---|---|
| `test_pos_06_authority_class_has_4_values` | `test_pos_06_authority_class_vocab_when_present` | M2 로드 → `authority_class` 가진 레코드만 값 ∈ 4-enum. A-2a 엔 없어 **공허 통과**. 주석: `# A-2b backfill 후 실질 검증` |
| `test_pos_07_all_new_fields_optional` | `test_pos_07_new_fields_optional_no_fail` | 6필드 없는 합성 레코드에 validator per-record 검사 → FAIL 0 |

### 5.3 신규 추가 (3)

- `test_neg_01_no_corpus_tier_in_m2` — M2 `sources[]` 각 레코드에 `corpus_tier` 키 없음.
- `test_m2_records_only_known_keys` — 각 레코드 `set(record) ⊆ {10 base} ∪ {6 ADR-030}`; A-2a: 정확히 10 base.
- `test_validator_has_no_schema_path` — `scripts/m2_source_registry_validator.py` 소스에
  `"SCHEMA_PATH"` / `"source_manifest.schema"` 문자열 부재 (§2-1 회귀 가드).

### 5.4 그대로 유지 (변경 없음)

`test_neg_04` · `test_neg_05` · `test_neg_07` · `test_neg_08` · `test_iso_01` · `test_iso_02` ·
`test_int_01`(validator exit 0) · `test_int_02`(schema YAML 파싱 — revert 후에도 통과) ·
`test_int_03`(M2 14) · `test_int_04`(M1 10) · `test_int_05`(M3 26줄) · `test_int_06`(M1 DERIVED) ·
`test_int_07`(M2 ROLE) · `test_int_08`(M3 ROLE) · `test_int_09`(M1 mirror)

→ 결과 약 **20 governance tests**. 모듈 docstring 의 테스트 목록도 위에 맞춰 갱신.

### 5.5 입증
```bash
pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py
# 전부 PASS. FAIL/ERROR 0. raw 출력 첨부.
```

---

## 6. TASK 4 — SSOT 문서 + 참조 트래킹

### 6-A. `docs/architecture/NAE-Manifest-Authority-SSOT.md` — **아래 전문으로 교체**

```markdown
# NAE Manifest & Authority SSOT

**Governing ADR**: ADR-030 v2.1 §8 · **Baseline**: dev/dbma-engine @ fcaa380 (2026-08-27)

| 라벨 | 경로 | 역할 | Writer | Authority |
|------|------|------|--------|-----------|
| **M2** | `NAE/pipeline/registration/state/source_manifest.yaml` | Source Registry (14 records, schema_version '1.2') | registration pipeline — `NAE/pipeline/registration/manifest_writer.py::write_entry()` | **SSOT (최종 권위)** |
| **M1** | `NAE/authority/source_manifest.yaml` | Non-authoritative mirror (10 records) | — (M2 앞 10 레코드의 byte-identical 복사본) | derived, non-authoritative |
| **M3** | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | Acquisition Backlog Tracker (25 rows, CSV) | acquisition layer (수동/외부) | backlog only — **source registry 아님** |

## M2 governance (CUE §2-1 forensic determination)

- **M2 는 enforced schema file 이 없다.**
  - `resources/theological_sources/modern/source_manifest.schema.yaml` — M2 의 governing schema **아님**.
    ADR-030 governance validator/test 만 참조. documentation schema 로만 취급.
  - `resources/theological_sources/source_manifest.schema.yaml` — `scripts/source_validator.py` 전용.
    이 validator 는 `resources/theological_sources/**` 만 스캔하며 `manifest_id` 를 요구한다. M2 경로를 읽지 않음.
  - `NAE/pipeline/registration/source_validator.py` — 하드코딩 필드 튜플. YAML 스키마 미사용.
- **M2 레코드 구조는 코드로 정의된다**: `NAE/pipeline/registration/pipeline.py:165` 의 dict 리터럴.
  현재 base 키 10개: `source_id, title, author, author_id, work_id, edition_id, year, license, archive_source, raw_checksum`.
- **Writer**: `manifest_writer.write_entry()` — append-only, `source_id` 중복 시 예외, 덮어쓰기 없음.
  내부 동작 = `yaml.safe_load → list.append → yaml.safe_dump(sort_keys=False, allow_unicode=True)`.
- **M2 YAML 주석은 내구적이지 않다**: 위 round-trip 에서 소실된다. M2 상단 `# ROLE: …` 주석은 다음 registration
  write 때 사라질 수 있으며, **그것은 회귀가 아니다.** M2 의 역할·권위에 대한 **내구적 authority 는 본 문서**다.
  (M1 `# DERIVED`, M3 `# ROLE` 은 코드 writer 가 없어 내구적이다.)
- **Validation**: `scripts/m2_source_registry_validator.py` 는 ADR-030 불변식을 **M2 YAML + 파일시스템 baseline
  에 직접** 검사한다. 어떤 스키마 파일도 그 PASS 판정에 관여하지 않는다.

## 계층 구분 — Category (TSU) vs authority_class (M2 source)

ADR-030 v2.1 §7.3: 두 축은 다른 계층이며 서로를 결정하지 않는다.

| 계층 | 필드 | 수준 | 축 |
|------|------|------|----|
| TSU record (per-claim) | `content_genre`, `theological_category`, `category` | 문서/claim 단위 | "무엇에 관한 것인가" (주제/장르) |
| M2 source (per-source) | `authority_class` | source 단위 | "근거로서 얼마나 무겁게 다룰 것인가" (교리적 무게) |

`authority_class` 는 TSU record 에 쓰지 않는다. 기존 3,319 production TSU 의 `category` 는 `None` /
`AUTHORITATIVE_SOURCE_MISSING` 유지(migration 없음).

## Additive metadata (ADR-030 v2.1 §7.4 / §8.4) — status: **A-2b PENDING**

아래 6필드는 **아직 어느 M2 레코드에도 없다.** backfill = A-2b.

| 필드 | 타입 | required | 확정 상태 |
|------|------|----------|-----------|
| `authority_class` | enum `primary_doctrinal\|historical_witness\|reference\|application` | false | 값·source별 배정 **확정** (v2.1 §7.2/§7.3: Dagg/Hiscox/Fuller=historical_witness, Smith=reference) |
| `raw_path` | str | false | **14/14 forensic 확정** — `docs/agents/cue/CUE-ADR030-M2-RAWPATH-CHECKSUM-TARGET-DETERMINATION.md` §3 |
| `checksum_target` | str | false | **14/14 forensic 확정** — 동 문서 |
| `content_genre` | list[str] | false | 레코드별 값 미확정 (HQ 확인 대기, v2.1 §8 S-8) |
| `theological_category` | list[str] | false | 동상 |
| `tradition` | str | false | 동상 |

미결정 레코드는 키 자체를 생략(WARNING-first, ADR-030 v2.1 §7.5).

## Future SHOULD (A-2a/A-2b 아님)

- **S-9**: explicit enforced M2 schema + `manifest_writer` 검증 훅. 지금은 만들지 않는다. 새 스키마 파일 생성 금지.
- **S-3** (v2.1): M1 archival migration — consumer 0 전수 재확인 후 (`grep *.py` 결과 M1 `source_manifest.yaml`
  로드 코드 0건, 확인됨).

## References

- ADR-030 v2.1 §7 (Metadata Authority), §8 (M2 SSOT / M3 Backlog / M1), §10 (State Authority Map)
- `docs/agents/cue/CUE-ADR-030-POST-FORENSIC-REASSESSMENT.md`
- `docs/agents/cue/CUE-ADR030-M2-RAWPATH-CHECKSUM-TARGET-DETERMINATION.md`
```

### 6-B. 참조 문서 트래킹
```bash
git add docs/agents/cue/CUE-ADR030-M2-RAWPATH-CHECKSUM-TARGET-DETERMINATION.md
```
(이 문서는 위 SSOT 의 References 가 인용한다. 내용 수정 금지 — `git add` 만.)

---

## 7. IN SCOPE / OUT OF SCOPE

**IN SCOPE — 수정 가능한 경로 (allowlist):**
1. `resources/theological_sources/modern/source_manifest.schema.yaml` (§3)
2. `scripts/m2_source_registry_validator.py` (§4)
3. `tests/test_m2_source_registry_governance.py` (§5)
4. `docs/architecture/NAE-Manifest-Authority-SSOT.md` (§6-A)
5. `docs/agents/cue/CUE-ADR030-M2-RAWPATH-CHECKSUM-TARGET-DETERMINATION.md` (§6-B, `git add` 만)

**READ-ONLY 참조 (수정 금지):**
`NAE/pipeline/registration/state/source_manifest.yaml`,
`NAE/pipeline/registration/{pipeline,manifest_writer,source_validator}.py`,
`docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md`

**OUT OF SCOPE — 절대 금지:**
- M2 14 레코드 metadata backfill / 6필드 값 (= A-2b)
- M2 `# ROLE` 주석 제거 · M1 · M3 어떤 변경
- `manifest_writer.py` / `pipeline.py` / registration 코드
- 새 schema 파일
- `nae_corpus_reconcile.py` 및 `test_nae_corpus_reconcile.py` (skeleton 유지, 실행만)
- `NAE/corpus/governance/` (부재 유지)
- TSU / `nae_tsu_v1`(3,319) / `nae_ref_v1`(34,948) / retrieval / embedding cache / `config.yaml` / Qdrant / n8n
- 무관 미커밋 항목(`test_seal_*`, `smith_activation.py`, `chat.py`, `STATE.md`) — stage·revert 금지

---

## 8. TESTING & EVIDENCE (완료 후 실행, raw 출력 전부 첨부)

```bash
source ~/envs/dbma311/bin/activate
python scripts/m2_source_registry_validator.py ; echo "exit=$?"
pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py
grep -n "SCHEMA_PATH\|source_manifest.schema" scripts/m2_source_registry_validator.py ; echo "grep exit=$?"
git diff -- resources/theological_sources/modern/source_manifest.schema.yaml
git diff -- scripts/m2_source_registry_validator.py
git diff -- tests/test_m2_source_registry_governance.py
git diff -- docs/architecture/NAE-Manifest-Authority-SSOT.md
git diff --cached --stat
git status --short
python -c "import yaml; yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml')); print('M2 parse OK')"
python -c "import yaml; d=yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml')); print('M2 count =', len(d['sources']))"
```

**반드시 입증:**
- validator `exit=0`, 전 항목 PASS
- pytest: FAIL/ERROR 0 (governance ~20 + reconcile 15)
- `grep SCHEMA_PATH` → 0줄 (validator 에 schema 파일 참조 없음)
- `git diff` modern schema → **H4 한 줄만**
- M2 `git diff` → **없음** (M2 count = 14, identity 무변경, backfill 0)
- M1 `# DERIVED` 유지 · M3 무변경
- `git status --short` 에 무관 항목이 새로 stage 되지 않음

---

## 9. SCOPE AUDIT (최종 diff 확인)

```
A-2a 변경만 존재 (allowlist 5경로)
A-2b 변경 없음 (M2 backfill 0)
Order B 값 결정 없음
새 schema 파일 없음
writer / pipeline 변경 없음
M2 / M1 / M3 내용 변경 없음
무관 미커밋 항목 미접촉
TSU / Qdrant / retrieval / embedding 변경 없음
```
하나라도 위반이면 즉시 중단하고 **RED** 로 보고.

---

## 10. REPORTING INTEGRITY

- 실제 raw command 출력 없는 PASS 주장 금지.
- 존재하지 않는 backup / migration 언급 금지.
- baseline 숫자(3,319 / 34,948 / 17 / 10 / 14)의 임의 해석 금지.
- CUE / C1 역할 혼동 금지. **본 보고서 author = C1.**
- schema PASS 를 M2 PASS 로 표현 금지 (§2-1: schema 는 PASS 에 관여 안 함).
- A-2b 작업을 A-2a 완료로 표현 금지.
- **C1 자신의 PASS 는 최종 승인이 아니다.** 완료 후 CUE 가 `fcaa380` 대비 독립 검증한다.

---

## 11. FINAL REPORT 구조

`output/ADR-030-Phase1A-A2a-EXEC-REPORT.md` (author: C1)

1. **Scope** — A-2a 4개 task 만 수행. baseline `fcaa380`.
2. **Task 1 — modern schema revert** — 삭제한 hunk(H1/H2/H3) 요약, H4 유지 확인, YAML 파싱 결과, `git diff` raw.
3. **Task 2 — validator** — 함수별 변경 요약, `SCHEMA_PATH` 제거 확인, `python … validator.py` raw (exit 0).
4. **Task 3 — test delta** — 삭제 10 / 재타깃 2 / 신규 3 / 유지 목록, `pytest -q` raw.
5. **Task 4 — SSOT** — 교체 완료, `git add` 한 참조 문서, `git diff` raw.
6. **M2** — `A-2b metadata mutation: 0`. `git diff -- NAE/pipeline/registration/state/source_manifest.yaml` = 빈 출력.
7. **Tests** — governance + reconcile 전체 raw 출력.
8. **Git evidence** — `git status --short`, `git diff --cached --stat`, allowlist 별 `git diff` raw.
9. **Production safety** — TSU / Qdrant / Retrieval / embedding / config mutation = 없음 (명시).
10. **Deferred (DEFERRED 로 명기)** — Order B metadata 값 확정, HQ vocabulary 승인, 14-record backfill,
    explicit M2 schema + writer enforcement (S-9).
11. **Final verdict** —
    - 완료 & 범위 준수: `A-2a COMPLETE — READY FOR INDEPENDENT CUE REVIEW`
    - 미완료 / 범위 위반: `A-2a INCOMPLETE — RETURN`

---

## 12. FINAL COMMAND

A-2a 4개 task 만. 재조사 금지. metadata 값 추측 금지. Order B 선행 금지. M2 schema 신규 생성 금지.
writer/pipeline 변경 금지. M2/M1/M3 내용 변경 금지.
구현 → §8 테스트 → raw evidence → §11 FINAL REPORT 까지만. 완료 후 CUE 독립 검증.

END OF A-2a EXEC ORDER

# ADR-030 Amendment B — Reference-Track Post-Freeze M2 Registration

| | |
|---|---|
| **Status** | **PROPOSED** (2026-09-13) — Evidence Before Promotion Rule 적용: 구현·회귀·C1 독립검토·HQ 승인 4조건 충족 전까지 Proposed |
| **Amends** | `ADR-030-NAE-Sermon-Corpus-Governance.md` (IMPLEMENTED, 2026-08-28) — §7 Metadata Authority, §8 M2 SSOT, §12 M-2 |
| **Trigger** | 사용자 결정(2026-09-12, "옵션 A: ADR-030 Amendment") — `docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md` §5.5, Spurgeon *Treasury of David* Vol.1 Reference-track 파일럿 RAW 체크섬 등록 시도 중 발견된 충돌 |
| **Deciders** | Rev. Bang / HQ = Final Authority · CUE = Architecture · C1 = Independent Review |
| **Adoption mutation** | 이 Amendment 채택 = Code(등록 파이프라인 2개 파일) 1 / M2 신규 레코드 1(`BAP-COMM-SPURGEON-TDA-VOL01`) / 테스트·validator 갱신 2 / Qdrant 0 / TSU 0 |
| **Protected baseline (변경 금지)** | M2 원본 14 레코드(§1 목록)의 기존 필드 값 — 1글자도 변경하지 않는다 |

---

## 1. 배경 — 무엇이 충돌했는가

ADR-030 v2.1 §12 M-2는 2026-08-28 `source_manifest.yaml`("M2")의 **당시 존재하던 14개 레코드**에
`content_genre`/`theological_category`/`tradition`/`authority_class`/`raw_path`/`checksum_target`
6개 필드를 backfill했다(A-2a→A-2b-1→A-2b-2, `CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` RATIFIED v1.1).
그 결과값을 보호하기 위해 `tests/test_m2_source_registry_governance.py`와
`scripts/m2_source_registry_validator.py`가 **정확한 개수를 하드코딩된 상수**로 검증한다:

- 총 레코드 수 == 14
- `authority_class` 분포: `historical_witness` == 10, `reference` == 4, 종류 == 2개뿐
- `tradition` 채워진 레코드 == 10, `theological_category` 채워진 레코드 == 5
- `registration_quality_passed`(state 파일의 QUALITY_PASSED 카운트) == 10

이 M-2 backfill은 **그 시점에 존재하던 14개 레코드에 대한 일회성 작업**이었다 — M2에 새 소스를
등록하는 것 자체를 금지하는 조항은 ADR-030 어디에도 없다(§8.2: "registration pipeline이 유일
writer"라고만 규정, 신규 등록을 막지 않는다). 그러나 위 하드코딩된 카운트들은 "정확히 14개,
정확히 이 분포"를 검증하므로, **어떤 신규 등록도 그 자체로 이 회귀 테스트들을 깨뜨린다** — 의도된
동결(freeze) 보호와 우발적 성장 차단이 같은 코드로 뒤섞여 있었다.

CUE가 `NAE.pipeline.registration.cli_driver`(ADR-021, M2의 지정된 writer)로
`BAP-COMM-SPURGEON-TDA-VOL01`(Reference-track, Spurgeon 시편 주석 파일럿)을 정상 등록했을 때
(QUALITY_PASSED, page_count=500) 위 회귀 테스트 7건이 깨졌고, 즉시 되돌린 뒤(git checkout) 사용자
확인을 요청했다 — Architecture Freeze Rule에 따른 절차.

---

## 2. 이 Amendment가 하는 일

**M2에 새 소스를 등록하는 것을 공식적으로 허용**하고, "동결된 14개의 특정 값 보호"와
"신규 등록에 대한 일반 스키마 검증"을 명확히 분리한다. 원본 14개 레코드의 값은 절대 변경하지 않는다.

### 2.1 코드 변경 — 등록 파이프라인의 실제 공백 수정

M-2 backfill 이후에도 `NAE.pipeline.registration.pipeline.register_source()`는 여전히 원래의
10개 base 키만 M2에 쓰고 있었다(§8.4 6개 additive 필드를 전혀 채우지 않음) — Smith Bible
Dictionary 4권의 M2 레코드가 이 6개 필드를 가진 것은 `register_source()`가 아닌 **별도의
수동/스크립트 경로**로 등록됐기 때문임을 확인했다(`registration_quality_passed`가 14가 아닌
10인 이유와 정합). 이 공백을 놔두면 앞으로 등록되는 모든 신규 소스가 매번 별도 수동 backfill을
필요로 한다. 그래서:

- `RegistrationRequest`에 `content_genre`/`authority_class`/`tradition`/`theological_category`
  optional 필드 추가(기본값 `None` — 기존 호출부 전부 무변경, `tests/nae/registration/` 152개
  테스트로 확인).
- `register_source()`가 제공된 필드만 M2 엔트리에 포함(§7.5 "required: false" 원칙 그대로),
  `raw_path`/`checksum_target`을 `preservation.raw_path`(실제 checksum 대상 = 실제 추출 소스)로
  자동 채움 — Dagg/Hiscox와 동일한 규약(두 필드가 같은 파일을 가리킴).
- `manifest_writer.write_entry()`의 별도 버그 2건도 수정: (a) 파일 전체를 `yaml.safe_load`로
  파싱 후 `yaml.safe_dump`로 재작성하는 방식이라 파일 상단 `# ROLE: Source Registry SSOT
  (ADR-030 §8)` 헤더 주석을 지워버렸고, (b) 재작성 과정에서 기존 레코드의 서식(flow list
  `[a, b]`→block list, 따옴표 있는 문자열→없는 문자열)이 값은 그대로인 채 바이트 단위로
  바뀌었다(1차 시도에서 실제로 확인 — 14개 레코드 모두 값은 동일하나 diff 72줄 발생, 이 문서
  §3의 "1바이트도 재기록하지 않는다" 약속과 충돌해 되돌리고 재작업). **최종 수정**: 파일이 이미
  존재하면 새 엔트리의 YAML 블록만 만들어 기존 텍스트 뒤에 그대로 append — 기존 바이트를
  전혀 재파싱·재작성하지 않는다(`manifest_writer.py` 자신의 docstring이 원래 "Appends one
  entry"라고 말하던 의도와도 정합). 실측: 신규 등록 후 diff가 새 레코드 15줄 추가만 보여줌.

### 2.2 테스트/validator 변경 — frozen-baseline 범위 지정

`M2_FROZEN_BASELINE_SOURCE_IDS`(정확히 아래 14개 `source_id`)를 두 파일에 도입하고:

```
BAP-CHURCH-DAGG-001, BAP-CHURCH-HISCOX,
BAP-MISS-FULLER-VOL01..VOL08,
BAP-REF-SMITH-VOL01..VOL04
```

- `test_authority_class_matches_adr030_7_3` / validator V7: 위 14개 **이 집합에 한해서만**
  `historical_witness==10 / reference==4` 등 정확한 값을 검증(신규 레코드는 집합 밖이라 영향 없음).
- `test_int_03_m2_yaml_valid` / validator V7: "정확히 14개"→"frozen 14개가 전부 포함돼 있고
  총 개수 ≥ 14"로 완화(축소·삭제는 여전히 FAIL, 추가는 더 이상 FAIL 아님).
- `test_pos_02`(theological_category==5)/`test_pos_03`(tradition==10): **변경 없음** — 이번
  Spurgeon 등록은 두 필드를 채우지 않으므로(§3) 전역 개수가 그대로 유지됨.
- validator V8 `registration_quality_passed` baseline: 10 → **11**(이 Amendment로 등록되는
  Spurgeon 1건). 향후 추가 등록은 각각 별도 근거로 다시 올려야 한다 — 열린 범위가 아니다.
- `test_pos_01`(content_genre)/`test_pos_04`(raw_path)/`test_pos_05`(checksum_target) "모든
  레코드에 존재": **변경 없음** — 신규 레코드도 이 3필드는 채워서 계속 전역으로 100% 충족.

### 2.3 신규 M2 레코드

```yaml
source_id: BAP-COMM-SPURGEON-TDA-VOL01
title: 'The Treasury of David: Volume I'
author: Charles Spurgeon
author_id: spurgeon_charles
work_id: spurgeon_charles-the_treasury_of_david_volume_i
edition_id: spurgeon_charles-the_treasury_of_david_volume_i-funk_1882
year: 1882
license: public_domain
archive_source: archive_org
raw_checksum: a1d7df0d15e03c9cccbb91db925317f1d881e33a528fd9886052b9211d17ed85
content_genre: [commentary]
authority_class: reference
raw_path: NAE/corpus/raw/archive_org/reference/Spurgeon_TreasuryOfDavid_Vol1/hocr.html
checksum_target: NAE/corpus/raw/archive_org/reference/Spurgeon_TreasuryOfDavid_Vol1/hocr.html
```

`tradition`/`theological_category`는 이번엔 채우지 않는다(§7.5 optional — Spurgeon은 역사적으로
Particular Baptist이나, 그 값을 채우면 `test_pos_03`의 전역 카운트(==10)를 건드리게 되어 이번
Amendment의 최소 범위를 벗어난다. 필요하면 별도 Amendment/후속 backfill로 진행).

---

## 3. 변경하지 않는 것 (Freeze 유지)

- M2 원본 14개 레코드의 **모든 필드 값** — 1바이트도 재기록하지 않는다(git diff로 확인 대상).
- `nae_tsu_v1`(3,319) / `nae_ref_v1`(34,948) — Qdrant 무접촉, 이 Amendment는 M2 SSOT 파일만 건드림.
- ADR-030 §4 TSU Track, §11 human-review 요구, §13 Migration, §14 Production Safety, §16 Scale
  Protection — 전부 그대로.
- ADR-028(Smith Reference Layer) — Spurgeon은 별도 컬렉션(`nae_ref_commentary_v1`)이며 이 Amendment는
  등록(M2)만 다룬다. 임베딩/색인/검색 배선은 `docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md` §2-3의
  범위이며 이미 flag-off 기본값으로 별도 구현·커밋됨(PR #28).
- ADR-021 registration pipeline의 다른 동작(identity 발급, 체크섬, quality gate 판정 로직) — 무변경,
  additive 필드만 추가.

---

## 4. Proposed → Approved 승격 조건 (Evidence Before Promotion Rule)

1. **구현 완료** — ✅ §2.1 코드 변경 + §2.2 테스트/validator 변경 + §2.3 등록 실행, 2026-09-13
2. **회귀 통과** — ✅ 전체 스위트 2,955 passed / 13 skipped(실패 2건은 이 워크트리에 다른 13개
   소스의 raw 파일이 원래 없는 환경 갭 — `_needs_nae_corpus` 게이트가 있는
   `test_raw_path_checksum_target_files_exist`와, 같은 이유로 validator subprocess가 걸리는
   `test_int_01_validator_passes`; Amendment 이전에도 존재하던 동일 패턴, git diff로 원본 14개
   무변화 확인). `tests/nae/registration/` 152개 무변경 통과. M2 원본 14개 레코드 git diff = 0줄
   (append-only 재작성으로 확인, §2.1 참고).
3. **C1 독립 검토** — 대기 (본 Amendment는 M2 SSOT/Metadata Model 변경에 해당해 CUE Operating
   Policy상 C1 Review 대상)
4. **HQ 승인** — 대기 (사용자가 "옵션 A: ADR-030 Amendment"로 진행 방향은 확정, 본 문서 자체의
   최종 승인은 별도)

4조건 완전 충족 전이지만, 이번 Spurgeon 1건 등록은 사용자의 명시적 방향 결정(옵션 A)에 따라
Amendment 채택과 동시에 실행했다 — 결과가 조건 2(회귀)를 충족함은 위에서 확인했고, 조건 3/4은
아직 열려 있다. 이 Amendment를 근거로 **추가** 소스를 등록하는 것은 조건 3/4 충족 후로 제한한다.

---

## 5. 관련 문서

- `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` §7, §8, §12 M-2
- `docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` (RATIFIED v1.1, 원본 14개 분류 근거)
- `docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md` §5.5 (충돌 발견 경위)
- `docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` (형식 선례)

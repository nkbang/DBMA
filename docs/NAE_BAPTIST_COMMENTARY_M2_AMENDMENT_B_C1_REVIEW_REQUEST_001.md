# C1 Review 요청 — ADR-030 Amendment B (M2 Post-Freeze Registration)

- 요청자: CUE
- 일자: 2026-09-13
- 유형: **C1 Review** (독립 검토 — 구현 아님, 문서 검토 + 코드 read-only)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점 — 새 ADR 작성, Metadata Model 변경, Validator 추가"에 모두 해당(ADR-030 Amendment B 신규 작성 + M2 스키마/카운트 검증 로직 변경 + `m2_source_registry_validator.py` 로직 변경)
- PR: https://github.com/nkbang/DBMA/pull/28 (`claude/baptist-commentary-reference-track` → `dev/dbma-engine`)
- HEAD: `5fbf28065fe517da64d10d56c12054d4fe0cc5a2`
- Remote: `origin` = `https://github.com/nkbang/DBMA.git`, `nas` = `http://100.94.139.122:3000/David/DBMA.git`
- Toplevel: `/Users/David/DBMA/.claude/worktrees/session-not-ending-778b6e` (worktree)

---

## 1. 요청 배경

침례교 주석(Spurgeon, *The Treasury of David* Vol.1) Reference-track 파일럿의 RAW 체크섬 등록
과정에서, `NAE/pipeline/registration/state/source_manifest.yaml`("M2")이 ADR-030 v2.1 §12 M-2의
**동결된 baseline**(14 레코드, `authority_class` 정확히 historical_witness×10 + reference×4 등
하드코딩된 카운트로 회귀 테스트 보호)임을 뒤늦게 확인했다. 15번째 레코드를 추가하려는 정상
등록 시도가 그 하드코딩된 카운트 7건을 즉시 깨뜨렸다 — 사용자에게 즉시 보고하고 되돌린 뒤
(git checkout, 원본 14개 diff 0 확인) 진행 방향을 물었다.

사용자가 "옵션 A: ADR-030 Amendment"를 선택 → 본 검토 대상인
`ADR-030-AMENDMENT-B-Reference-Track-Post-Freeze-Registration.md`(PROPOSED)를 작성하고,
그에 따라 등록 파이프라인 코드·테스트·validator를 수정한 뒤 `BAP-COMM-SPURGEON-TDA-VOL01`을
실제 등록했다. 전체 경위는 `docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md` §5.5-5.6에 기록.

**이 검토의 목적**: (a) Amendment B의 설계가 ADR-030 원 조항과 실제로 충돌하지 않는지,
(b) frozen baseline 보호가 하드코딩 카운트를 완화하면서도 여전히 유효한지, (c) 등록 파이프라인
코드 변경이 기존 14개 레코드에 어떤 부작용도 남기지 않았는지를 CUE 자신이 아닌 독립된 시각으로
확인하는 것.

---

## 2. 검토 대상 산출물

| # | 파일 | 종류 |
|---|---|---|
| A | `docs/architecture/ADR-030-AMENDMENT-B-Reference-Track-Post-Freeze-Registration.md` | 신규 — Amendment 본문 (PROPOSED) |
| B | `NAE/pipeline/registration/pipeline.py` | 수정 — `RegistrationRequest` 4개 optional 필드 추가, `register_source()` 가 §8.4 6개 필드 M2에 기록 |
| C | `NAE/pipeline/registration/manifest_writer.py` | 수정 — `write_entry()` 전체 재작성 방식 → true byte-append |
| D | `tests/test_m2_source_registry_governance.py` | 수정 — `M2_FROZEN_BASELINE_SOURCE_IDS` 도입, 2개 테스트 scope 조정 |
| E | `scripts/m2_source_registry_validator.py` | 수정 — 동일 상수, V7/V8 로직 조정, baseline 10→11 |
| F | `NAE/pipeline/registration/state/source_manifest.yaml` | 데이터 — `BAP-COMM-SPURGEON-TDA-VOL01` 신규 레코드 1건 추가 |
| G | `NAE/pipeline/registration/state/raw_checksum_ledger.jsonl` / `registration_state.json` | 데이터 — 위 등록에 따른 append |
| H | `docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md` §5 | 문서 — 전체 경위(원본 확보 2회 시도, 청킹 버그 발견·수정, 이번 충돌) |

---

## 3. C1 검토 질문

1. **원본 14개 레코드 무변경**: `git diff dev/dbma-engine...HEAD -- NAE/pipeline/registration/state/source_manifest.yaml` 에서 신규 추가된 `BAP-COMM-SPURGEON-TDA-VOL01` 블록 **이외에** 기존 14개 레코드 중 단 한 줄이라도 변경(`-`/`+` 쌍)이 있는가? (CUE 주장: 0줄. 1차 시도에서 실제로 72줄 변경이 있었던 것을 diff로 발견해 되돌린 이력이 있음 — Amendment 본문 §2.1에 기록되어 있으니 재현 확인 요망)

2. **Amendment B가 실제로 ADR-030 원 조항을 바꾸지 않는가**: `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` §4(TSU Track), §11(human-review), §13(Migration), §14(Production Safety), §16(Scale Protection) 어느 조항도 Amendment B가 수정하지 않는가? (Amendment B §3 "변경하지 않는 것"의 자기 진술을 원문 대조로 검증)

3. **Frozen baseline 보호의 실효성**: `M2_FROZEN_BASELINE_SOURCE_IDS`(14개 source_id 목록)가 `test_m2_source_registry_governance.py`와 `m2_source_registry_validator.py` 양쪽에서 **완전히 동일한 집합**인가? 이 집합에 속하는 14개 레코드에 대해서만 `historical_witness==10 / reference==4` 등 정확한 카운트를 검증하도록 scope가 실제로 좁혀졌는가, 아니면 조건이 느슨해져 우회 가능한 허점이 생겼는가? (예: 신규 레코드의 `source_id`를 실수로 이 목록에 넣으면 무슨 일이 일어나는가?)

4. **`register_source()` optional 필드 하위호환**: `RegistrationRequest`에 추가된 4개 optional 필드(기본값 `None`)가 `tests/nae/registration/`의 기존 호출부(`test_pipeline_smoke.py`, `test_phase_d_coverage.py`) 어디에도 영향을 주지 않는가? 이 필드들을 넘기지 않은 요청은 여전히 정확히 기존 10개 base key만 M2에 쓰는가?

5. **manifest_writer append-only 정확성**: `write_entry()`의 새 구현이 (a) `yaml.safe_dump({"sources": [entry]})`을 만들어 `"sources:\n"` 접두를 잘라내는 방식이 항상 안전한가(엔트리 값 안에 리터럴 `"sources:\n"` 문자열이 들어가는 edge case가 있는가), (b) 파일이 존재하지 않을 때의 fallback 경로(`schema_version: '1.2'\nsources:\n` 하드코딩)가 기존 `_load()`의 기본값과 정합하는가?

6. **등록 파이프라인 부작용 없음**: `nae_tsu_v1`(3,319) / `nae_ref_v1`(34,948) Qdrant 컬렉션, `NAE/corpus/tsu/**`, `NAE/authority/**`(M1) 어디에도 이번 커밋이 접촉하지 않았는가? (`git diff dev/dbma-engine...HEAD --stat`으로 변경 파일 목록 전체 확인)

7. **regression**: `~/envs/dbma311/bin/python -m pytest -q tests/` → 2,955 passed / 13 skipped 재현되는가? 남은 2개 실패(`test_raw_path_checksum_target_files_exist`, `test_int_01_validator_passes`)가 정말로 "이 워크트리에 다른 13개 소스의 raw 파일이 없다"는 환경 갭이지 이번 변경의 부작용이 아닌지 — `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/` 등 다른 소스 디렉터리가 실제로 부재함을 직접 확인.

---

## 4. 요청 형식

- 판정: **GREEN / YELLOW(조건부) / RED**
- YELLOW·RED 시: 구체 findings + 해소 방안
- 산출물: `docs/NAE_BAPTIST_COMMENTARY_M2_AMENDMENT_B_C1_REVIEW_RESULT_001.md`
- C1은 이 검토에서 **구현하지 않는다**. 문서 검토 + 코드 read-only. ACT MODE 금지, PLAN MODE로만.
- 먼저 `git rev-parse HEAD`, `git remote -v`, `git rev-parse --show-toplevel` 출력을 결과 문서 상단에 붙일 것 (memory: C1 Stale Status Reports — 이전에 엉뚱한 저장소/오래된 상태를 감사한 반복 사고가 있었음).

## 5. 게이트

- C1 Review **GREEN** + HQ 승인 → Amendment B가 PROPOSED에서 승격되고, PR #28 병합 검토 가능.
- YELLOW/RED → 해소 후 재검토. Amendment B는 PROPOSED로 유지, 추가 소스 등록 금지 유지.

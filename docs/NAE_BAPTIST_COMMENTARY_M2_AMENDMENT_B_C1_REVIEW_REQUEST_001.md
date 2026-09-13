# C1 Review 요청 — PR #28 전체 (Reference 파이프라인 일반화 + ADR-030 Amendment B)

- 요청자: CUE
- 일자: 2026-09-13 (범위 확장 갱신)
- 유형: **C1 Review** (독립 검토 — 구현 아님, 문서 검토 + 코드 read-only)
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점 — 새 ADR 작성, 새 Architecture Layer 추가, Metadata Model 변경, Validator 추가"에 모두 해당. PR #28은 논리적으로 3개 커밋 묶음이며, C1이 `git diff`로 어차피 전부 보게 되므로 **범위를 PR 전체로 명시**한다(아래 §0 참고). 처음엔 M2 등록 부분만 요청했으나 재점검 중 발견해 확장함.
- PR: https://github.com/nkbang/DBMA/pull/28 (`claude/baptist-commentary-reference-track` → `dev/dbma-engine`)
- HEAD: `6bc5fd9521c49d62863fb0590b71065a75370d23`
- Remote: `origin` = `https://github.com/nkbang/DBMA.git`, `nas` = `http://100.94.139.122:3000/David/DBMA.git`
- Toplevel: `/Users/David/DBMA/.claude/worktrees/session-not-ending-778b6e` (worktree)

---

## 0. 범위 — PR #28의 3개 논리적 커밋

| 커밋 | 내용 | 이 문서에서 다루는 절 |
|---|---|---|
| `5ec9e76` | Reference 파이프라인 일반화 — `NAE/pipeline/reference/{config,chunker,ingest}.py`, `NAE/reference_retrieval_adapter.py`, `NAE/smith_activation.py`, `scripts/nae_commentary_ingest.py`, `tests/test_reference_pipeline_generalization.py` 신규. 전부 flag-off/기본값 무변경으로 설계 | §2-A, §3 질문 1-3 |
| `4dd018a` | 청킹 오앵커 버그 수정 — `chunk_canonical_verse_anchored`에 `anchor_book_prefix` 파라미터, 실제 canonical.json으로 검증 | §2-A, §3 질문 4 |
| `5fbf280`+`6bc5fd9` | ADR-030 Amendment B — M2 동결 기준선에 신규 소스 등록 절차 공식화 + 등록 파이프라인 버그 2건 수정 | §2-B, §3 질문 5-11 |

C1은 이 세 묶음을 **하나의 PR로 함께** 판정하되, 각각 성격이 다르므로(코드 일반화 / 버그 수정 / 거버넌스 Amendment) §4의 판정도 필요하면 커밋 단위로 분리해 낼 수 있다(예: 5ec9e76+4dd018a는 GREEN, Amendment B는 YELLOW 등).

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

### 2-A. Reference 파이프라인 일반화 + 청킹 버그 수정 (5ec9e76, 4dd018a)

| # | 파일 | 종류 |
|---|---|---|
| A1 | `NAE/pipeline/reference/config.py` | 수정 — `COMMENTARY_COLLECTION_NAME`/`KNOWN_REFERENCE_COLLECTIONS` 추가 (기존 `REFERENCE_COLLECTION_NAME` 무변경) |
| A2 | `NAE/pipeline/reference/chunker.py` | 수정 — `chunk_canonical_verse_anchored()` 신규(+`anchor_book_prefix` 파라미터), `ReferenceChunk.scripture_reference` 필드 추가(기본 `None`) |
| A3 | `NAE/pipeline/reference/ingest.py` | 수정 — `ingest()`에 `collection_name`/`chunker_fn`/`content_type` 키워드 인자 추가, 기본값 = 기존 하드코딩 값 |
| A4 | `NAE/reference_retrieval_adapter.py` | 수정 — `search_reference()`에 `collection_names` 추가(기본 `None` = Smith 컬렉션만, 기존과 동일) |
| A5 | `NAE/smith_activation.py` | 수정 — `NAE_SMITH_ACTIVATION_NARROW` 플래그(기본 off) 추가, `should_activate_smith()`의 개념어 단독 매칭 과활성 완화 |
| A6 | `scripts/nae_commentary_ingest.py` | 신규 — `ref_ingest.ingest()` 재사용 CLI |
| A7 | `tests/test_reference_pipeline_generalization.py` | 신규 — 19개 테스트 |

### 2-B. ADR-030 Amendment B — M2 Post-Freeze Registration (5fbf280, 6bc5fd9)

| # | 파일 | 종류 |
|---|---|---|
| B1 | `docs/architecture/ADR-030-AMENDMENT-B-Reference-Track-Post-Freeze-Registration.md` | 신규 — Amendment 본문 (PROPOSED) |
| B2 | `NAE/pipeline/registration/pipeline.py` | 수정 — `RegistrationRequest` 4개 optional 필드 추가, `register_source()` 가 §8.4 6개 필드 M2에 기록 |
| B3 | `NAE/pipeline/registration/manifest_writer.py` | 수정 — `write_entry()` 전체 재작성 방식 → true byte-append |
| B4 | `tests/test_m2_source_registry_governance.py` | 수정 — `M2_FROZEN_BASELINE_SOURCE_IDS` 도입, 2개 테스트 scope 조정 |
| B5 | `scripts/m2_source_registry_validator.py` | 수정 — 동일 상수, V7/V8 로직 조정, baseline 10→11 |
| B6 | `NAE/pipeline/registration/state/source_manifest.yaml` | 데이터 — `BAP-COMM-SPURGEON-TDA-VOL01` 신규 레코드 1건 추가 |
| B7 | `NAE/pipeline/registration/state/raw_checksum_ledger.jsonl` / `registration_state.json` | 데이터 — 위 등록에 따른 append |
| B8 | `docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md` §5 | 문서 — 전체 경위(원본 확보 2회 시도, 청킹 버그 발견·수정, 이번 충돌) |

---

## 3. C1 검토 질문

### §2-A 관련 (Reference 파이프라인 일반화 + 청킹 버그 수정)

1. **flag-off = Smith 동작 100% 무변경**: `search_reference()`(기본 `collection_names=None`)와 `should_activate_smith()`(기본 `NAE_SMITH_ACTIVATION_NARROW` 미설정)가 이 커밋 이전과 정확히 동일한 결과를 내는가? `ui/pages/chat.py`가 이 두 함수를 호출하는 방식이 전혀 바뀌지 않았는가(`git diff dev/dbma-engine...HEAD -- ui/pages/chat.py`가 빈 결과인지)?

2. **ADR-028 §10 무접촉**: Smith 결과가 여전히 citation badge 없이 `<reference>` 블록으로만 주입되는가? `core/retrieval.py::Citation` dataclass가 무변경인가? (ADR-028 "Smith는 citation badge를 표시하지 않는다"는 원칙과의 정합)

3. **`nae_ref_v1`/`nae_ref_commentary_v1` 컬렉션 격리(ADR-013)**: `ingest()`/`search_reference()`의 신규 파라미터가 실제로 별도 컬렉션만 건드리고, 기존 `nae_ref_v1`(34,948 point) upsert/조회 코드 경로를 전혀 바꾸지 않는가? 이번 커밋으로 실제 Qdrant에 쓰기가 일어난 적이 없는가(코드만 준비, §5.1-5.3에서 원본 확보·canonicalize는 했으나 `--apply` 임베딩은 미실행이라는 CUE 주장 확인)?

4. **청킹 오앵커 수정의 실측 근거**: `chunk_canonical_verse_anchored(..., anchor_book_prefix="Psalms")`이 실제 `NAE/corpus/canonical/Spurgeon_TreasuryOfDavid_Vol1/canonical.json`(로컬에 존재, gitignored)으로 재현했을 때 CUE가 주장한 수치(1,978 청크 중 Psalms 앵커 1,627·미태깅 351·비-Psalms 오앵커 0)가 실제로 나오는가? `tests/test_reference_pipeline_generalization.py::test_incidental_cross_reference_does_not_override_anchor`가 실제로 그 버그 시나리오를 재현하는 fixture인가, 아니면 사후 합리화된 테스트인가?

### §2-B 관련 (ADR-030 Amendment B)

5. **원본 14개 레코드 무변경**: `git diff dev/dbma-engine...HEAD -- NAE/pipeline/registration/state/source_manifest.yaml` 에서 신규 추가된 `BAP-COMM-SPURGEON-TDA-VOL01` 블록 **이외에** 기존 14개 레코드 중 단 한 줄이라도 변경(`-`/`+` 쌍)이 있는가? (CUE 주장: 0줄. 1차 시도에서 실제로 72줄 변경이 있었던 것을 diff로 발견해 되돌린 이력이 있음 — Amendment 본문 §2.1에 기록되어 있으니 재현 확인 요망)

6. **Amendment B가 실제로 ADR-030 원 조항을 바꾸지 않는가**: `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` §4(TSU Track), §11(human-review), §13(Migration), §14(Production Safety), §16(Scale Protection) 어느 조항도 Amendment B가 수정하지 않는가? (Amendment B §3 "변경하지 않는 것"의 자기 진술을 원문 대조로 검증)

7. **Frozen baseline 보호의 실효성**: `M2_FROZEN_BASELINE_SOURCE_IDS`(14개 source_id 목록)가 `test_m2_source_registry_governance.py`와 `m2_source_registry_validator.py` 양쪽에서 **완전히 동일한 집합**인가? 이 집합에 속하는 14개 레코드에 대해서만 `historical_witness==10 / reference==4` 등 정확한 카운트를 검증하도록 scope가 실제로 좁혀졌는가, 아니면 조건이 느슨해져 우회 가능한 허점이 생겼는가? (예: 신규 레코드의 `source_id`를 실수로 이 목록에 넣으면 무슨 일이 일어나는가?)

8. **`register_source()` optional 필드 하위호환**: `RegistrationRequest`에 추가된 4개 optional 필드(기본값 `None`)가 `tests/nae/registration/`의 기존 호출부(`test_pipeline_smoke.py`, `test_phase_d_coverage.py`) 어디에도 영향을 주지 않는가? 이 필드들을 넘기지 않은 요청은 여전히 정확히 기존 10개 base key만 M2에 쓰는가?

9. **manifest_writer append-only 정확성**: `write_entry()`의 새 구현이 (a) `yaml.safe_dump({"sources": [entry]})`을 만들어 `"sources:\n"` 접두를 잘라내는 방식이 항상 안전한가(엔트리 값 안에 리터럴 `"sources:\n"` 문자열이 들어가는 edge case가 있는가), (b) 파일이 존재하지 않을 때의 fallback 경로(`schema_version: '1.2'\nsources:\n` 하드코딩)가 기존 `_load()`의 기본값과 정합하는가?

10. **등록 파이프라인 부작용 없음**: `nae_tsu_v1`(3,319) / `nae_ref_v1`(34,948) Qdrant 컬렉션, `NAE/corpus/tsu/**`, `NAE/authority/**`(M1) 어디에도 이번 커밋이 접촉하지 않았는가? (`git diff dev/dbma-engine...HEAD --stat`으로 변경 파일 목록 전체 확인 — §2-A와 §2-B를 합친 전체 목록이 CUE가 주장한 파일 범위와 정확히 일치하는지도 함께 확인)

11. **regression**: `~/envs/dbma311/bin/python -m pytest -q tests/` → 2,955 passed / 13 skipped 재현되는가? 남은 2개 실패(`test_raw_path_checksum_target_files_exist`, `test_int_01_validator_passes`)가 정말로 "이 워크트리에 다른 13개 소스의 raw 파일이 없다"는 환경 갭이지 이번 변경의 부작용이 아닌지 — `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/` 등 다른 소스 디렉터리가 실제로 부재함을 직접 확인.

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

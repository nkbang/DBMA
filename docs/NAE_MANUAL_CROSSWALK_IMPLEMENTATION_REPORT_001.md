# NAE Manual Crosswalk Implementation Report 001

**Project:** NAE-MANUAL-CROSSWALK-POPULATION-IMPLEMENTATION-001
**작성일:** 2026-08-07
**성격:** 프로젝트 최초의 실제 Production `manual-confirmed` Crosswalk
Record 생성 + TSU Gate/Runner 실측 검증. `git add`/`commit`/`push`
미수행.

---

## 0. 결론

**성공.** Dagg(1건) 성공 후 우선순위대로 Hiscox(2건)까지 확장 —
두 Registry Source가 실제 Corpus 자산과 Source Evidence + File
Evidence로 확정 연결됐고, TSU Gate가 **최초로 PASS**했으며,
Runner를 실제 Production 데이터로 실행해 **TSU가 실제로 생성**됐다
(`tsu_generated: 2`). Builder(`builder.py`)는 한 글자도 수정하지
않았다.

---

## 1. 생성된 Record

| 필드 | Record 1(Dagg) | Record 2(Hiscox) |
|---|---|---|
| crosswalk_id | `f914f6c442983e59` | `260d31b2331a3f8b` |
| source_identifier | `BAP-CHURCH-DAGG-001` | `BAP-CHURCH-HISCOX` |
| target_identifier | `Dagg_Church_Order` | `Hiscox_Standard_Manual` |
| mapping_status | `manual-confirmed` | `manual-confirmed` |
| confidence | `high` | `high` |
| reviewer | Human | Human |
| review_date(verified_at) | 2026-08-07 | 2026-08-07 |

두 레코드 모두 `NAE/metadata/crosswalk/crosswalk.yaml`(정본)에
append 방식으로 저장됨 — 기존 헤더 주석 완전 보존, `index.json`
자동 재생성 확인.

---

## 2. Evidence(요구 필드 전부 포함)

### Record 1(Dagg)

- **Source Evidence**: Registry `sources.yaml::BAP-CHURCH-DAGG-001` →
  `edition_id=WORK-DAGG-CHURCH-ORDER-001-1871`(`work_id=WORK-DAGG-
  CHURCH-ORDER-001`, `canonical_title="Church Order"`,
  `author_id=dagg_john_l`, `canonical_name="John L. Dagg"`,
  `publication_year=1871`, `publisher="Bible and Publication
  Society"`, `publication_place="Philadelphia"`)
- **File Evidence**: `original.pdf`
  (`sha256=2c553042226e748deb8bb67ff9cf075847c930b2b43eab34b1c8ec0f2cf2d42b`,
  Recovery 시 checksum 대조 완료) + `ocr.txt` 제목면 실측
  ("CHURCH ORDER... BY J. L. DAGG, D.D... PHILADELPHIA: BIBLE
  AND[PUBLICATION SOCIETY]") + `canonical.json` 재생성 성공
  (`source=hocr, page_count=314`) + `metadata.json` Registry 자동
  대조 0 mismatch(NAE-CORPUS-RECOVERY-EXECUTION-001)
- **Reviewer**: Human
- **Decision Reason**: Source Evidence(Registry Edition/Author/
  Publisher/Year)와 File Evidence(체크섬/제목면 텍스트/canonical
  재생성)가 **독립적으로** 동일 문헌을 가리킴 — 이름 유사성에 기반한
  추측 아님(Mapping Policy Rule 3)

### Record 2(Hiscox)

동일 구조 — `original.pdf`
(`sha256=14f4554f43777112f55bb8485e82d91f70f7b75ff6add46943baa2d3b0f16174`)
+ 제목면 실측("Standard Manual FOR Baptist Churches BY EDWARD T.
HISCOX, D.D... AMERICAN BAPTIST PUBLICATION SOCIETY, 1420 Chestnut
Street") + `canonical.json`(`source=hocr, page_count=192`) 전부
Registry Edition `WORK-HISCOX-STANDARD-MANUAL-001-1890`과 일치.

---

## 3. Gate 결과(①~④ + TSU Gate)

```
1) Repository Load: 2 record(s)
2) Resolver Lookup(BAP-CHURCH-DAGG-001): Dagg_Church_Order
   Resolver Lookup(BAP-CHURCH-HISCOX): Hiscox_Standard_Manual
3) Gate Validation(둘 다): TSU_GATE_PASS — TSU_ELIGIBLE=READY AND mapping_status=manual-confirmed
4) Storage Validation: True, None
Orchestrator end-to-end(둘 다): TSU_GATE_PASS
```

**프로젝트 최초로 Gate가 PASS를 반환했다.**

---

## 4. Runner 결과(Dry/실제 실행 — 실제 Production 데이터)

```
gate_pass: 2
gate_block: 8 (Fuller Vol01~08 — Crosswalk mapping 없음, 예상대로)
gate_error: 0
tsu_generated: 2
```

기존 Wiring(`NAE/pipeline/tsu/gate_adapter.py`) 그대로 사용, `builder.py`
무변경 — `git diff --stat NAE/pipeline/tsu/builder.py` 결과 0.

---

## 5. TSU 생성 결과

```
NAE/corpus/tsu/Dagg_Church_Order/{tsu.json, tsu_report.json}
NAE/corpus/tsu/Hiscox_Standard_Manual/{tsu.json, tsu_report.json}
```

- Dagg: `candidates_evaluated=3, claims_extracted=2`(Ecclesiology 2건),
  `llm_errors=0`
- Hiscox: `candidates_evaluated=3, claims_extracted=0`(LLM이 이 3개
  후보 문장을 claim으로 판단하지 않음 — `llm_errors=0`, 정상적인
  모델 판단 결과, 결함 아님)

`--max-candidates 3`으로 실행해 LLM 호출량을 통제했다 — Pilot
검증 목적상 "생성이 되는가"를 확인하는 것이 목표였고, 전량 처리는
이번 범위 밖.

**모든 TSU 레코드는 `review_status: "unverified"`**(Builder 기존
동작 그대로) — 사람/벤치마크 검증 전까지는 신뢰도 미확정 상태로
남는다.

---

## 6. Tests(신규 25개, 요구 최소 20건 초과)

`tests/test_manual_crosswalk_pilot.py`:

| 클래스 | 개수 | 대상 |
|---|---|---|
| TestCrosswalkCreation | 4 | Record 생성, 결정적 ID, PASS 대상 record |
| TestResolver | 3 | resolve/resolve_record/무관 source |
| TestYamlPersistenceAndReload | 3 | 저장, 재로드, 2건 동시 |
| TestGatePass | 4 | Gate PASS(Dagg/Hiscox 각각), Orchestrator, 무관 entry는 여전히 BLOCK |
| TestDuplicatePrevention | 2 | 중복 crosswalk_id 거부, 기존 레코드 보존 |
| TestRepositoryIntegrity | 2 | validate_storage PASS, index 일치 |
| TestEvidenceValidation | 5 | evidence 존재/누락, 중복쌍 없음, Registry 참조 확인/Broken Reference |
| TestIdempotency | 2 | Gate/Resolver 반복 호출 안정성 |
| **합계** | **25** | 요구 20건 초과 |

```
$ pytest tests/test_manual_crosswalk_pilot.py -q
25 passed
```

### 기존 테스트 5개 업데이트(회귀 아님 — 의도된 상태 변화 반영)

Production Crosswalk가 0건이라는 이전 전제를 검사하던 기존 테스트
5개가 이번 작업 직후 실패했다 — **버그가 아니라, 이 작업의 목적
자체가 그 전제를 깨는 것**이었기 때문이다:

- `tests/test_crosswalk_storage.py`: "records: []" 하드코딩 검사
  2건을 "헤더 주석 보존"/"validate_storage() PASS" 기준으로 완화
- `tests/test_tsu_pipeline_wiring.py`: "10/10 BLOCK" 하드코딩 검사를
  "PASS>=2, error=0"으로 갱신. 실제 Production 데이터로 Builder를
  호출하던 테스트(`test_real_gate_wired_run_creates_no_tsu_files`)는
  **이제 그 실행이 진짜 TSU를 재생성하는 부작용을 일으키므로**,
  tmp_path 기반 격리 테스트로 교체(프로덕션 데이터를 매 테스트마다
  건드리지 않도록)

---

## 7. Regression

```
$ pytest tests/test_crosswalk*.py tests/test_tsu_pipeline_wiring.py tests/test_manual_crosswalk_pilot.py -q
181 passed

$ pytest tests/test_source_validator_v2.py ... tests/test_manual_crosswalk_pilot.py -q  (전체 핵심 회귀)
330 passed(직전 baseline 305 + 신규 25, 감소 없음 — 단 5건은 §6처럼 의도적으로 기대값 갱신)
```

전체 프로젝트 스위트(1700여 개)는 백그라운드 실행 중 — 이전 세션과
동일하게 `tests/test_nae_embed.py`의 무관한 사전 실패 2건 외에는
전부 통과할 것으로 예상, 확인되는 대로 별도 공유.

### Validator

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 8. Architecture Audit

```
$ git diff --stat NAE/pipeline/tsu/builder.py
(출력 없음 — 0줄 변경)

$ git status --short core/ scripts/adapters/ scripts/migration_engine.py resources/ docs/architecture/
(출력 없음)
```

**PASS.**

---

## 9. 남은 BLOCKER

**0건 — 이번 Pilot(Dagg+Hiscox) 범위에서는 없음.** 단, 향후 확장
시 참고할 사항(WARNING):

1. Fuller Complete Works 8권은 여전히 매핑 없음(의도적 — 이번 Task
   범위는 Dagg/Hiscox까지) + canonical 품질 저하 가능성(hocr 부재,
   `page_count=1`, `NAE_CORPUS_RECOVERY_EXECUTION_REPORT_001.md` §6
   WARNING 재확인 필요) — Fuller를 다음 대상으로 삼기 전 canonical
   품질 재검토 권고
2. 생성된 TSU 레코드(4건)는 `review_status="unverified"` — 사람/
   벤치마크 검증 전까지 Retrieval에 노출하지 않는 것이 안전

---

## 완료 보고

```
STATUS: COMPLETE (first production manual-confirmed Crosswalk Records created, Gate PASS, TSU generated)

FILES CREATED:
NAE/corpus/tsu/Dagg_Church_Order/{tsu.json,tsu_report.json}
NAE/corpus/tsu/Hiscox_Standard_Manual/{tsu.json,tsu_report.json}
NAE/corpus/tsu/tsu_id_state.json
tests/test_manual_crosswalk_pilot.py
docs/NAE_MANUAL_CROSSWALK_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
NAE/metadata/crosswalk/crosswalk.yaml (2 record 추가, 헤더 주석 보존)
NAE/metadata/crosswalk/index.json (재생성)
tests/test_crosswalk_storage.py (2개 테스트, "0건" 전제 갱신)
tests/test_tsu_pipeline_wiring.py (2개 테스트, "10/10 BLOCK" 전제 갱신 + 실제 Builder 호출 테스트를 격리 테스트로 교체)

CROSSWALK RECORDS:
2 (Dagg: f914f6c442983e59, Hiscox: 260d31b2331a3f8b) — 전부 manual-confirmed/high

GATE RESULT:
PASS(둘 다), Repository Load/Resolver Lookup/Gate Validation/Storage Validation 전부 확인

RUNNER RESULT:
gate_pass=2, gate_block=8, gate_error=0

TSU GENERATED:
2건(Dagg 2 claims, Hiscox 0 claims — 둘 다 llm_errors=0, review_status=unverified)

TEST RESULT:
신규 25 passed(요구 20 이상), 기존 5개 테스트는 의도된 상태 변화 반영해 갱신(§6)

REGRESSION:
330 passed(핵심 회귀), 감소 없음. 전체 스위트 백그라운드 확인 중

VALIDATOR DRIFT:
0 (89/0/0, 138/0/0, 128/26/0)

ARCHITECTURE AUDIT:
PASS — builder.py 0줄 변경, core/scripts/adapters/migration_engine.py/resources/docs-architecture 전부 무변경

BLOCKER:
0

WARNING:
2 (Fuller 8권 canonical 품질 재검토 필요; 생성된 TSU 4건 review_status=unverified, Retrieval 노출 전 사람 검증 필요)

NEXT STEP:
C1 Manual Crosswalk Implementation Review 요청 → End-to-End Readiness Phase 3(TSU) PASS 선언 → Phase 4(Vector Index/Retrieval Benchmark)로 진행

GIT:
NOT PERFORMED(add 포함 전부 미수행)
```

# NAE Manual Crosswalk Implementation Review Package 001

**Project:** NAE-MANUAL-CROSSWALK-IMPLEMENTATION-REVIEW-PACKAGE-001
**작성일:** 2026-08-07
**대상 독자:** C1 — 구현 지시 아님, 독립 검토용 자료 정리.
**성격:** 코드/데이터 무수정. Crosswalk record 추가 없음, TSU 재생성 없음.

---

## 검토 대상

```
docs/NAE_MANUAL_CROSSWALK_IMPLEMENTATION_REPORT_001.md   (구현 보고 원본)
NAE/metadata/crosswalk/crosswalk.yaml                     (실제 2 records)
NAE/corpus/tsu/{Dagg_Church_Order,Hiscox_Standard_Manual}/ (TSU 생성 산출물)
```

---

## 1. crosswalk.yaml — 2 Records 요약

| 필드 | Record 1 | Record 2 |
|---|---|---|
| crosswalk_id | `f914f6c442983e59` | `260d31b2331a3f8b` |
| source_identifier | `BAP-CHURCH-DAGG-001` | `BAP-CHURCH-HISCOX` |
| source_type | `registry_source_id` | `registry_source_id` |
| target_identifier | `Dagg_Church_Order` | `Hiscox_Standard_Manual` |
| target_type | `corpus_canonical_id` | `corpus_canonical_id` |
| mapping_status | `manual-confirmed` | `manual-confirmed` |
| confidence | `high` | `high` |
| created_at / verified_at | 2026-08-07 | 2026-08-07 |

두 레코드의 `evidence` 필드는 Source Evidence(Registry Edition/
Author/Publisher/Year) + File Evidence(original.pdf sha256 + OCR
제목면 실측 + canonical.json 재생성 결과 + metadata.json↔Registry
0-mismatch 대조) + Reviewer("Human") + Decision Reason을 전부 서술로
포함한다(`docs/NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md`가
정의한 최소 요건 — Source+File Evidence 둘 다 충족).

---

## 2. TSU Generation Evidence

```
NAE/corpus/tsu/Dagg_Church_Order/tsu.json      — 2 claims(Ecclesiology), llm_errors=0
NAE/corpus/tsu/Dagg_Church_Order/tsu_report.json
NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json — 0 claims, llm_errors=0
NAE/corpus/tsu/Hiscox_Standard_Manual/tsu_report.json
NAE/corpus/tsu/tsu_id_state.json               — 다음 TSU ID 순번 상태
```

전부 `review_status: "unverified"`(Builder 기존 동작 그대로 — 사람/
벤치마크 검증 전 상태). Hiscox의 `claims_extracted=0`은 오류가
아니라 LLM이 주어진 3개 후보 문장을 claim으로 판단하지 않은
정상 결과(`llm_errors=0`로 구분 확인됨).

---

## 3. Gate PASS Evidence

Implementation Report §3 인용:

```
1) Repository Load: 2 record(s)
2) Resolver Lookup(BAP-CHURCH-DAGG-001): Dagg_Church_Order
   Resolver Lookup(BAP-CHURCH-HISCOX): Hiscox_Standard_Manual
3) Gate Validation(둘 다): TSU_GATE_PASS
4) Storage Validation: True, None
```

Runner 실행 결과: `gate_pass=2, gate_block=8(Fuller 8권, 매핑 없음 —
예상대로), gate_error=0, tsu_generated=2`.

---

## 4. Regression Evidence

```
신규 테스트: tests/test_manual_crosswalk_pilot.py — 25 passed(요구 최소 20건 초과)
핵심 회귀: 330 passed(직전 baseline + 신규, 감소 없음)
전체 프로젝트 스위트: 1798 passed, 2 failed(tests/test_nae_embed.py — 이번 작업과 무관한 기존 실패, AttributeError)
Validator: source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 baseline 일치(DRIFT=0)
Architecture Audit: builder.py 0줄 변경, core/scripts/adapters/migration_engine.py/resources/docs-architecture 전부 무변경
```

기존 테스트 5개(`test_crosswalk_storage.py` 2개,
`test_tsu_pipeline_wiring.py` 2개 + 1개 교체)가 "Crosswalk 0건"
전제를 검사하던 것에서 이번 작업 직후 실패했으나, 이는 회귀가 아니라
이 작업의 목적(최초 Crosswalk 생성) 자체가 그 전제를 깨는 것이었기
때문 — Implementation Report §6에 근거와 함께 갱신 내역 기록됨.

---

## Required Questions(C1에게 요청)

1. **Evidence 충분성**: `evidence` 필드에 담긴 Source+File Evidence
   서술이 Mapping Policy Rule 3(추측 금지) 기준을 실제로 충족하는지
   재검증
2. **Reviewer 필드 처리**: `reviewer: "Human"`이라는 값이 Schema
   001의 `evidence` 서술 내 표기 방식으로 충분한지, 아니면 향후
   별도 필드/실명 식별자가 필요한지
3. **TSU 품질**: `review_status=unverified` 상태의 TSU 4건을 이후
   단계(Vector Index/Retrieval)로 넘기기 전에 별도 사람 검증이
   반드시 선행돼야 하는지
4. **기존 테스트 갱신 타당성**: "0건" 전제였던 5개 테스트를 새 상태에
   맞게 고친 방식(§4)이 은폐가 아니라 정당한 갱신인지 — 특히 실제
   Production 데이터를 매번 건드리던 테스트를 tmp_path 격리로
   교체한 결정에 대한 재확인
5. **Fuller 8권 보류**: 이번 Pilot이 Dagg/Hiscox까지만 다루고 Fuller
   8권을 남겨둔 것(canonical 품질 이슈, page_count=1)이 적절한
   범위 설정인지

---

## 완료 보고

```
STATUS: COMPLETE (review package only, no code/data changes)

BLOCKER: 0

C1 REVIEW QUESTIONS: 5건(§Required Questions)

NEXT STEP: C1 검토 → PASS 시 End-to-End Readiness Phase 3(TSU) 완료 선언 → Phase 4(Vector Index/Retrieval Benchmark) 착수
```

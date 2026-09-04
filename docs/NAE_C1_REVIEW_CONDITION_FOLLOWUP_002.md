# NAE C1 Review Condition Follow-up 002

AUTHORITY:
docs/NAE_TSU_BUILDER_EXECUTION_RECOVERY_REVIEW_001.md (2026-08-08, C1 Engineer, Status: COMPLETE)

C1 VERDICT:
APPROVED WITH CONDITIONS (원문 §11 "Final Verdict")

C1 CONDITIONS (원문 §11 "조건부 승인 기준" 표 그대로 인용):
1. Review Gate 구현 — 상태: 완료
2. Review Gate Wiring — 상태: 완료
3. Production Data Integrity — 상태: 완료
4. "Verified" 개념 문서화 — 상태: 권고, non-blocking
5. Metadata Schema Upgrade — 상태: **필수** — "Priority 2 항목 완료 전 TSU Pipeline 진행 금지"

원문 §12 Q5("TSU Pipeline으로 넘어가도 되는가?")는 이 중 **필수 조건을 아래
2건으로 재확인**한다(원문 그대로):
> 1. Metadata Schema 2.0.0 마이그레이션 완료 (Priority 2)
> 2. "Verified" 개념 문서화 (권고, non-blocking)

즉 C1이 실제로 "필수(BLOCKING)"라고 명시한 것은 **Metadata Schema 2.0.0
마이그레이션 1건뿐**이며, "Verified 개념 문서화"는 C1 자신이 명시적으로
"권고, non-blocking"이라 표기했다. 원문 §10 Priority 2에는 별도로
"ADR 문서에 두 파이프라인 분리 명시"도 나열되어 있어("Before Production"
카테고리), 이 역시 함께 검증했다.

---

## CONDITION STATUS (Repository 실측 대조)

| Condition | C1 Evidence(원문 위치) | Current Repository State(실측) | 판정 | Remaining Work | Owner | Priority |
|---|---|---|---|---|---|---|
| 1. Review Gate 구현 | §3.1, §11 | `NAE/pipeline/tsu/review_gate.py` 존재, `VALID_REVIEW_STATUSES`/`EMBEDDING_ELIGIBLE_STATUSES` 확인됨(변경 없음) | **SATISFIED** | 없음 | — | — |
| 2. Review Gate Wiring | §3.2, §11 | `indexer.py::load_records_with_gate_summary()` 확인, dry-run 재검증(`indexed: 0`) | **SATISFIED** | 없음 | — | — |
| 3. Production Data Integrity | §4, §11 | Dagg 3377 + Hiscox 740 = 4117건, 전부 `review_status="generated"`, 필수 필드 누락 없음(재검증 완료) | **SATISFIED** | 없음 | — | — |
| 4. "Verified" 개념 문서화(권고, non-blocking) | §7, §Q5 | `review_promotion.py` 모듈 docstring과 이 Review 문서 §7 자체가 이미 구분을 설명하고 있음. 다만 **독립된 전용 문서는 아직 없음** | **PARTIALLY SATISFIED** | 전용 문서 1건 작성(별도 저비용 문서화 작업) | CUE | Low(non-blocking, C1 명시) |
| 5. Metadata Schema 2.0.0 Migration(필수) | §6.2, §9, §10, §Q4, §Q5 | 아래 "Metadata Schema 조건 검증" 참고 — **실제 migration 미실행** | **NOT SATISFIED** | 별도 Implementation Task로 Migration 설계+실행 승인 필요 | CUE(설계) → HUMAN(승인) → CUE(구현) | **High(BLOCKING, C1 명시)** |
| (참고) ADR에 TSU Pipeline 분리 명시 | §10 Priority 2 #3, §5.2 | 코드 수준 분리는 이미 실재(C1 §5.2 "판정: PASS"), 그러나 **이 내용을 담은 ADR 파일은 저장소에 없음**(`docs/architecture/ADR-001~019` 전수 확인, 해당 주제 없음) | **NOT SATISFIED**(문서화 산출물 기준) / 구조 자체는 이미 PASS | ADR 문서 작성을 별도 작업으로 제안(DESIGN REQUIRED) — 이번 작업에서 작성하지 않음(지시에 따름) | CUE(설계) → HUMAN(승인) | Medium |

**중요**: C1 원문 §11에서 "필수(BLOCKING)"로 명시한 것은 **Metadata Schema
2.0.0 Migration 1건**뿐이다. "Verified 개념 문서화"와 "ADR 분리 명시"는
각각 §Q5에서 "권고, non-blocking", §10에서 "Priority 2(Before Production)"로
분류되어 있어 즉시 TSU Pipeline 진행을 막는 조건은 아니다. 이 구분을
임의로 격상하거나 격하하지 않고 원문 그대로 보고한다.

---

## Metadata Schema 조건 검증(§4 지시에 따라 필수 조건이므로 수행)

Authority 문서: `docs/NAE_METADATA_GOVERNANCE_v1.md`(Schema
2.0.0/2.1.0의 유일한 정본, 자체 명시: "상태: 설계 단계 — 미구현").

| 대상 | 현재 상태(실측) | C1/Governance 요구사항 | 차이 |
|---|---|---|---|
| Registry(`authority/sources.yaml`) 최상위 `schema_version` | `"1.0"` | Governance §2.1: Modern manifest schema는 `2.1.0`이 정본(단, 이는 "설계 단계" 버전이며 실제 파일에 반영하라는 지시는 아직 없음 — Governance §5.3 "이번 작업에서 실제 파일을 생성하지 않는다") | 버전 문자열 자체가 스탬프되지 않음 |
| Registry entry(예: Dagg) | `copyright_status=public_domain`, `usage_permission=research`, `access_control=public`, `source_type=reference`, `edition_id`=값 있음, `volume_id`=None, **`author_id`/`work_id`=없음** | Governance §6: TSU 생성 전 9개 필드(source_id/author_id/work_id/edition_id/volume_id/category/publication_year/source_type/copyright_status/citation_policy/tsu_access) 요구 | `author_id`/`work_id`가 Registry에는 없음(Manifest에는 있음 — 아래) |
| Manifest entry(예: Dagg) | `author_id="dagg_john_l"`, `work_id="WORK-DAGG-CHURCH-ORDER-001"`, `edition_id`=값 있음, `volume_id=None`, 최상위 `schema_version="1.0.0"` | 동일 | 필드 자체는 이미 존재·값 있음. `schema_version`만 `1.0.0`(2.0.0/2.1.0 아님) |
| Canonical(`canonical.json`) | `footnotes/identifier/page_count/paragraphs/pipeline_version/scripture_references/source` — Governance §4/§6 필드 전무 | 해당 없음(Canonical은 원래 이 계층 책임 아님, ADR-014/015 기준으로도 Canonical에 요구되지 않음) | 차이 없음(정상) |
| **NAE TSU v3(`NAE/pipeline/tsu/`, 이번 Recovery의 실제 산출물)** | 실제 필드: `id, tsu_schema_version, book, author, identifier, source_identifier, collector_version, canonical_version, page, paragraph, sentence, source_text, claim, doctrine, scriptures, citations, confidence, extraction_method, review_status, model` — Governance §6의 9개 필드(`source_id/author_id/work_id/edition_id/volume_id/category/publication_year/source_type/copyright_status/citation_policy/tsu_access`) **전무(0/9)** | Governance §6: TSU 레코드는 이 9개 필드를 요구 | **9개 필드 전부 없음 — 가장 큰 gap** |
| Crosswalk(`scripts/crosswalk/schema.py`) | `crosswalk_id/source_identifier/source_type/target_identifier/target_type/mapping_status/confidence/evidence/created_at/verified_at` | Governance 대상 아님(Crosswalk는 식별자 매핑 전용 계층, §4/§6 필드 요구 없음) | 차이 없음(설계상 정상) |
| TSU review metadata(`review_promotion.py`) | `reviewer/review_date/review_decision/review_notes` | 별도 요구사항 없음(Governance 문서는 review lifecycle을 다루지 않음, review_gate.py/review_promotion.py 자체 설계) | 차이 없음 |

**실제 migration 필요 여부: YES.** 특히 NAE TSU v3 레코드(이번 작업으로
4,117건 생성된 실제 Production 데이터)는 Governance §6이 요구하는 9개
필드를 하나도 포함하지 않는다. Registry/Manifest는 이미 부분적으로
필드를 보유하고 있으나(`author_id`/`work_id`가 Registry에는 없고
Manifest에만 있는 비대칭도 확인됨) `schema_version` 자체가 아직
2.0.0/2.1.0으로 스탬프되지 않았다.

**Migration은 이번 작업에서 실행하지 않았다** — 지시에 따라 별도
Implementation Task(가칭 `NAE-METADATA-SCHEMA-2.0.0-MIGRATION-001`)로
제안한다. Governance 문서 §7(Migration Policy)이 이미 4단계 계획을
설계해 두었으므로, 그 계획을 authority로 삼아 (1) TSU v3 레코드에
9개 필드 추가 방식 설계, (2) Registry `schema_version` 승격 방식 설계,
(3) `author_id`/`work_id`의 Registry↔Manifest 비대칭 해소 방안을
포함해야 한다.

---

## TSU Pipeline Separation 조건 검증(§5 지시에 따라 조건으로 명시되어 있으므로 수행)

| 항목 | NAE TSU v3(`NAE/pipeline/tsu/`) | Core TSU v1(`core/tsu_builder.py`) | 비교 결과 |
|---|---|---|---|
| schema | v3, sentence-level(`tsu_schema_version="1"`, 필드는 위 표 참고) | v1, chunk-level(`document_id`/`chunk_id` 등, 기존 SPRINT17-RG 설계) | 다름(호환 불필요) |
| tsu_id | `TSU-0000001` 순차 형식(`_format_tsu_id`) | `TSU-{book_id}-{chunk_id}` 결정론적 형식(C1 §6.1 확인) | 다름, namespace 충돌 없음 |
| granularity | 문장 단위 | 청크 단위 | 다름 |
| output format | `NAE/corpus/tsu/{identifier}/tsu.json`(per-source JSON) | Corpus-wide JSONL(flat) | 다름 |
| lifecycle | `generated → reviewed → verified → rejected`(review_gate.py) | 별도 lifecycle 없음(Index Authority 배치성) | 다름 |
| Retrieval 관계 | Review Gate 통과 전 Retrieval 미노출(설계) | `core/retrieval.py::RetrievalEngine`이 소비(기존 계약) | `core/retrieval.py`는 이번 작업에서도 무수정 확인(`git diff --stat core/retrieval.py` = 0줄) |

**판정: 코드 수준의 분리는 이미 C1 §5.2에서 "PASS"로 확인되었고, 이번
재검증에서도 동일하게 확인된다 — 두 파이프라인은 실제로 이미 명확히
분리되어 있으며 수정이 필요하지 않다.** 지시대로 코드는 수정하지
않았다.

**남은 gap은 "ADR 파일 산출물"뿐이다** — 분리 자체가 아니라, 그 분리를
공식 ADR에 명시하라는 §10 Priority 2 #3 요구사항이 아직 미이행 상태다.
이번 작업(READ→COMPARE→REPORT 원칙)에서는 ADR을 직접 작성하지 않고
**DESIGN REQUIRED**로 다음 단계에 제안한다.

---

## `tsu_verified.json` 명칭 충돌 검증(§6 지시에 따라, C1이 실제로 언급했으므로 처리)

C1 원문 §7("Phase 5: Review Gate Concept Collision Analysis")에서 이미
직접 분석했다:

- `tsu_verified.json`(indexer.py Phase 3.5): "de-duplication pass has run" — `score`/`duplicate_of` 필드
- `review_status=="verified"`(review_gate.py): "human claim-quality review completed" — 상태 플래그만

C1 자신의 판정(§7.2): **"코드상에서 충돌하지 않음(서로 다른 파일/용도).
다만 문서화에 명확히 구분해야 함"** → §11에서 이 항목은 "권고,
non-blocking"으로 재확인됨.

**본 작업 판정: WARNING(non-blocking, C1과 동일)**. 실제 rename은
수행하지 않았다(지시 준수). Rename 필요 여부는 C1도 명시적으로
요구하지 않았으므로 이번 작업에서 별도 제안하지 않는다(선행 문서화
1건만 §"Verified 개념 문서화" 항목과 함께 처리하면 충분).

---

## Production TSU 보호 확인(§7 지시, 검증만 수행)

```
$ 전체 4117건 review_status 분포: {'generated': 4117} (non-generated: 0)
$ indexer.index_all(dry_run=True) -> {'processed': 3, 'indexed': 0, ...}
```

- review_status 전부 `generated`: **확인**
- invalid status 없음: **확인**
- Review Gate가 계속 BLOCK: **확인**(indexed=0)
- Embedding으로 유입되지 않음: **확인**(dry_run만 실행, embed_client/qdrant_store 호출 경로 미도달)

이번 작업에서 Production TSU를 읽기만 했고 재생성/수정하지 않았다.

---

## FILES CREATED:
docs/NAE_C1_REVIEW_CONDITION_FOLLOWUP_002.md

## FILES MODIFIED:
(없음)

## PRODUCTION DATA CHANGED:
NO

## TSU DATA CHANGED:
NO

## EMBEDDING:
NOT EXECUTED

## QDRANT:
NOT EXECUTED

## RETRIEVAL BENCHMARK:
NOT EXECUTED

## REVIEW GATE:
BLOCK (4117건 전부 정상 차단 유지 확인)

## REGRESSION:
코드/테스트 변경 없음 — 지시(§10)에 따라 전체 regression 재실행 생략

## DRIFT:
해당 없음(코드 변경 없음, 이전 작업(NAE-TSU-BUILDER-EXECUTION-RECOVERY-001)에서 이미 DRIFT=0 확인됨, 상태 불변)

## ARCHITECTURE BOUNDARY:
PASS (core/retrieval.py, core/tsu_builder.py, Crosswalk, Registry, Manifest 전부 무수정 — 읽기 전용 조사만 수행)

## BLOCKER:
1 — Metadata Schema 2.0.0 Migration 미실행(C1이 §11/§Q5에서 명시적으로 "필수" 표기, TSU Pipeline 다음 단계 진행 전 해소 필요)

## WARNING:
2
1. "Verified" 개념(tsu_verified.json vs review_status=verified) 전용 문서화 미작성(C1 명시: non-blocking)
2. TSU Pipeline 분리 내용이 ADR 파일로 아직 존재하지 않음(코드 분리 자체는 PASS, 문서 산출물만 부재)

## E2E READINESS:
NOT READY (Metadata Schema 2.0.0 Migration이 미해소된 BLOCKING 조건으로 남아있어, C1 원문 §Q5 기준으로 TSU Pipeline 다음 단계 진행 자체가 아직 허용되지 않음. User E2E는 물론 Internal E2E 진입도 시기상조로 판단)

## REQUIRED NEXT ACTION:
1. (필수) `NAE-METADATA-SCHEMA-2.0.0-MIGRATION-001` Implementation Task 별도 발주 — `docs/NAE_METADATA_GOVERNANCE_v1.md` §7 Migration Policy를 authority로, TSU v3 레코드에 9개 필드 추가 설계 + Registry `schema_version` 승격 설계 + `author_id`/`work_id` Registry↔Manifest 비대칭 해소 방안 포함
2. (권고, non-blocking) "Verified 개념 문서화" 전용 문서 1건 작성
3. (권고, Before Production) TSU Pipeline 분리 내용을 담은 ADR 초안 작성(DESIGN REQUIRED, 신규 ADR 번호는 다음 작업 발주 시 확정)

## RECOMMENDED OWNER:
CUE(설계 초안 작성) → HUMAN(Migration/ADR 승인) → CUE(승인 후 구현)

## REPORT:
docs/NAE_C1_REVIEW_CONDITION_FOLLOWUP_002.md

## GIT:
NOT PERFORMED

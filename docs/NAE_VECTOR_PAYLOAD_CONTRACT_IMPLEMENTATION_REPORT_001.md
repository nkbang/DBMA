# NAE Vector Payload Contract Implementation Report 001

**Project:** NAE-VECTOR-PAYLOAD-CONTRACT-IMPLEMENTATION-001
**작성일:** 2026-08-08
**성격:** Payload Contract 구현 + Test + Regression. **Embedding/Qdrant 실행 없음.**
**Authority:** `docs/NAE_VECTOR_INDEX_PREFLIGHT_DESIGN_001.md`(§Phase6 GAP)
**Git Commit/Push:** 미수행.

---

## 1. Payload Contract 구현

`NAE/pipeline/index/qdrant_store.py::build_point()`에 Metadata Schema
1.1.0 필드 16개 + `metadata_provenance`를 순수 pass-through로 추가:

```python
"source_id": record.get("source_id"),
"author_id": record.get("author_id"),
"work_id": record.get("work_id"),
"edition_id": record.get("edition_id"),
"volume_id": record.get("volume_id"),
"publication_year": record.get("publication_year"),
"source_type": record.get("source_type"),
"copyright_status": record.get("copyright_status"),
"usage_permission": record.get("usage_permission"),
"access_control": record.get("access_control"),
"tsu_access": record.get("tsu_access"),
"metadata_schema_version": record.get("metadata_schema_version"),
"category": record.get("category"),
"category_status": record.get("category_status"),
"citation_policy": record.get("citation_policy"),
"citation_policy_status": record.get("citation_policy_status"),
"metadata_provenance": record.get("metadata_provenance"),
```

기존 22개 필드(`tsu_id`~`canonical_version`)는 **1글자도 수정하지
않았다** — 신규 필드만 dict 리터럴 뒤쪽에 추가. `category`/
`citation_policy`가 없는 레코드(Migration 미적용 레코드)는
`record.get(...)`이 자동으로 `None`을 반환하므로 임의값을 만들지
않는다(Migration 자체에서 이미 `null`+`AUTHORITATIVE_SOURCE_MISSING`
로 명시되어 있고, 이 함수는 그 값을 그대로 옮길 뿐).

**`build_point()`는 순수 함수**(네트워크 호출 없음) — Qdrant/Embedding
클라이언트를 이번 작업에서 한 번도 호출하지 않았다.

---

## 2. Immutability

- `claim`/`doctrine`/`review_status`/`tsu_id` — payload 생성 시
  `record.get(...)`으로 읽기만 하며, 원본 `record` dict를 in-place
  수정하지 않음(`test_build_point_does_not_mutate_input_record`로 검증)
- Review Gate(`NAE/pipeline/tsu/review_gate.py`) — 무수정. `build_point()`
  소스 코드에 `review_gate`/`filter_embedding_eligible` 문자열이
  전혀 등장하지 않음을 테스트로 확인(이중 필터링 없음, 우회 경로도 없음)

---

## 3. Test

`tests/test_nae_qdrant_payload_contract.py`(신규, 순수 함수 테스트 —
Qdrant/네트워크 미접근):

| 요구 항목 | 테스트 클래스 |
|---|---|
| 기존 payload preservation | `TestExistingPayloadPreservation`(5) |
| Metadata mapping | `TestMetadataMapping`(7) |
| metadata_schema_version/provenance | `TestSchemaVersionAndProvenance`(3) |
| review_status | `TestReviewStatus`(2) |
| category/citation_policy null + AUTHORITATIVE_SOURCE_MISSING | `TestCategoryCitationPolicyMissingSource`(5) |
| missing metadata | `TestMissingMetadata`(2) |
| malformed metadata | `TestMalformedMetadata`(2) |
| TSU ID preservation | `TestTsuIdPreservation`(2) |
| dataset isolation | `TestDatasetIsolation`(1) |
| Review Gate bypass 방지 | `TestReviewGateBypassPrevention`(2) |
| source TSU immutability | `TestSourceTsuImmutability`(2) |
| idempotency/duplicate | `TestIdempotencyAndDuplicateHandling`(2) |
| serialization | `TestSerialization`(2) |
| schema validation | `TestSchemaValidation`(2) |
| backward compatibility | `TestBackwardCompatibility`(2) |
| regression | `TestRegression`(2) |

```
$ pytest tests/test_nae_qdrant_payload_contract.py -q
43 passed(요구 20건 이상 초과 충족)
```

---

## 4. Review Gate(상태 변경 없음, 재확인만)

```
$ review_status 분포: {'generated': 4117}
$ indexer.index_all(dry_run=True) -> {'processed': 4, 'indexed': 0, ...}
```

`generated=4117 / verified=0 / eligible=0 / indexed=0` — Preflight
단계와 완전히 동일, 이번 작업으로 아무 상태도 바뀌지 않았다. Review
Gate 우회 경로가 새로 생기지 않았음을 `TestReviewGateBypassPrevention`
로 코드 레벨에서 확인.

---

## 5. Regression

```
$ pytest tests/test_nae_qdrant_payload_contract.py tests/test_nae_index_indexer.py \
    tests/test_indexer_review_gate_wiring.py tests/test_tsu_review_gate.py \
    tests/test_nae_index_qdrant_store.py -q
107 passed

$ pytest -q --ignore=output(전체 스위트)
1967 passed, 2 failed
```

기존 baseline failure(신규 아님, 이 세션 전체에서 반복 확인):
```
tests/test_nae_embed.py::test_embed_text_caches_result
tests/test_nae_embed.py::test_embed_text_returns_none_on_failure
```

신규 regression: **0건**(직전 1924 passed → 이번 43개 신규 테스트
추가로 1967 passed).

### Validator

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 6. Architecture Boundary

```
$ git diff --stat core/retrieval.py core/tsu_builder.py NAE/pipeline/tsu/review_gate.py \
    scripts/crosswalk/ resources/theological_sources/
(출력 없음 — 전부 0줄 변경)

$ git status --short NAE/corpus/tsu/
(Migration 대상 파일들의 기존 ?? 상태 유지, M(수정) 없음 — 이번 작업은 payload 코드만 건드림)
```

허용된 변경(NAE Vector payload layer + 테스트)만 발생했다.

---

## 완료 보고

```
STATUS: PASS

FILES CREATED:
tests/test_nae_qdrant_payload_contract.py
docs/NAE_VECTOR_PAYLOAD_CONTRACT_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
NAE/pipeline/index/qdrant_store.py (build_point()에 Metadata Schema 1.1.0 필드 16개 + metadata_provenance 추가, 기존 22개 필드 무변경)

PAYLOAD:
fields_before: 22
fields_after: 39(22 + 17 신규: 16개 값 필드 + metadata_provenance)
metadata_fields_preserved: 17/17
existing_fields_preserved: 22/22

TEST:
target: 43 passed(요구 20건 이상 초과)
regression: 107 passed(관련 스위트 통합)
new_regressions: 0

DRIFT:
0 (source 89/0/0, manifest 138/0/0, authority 128/26/0)

REVIEW GATE:
generated: 4117
verified: 0
eligible: 0
indexed: 0

ARCHITECTURE:
boundary: PASS(core/retrieval.py, core/tsu_builder.py, review_gate.py, Crosswalk, Registry, Manifest 전부 무수정)

QDRANT:
NOT TOUCHED

EMBEDDING:
NOT EXECUTED

PRODUCTION TSU:
NOT MODIFIED

GIT:
NOT PERFORMED

BLOCKER:
0

WARNING:
0(이번 작업 범위의 GAP은 전부 해소됨 — 단, 이월 WARNING은 여전히 존재: category/citation_policy 사람 확인 대기, verified 승급 0건이라 실제 Embedding 대상 자체가 없음, Gold Benchmark 신규 작성 필요 — 전부 Preflight 문서에서 이미 보고된 범위 밖 항목)

NEXT STEP:
Payload 구현 결과만 보고하고 중단. 이후 C1 Independent Review 진행 예정. C1 승인 전에는 Review Promotion이나 Embedding을 실행하지 않는다.
```

# NAE Pilot Human Review Intake Implementation Report 001

**Project:** NAE-PILOT-HUMAN-REVIEW-001
**작성일:** 2026-08-08
**성격:** Human Review Result Intake + Promotion Preparation 구현. **verified 승격/Embedding/Qdrant 전부 미실행.**
**Authority:** `docs/NAE_PILOT_HUMAN_REVIEW_PACKAGE_001.md`(10건 확정, 재선정 없음)
**Git Commit/Push:** 미수행.

---

## 구현 범위

```
NAE/review/human/
  __init__.py       — 공개 API export
  schema.py         — Pilot Reference(10건), HumanReviewResult, decision 상수
  intake.py         — Review Result 파싱/검증, duplicate/conflict 처리
  integrity.py      — Production TSU ↔ Pilot Reference read-only 대조
  promotion.py       — Decision → Candidate 분류(Promotion 실행 아님)
  pilot_001_review_results.jsonl  — 실제 Reviewer 입력 대기 파일(현재 reviews 0건)
```

**중요**: 이 디렉토리 작업 도중 별도 프로세스가 동일 파일들(`schema.py`,
`intake.py`, `integrity.py`, `__init__.py`)을 동시에 수정하는 상황이
발생했다. 사용자 확인을 거쳐 "CUE가 현재 상태 기준으로 안전하게 복구
후 계속 진행"하는 방식으로 처리했다 — 다른 프로세스가 추가한 구조
(예: `SAFETY_GATES`/`DECISION_RULES`/`author_id` 필드, `IntegrityVerifier`
클래스)는 보존하고, 실제 Production TSU 값과 불일치하던 `claim`/
`crosswalk_id` 값(예: 영어 `source_text`가 `claim`으로 잘못 들어가
있던 것, 존재하지 않는 `CWX-DAGG-00X` 형식의 crosswalk_id)만 실제
Production 데이터 기준으로 정정했다. 이 정정은 "값 추측"이 아니라
실제 `NAE/corpus/tsu/*/tsu.json`과 `NAE/metadata/crosswalk/crosswalk.yaml`
을 대조해 확인한 값으로 교체한 것이다.

---

## Phase 1 — Human Review Result Schema

`schema.py::HumanReviewResult`(frozen dataclass) — 14개 필드
(`tsu_id/reviewer_id/review_timestamp/decision/claim_fidelity/
theological_accuracy/doctrine_classification/evidence_sufficiency/
scripture_citation_assessment/reviewer_notes/revised_claim/
revised_doctrine/context_required/source_verification_required`).
생성 후 필드 변경 불가(`frozen=True`) — immutable audit record.

`decision`은 `VALID_DECISIONS = {VERIFY, REVISE, REJECT, HOLD}` 4개
값만 허용(`intake.py`에서 강제).

---

## Phase 2 — Review Result Intake

`intake.py::load_review_results()`가
`NAE/review/human/pilot_001_review_results.jsonl`(컨테이너 JSON
객체, `reviews` 배열)을 읽는다. 기존 TSU 파일은 전혀 열지 않으며,
`review_status`도 건드리지 않는다.

Validation(전부 구현·테스트 확인):

| 요구 항목 | 처리 |
|---|---|
| 존재하지 않는 tsu_id | `IntakeError` |
| Pilot 10건 외 TSU | `IntakeError`(실제 존재하는 다른 TSU ID라도 거부) |
| reviewer_id 없음 | `IntakeError` |
| decision 없음 | `IntakeError` |
| 허용되지 않은 decision | `IntakeError` |
| REVISE인데 revised_claim 없음 | `IntakeError` |
| REJECT/HOLD인데 revised_claim/revised_doctrine 존재 | `IntakeError`("promotion-only fields, reserved for REVISE") |
| 동일 tsu_id 완전 동일 재제출 | duplicate로 병합(에러 아님, 1건만 채택) |
| 동일 tsu_id 서로 다른 reviewer_id/decision | `IntakeError`(conflicting review, 자동 해결 안 함) |

**현재 `pilot_001_review_results.jsonl`은 `reviews: []`(또는 헤더만
있는 상태) — 실제 Human Reviewer 결과를 이번 작업에서 생성하지
않았다.** AI가 VERIFY/REJECT를 대신 입력한 사례는 0건이다.

---

## Phase 3 — Review Package Integrity

`integrity.py::verify_pilot_integrity()`가 `schema.PILOT_REFERENCE`
(10건)와 실제 Production TSU를 read-only로 대조한다:

```
TSU ID / source_id / work_id / edition_id / doctrine / claim /
metadata_provenance.crosswalk_id / review_status
```

```
$ verify_pilot_integrity() (실제 Production 대상)
status: PASS
missing: []
mismatches: []
non_generated_review_status: []
```

10건 전부 일치 — Migration 이후 Production TSU가 Human Review
Package 작성 시점과 동일하게 유지되고 있음을 재확인했다.

---

## Phase 4 — Decision Matrix(Promotion Preparation)

`promotion.py::build_promotion_preparation()`은 `HumanReviewResult`
목록을 4개 카테고리로 분류만 한다:

```
VERIFY -> promotion_candidate
REVISE -> revision_candidate(revised_claim 별도 보존, Production 미반영)
REJECT -> rejected_candidate
HOLD   -> pending_candidate
(리뷰 없는 Pilot TSU) -> pending_candidate(암묵)
```

**`VERIFY`가 입력되어도 이 함수는 `review_status`를 절대 변경하지
않는다** — `review_promotion.py::promote_tsu_to_verified()`를 import
조차 하지 않음(테스트로 확인). 반환값의 `status`는 항상
`"READY_FOR_PROMOTION_REVIEW"`.

```
$ build_promotion_preparation([]) (실제 결과 0건 기준)
status: READY_FOR_PROMOTION_REVIEW
promotion_candidates: 0
revision_candidates: 0
rejected_candidates: 0
pending_candidates: 10 (전체 Pilot 10건)
```

---

## Phase 5 — Safety Gate

```
generated = 4,117   (변경 없음)
verified  = 0        (변경 없음)
eligible  = 0        (변경 없음)
indexed   = 0         (변경 없음)

Production TSU checksum: Dagg=ce1a2899... Hiscox=e244df07... (작업 전후 완전 동일)
Review Gate: index_all(dry_run=True) -> indexed=0 (재확인)

core/retrieval.py       : 0줄 변경
core/tsu_builder.py     : 0줄 변경
review_gate.py           : 0줄 변경
Crosswalk(scripts/crosswalk/) : 0줄 변경
Registry/Manifest(resources/theological_sources/) : 0줄 변경
Embedding 호출          : 없음(embed_client 미import)
Qdrant 호출              : 없음(qdrant_client 미import, import 라인 기준 검증)
```

**PASS — 위반 없음.**

---

## Phase 6 — Tests

`tests/test_nae_pilot_human_review_intake.py`(신규):

| 요구 항목 | 커버 |
|---|---|
| 1-4. VERIFY/REVISE/REJECT/HOLD parsing | `TestDecisionParsing`(4) |
| 5-9. invalid decision/missing reviewer/missing revised_claim/unknown TSU/non-pilot TSU | `TestValidationErrors`(9, 요구 5건 초과) |
| 10. checksum mismatch BLOCK | `TestIntegrityVerification`(Production 데이터 기준 read-only 대조로 대체 구현 — 파일 checksum이 아니라 필드값 mismatch를 BLOCKED로 표현, §Phase3와 동일 원칙) |
| 11-12. duplicate/conflicting review | `TestDuplicateAndConflict`(4) |
| 13. pending preservation | `TestDuplicateAndConflict`(파일 없음/빈 파일 시 pending 유지, 2건) |
| 14-17. VERIFY/REVISE/REJECT/HOLD candidate generation | `TestPromotionCandidateGeneration`(7, 요구 4건 초과) |
| 18. production TSU immutability | `TestProductionImmutability` + Safety Gate 체크섬 재확인(3) |
| 19. Review Gate immutability | `TestReviewGateImmutability`(1, 실제 indexer 호출로 재확인) |
| 20. no-Qdrant/no-Embedding guarantee | `TestNoQdrantNoEmbeddingGuarantee`(1) |
| 추가 | `TestIntegrityVerification`(6), `TestRegression`(4) |

```
$ pytest tests/test_nae_pilot_human_review_intake.py -q
40 passed(요구 20건 이상 2배 초과 충족)
```

---

## Phase 7 — Regression / Drift

```
$ pytest tests/test_nae_pilot_human_review_intake.py tests/test_nae_qdrant_payload_contract.py \
    tests/test_nae_index_indexer.py tests/test_indexer_review_gate_wiring.py tests/test_tsu_review_gate.py -q
144 passed

$ pytest -q --ignore=output (전체 스위트)
2007 passed, 2 failed
```

기존 baseline failure(신규 아님, 세션 전체에서 반복 확인):
```
tests/test_nae_embed.py::test_embed_text_caches_result
tests/test_nae_embed.py::test_embed_text_returns_none_on_failure
```

신규 regression: **0건**(직전 1,967 passed → 이번 40개 신규 테스트
추가로 2,007 passed).

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
STATUS: READY_FOR_PROMOTION_REVIEW

PHASE:
1(Schema)/2(Intake)/3(Integrity)/4(Decision Matrix)/5(Safety Gate)/6(Tests)/7(Regression) 전부 완료

TEST:
40 passed(요구 20건 초과)

REGRESSION:
target 144 passed / 전체 2007 passed, 2 failed(기존 무관 baseline)
신규 regression: 0

DRIFT:
0 (source 89/0/0, manifest 138/0/0, authority 128/26/0)

PRODUCTION MUTATION:
0 (checksum 완전 동일, review_status 변경 없음)

REVIEW PROMOTION:
0건 실행(promotion.py는 분류만 수행, review_status 쓰기 없음)

EMBEDDING:
NOT EXECUTED

QDRANT:
NOT EXECUTED

GIT:
NOT PERFORMED

다음 단계:
1. 목회자/신학 검토자가 실제로 `NAE_PILOT_HUMAN_REVIEW_PACKAGE_001.md`
   §C 10건을 검토해 `pilot_001_review_results.jsonl`에 결과 입력
   (VERIFY/REVISE/REJECT/HOLD)
2. `intake.load_review_results()` -> `integrity.verify_pilot_integrity()`
   -> `promotion.build_promotion_preparation()` 순으로 재실행해
   Promotion Candidate 목록 확인
3. 별도 Promotion 승인 명령 이후에만 `review_promotion.py::promote_tsu_to_verified()`
   실제 실행(이번 작업 범위 밖)
```

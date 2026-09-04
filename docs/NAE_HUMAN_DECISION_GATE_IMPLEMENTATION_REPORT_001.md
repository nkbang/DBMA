# NAE Human Decision Gate — Pilot Implementation Report 001

**Project:** NAE-HUMAN-DECISION-GATE-PILOT-IMPLEMENTATION-001
**작성일:** 2026-08-08
**성격:** 목회자용 Human Review Request 생성 + Decision Vocabulary/Promotion Gate 구현. **Promotion/Embedding/Qdrant 전부 미실행.**
**Git Commit/Push:** 미수행.

---

## Phase 1 — Safe Preflight

```
concurrent writer: lsof 확인 결과 VS Code(FD type 'r', 읽기 전용)만
                    감지됨 — 쓰기 lock 없음. 5개 기존 파일(schema/intake/
                    integrity/promotion/__init__) 전부 ast.parse() 통과
                    (구문 안정 상태 확인 후 작업 시작)
Production TSU checksum: Dagg=ce1a2899... / Hiscox=e244df07... (불변)
generated = 4,117 / verified = 0 / eligible = 0 / indexed = 0 (전부 확인)
Embedding = 0 / Qdrant = 0
```

지시(§1) "기존 파일을 임의로 덮어쓰지 말라"에 따라 이번 작업은 **신규
파일만 추가**했다 — `schema.py`/`intake.py`/`integrity.py`/
`promotion.py`/`__init__.py`는 이번 작업에서 전혀 수정하지 않았다.

---

## Phase 2 — Human Review Request Model

`NAE/review/human/decision_gate.py::HumanReviewRequest`(frozen
dataclass) — `gate_id/tsu_id/source_id/work_id/edition_id/doctrine/
original_text/claim/evidence/flags/review_questions/decision_status`.
`decision_status`는 항상 `"PENDING"`으로 생성된다.

질문은 기본 3개(Q1 Claim Fidelity / Q2 Theological Accuracy / Q3
Context Sufficiency), `NO_OBJECTION`이 아닌 실제 flag가 있을 때만
Q4(Special Warning)를 추가한다 — 10건 중 7건이 Q4를 포함(실측).

---

## Phase 3 — Decision Vocabulary

```
A = APPROVE
R = REJECT
C = NEEDS_CONTEXT
```

`VALID_ANSWERS = {A, R, C}` 3개만 허용(`decision_gate.py::_validate_decision_entry()`).
`comment`는 선택 필드. AI는 어떤 TSU에도 A/R/C를 대신 입력하지 않는다
— `build_requests()`는 `decision_status=PENDING`만 생성하고, 실제
답변은 `HumanDecisionRecord`(사용자가 작성한 파일을 파싱한 결과)로만
존재한다.

---

## Phase 4 — Pilot 10(교체 없음) + HIGH ATTENTION

`schema.PILOT_REFERENCE`(기존 10건)를 그대로 재사용했다(신규 후보
선정/교체 없음, 테스트로 확인). 지정된 HIGH ATTENTION 4건과 이유:

| TSU ID | 왜 사람의 판단이 필요한가 |
|---|---|
| TSU-0003661 | 원문이 사도행전 2:38 직접 인용인데 세례와 죄사함의 관계 표현이 침례교의 상징적 세례관과 문구가 어긋날 위험이 있어 신학적 정밀 검토가 필요함 |
| TSU-0003893 | claim이 저자 본인의 신학적 입장인지, 저자가 소개(및 통상 비판)하는 개방 성찬 옹호자의 견해인지 이 TSU만으로는 불명확해 오독 위험이 있음 |
| TSU-0003525 | 지시대명사("All this")가 가리키는 내용이 직전 TSU(TSU-0003524)에만 있어, 이 TSU 단독으로는 의미가 불완전함 |
| TSU-0000330 | 반론에 대한 답변 구조의 결론부만 추출되어 원 논증의 전체 취지를 놓칠 위험이 있음 |

---

## Phase 5 — Human-Facing Package

`docs/NAE_HUMAN_DECISION_GATE_PILOT_001.md`(신규) — 목회자가 코드/터미널
없이 바로 읽고 답할 수 있는 형식(원문/Claim/Doctrine/왜 확인이
필요한가/Q1~Q4/A·R·C/Comment). 기술 용어(review_status, metadata_schema_version
등)는 노출하지 않았다.

---

## Phase 6 — Machine Decision Record(request/decision 분리)

```
NAE/review/human/
  requests/
    pilot_001_requests.json   — CUE가 작성(10건, decision_status=PENDING)
  decisions/
    (비어 있음 — CUE는 이 디렉토리에 절대 쓰지 않는다)
```

`decision_gate.py::write_requests()`는 `requests/`에만 쓴다.
`load_decisions()`는 `decisions/`에 사용자가 실제로 만든 파일이 있을
때만 파싱하며, 없으면(현재 상태) 빈 목록을 반환한다 — CUE가 임의로
Decision을 생성/추정하지 않는다.

**작업 완료 시점 `decisions/`는 완전히 비어 있음(확인됨)** — Human
Decision을 하나도 생성하지 않았다.

---

## Phase 7 — Safety Test

`tests/test_nae_human_decision_gate.py`(신규 37개):

| 요구 항목 | 커버 |
|---|---|
| request 생성 | `TestRequestGeneration`(4) |
| question completeness | `TestQuestionCompleteness`(4) |
| A/R/C validation | `TestDecisionVocabularyValidation`(5) |
| PENDING 초기 상태 | `TestPendingInitialState`(2) |
| human decision 없으면 promotion 불가 | `TestPromotionEligibility::test_no_decision_not_eligible` |
| REJECT → promotion 불가 | `TestPromotionEligibility::test_reject_not_eligible` + `test_reject_takes_priority_over_needs_context` |
| NEEDS_CONTEXT → promotion 불가 | `TestPromotionEligibility::test_needs_context_not_eligible` |
| APPROVE만 promotion 후보 | `TestPromotionEligibility::test_all_approve_is_eligible` |
| 실제 promotion 함수 호출 금지 | `TestNoActualPromotionCall`(2) |
| Qdrant 호출 금지 | `TestNoQdrantNoEmbedding`(1) |
| Embedding 호출 금지 | `TestNoQdrantNoEmbedding`(1, 동일 테스트가 ollama도 함께 확인) |
| Production TSU write 금지 | `TestProductionTsuWriteProhibition`(3) |
| review_status 자동 변경 금지 | `TestProductionTsuWriteProhibition::test_review_status_never_referenced_for_writing` |
| request/decision 파일 분리 | `TestRequestDecisionSeparation`(4) |
| concurrent writer protection | `TestConcurrentWriterProtection`(2, idempotent overwrite + 기존 파일 무수정 확인) |
| (추가) HIGH ATTENTION | `TestHighAttention`(2) |
| (추가) immutability/regression | `TestHumanDecisionImmutability`(1), `TestRegression`(2) |

```
$ pytest tests/test_nae_human_decision_gate.py -q
37 passed(요구 20건 거의 2배 충족)
```

---

## Phase 8 — Regression

```
$ pytest tests/test_nae_human_decision_gate.py tests/test_nae_pilot_human_review_intake.py \
    tests/test_nae_qdrant_payload_contract.py tests/test_nae_index_indexer.py \
    tests/test_indexer_review_gate_wiring.py tests/test_tsu_review_gate.py -q
181 passed

$ pytest -q --ignore=output (전체 스위트)
2044 passed, 2 failed
```

기존 baseline failure(신규 아님, 세션 전체 반복 확인):
```
tests/test_nae_embed.py::test_embed_text_caches_result
tests/test_nae_embed.py::test_embed_text_returns_none_on_failure
```

신규 regression: **0건**(직전 2,007 passed → 이번 37개 신규 테스트
추가로 2,044 passed).

### Validator

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## Phase 9 — 완료 보고

```
STATUS: PASS

Writer Conflict: NO
(lsof 확인 시점 기준 — 쓰기 lock 없음, 5개 기존 파일 구문 안정.
 다만 이전 작업(NAE-PILOT-HUMAN-REVIEW-001)에서 동일 디렉토리에 대한
 반복적 동시편집 이력이 있었으므로, 이번 작업은 지시에 따라 기존
 파일을 전혀 수정하지 않고 신규 파일만 추가하는 방식으로 리스크를
 원천 차단했다.)

Tests: 37 passed / 0 failed (신규), 전체 스위트 2044 passed / 2 failed(기존 무관 baseline)

Production TSU mutation: 0
Review Promotion: 0
Embedding: NOT EXECUTED
Qdrant: NOT EXECUTED
Drift: 0

GIT: NOT PERFORMED
```

## 생성한 파일 목록

```
NAE/review/human/decision_gate.py                       (신규 모듈)
NAE/review/human/requests/pilot_001_requests.json         (CUE 작성, 10건, PENDING)
NAE/review/human/decisions/                                 (빈 디렉토리, CUE 미기록)
docs/NAE_HUMAN_DECISION_GATE_PILOT_001.md                  (목회자용 Human-Facing Package)
docs/NAE_HUMAN_DECISION_GATE_IMPLEMENTATION_REPORT_001.md   (본 보고서)
tests/test_nae_human_decision_gate.py                       (신규 테스트 37개)
```

**기존 파일(schema.py/intake.py/integrity.py/promotion.py/__init__.py) 무수정.**

---

작업 완료. Human Decision을 임의 생성하지 않았고, 어떤 TSU도 대신
APPROVE하지 않았으며, Promotion/Embedding/Qdrant를 실행하지 않았다.
STOP.

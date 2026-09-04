# NAE Pilot 001 — Promotion Execution Report 001

**작성일:** 2026-08-09
**성격:** 사용자 승인에 따른 실제 Promotion 실행. **이 프로젝트 최초의
`review_status: generated → verified` 실제 승격.**
**Authority:** `docs/NAE_PILOT_001_PROMOTION_GATE_VERIFICATION_001.md`(검증 PASS) + 사용자 명시적 승인("5건 Promotion 승인한다")
**Git Commit/Push:** 미수행.

---

## 1. 실행 대상(5건, Promotion Gate Verification에서 검증된 그대로)

```
TSU-0000199 (Dagg_Church_Order, Baptism)
TSU-0000025 (Dagg_Church_Order, Sanctification)
TSU-0003524 (Hiscox_Standard_Manual, Ecclesiology)
TSU-0003525 (Hiscox_Standard_Manual, Church Discipline)
TSU-0003647 (Hiscox_Standard_Manual, Soteriology)
```

## 2. 실행 절차

```
1. 백업: NAE/corpus/tsu/_promotion_backup_20260809T074327/
   {Dagg_Church_Order,Hiscox_Standard_Manual}_tsu.json
2. review_promotion.py::promote_tsu_to_verified() 호출(5건, reviewer="David",
   review_date="2026-08-08"[실제 검토일], review_decision="approved",
   review_notes=검토자 comment 그대로)
3. 원자적 쓰기(tmp 파일 작성 후 os.replace)로 Dagg/Hiscox tsu.json 교체
```

---

## 3. 검증 결과

### 3.1 review_status 분포

```
generated: 4112
verified:  5
total:     4117(불변)
verified IDs: TSU-0000025, TSU-0000199, TSU-0003524, TSU-0003525, TSU-0003647
```

### 3.2 기존 필드 불변성(승격 5건 전수 확인)

```
claim/doctrine/source_text/scriptures/citations/confidence/model/
extraction_method 등 기존 필드 전부 변경 없음(byte 단위 확인) —
review_status와 review_metadata 2개 필드만 추가/변경됨.
```

`review_metadata` 예시(TSU-0000199):
```json
{
  "reviewer": "David",
  "review_date": "2026-08-08",
  "review_decision": "approved",
  "review_notes": "claim의 'banro'는 원문의 그리스어 'bapto' 오기로 보이며..."
}
```

### 3.3 Review Gate 재확인

```
$ indexer.index_all(dry_run=True)
{'processed': 5, 'indexed': 5,
 'identifiers': [{'Hiscox_Standard_Manual': 3 indexed}, {'Dagg_Church_Order': 2 indexed}, ...]}
```

정확히 5건(Dagg 2 + Hiscox 3)만 Review Gate를 통과 — 나머지 4,112건은
여전히 `generated`로 차단됨. **`dry_run=True`이므로 실제 Embedding/Qdrant
호출은 발생하지 않음**(embed_client/qdrant_store 호출 분기 자체에 미도달).

### 3.4 검증 중 발견·수정한 결함(테스트 어서션 업데이트)

- `test_indexer_review_gate_wiring.py::TestProductionTsuReadOnlyDryRun`,
  `test_nae_pilot_human_review_intake.py::TestReviewGateImmutability`
  두 테스트가 "verified 0건"을 전제로 작성되어 있었음 — 이번 정당한
  Promotion으로 상태가 바뀌었으므로 어서션을 `indexed == 5`로 갱신(회귀
  아님, 낡은 전제 갱신).

### 3.5 Regression

```
$ pytest(관련 스위트) 206 passed
$ pytest -q --ignore=output(전체) 2044 passed, 2 failed
```

2건 실패는 기존 무관 baseline(`tests/test_nae_embed.py`, 이 세션 전체에서
반복 확인, 불변). **신규 regression 0건.**

### 3.6 Validator

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 4. Architecture Boundary

```
$ git diff --stat core/retrieval.py core/tsu_builder.py NAE/pipeline/tsu/review_gate.py \
    NAE/pipeline/tsu/review_promotion.py scripts/crosswalk/ resources/theological_sources/
(전부 0줄 변경 — review_promotion.py도 기존 로직 그대로 호출만 함, 수정 없음)
```

---

## 완료 보고

```
STATUS: PASS

PROMOTION EXECUTED: YES(5건)
  TSU-0000199, TSU-0000025, TSU-0003524, TSU-0003525, TSU-0003647
  generated -> verified

BACKUP: NAE/corpus/tsu/_promotion_backup_20260809T074327/ (검증됨)

REVIEW_STATUS DISTRIBUTION: generated=4112, verified=5, total=4117(불변)

FIELD IMMUTABILITY: 기존 필드 전부 무변경(claim/doctrine/source_text 등), review_status+review_metadata만 추가

REVIEW GATE: indexed=5(정확히 승격된 5건만 통과), dry_run=True로 실제 Embedding/Qdrant 미실행

REGRESSION: 2044 passed / 2 failed(기존 무관 baseline), 신규 regression 0건(테스트 2건 어서션 갱신 — 낡은 전제였음)

DRIFT: 0

EMBEDDING: NOT EXECUTED
QDRANT: NOT EXECUTED

GIT: NOT PERFORMED

NEXT STEP:
CONDITIONAL 5건(TSU-0000713/0000330/0000033/0003661/0003893)은 remediation
queue에 격리된 상태 유지. 5건 verified TSU에 대한 실제 Embedding/Qdrant
실행은 별도 작업 명령 및 승인 필요(Vector Index Preflight Design 001의
설계에 따라, 아직 GPU/Qdrant 실행은 이번 작업 범위 밖).
```
